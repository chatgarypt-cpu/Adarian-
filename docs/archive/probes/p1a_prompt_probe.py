"""Run prompt-aware profiling for the Phase 1 analyzer prompt family."""

from __future__ import annotations

import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_client import LLMClient
from src.phase1 import ANALYZER_SYSTEM_PROMPT, ANALYZER_USER_PROMPT

RUNS_ROOT = PROJECT_ROOT / "profiling" / "output" / "runs"
BASELINE_MANIFEST_PATH = (
    PROJECT_ROOT
    / "profiling"
    / "output"
    / "baseline"
    / "v1.2.0_baseline"
    / "run_manifest.snapshot_v1.2.0_baseline.json"
)
TARGET_MODELS = [
    "qwen3-80b-tke",
    "qwen35-122b-a10b",
    "qwen3-32b-tke",
    "minimax",
]

LEVEL_SPECS: dict[str, dict[str, Any]] = {
    "L1": {
        "required_fields": ["event_scale", "event_controversy"],
        "optional_fields": [],
        "system_prompt": """你是一位资深的社会舆情分析师。你的任务是从一段事件材料中分析并设置最小参数。

请只输出严格 JSON，格式固定为：
{
  "event_scale": 0.0到1.0之间的浮点数,
  "event_controversy": 0.0到1.0之间的浮点数
}

约束：
1. 顶层只允许 `event_scale` 和 `event_controversy`
2. 两个字段都必须是 0.0-1.0 之间的浮点数
3. 不要输出解释，不要输出 markdown，不要输出代码块
""",
    },
    "L2": {
        "required_fields": ["event_scale", "event_controversy", "event_summary"],
        "optional_fields": [],
        "system_prompt": """你是一位资深的社会舆情分析师。你的任务是从一段事件材料中分析并设置参数。

请只输出严格 JSON，格式固定为：
{
  "event_scale": 0.0到1.0之间的浮点数,
  "event_controversy": 0.0到1.0之间的浮点数,
  "event_summary": "一句话概括事件（50字以内）"
}

约束：
1. 顶层只允许 `event_scale`、`event_controversy`、`event_summary`
2. `event_scale` 和 `event_controversy` 必须在 0.0-1.0 之间
3. `event_summary` 必须简洁，50字以内
4. 不要输出解释，不要输出 markdown，不要输出代码块
""",
    },
    "L3": {
        "required_fields": [
            "event_scale",
            "event_controversy",
            "event_summary",
            "event_type",
            "reasoning",
        ],
        "optional_fields": [],
        "system_prompt": ANALYZER_SYSTEM_PROMPT,
    },
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```json"):
        stripped = stripped[7:]
    elif stripped.startswith("```"):
        stripped = stripped[3:]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()


def parse_json_text(content: Any) -> tuple[bool, Any, str | None]:
    if isinstance(content, (dict, list)):
        return True, content, None
    if content is None:
        return False, None, "empty_response"
    if not isinstance(content, str):
        return False, None, f"unexpected_response_type:{type(content).__name__}"

    stripped = strip_code_fence(content)
    if not stripped:
        return False, None, "empty_response"
    try:
        return True, json.loads(stripped), None
    except json.JSONDecodeError as exc:
        return False, None, f"json_parse_error:{exc}"


def build_validator_system_prompt(level_name: str, required_fields: list[str]) -> str:
    field_list = "、".join(required_fields)
    return f"""你是一位严格的格式校验专家。你的任务是检查输入 JSON 是否符合 {level_name} 的 analyzer 输出要求。

【校验规则】
1. 必须是合法 JSON
2. 顶层必须是 object
3. 顶层必须且只允许包含这些字段：{field_list}
4. `event_scale` 和 `event_controversy` 必须是 0.0-1.0 之间的数字
5. 如果存在 `event_summary`，它必须是非空字符串，且长度不超过 50 个字符
6. 如果存在 `event_type`，它必须是非空字符串
7. 如果存在 `reasoning`，它必须是非空字符串

如果通过：
{{
  "pass": true,
  "message": "校验通过"
}}

如果不通过：
{{
  "pass": false,
  "errors": ["错误1", "错误2"]
}}
"""


def build_validator_user_prompt(seed_text: str, json_content: dict[str, Any]) -> str:
    return """请校验以下 JSON：

【种子材料】
{seed_text}

【待校验 JSON】
{json_content}
""".format(seed_text=seed_text, json_content=json.dumps(json_content, ensure_ascii=False))


def local_validate_payload(payload: Any, level_name: str, required_fields: list[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["顶层不是 JSON object"]

    payload_keys = set(payload.keys())
    required_keys = set(required_fields)
    if payload_keys != required_keys:
        missing = [field for field in required_fields if field not in payload]
        extra = [field for field in payload.keys() if field not in required_keys]
        if missing:
            errors.append(f"缺少字段: {', '.join(missing)}")
        if extra:
            errors.append(f"多余字段: {', '.join(extra)}")

    for field in ("event_scale", "event_controversy"):
        if field in payload:
            value = payload[field]
            if not isinstance(value, (int, float)):
                errors.append(f"{field} 必须是数字")
            elif not 0.0 <= float(value) <= 1.0:
                errors.append(f"{field} 必须在 0.0-1.0 之间")

    if "event_summary" in required_fields:
        value = payload.get("event_summary")
        if not isinstance(value, str) or not value.strip():
            errors.append("event_summary 必须是非空字符串")
        elif len(value.strip()) > 50:
            errors.append("event_summary 长度必须不超过 50")

    if level_name == "L3":
        event_type = payload.get("event_type")
        reasoning = payload.get("reasoning")
        if not isinstance(event_type, str) or not event_type.strip():
            errors.append("event_type 必须是非空字符串")
        if not isinstance(reasoning, str) or not reasoning.strip():
            errors.append("reasoning 必须是非空字符串")

    return errors


def count_valid_fields(payload: Any, required_fields: list[str]) -> int:
    if not isinstance(payload, dict):
        return 0

    valid_count = 0
    for field in required_fields:
        value = payload.get(field)
        if field in ("event_scale", "event_controversy"):
            if isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0:
                valid_count += 1
        elif field == "event_summary":
            if isinstance(value, str) and value.strip() and len(value.strip()) <= 50:
                valid_count += 1
        elif field in {"event_type", "reasoning"}:
            if isinstance(value, str) and value.strip():
                valid_count += 1
    return valid_count


def aggregate_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    parse_fail_rate = sum(1 for record in records if not record["json_parse_ok"]) / total
    timeout_rate = sum(1 for record in records if record["timeout"]) / total
    validator_fail_rate = sum(
        1 for record in records if record["json_parse_ok"] and not record["validator_pass"]
    ) / total

    completeness_values = [
        record["output_field_completeness"]
        for record in records
        if record["json_parse_ok"]
    ]
    output_field_completeness_rate = (
        sum(completeness_values) / len(completeness_values) if completeness_values else 0.0
    )

    scale_values = [
        float(record["event_scale_value"])
        for record in records
        if record["event_scale_value"] is not None
    ]
    if scale_values:
        scale_min = min(scale_values)
        scale_max = max(scale_values)
        scale_range = scale_max - scale_min
        scale_stddev = statistics.pstdev(scale_values) if len(scale_values) > 1 else 0.0
    else:
        scale_min = None
        scale_max = None
        scale_range = None
        scale_stddev = None

    return {
        "parse_fail_rate": parse_fail_rate,
        "timeout_rate": timeout_rate,
        "validator_fail_rate": validator_fail_rate,
        "output_field_completeness_rate": output_field_completeness_rate,
        "event_scale_stability": {
            "min": scale_min,
            "max": scale_max,
            "range": scale_range,
            "stddev": scale_stddev,
            "values": scale_values,
        },
    }


def classify_level(metrics: dict[str, Any]) -> str:
    if (
        metrics["parse_fail_rate"] == 0.0
        and metrics["timeout_rate"] == 0.0
        and metrics["validator_fail_rate"] == 0.0
        and metrics["output_field_completeness_rate"] >= 1.0
    ):
        return "stable"
    if metrics["parse_fail_rate"] >= 0.5 or metrics["timeout_rate"] >= 0.5:
        return "collapsed"
    return "degraded"


def build_summary_markdown(
    run_dir_rel: Path,
    summary_payload: dict[str, Any],
) -> str:
    lines: list[str] = [
        "# P1-A Prompt Probe Summary",
        "",
        f"- generated_at: {summary_payload['generated_at']}",
        f"- baseline_path: `{summary_payload['baseline_path']}`",
        f"- run_dir: `{run_dir_rel.as_posix()}`",
        "",
        "## Model x Level",
        "",
        "| model | level | status | parse_fail_rate | timeout_rate | validator_fail_rate | completeness | scale_range | scale_stddev |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for model_name, level_data in summary_payload["metrics"].items():
        for level_name, metrics in level_data.items():
            stability = metrics["event_scale_stability"]
            lines.append(
                f"| {model_name} | {level_name} | {metrics['status']} | "
                f"{metrics['parse_fail_rate']:.3f} | {metrics['timeout_rate']:.3f} | "
                f"{metrics['validator_fail_rate']:.3f} | {metrics['output_field_completeness_rate']:.3f} | "
                f"{'n/a' if stability['range'] is None else f'{stability['range']:.3f}'} | "
                f"{'n/a' if stability['stddev'] is None else f'{stability['stddev']:.3f}'} |"
            )

    lines.extend(
        [
            "",
            "## Findings",
            "",
        ]
    )
    for item in summary_payload["findings"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def build_findings(metrics_by_model: dict[str, dict[str, dict[str, Any]]]) -> list[str]:
    findings: list[str] = []
    for model_name, level_data in metrics_by_model.items():
        statuses = {level: data["status"] for level, data in level_data.items()}
        stable_levels = [level for level, status in statuses.items() if status == "stable"]
        degraded_levels = [level for level, status in statuses.items() if status == "degraded"]
        collapsed_levels = [level for level, status in statuses.items() if status == "collapsed"]

        if len(stable_levels) == 3:
            findings.append(f"{model_name} 在 L1/L2/L3 下都稳定。")
        elif stable_levels == ["L1", "L2"] and statuses.get("L3") != "stable":
            findings.append(f"{model_name} 呈现“L1/L2 稳定，但 L3 崩或显著退化”。")
        elif collapsed_levels:
            findings.append(f"{model_name} 在复杂度上升后开始崩溃，最早失稳层级为 {collapsed_levels[0]}。")
        elif degraded_levels:
            findings.append(f"{model_name} 在 {', '.join(degraded_levels)} 出现退化，但未完全崩溃。")
        else:
            findings.append(f"{model_name} 结果需人工复核。")
    return findings


def run_case(
    *,
    model_name: str,
    level_name: str,
    level_spec: dict[str, Any],
    case: dict[str, Any],
    generator_client: LLMClient,
    validator_client: LLMClient,
    max_retry_count: int,
) -> dict[str, Any]:
    required_fields = list(level_spec["required_fields"])
    final_record: dict[str, Any] | None = None
    attempt_summaries: list[dict[str, Any]] = []
    error_feedback = ""

    for attempt in range(max_retry_count + 1):
        started = time.perf_counter()
        timeout = False
        generator_success = False
        validator_pass = False
        json_parse_ok = False
        parse_error: str | None = None
        exception_type: str | None = None
        exception_message: str | None = None
        validator_errors: list[str] = []
        validator_raw_response: Any = None
        output_field_completeness = 0.0
        event_scale_value: float | None = None
        parsed_payload: Any = None
        review_latency_sec = 0.0

        system_prompt = level_spec["system_prompt"]
        user_prompt = ANALYZER_USER_PROMPT.format(seed_text=case["seed_text"])
        if error_feedback:
            user_prompt = user_prompt.rstrip() + f"\n\n【上一轮错误反馈】\n{error_feedback}\n"

        try:
            generator_raw_response = generator_client.generate(system=system_prompt, user=user_prompt)
            generator_success = True
            json_parse_ok, parsed_payload, parse_error = parse_json_text(generator_raw_response)
            if json_parse_ok:
                output_field_completeness = (
                    count_valid_fields(parsed_payload, required_fields) / len(required_fields)
                )
                if isinstance(parsed_payload, dict):
                    scale_value = parsed_payload.get("event_scale")
                    if isinstance(scale_value, (int, float)) and 0.0 <= float(scale_value) <= 1.0:
                        event_scale_value = float(scale_value)

                    validator_system = build_validator_system_prompt(level_name, required_fields)
                    validator_user = build_validator_user_prompt(case["seed_text"], parsed_payload)
                    validator_started = time.perf_counter()
                    validator_raw_response = validator_client.generate(
                        system=validator_system,
                        user=validator_user,
                    )
                    review_latency_sec = time.perf_counter() - validator_started
                    validator_json_ok, validator_parsed, validator_parse_error = parse_json_text(
                        validator_raw_response
                    )
                    if validator_json_ok and isinstance(validator_parsed, dict):
                        validator_pass = bool(validator_parsed.get("pass"))
                        validator_errors = list(validator_parsed.get("errors", []))
                    elif validator_parse_error:
                        validator_errors = [validator_parse_error]
                    local_errors = local_validate_payload(parsed_payload, level_name, required_fields)
                    if local_errors:
                        validator_pass = False
                        validator_errors = local_errors
        except Exception as exc:
            exception_type = exc.__class__.__name__
            exception_message = str(exc)
            message = str(exc).lower()
            timeout = "timeout" in exception_type.lower() or "timeout" in message or "timed out" in message
            generator_raw_response = None
        end_to_end_latency_sec = time.perf_counter() - started
        generator_latency_sec = end_to_end_latency_sec - review_latency_sec

        attempt_summary = {
            "attempt": attempt,
            "json_parse_ok": json_parse_ok,
            "timeout": timeout,
            "validator_pass": validator_pass,
            "parse_error": parse_error,
            "validator_errors": validator_errors,
            "exception_type": exception_type,
            "exception_message": exception_message,
            "output_field_completeness": round(output_field_completeness, 6),
        }
        attempt_summaries.append(attempt_summary)

        final_record = {
            "timestamp": utc_now_iso(),
            "model_name": model_name,
            "level": level_name,
            "seed_case_id": case["case_id"],
            "required_fields": required_fields,
            "attempt": attempt,
            "attempt_count": attempt + 1,
            "max_retry_count": max_retry_count,
            "json_parse_ok": json_parse_ok,
            "timeout": timeout,
            "validator_pass": validator_pass,
            "validator_errors": validator_errors,
            "generator_success": generator_success,
            "generator_latency_sec": round(generator_latency_sec, 6),
            "review_latency_sec": round(review_latency_sec, 6),
            "end_to_end_latency_sec": round(end_to_end_latency_sec, 6),
            "exception_type": exception_type,
            "exception_message": exception_message,
            "parse_error": parse_error,
            "output_field_completeness": round(output_field_completeness, 6),
            "event_scale_value": event_scale_value,
            "attempt_summaries": attempt_summaries,
        }

        error_lines: list[str] = []
        if parse_error:
            error_lines.append(parse_error)
        error_lines.extend(validator_errors)
        if exception_message:
            error_lines.append(exception_message)
        error_feedback = "\n".join(f"- {item}" for item in error_lines) if error_lines else ""

        if validator_pass or timeout:
            break

    if final_record is None:
        raise RuntimeError("run_case did not produce a final record")
    return final_record


def main() -> int:
    manifest = load_json(BASELINE_MANIFEST_PATH)
    chain_manifest = manifest["chain_benchmark"]
    chain_runner = manifest["chain_runner"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_ROOT / f"run_{timestamp}_p1a_prompt_probe"
    run_dir.mkdir(parents=True, exist_ok=False)
    raw_log_path = run_dir / "p1a_probe_raw_logs.jsonl"
    summary_json_path = run_dir / "p1a_probe_summary.json"
    summary_md_path = run_dir / "p1a_probe_summary.md"

    max_retry_count = int(chain_manifest["max_retry_count"])
    request_timeout = float(chain_runner["timeout_sec"])
    provider = str(chain_manifest["provider"])
    api_key = str(chain_manifest["api_key"])
    base_url = str(chain_manifest["base_url"])
    generator_temperature = float(chain_manifest["generator_temperature"])
    validator_temperature = float(chain_manifest["validator_temperature"])
    max_tokens = int(chain_manifest["max_tokens"])
    validator_model_name = str(chain_manifest["validator_model"])
    cases = [
        case for case in chain_manifest["cases"] if case["case_id"] in {
            "case_1_mid_scale_mid_controversy",
            "case_2_midhigh_scale_high_controversy",
            "case_3_high_scale_high_controversy",
        }
    ]

    records: list[dict[str, Any]] = []
    metrics_by_model: dict[str, dict[str, dict[str, Any]]] = {}

    for model_name in TARGET_MODELS:
        console.print(f"[cyan]probe model:[/cyan] {model_name}")
        generator_client = LLMClient(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            temperature=generator_temperature,
            max_tokens=max_tokens,
            request_timeout=request_timeout,
        )
        validator_client = LLMClient(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=validator_model_name,
            temperature=validator_temperature,
            max_tokens=max_tokens,
            request_timeout=request_timeout,
        )

        model_metrics: dict[str, dict[str, Any]] = {}
        for level_name, level_spec in LEVEL_SPECS.items():
            console.print(f"  [magenta]level:[/magenta] {level_name}")
            level_records: list[dict[str, Any]] = []
            for case in cases:
                level_record = run_case(
                    model_name=model_name,
                    level_name=level_name,
                    level_spec=level_spec,
                    case=case,
                    generator_client=generator_client,
                    validator_client=validator_client,
                    max_retry_count=max_retry_count,
                )
                records.append(level_record)
                level_records.append(level_record)
            metrics = aggregate_metrics(level_records)
            metrics["status"] = classify_level(metrics)
            model_metrics[level_name] = metrics
        metrics_by_model[model_name] = model_metrics

    raw_text = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
    raw_log_path.write_text(raw_text + ("\n" if raw_text else ""), encoding="utf-8")

    findings = build_findings(metrics_by_model)
    summary_payload = {
        "generated_at": utc_now_iso(),
        "baseline_path": "profiling/output/baseline/v1.2.0_baseline",
        "run_dir": str(run_dir),
        "models": TARGET_MODELS,
        "levels": list(LEVEL_SPECS.keys()),
        "validator_model": validator_model_name,
        "metrics": metrics_by_model,
        "record_count": len(records),
        "findings": findings,
    }
    summary_json_path.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary_md = build_summary_markdown(run_dir.relative_to(PROJECT_ROOT), summary_payload)
    summary_md_path.write_text(summary_md, encoding="utf-8")

    console.print(f"[green]probe completed[/green]: {run_dir}")
    for model_name, level_data in metrics_by_model.items():
        for level_name, metrics in level_data.items():
            console.print(
                f"  {model_name} {level_name}: "
                f"parse_fail_rate={metrics['parse_fail_rate']:.3f}, "
                f"timeout_rate={metrics['timeout_rate']:.3f}, "
                f"validator_fail_rate={metrics['validator_fail_rate']:.3f}, "
                f"completeness={metrics['output_field_completeness_rate']:.3f}, "
                f"status={metrics['status']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
