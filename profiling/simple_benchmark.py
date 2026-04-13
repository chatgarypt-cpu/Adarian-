"""Simple prompt benchmark runner for v1.1.19 profiling.

Manifest-only mode:
- only reads `run_manifest.json`
- only accepts the `simple_benchmark` section
- does not define fallback scope or default benchmark parameters
- preserves raw failures in structured logs
"""

from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence

import config
from rich.console import Console
from src.llm_client import LLMClient

PROFILE_ROOT = Path(config.PROJECT_ROOT) / "profiling"
RAW_LOG_DIR = PROFILE_ROOT / "output" / "raw_logs"
console = Console()


def _now_ts() -> float:
    return time.time()


def _strip_code_fences(text: str) -> str:
    payload = text.strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.IGNORECASE)
        payload = re.sub(r"\s*```$", "", payload)
    return payload.strip()


def _extract_json_candidate(text: str) -> str:
    payload = _strip_code_fences(text)
    if not payload:
        return payload
    if not payload.startswith("{"):
        start = payload.find("{")
        end = payload.rfind("}")
        if start != -1 and end != -1 and end > start:
            payload = payload[start : end + 1]
    return payload.strip()


def _safe_json_loads(text: str) -> tuple[dict[str, Any] | None, str | None]:
    candidate = _extract_json_candidate(text)
    if not candidate:
        return None, "empty_response"
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return None, f"json_decode_error: {exc.msg}"
    if not isinstance(data, dict):
        return None, "json_root_not_object"
    return data, None


def _schema_check_simple_payload(payload: Mapping[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if "summary" not in payload:
        errors.append("missing_field: summary")
    elif not isinstance(payload["summary"], str) or not payload["summary"].strip():
        errors.append("invalid_field: summary")

    if "risk_level" not in payload:
        errors.append("missing_field: risk_level")
    elif payload["risk_level"] not in {"low", "medium", "high"}:
        errors.append("invalid_field: risk_level")

    return len(errors) == 0, errors


@dataclass(slots=True)
class SimpleBenchmarkCase:
    """Frozen simple benchmark case from manifest."""

    case_id: str
    system_prompt: str
    user_prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SimpleBenchmarkRunSpec:
    """Resolved simple benchmark spec from manifest."""

    manifest: dict[str, Any]
    manifest_path: Path | None
    run_name: str
    models: list[str]
    cases: list[SimpleBenchmarkCase]
    concurrency_levels: list[int]
    rounds: int
    timeout_sec: float
    temperature: float
    max_tokens: int
    provider: str
    api_key: str
    base_url: str


@dataclass(slots=True)
class SimpleBenchmarkSample:
    """Single LLM call record."""

    sample_id: str
    request_id: str
    attempt_id: str
    model_name: str
    case_id: str
    concurrency_level: int
    round_index: int
    slot_index: int
    mode: str
    started_at_unix: float
    finished_at_unix: float | None
    elapsed_sec: float
    timeout: bool
    empty_response: bool
    exception_type: str | None
    exception_message: str | None
    raw_response: str | None
    json_parse_ok: bool
    schema_ok: bool
    schema_errors: list[str]
    parsed_payload: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SimpleBenchmarkRoundResult:
    """One round of requests at a given concurrency level."""

    round_index: int
    concurrency_level: int
    started_at_unix: float
    finished_at_unix: float
    elapsed_sec: float
    samples: list[SimpleBenchmarkSample]


@dataclass(slots=True)
class SimpleBenchmarkConcurrencyResult:
    """Aggregated result for one concurrency level."""

    concurrency_level: int
    rounds: int
    total_requests: int
    completed_count: int
    timeout_count: int
    exception_count: int
    empty_response_count: int
    json_parse_ok_count: int
    schema_ok_count: int
    avg_latency_sec: float
    completed_avg_latency_sec: float
    min_latency_sec: float
    max_latency_sec: float
    throughput_rps: float
    timeout_rate: float
    error_rate: float
    json_parse_ok_rate: float
    schema_ok_rate: float
    samples: list[SimpleBenchmarkSample]
    round_results: list[SimpleBenchmarkRoundResult]


@dataclass(slots=True)
class SimpleBenchmarkModelResult:
    """All benchmark results for a single model."""

    model_name: str
    case_results: list[dict[str, Any]]
    summary: dict[str, Any]


@dataclass(slots=True)
class SimpleBenchmarkReport:
    """Top-level benchmark report returned to main runner."""

    meta: dict[str, Any]
    cases: list[SimpleBenchmarkCase]
    models: list[SimpleBenchmarkModelResult]
    records: list[SimpleBenchmarkSample]

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": self.meta,
            "cases": [case.to_dict() for case in self.cases],
            "models": [asdict(model) for model in self.models],
            "records": [record.to_dict() for record in self.records],
        }


def _load_manifest_source(manifest_source: str | Path | Mapping[str, Any]) -> tuple[dict[str, Any], Path | None]:
    if isinstance(manifest_source, (str, Path)):
        manifest_path = Path(manifest_source)
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("run_manifest.json must contain a JSON object")
        return data, manifest_path
    if isinstance(manifest_source, Mapping):
        return dict(manifest_source), None
    raise TypeError("manifest_source must be a path or mapping")


def _require_section(raw_manifest: Mapping[str, Any], section_name: str) -> dict[str, Any]:
    section = raw_manifest.get(section_name)
    if not isinstance(section, Mapping):
        raise ValueError(f"run_manifest.json missing required object: `{section_name}`")
    return dict(section)


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"manifest field `{field_name}` is required and must be non-empty string")
    return value.strip()


def _require_positive_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"manifest field `{field_name}` is required and must be int")
    if value <= 0:
        raise ValueError(f"manifest field `{field_name}` must be positive")
    return value


def _require_positive_float(value: Any, field_name: str) -> float:
    if value is None:
        raise ValueError(f"manifest field `{field_name}` is required")
    result = float(value)
    if result <= 0:
        raise ValueError(f"manifest field `{field_name}` must be positive")
    return result


def _require_str_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"manifest field `{field_name}` must be a non-empty list")
    result = [str(item).strip() for item in value if str(item).strip()]
    if not result:
        raise ValueError(f"manifest field `{field_name}` is empty")
    return result


def _require_int_list(value: Any, field_name: str) -> list[int]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"manifest field `{field_name}` must be a non-empty list")
    result = [int(item) for item in value]
    if any(item <= 0 for item in result):
        raise ValueError(f"manifest field `{field_name}` must contain positive integers")
    return result


def _normalize_cases(raw_cases: Any) -> list[SimpleBenchmarkCase]:
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("manifest field `simple_benchmark.cases` must be a non-empty list")

    normalized: list[SimpleBenchmarkCase] = []
    for case in raw_cases:
        if not isinstance(case, Mapping):
            raise TypeError("each simple benchmark case must be an object")
        normalized.append(
            SimpleBenchmarkCase(
                case_id=_require_non_empty_str(case.get("case_id"), "simple_benchmark.cases[].case_id"),
                system_prompt=_require_non_empty_str(case.get("system_prompt"), "simple_benchmark.cases[].system_prompt"),
                user_prompt=_require_non_empty_str(case.get("user_prompt"), "simple_benchmark.cases[].user_prompt"),
                metadata=dict(case.get("metadata") or {}),
            )
        )
    return normalized


def resolve_simple_benchmark_spec(manifest_source: str | Path | Mapping[str, Any]) -> SimpleBenchmarkRunSpec:
    """Resolve the exact benchmark scope from run manifest."""
    raw_manifest, manifest_path = _load_manifest_source(manifest_source)
    manifest = _require_section(raw_manifest, "simple_benchmark")

    return SimpleBenchmarkRunSpec(
        manifest=manifest,
        manifest_path=manifest_path,
        run_name=_require_non_empty_str(manifest.get("run_name"), "simple_benchmark.run_name"),
        models=_require_str_list(manifest.get("models"), "simple_benchmark.models"),
        cases=_normalize_cases(manifest.get("cases")),
        concurrency_levels=_require_int_list(manifest.get("concurrency_levels"), "simple_benchmark.concurrency_levels"),
        rounds=_require_positive_int(manifest.get("rounds"), "simple_benchmark.rounds"),
        timeout_sec=_require_positive_float(manifest.get("timeout_sec"), "simple_benchmark.timeout_sec"),
        temperature=_require_positive_float(manifest.get("temperature"), "simple_benchmark.temperature"),
        max_tokens=_require_positive_int(manifest.get("max_tokens"), "simple_benchmark.max_tokens"),
        provider=_require_non_empty_str(manifest.get("provider"), "simple_benchmark.provider"),
        api_key=_require_non_empty_str(manifest.get("api_key"), "simple_benchmark.api_key"),
        base_url=_require_non_empty_str(manifest.get("base_url"), "simple_benchmark.base_url"),
    )


def _build_client(
    model_name: str,
    *,
    temperature: float,
    max_tokens: int,
    provider: str,
    api_key: str,
    base_url: str,
    request_timeout: float,
) -> LLMClient:
    return LLMClient(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        request_timeout=request_timeout,
    )


def _run_single_call(
    *,
    client: LLMClient,
    model_name: str,
    case: SimpleBenchmarkCase,
    concurrency_level: int,
    round_index: int,
    slot_index: int,
    timeout_sec: float,
) -> SimpleBenchmarkSample:
    sample_id = f"{model_name}:{case.case_id}:c{concurrency_level}:r{round_index}:s{slot_index}"
    started_at = _now_ts()
    perf_start = time.perf_counter()

    timeout = False
    empty_response = False
    exception_type: str | None = None
    exception_message: str | None = None
    raw_response: str | None = None
    json_parse_ok = False
    schema_ok = False
    schema_errors: list[str] = []
    parsed_payload: dict[str, Any] | None = None

    try:
        console.print(
            f"[cyan]simple_runner[/cyan] model={model_name} case={case.case_id} "
            f"round={round_index} slot={slot_index} stage=before_request"
        )
        raw_response = client.generate(case.system_prompt, case.user_prompt)
        console.print(
            f"[cyan]simple_runner[/cyan] model={model_name} case={case.case_id} "
            f"round={round_index} slot={slot_index} stage=after_response"
        )
        if not isinstance(raw_response, str):
            raw_response = str(raw_response)
        stripped = raw_response.strip()
        empty_response = not stripped
        if not empty_response:
            parsed_payload, parse_error = _safe_json_loads(stripped)
            if parse_error is None and parsed_payload is not None:
                json_parse_ok = True
                schema_ok, schema_errors = _schema_check_simple_payload(parsed_payload)
            else:
                exception_type = "JSONParseError"
                exception_message = parse_error
        else:
            exception_type = "EmptyResponseError"
            exception_message = "empty_response"
    except Exception as exc:
        exception_type = type(exc).__name__
        exception_message = str(exc)

    elapsed_sec = time.perf_counter() - perf_start
    finished_at = _now_ts()

    return SimpleBenchmarkSample(
        sample_id=sample_id,
        request_id=sample_id,
        attempt_id=sample_id,
        model_name=model_name,
        case_id=case.case_id,
        concurrency_level=concurrency_level,
        round_index=round_index,
        slot_index=slot_index,
        mode="serial" if concurrency_level == 1 else "concurrent",
        started_at_unix=started_at,
        finished_at_unix=finished_at,
        elapsed_sec=elapsed_sec,
        timeout=timeout,
        empty_response=empty_response,
        exception_type=exception_type,
        exception_message=exception_message,
        raw_response=raw_response,
        json_parse_ok=json_parse_ok,
        schema_ok=schema_ok,
        schema_errors=schema_errors,
        parsed_payload=parsed_payload,
    )


def _run_concurrency_round(
    *,
    client: LLMClient,
    model_name: str,
    case: SimpleBenchmarkCase,
    concurrency_level: int,
    round_index: int,
    timeout_sec: float,
) -> SimpleBenchmarkRoundResult:
    started_at = _now_ts()
    perf_start = time.perf_counter()
    executor = ThreadPoolExecutor(max_workers=concurrency_level)
    futures = [
        executor.submit(
            _run_single_call,
            client=client,
            model_name=model_name,
            case=case,
            concurrency_level=concurrency_level,
            round_index=round_index,
            slot_index=slot_index,
            timeout_sec=timeout_sec,
        )
        for slot_index in range(1, concurrency_level + 1)
    ]

    done, not_done = wait(futures, timeout=timeout_sec)
    samples: list[SimpleBenchmarkSample] = []
    for future in futures:
        if future in done:
            samples.append(future.result())
        else:
            future.cancel()
            samples.append(
                    SimpleBenchmarkSample(
                        sample_id=f"{model_name}:{case.case_id}:c{concurrency_level}:r{round_index}:timeout",
                        request_id=f"{model_name}:{case.case_id}:c{concurrency_level}:r{round_index}:timeout",
                        attempt_id=f"{model_name}:{case.case_id}:c{concurrency_level}:r{round_index}:timeout",
                        model_name=model_name,
                    case_id=case.case_id,
                    concurrency_level=concurrency_level,
                    round_index=round_index,
                    slot_index=-1,
                    mode="serial" if concurrency_level == 1 else "concurrent",
                    started_at_unix=started_at,
                    finished_at_unix=_now_ts(),
                    elapsed_sec=timeout_sec,
                    timeout=True,
                    empty_response=False,
                    exception_type="TimeoutError",
                    exception_message=f"call exceeded {timeout_sec:.2f}s",
                    raw_response=None,
                    json_parse_ok=False,
                    schema_ok=False,
                    schema_errors=["timeout"],
                    parsed_payload=None,
                )
            )

    if not_done:
        console.print(
            f"[yellow]simple_runner[/yellow] model={model_name} case={case.case_id} "
            f"round={round_index} stage=executor_timeout pending={len(not_done)}"
        )
    executor.shutdown(wait=False, cancel_futures=True)

    return SimpleBenchmarkRoundResult(
        round_index=round_index,
        concurrency_level=concurrency_level,
        started_at_unix=started_at,
        finished_at_unix=_now_ts(),
        elapsed_sec=time.perf_counter() - perf_start,
        samples=samples,
    )


def _aggregate_concurrency_results(
    *,
    concurrency_level: int,
    rounds: int,
    round_results: list[SimpleBenchmarkRoundResult],
) -> SimpleBenchmarkConcurrencyResult:
    samples = [sample for round_result in round_results for sample in round_result.samples]
    total_requests = len(samples)
    completed_samples = [sample for sample in samples if not sample.timeout]
    latencies = [sample.elapsed_sec for sample in samples]
    completed_latencies = [sample.elapsed_sec for sample in completed_samples]

    timeout_count = sum(1 for sample in samples if sample.timeout)
    exception_count = sum(1 for sample in samples if sample.exception_type and not sample.timeout)
    empty_response_count = sum(1 for sample in samples if sample.empty_response)
    json_parse_ok_count = sum(1 for sample in samples if sample.json_parse_ok)
    schema_ok_count = sum(1 for sample in samples if sample.schema_ok)
    completed_count = len(completed_samples)

    avg_latency_sec = mean(latencies) if latencies else 0.0
    completed_avg_latency_sec = mean(completed_latencies) if completed_latencies else 0.0
    min_latency_sec = min(latencies) if latencies else 0.0
    max_latency_sec = max(latencies) if latencies else 0.0
    total_elapsed_sec = sum(round_result.elapsed_sec for round_result in round_results)
    throughput_rps = (total_requests / total_elapsed_sec) if total_elapsed_sec > 0 else 0.0

    return SimpleBenchmarkConcurrencyResult(
        concurrency_level=concurrency_level,
        rounds=rounds,
        total_requests=total_requests,
        completed_count=completed_count,
        timeout_count=timeout_count,
        exception_count=exception_count,
        empty_response_count=empty_response_count,
        json_parse_ok_count=json_parse_ok_count,
        schema_ok_count=schema_ok_count,
        avg_latency_sec=avg_latency_sec,
        completed_avg_latency_sec=completed_avg_latency_sec,
        min_latency_sec=min_latency_sec,
        max_latency_sec=max_latency_sec,
        throughput_rps=throughput_rps,
        timeout_rate=(timeout_count / total_requests) if total_requests else 0.0,
        error_rate=((timeout_count + exception_count) / total_requests) if total_requests else 0.0,
        json_parse_ok_rate=(json_parse_ok_count / total_requests) if total_requests else 0.0,
        schema_ok_rate=(schema_ok_count / total_requests) if total_requests else 0.0,
        samples=samples,
        round_results=round_results,
    )


def _aggregate_model_summary(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    all_concurrency = [
        concurrency_result
        for case_result in case_results
        for concurrency_result in case_result["concurrency_results"]
    ]
    if not all_concurrency:
        return {
            "total_requests": 0,
            "completed_count": 0,
            "timeout_count": 0,
            "exception_count": 0,
            "empty_response_count": 0,
            "json_parse_ok_count": 0,
            "schema_ok_count": 0,
            "avg_latency_sec": 0.0,
            "timeout_rate": 0.0,
            "error_rate": 0.0,
        }

    total_requests = sum(item.total_requests for item in all_concurrency)
    completed_count = sum(item.completed_count for item in all_concurrency)
    timeout_count = sum(item.timeout_count for item in all_concurrency)
    exception_count = sum(item.exception_count for item in all_concurrency)
    empty_response_count = sum(item.empty_response_count for item in all_concurrency)
    json_parse_ok_count = sum(item.json_parse_ok_count for item in all_concurrency)
    schema_ok_count = sum(item.schema_ok_count for item in all_concurrency)
    total_latency_weight = sum(item.total_requests for item in all_concurrency)
    weighted_avg_latency_sec = (
        sum(item.avg_latency_sec * item.total_requests for item in all_concurrency) / total_latency_weight
        if total_latency_weight
        else 0.0
    )
    timeout_rate = (timeout_count / total_requests) if total_requests else 0.0
    error_rate = ((timeout_count + exception_count) / total_requests) if total_requests else 0.0

    return {
        "total_requests": total_requests,
        "completed_count": completed_count,
        "timeout_count": timeout_count,
        "exception_count": exception_count,
        "empty_response_count": empty_response_count,
        "json_parse_ok_count": json_parse_ok_count,
        "schema_ok_count": schema_ok_count,
        "avg_latency_sec": weighted_avg_latency_sec,
        "timeout_rate": timeout_rate,
        "error_rate": error_rate,
        "json_parse_ok_rate": (json_parse_ok_count / total_requests) if total_requests else 0.0,
        "schema_ok_rate": (schema_ok_count / total_requests) if total_requests else 0.0,
    }


def _slugify_filename(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._-")
    return cleaned or "simple_benchmark"


def _build_raw_log_path(run_name: str) -> Path:
    RAW_LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return RAW_LOG_DIR / f"{_slugify_filename(run_name)}_{timestamp}.jsonl"


def _write_raw_logs(*, raw_log_path: Path, spec: SimpleBenchmarkRunSpec, report: SimpleBenchmarkReport) -> Path:
    payloads: list[dict[str, Any]] = [
        {
            "record_type": "run_meta",
            "run_name": spec.run_name,
            "manifest_path": str(spec.manifest_path) if spec.manifest_path else None,
            "models": spec.models,
            "cases": [case.to_dict() for case in spec.cases],
            "concurrency_levels": spec.concurrency_levels,
            "rounds": spec.rounds,
            "timeout_sec": spec.timeout_sec,
            "created_at_unix": report.meta.get("created_at_unix"),
        }
    ]
    payloads.extend({"record_type": "sample", **record.to_dict()} for record in report.records)
    raw_log_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in payloads) + "\n",
        encoding="utf-8",
    )
    return raw_log_path


def _run_simple_benchmark(spec: SimpleBenchmarkRunSpec) -> SimpleBenchmarkReport:
    report_models: list[SimpleBenchmarkModelResult] = []
    all_records: list[SimpleBenchmarkSample] = []

    for model_name in spec.models:
        client = _build_client(
            model_name,
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
            provider=spec.provider,
            api_key=spec.api_key,
            base_url=spec.base_url,
            request_timeout=spec.timeout_sec,
        )

        case_results: list[dict[str, Any]] = []
        for case in spec.cases:
            concurrency_results: list[SimpleBenchmarkConcurrencyResult] = []
            for concurrency_level in spec.concurrency_levels:
                round_results = [
                    _run_concurrency_round(
                        client=client,
                        model_name=model_name,
                        case=case,
                        concurrency_level=concurrency_level,
                        round_index=round_index,
                        timeout_sec=spec.timeout_sec,
                    )
                    for round_index in range(1, spec.rounds + 1)
                ]
                concurrency_result = _aggregate_concurrency_results(
                    concurrency_level=concurrency_level,
                    rounds=spec.rounds,
                    round_results=round_results,
                )
                concurrency_results.append(concurrency_result)
                all_records.extend(concurrency_result.samples)

            case_results.append({"case": case.to_dict(), "concurrency_results": concurrency_results})

        report_models.append(
            SimpleBenchmarkModelResult(
                model_name=model_name,
                case_results=case_results,
                summary=_aggregate_model_summary(case_results),
            )
        )

    meta = {
        "version": "v1.1.19",
        "profile_name": "simple_prompt_benchmark",
        "run_name": spec.run_name,
        "manifest_path": str(spec.manifest_path) if spec.manifest_path else None,
        "manifest": spec.manifest,
        "models": spec.models,
        "cases": [case.to_dict() for case in spec.cases],
        "concurrency_levels": spec.concurrency_levels,
        "rounds": spec.rounds,
        "timeout_sec": spec.timeout_sec,
        "provider": spec.provider,
        "temperature": spec.temperature,
        "max_tokens": spec.max_tokens,
        "created_at_unix": _now_ts(),
    }

    return SimpleBenchmarkReport(meta=meta, cases=spec.cases, models=report_models, records=all_records)


def run_simple_benchmark(manifest_source: str | Path | Mapping[str, Any]) -> SimpleBenchmarkReport:
    """Run the benchmark described by run_manifest.json."""
    spec = resolve_simple_benchmark_spec(manifest_source)
    report = _run_simple_benchmark(spec)
    raw_log_path = _build_raw_log_path(spec.run_name)
    console.print(f"[cyan]simple_runner[/cyan] run_name={spec.run_name} stage=before_write_raw_log path={raw_log_path}")
    _write_raw_logs(raw_log_path=raw_log_path, spec=spec, report=report)
    report.meta["raw_log_path"] = str(raw_log_path)
    return report


def benchmark_simple_prompt(manifest_source: str | Path | Mapping[str, Any]) -> SimpleBenchmarkReport:
    """Alias for callers that use benchmark naming."""
    return run_simple_benchmark(manifest_source)


def dump_report(report: SimpleBenchmarkReport | Mapping[str, Any], path: str | Path) -> Path:
    payload = report.to_dict() if isinstance(report, SimpleBenchmarkReport) else dict(report)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the v1.1.19 simple prompt benchmark")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to run_manifest.json")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    report = run_simple_benchmark(args.manifest)
    payload = report.to_dict()
    if args.output:
        dump_report(payload, args.output)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
