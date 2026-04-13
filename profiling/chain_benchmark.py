"""Manifest-driven Generator -> Validator -> Retry chain benchmark runner.

Manifest-only mode:
- only accepts `run_manifest.json`
- only reads the `chain_benchmark` section
- does not define fallback fields or default execution parameters
- keeps retry and validator rules unchanged
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in (None, ""):
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

import config
from rich.console import Console
from profiling.prompts import build_generator_prompts, build_validator_prompts
from src.llm_client import LLMClient

PROFILE_ROOT = config.PROJECT_ROOT / "profiling"
RAW_LOG_DIR = PROFILE_ROOT / "output" / "raw_logs"
console = Console()


@dataclass(frozen=True)
class ManifestBundle:
    """Normalized manifest inputs."""

    run_name: str
    generator_models: list[str]
    validator_model: str
    max_retry_count: int
    cases: list[dict[str, Any]]
    raw_log_dir: Path
    provider: str
    api_key: str
    base_url: str
    generator_temperature: float
    validator_temperature: float
    max_tokens: int
    request_timeout: float


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```json"):
        stripped = stripped[7:]
    elif stripped.startswith("```"):
        stripped = stripped[3:]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()


def _parse_json_text(content: Any) -> tuple[bool, Any, str | None]:
    """Parse strict JSON content and preserve failures verbatim."""
    if isinstance(content, (dict, list)):
        return True, content, None
    if content is None:
        return False, None, "empty_response"
    if not isinstance(content, str):
        return False, None, f"unexpected_response_type:{type(content).__name__}"

    stripped = _strip_code_fence(content)
    if not stripped:
        return False, None, "empty_response"
    try:
        return True, json.loads(stripped), None
    except json.JSONDecodeError as exc:
        return False, None, f"json_parse_error:{exc}"


def _is_timeout_error(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    return "timeout" in name or "timeout" in message or "timed out" in message


def _unique_error_types(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"manifest field `{field_name}` is required and must be non-empty string")
    return value.strip()


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"manifest field `{field_name}` is required and must be int")
    if value < 0:
        raise ValueError(f"manifest field `{field_name}` must be non-negative")
    return value


def _require_positive_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"manifest field `{field_name}` is required and must be int")
    if value <= 0:
        raise ValueError(f"manifest field `{field_name}` must be positive")
    return value


def _require_float(value: Any, field_name: str) -> float:
    if value is None:
        raise ValueError(f"manifest field `{field_name}` is required")
    return float(value)


def _require_cases(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("manifest field `chain_benchmark.cases` must be a non-empty list")
    cases: list[dict[str, Any]] = []
    for case in value:
        if not isinstance(case, Mapping):
            raise TypeError("each chain benchmark case must be an object")
        case_id = _require_non_empty_str(case.get("id"), "chain_benchmark.cases[].id")
        seed_text = _require_non_empty_str(case.get("seed_text"), "chain_benchmark.cases[].seed_text")
        event_type = _require_non_empty_str(case.get("event_type"), "chain_benchmark.cases[].event_type")
        event_summary = _require_non_empty_str(case.get("event_summary"), "chain_benchmark.cases[].event_summary")
        event_scale = _require_float(case.get("event_scale"), "chain_benchmark.cases[].event_scale")
        event_controversy = _require_float(case.get("event_controversy"), "chain_benchmark.cases[].event_controversy")
        cases.append(
            {
                "id": case_id,
                "case_id": case_id,
                "seed_text": seed_text,
                "event_type": event_type,
                "event_summary": event_summary,
                "event_scale": event_scale,
                "event_controversy": event_controversy,
            }
        )
    return cases


def _require_model_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"manifest field `{field_name}` must be a non-empty list")
    result = [str(item).strip() for item in value if str(item).strip()]
    if not result:
        raise ValueError(f"manifest field `{field_name}` is empty")
    return result


def _resolve_manifest(raw_manifest: Mapping[str, Any], manifest_path: Path) -> ManifestBundle:
    manifest = raw_manifest.get("chain_benchmark")
    if not isinstance(manifest, Mapping):
        raise ValueError("run_manifest.json missing required object: `chain_benchmark`")
    chain_runner_section = raw_manifest.get("chain_runner")
    if not isinstance(chain_runner_section, Mapping):
        raise ValueError("run_manifest.json missing required object: `chain_runner`")

    raw_log_dir_value = _require_non_empty_str(manifest.get("raw_log_dir"), "chain_benchmark.raw_log_dir")
    raw_log_dir = Path(raw_log_dir_value)
    if not raw_log_dir.is_absolute():
        raw_log_dir = (config.PROJECT_ROOT / raw_log_dir).resolve()

    return ManifestBundle(
        run_name=_require_non_empty_str(manifest.get("run_name"), "chain_benchmark.run_name"),
        generator_models=_require_model_list(manifest.get("generator_model"), "chain_benchmark.generator_model"),
        validator_model=_require_non_empty_str(manifest.get("validator_model"), "chain_benchmark.validator_model"),
        max_retry_count=_require_non_negative_int(manifest.get("max_retry_count"), "chain_benchmark.max_retry_count"),
        cases=_require_cases(manifest.get("cases")),
        raw_log_dir=raw_log_dir,
        provider=_require_non_empty_str(manifest.get("provider"), "chain_benchmark.provider"),
        api_key=_require_non_empty_str(manifest.get("api_key"), "chain_benchmark.api_key"),
        base_url=_require_non_empty_str(manifest.get("base_url"), "chain_benchmark.base_url"),
        generator_temperature=_require_float(manifest.get("generator_temperature"), "chain_benchmark.generator_temperature"),
        validator_temperature=_require_float(manifest.get("validator_temperature"), "chain_benchmark.validator_temperature"),
        max_tokens=_require_positive_int(manifest.get("max_tokens"), "chain_benchmark.max_tokens"),
        request_timeout=_require_float(chain_runner_section.get("timeout_sec"), "chain_runner.timeout_sec"),
    )


def _build_error_feedback(error_types: Sequence[str], validator_errors: Sequence[str]) -> str:
    if validator_errors:
        return "\n".join(f"- {item}" for item in validator_errors)
    if error_types:
        return "\n".join(f"- {item}" for item in error_types)
    return ""


def _count_entities(payload: Mapping[str, Any] | None) -> tuple[int, int, int, bool, bool]:
    if not isinstance(payload, Mapping):
        return 0, 0, 0, False, False

    event_entities = payload.get("event_entities", [])
    opinion_spreaders = payload.get("opinion_spreaders", [])
    entity_count = len(event_entities) if isinstance(event_entities, list) else 0
    spreader_count = len(opinion_spreaders) if isinstance(opinion_spreaders, list) else 0

    estimated_sum = 0
    has_positive_p = False
    has_negative_p = False
    if isinstance(opinion_spreaders, list):
        for item in opinion_spreaders:
            if not isinstance(item, Mapping):
                continue
            estimated_sum += int(item.get("estimated_percentage", 0) or 0)
            p_value = item.get("P")
            if p_value == 1:
                has_positive_p = True
            elif p_value == -1:
                has_negative_p = True

    return entity_count, spreader_count, estimated_sum, has_positive_p, has_negative_p


def _build_attempt_record(
    *,
    model_name: str,
    validator_model: str,
    seed_case_id: str,
    mode: str,
    retry_count: int,
    request_id: str,
    attempt_id: str,
    generator_latency_sec: float,
    review_latency_sec: float,
    end_to_end_latency_sec: float,
    generator_success: bool,
    validator_pass: bool,
    timeout: bool,
    empty_response: bool,
    json_parse_ok: bool,
    entity_count: int,
    opinion_spreader_count: int,
    estimated_percentage_sum: int,
    has_positive_P: bool,
    has_negative_P: bool,
    error_types: Sequence[str],
    exception_type: str | None,
    exception_message: str | None,
    generator_raw_response: Any,
    generator_parsed_json: Any,
    validator_raw_response: Any,
    validator_parsed_json: Any,
    validator_errors: Sequence[str],
    error_feedback: str,
) -> dict[str, Any]:
    return {
        "model_name": model_name,
        "validator_model_name": validator_model,
        "seed_case_id": seed_case_id,
        "mode": mode,
        "request_id": request_id,
        "attempt_id": attempt_id,
        "generator_latency_sec": round(generator_latency_sec, 6),
        "review_latency_sec": round(review_latency_sec, 6),
        "end_to_end_latency_sec": round(end_to_end_latency_sec, 6),
        "generator_success": generator_success,
        "validator_pass": validator_pass,
        "retry_count": retry_count,
        "timeout": timeout,
        "empty_response": empty_response,
        "json_parse_ok": json_parse_ok,
        "entity_count": entity_count,
        "opinion_spreader_count": opinion_spreader_count,
        "estimated_percentage_sum": estimated_percentage_sum,
        "has_positive_P": has_positive_P,
        "has_negative_P": has_negative_P,
        "error_types": list(error_types),
        "exception_type": exception_type,
        "exception_message": exception_message,
        "validator_errors": list(validator_errors),
        "error_feedback": error_feedback,
        "generator_raw_response": generator_raw_response,
        "generator_parsed_json": generator_parsed_json,
        "validator_raw_response": validator_raw_response,
        "validator_parsed_json": validator_parsed_json,
    }


def _build_timeout_result(
    *,
    generator_model: str,
    validator_model: str,
    case: Mapping[str, Any],
    max_retry_count: int,
    request_timeout: float,
) -> dict[str, Any]:
    seed_case_id = str(case["id"])
    request_id = f"{generator_model}:{seed_case_id}"
    attempt = _build_attempt_record(
        model_name=generator_model,
        validator_model=validator_model,
        seed_case_id=seed_case_id,
        mode="first_pass",
        retry_count=0,
        request_id=request_id,
        attempt_id=f"{request_id}:attempt:0",
        generator_latency_sec=request_timeout,
        review_latency_sec=0.0,
        end_to_end_latency_sec=request_timeout,
        generator_success=False,
        validator_pass=False,
        timeout=True,
        empty_response=False,
        json_parse_ok=False,
        entity_count=0,
        opinion_spreader_count=0,
        estimated_percentage_sum=0,
        has_positive_P=False,
        has_negative_P=False,
        error_types=["timeout", "generator_error:RunnerTimeout"],
        exception_type="RunnerTimeout",
        exception_message=f"chain case exceeded runner timeout {request_timeout:.2f}s",
        generator_raw_response=None,
        generator_parsed_json=None,
        validator_raw_response=None,
        validator_parsed_json=None,
        validator_errors=[],
        error_feedback="",
    )
    return {
        "model_name": generator_model,
        "validator_model_name": validator_model,
        "seed_case_id": seed_case_id,
        "max_retry_count": max_retry_count,
        "generator_latency_sec": round(request_timeout, 6),
        "review_latency_sec": 0.0,
        "end_to_end_latency_sec": round(request_timeout, 6),
        "json_parse_ok": False,
        "validator_pass": False,
        "retry_count": 0,
        "error_types": ["timeout", "generator_error:RunnerTimeout"],
        "entity_count": 0,
        "opinion_spreader_count": 0,
        "estimated_percentage_sum": 0,
        "has_positive_P": False,
        "has_negative_P": False,
        "attempts": [attempt],
        "final_generator_json": None,
        "final_validator_json": None,
        "case": dict(case),
    }


def run_chain_case(
    *,
    generator_model: str,
    validator_model: str,
    case: Mapping[str, Any],
    max_retry_count: int = 2,
    provider: str,
    api_key: str,
    base_url: str,
    generator_temperature: float,
    validator_temperature: float,
    max_tokens: int,
    request_timeout: float,
) -> dict[str, Any]:
    """Run a single generator -> validator -> retry case.

    max_retry_count means retries after the first generator attempt.
    """
    case_data = dict(case)
    seed_case_id = str(case_data["id"])
    generator_client = LLMClient(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=generator_model,
        temperature=generator_temperature,
        max_tokens=max_tokens,
        request_timeout=request_timeout,
    )
    validator_client = LLMClient(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=validator_model,
        temperature=validator_temperature,
        max_tokens=max_tokens,
        request_timeout=request_timeout,
    )

    sample_start = time.perf_counter()
    attempt_logs: list[dict[str, Any]] = []
    accumulated_error_types: list[str] = []
    final_generator_json: Any = None
    final_validator_json: Any = None
    final_validator_errors: list[str] = []
    final_json_parse_ok = False
    final_validator_pass = False
    final_retry_count = 0
    total_generator_latency = 0.0
    total_review_latency = 0.0

    for attempt_index in range(max_retry_count + 1):
        mode = "first_pass" if attempt_index == 0 else "retry_pass"
        request_id = f"{generator_model}:{seed_case_id}"
        attempt_id = f"{request_id}:attempt:{attempt_index}"
        attempt_error_types: list[str] = []
        generator_raw_response: Any = None
        validator_raw_response: Any = None
        generator_parsed_json: Any = None
        validator_parsed_json: Any = None
        validator_errors: list[str] = []
        generator_success = False
        validator_pass = False
        timeout = False
        empty_response = False
        json_parse_ok = False
        generator_latency = 0.0
        review_latency = 0.0
        exception_type: str | None = None
        exception_message: str | None = None
        stop_case_after_attempt = False

        try:
            console.print(
                f"[cyan]chain_runner[/cyan] model={generator_model} case={seed_case_id} "
                f"attempt={attempt_index} stage=before_generator_request"
            )
            generator_system, generator_user = build_generator_prompts(
                case_data,
                _build_error_feedback(accumulated_error_types, final_validator_errors),
            )
            generator_call_start = time.perf_counter()
            generator_raw_response = generator_client.generate(
                system=generator_system,
                user=generator_user,
                response_model=None,
            )
            generator_latency = time.perf_counter() - generator_call_start
            console.print(
                f"[cyan]chain_runner[/cyan] model={generator_model} case={seed_case_id} "
                f"attempt={attempt_index} stage=after_generator_response"
            )
            generator_success = True
            empty_response = not bool(str(generator_raw_response).strip())
            if empty_response:
                attempt_error_types.append("empty_response")

            json_parse_ok, generator_parsed_json, parse_error = _parse_json_text(generator_raw_response)
            if not json_parse_ok and parse_error:
                attempt_error_types.append(parse_error)
        except Exception as exc:
            generator_success = False
            exception_type = type(exc).__name__
            exception_message = str(exc)
            if _is_timeout_error(exc):
                timeout = True
                attempt_error_types.append("timeout")
            else:
                attempt_error_types.append(f"generator_error:{exc.__class__.__name__}")
            stop_case_after_attempt = True

        if json_parse_ok and isinstance(generator_parsed_json, Mapping):
            validator_system, validator_user = build_validator_prompts(case_data["seed_text"], dict(generator_parsed_json))
            validator_latency_start = time.perf_counter()
            try:
                console.print(
                    f"[cyan]chain_runner[/cyan] model={generator_model} case={seed_case_id} "
                    f"attempt={attempt_index} stage=before_validator_request"
                )
                validator_raw_response = validator_client.generate(
                    system=validator_system,
                    user=validator_user,
                    response_model=None,
                )
                review_latency = time.perf_counter() - validator_latency_start
                console.print(
                    f"[cyan]chain_runner[/cyan] model={generator_model} case={seed_case_id} "
                    f"attempt={attempt_index} stage=after_validator_response"
                )
                validator_json_ok, validator_parsed_json, validator_parse_error = _parse_json_text(validator_raw_response)
                if validator_json_ok and isinstance(validator_parsed_json, Mapping):
                    validator_pass = bool(validator_parsed_json.get("pass"))
                    if validator_pass:
                        final_validator_json = validator_parsed_json
                    else:
                        validator_errors = list(validator_parsed_json.get("errors", []))
                        attempt_error_types.append("validator_fail")
                else:
                    validator_pass = False
                    if validator_parse_error:
                        attempt_error_types.append(f"validator_{validator_parse_error}")
            except Exception as exc:
                review_latency = time.perf_counter() - validator_latency_start
                validator_pass = False
                exception_type = type(exc).__name__
                exception_message = str(exc)
                if _is_timeout_error(exc):
                    timeout = True
                    attempt_error_types.append("timeout")
                else:
                    attempt_error_types.append(f"validator_error:{exc.__class__.__name__}")
        else:
            if not json_parse_ok:
                attempt_error_types.append("json_parse_failed")

        if validator_pass:
            final_generator_json = generator_parsed_json
            final_json_parse_ok = True
            final_validator_pass = True
            final_validator_errors = validator_errors
            final_retry_count = attempt_index
        else:
            final_json_parse_ok = bool(json_parse_ok)
            final_validator_pass = False
            final_validator_errors = validator_errors
            final_retry_count = attempt_index

        entity_count, opinion_spreader_count, estimated_sum, has_positive_p, has_negative_p = _count_entities(
            generator_parsed_json if isinstance(generator_parsed_json, Mapping) else None
        )

        end_to_end_latency = time.perf_counter() - sample_start
        total_generator_latency += generator_latency
        total_review_latency += review_latency
        attempt_logs.append(
            _build_attempt_record(
                model_name=generator_model,
                validator_model=validator_model,
                seed_case_id=seed_case_id,
                mode=mode,
                retry_count=attempt_index,
                request_id=request_id,
                attempt_id=attempt_id,
                generator_latency_sec=generator_latency,
                review_latency_sec=review_latency,
                end_to_end_latency_sec=end_to_end_latency,
                generator_success=generator_success,
                validator_pass=validator_pass,
                timeout=timeout,
                empty_response=empty_response,
                json_parse_ok=json_parse_ok,
                entity_count=entity_count,
                opinion_spreader_count=opinion_spreader_count,
                estimated_percentage_sum=estimated_sum,
                has_positive_P=has_positive_p,
                has_negative_P=has_negative_p,
                error_types=attempt_error_types,
                exception_type=exception_type,
                exception_message=exception_message,
                generator_raw_response=generator_raw_response,
                generator_parsed_json=generator_parsed_json,
                validator_raw_response=validator_raw_response,
                validator_parsed_json=validator_parsed_json,
                validator_errors=validator_errors,
                error_feedback=_build_error_feedback(attempt_error_types, validator_errors),
            )
        )

        accumulated_error_types = _unique_error_types(accumulated_error_types + attempt_error_types)
        if validator_pass or stop_case_after_attempt:
            break

    end_to_end_latency = time.perf_counter() - sample_start
    final_entity_count, final_spreader_count, final_percentage_sum, final_has_positive_p, final_has_negative_p = _count_entities(
        final_generator_json if isinstance(final_generator_json, Mapping) else None
    )

    return {
        "model_name": generator_model,
        "validator_model_name": validator_model,
        "seed_case_id": seed_case_id,
        "max_retry_count": max_retry_count,
        "generator_latency_sec": round(total_generator_latency, 6),
        "review_latency_sec": round(total_review_latency, 6),
        "end_to_end_latency_sec": round(end_to_end_latency, 6),
        "json_parse_ok": final_json_parse_ok,
        "validator_pass": final_validator_pass,
        "retry_count": final_retry_count,
        "error_types": accumulated_error_types,
        "entity_count": final_entity_count,
        "opinion_spreader_count": final_spreader_count,
        "estimated_percentage_sum": final_percentage_sum,
        "has_positive_P": final_has_positive_p,
        "has_negative_P": final_has_negative_p,
        "attempts": attempt_logs,
        "final_generator_json": final_generator_json,
        "final_validator_json": final_validator_json,
        "case": case_data,
    }


def run_chain_benchmark(*, manifest_path: str | Path | None = None) -> dict[str, Any]:
    """Execute the benchmark strictly from run_manifest.json."""
    if manifest_path is None:
        raise ValueError("manifest_path is required in manifest-only mode")
    resolved_manifest_path = Path(manifest_path)
    if not resolved_manifest_path.exists():
        raise FileNotFoundError(f"run_manifest.json 不存在: {resolved_manifest_path}")

    manifest = _load_json(resolved_manifest_path)
    if not isinstance(manifest, Mapping):
        raise ValueError("run_manifest.json 必须是 JSON 对象")

    bundle = _resolve_manifest(manifest, resolved_manifest_path)
    bundle.raw_log_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_log_path = bundle.raw_log_dir / f"{bundle.run_name}_{resolved_manifest_path.stem}_{run_id}.jsonl"

    raw_rows: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    for generator_model in bundle.generator_models:
        for case in bundle.cases:
            console.print(
                f"[cyan]chain_runner[/cyan] model={generator_model} case={case['id']} stage=begin_case"
            )
            holder: dict[str, Any] = {}
            worker_error: dict[str, BaseException] = {}

            def _worker() -> None:
                try:
                    holder["result"] = run_chain_case(
                        generator_model=generator_model,
                        validator_model=bundle.validator_model,
                        case=case,
                        max_retry_count=bundle.max_retry_count,
                        provider=bundle.provider,
                        api_key=bundle.api_key,
                        base_url=bundle.base_url,
                        generator_temperature=bundle.generator_temperature,
                        validator_temperature=bundle.validator_temperature,
                        max_tokens=bundle.max_tokens,
                        request_timeout=bundle.request_timeout,
                    )
                except BaseException as exc:
                    worker_error["error"] = exc

            worker = threading.Thread(target=_worker, name=f"chain_case_{generator_model}_{case['id']}", daemon=True)
            worker.start()
            worker.join(timeout=bundle.request_timeout)
            if "error" in worker_error:
                raise worker_error["error"]
            if worker.is_alive():
                console.print(
                    f"[yellow]chain_runner[/yellow] model={generator_model} case={case['id']} "
                    f"stage=runner_timeout timeout_sec={bundle.request_timeout}"
                )
                result = _build_timeout_result(
                    generator_model=generator_model,
                    validator_model=bundle.validator_model,
                    case=case,
                    max_retry_count=bundle.max_retry_count,
                    request_timeout=bundle.request_timeout,
                )
            else:
                result = holder["result"]
            results.append(result)
            raw_rows.extend(result["attempts"])
            raw_log_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in raw_rows) + ("\n" if raw_rows else ""),
                encoding="utf-8",
            )

    console.print(f"[cyan]chain_runner[/cyan] run_name={bundle.run_name} stage=before_write_raw_log path={raw_log_path}")

    return {
        "manifest_path": str(resolved_manifest_path),
        "raw_log_path": str(raw_log_path),
        "generator_models": bundle.generator_models,
        "validator_model": bundle.validator_model,
        "max_retry_count": bundle.max_retry_count,
        "case_count": len(bundle.cases),
        "results": results,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manifest-driven generator -> validator chain benchmark")
    parser.add_argument("--manifest", required=True, help="Path to run_manifest.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    payload = run_chain_benchmark(manifest_path=args.manifest)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
