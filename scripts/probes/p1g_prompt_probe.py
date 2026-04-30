"""Run prompt-aware profiling for the Phase 1 generator prompt family."""

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
from src.phase1_entity_extraction import GENERATOR_SYSTEM_PROMPT, GENERATOR_USER_PROMPT

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

REPEATS = 3

G1_SYSTEM_PROMPT = """你是一位资深的事件分析专家。你的任务是从事件材料中提取最小事件实体列表。

请只输出严格 JSON，格式固定为：
{
  "event_entities": [
    {
      "name": "实体名称",
      "type": "individual | organization | group",
      "role": "在事件中的角色"
    }
  ]
}

约束：
1. 顶层只允许 `event_entities`
2. `event_entities` 必须是数组，至少 1 个元素
3. 每个元素只允许 `name` / `type` / `role`
4. `type` 只允许 `individual` / `organization` / `group`
5. 不要输出解释，不要输出 markdown，不要输出代码块
"""

G2_SYSTEM_PROMPT = """你是一位资深的事件分析专家。你的任务是从事件材料中完成两项工作：
1. 提取事件实体
2. 生成最小意见传播者结构

【参数信息】
- event_scale: {event_scale}
- event_controversy: {event_controversy}
- 事件类型: {event_type}
- 事件摘要: {event_summary}

请只输出严格 JSON，格式固定为：
{{
  "event_entities": [
    {{
      "name": "实体名称",
      "type": "individual | organization | group",
      "role": "在事件中的角色"
    }}
  ],
  "opinion_spreaders": [
    {{
      "group_name": "群体名称",
      "related_event_entity": "关联事件实体",
      "description": "简短描述",
      "I": 0,
      "P": 1,
      "estimated_percentage": 30
    }}
  ]
}}

约束：
1. 顶层只允许 `event_entities` 和 `opinion_spreaders`
2. `related_event_entity` 必须引用 `event_entities.name`
3. `estimated_percentage` 总和约等于 100（允许 ±5）
4. 不要输出解释，不要输出 markdown，不要输出代码块
"""

LEVEL_SPECS: dict[str, dict[str, Any]] = {
    "G1": {"system_prompt": G1_SYSTEM_PROMPT},
    "G2": {"system_prompt": G2_SYSTEM_PROMPT},
    "G3": {"system_prompt": GENERATOR_SYSTEM_PROMPT},
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


def build_user_prompt(case: dict[str, Any], error_feedback: str) -> str:
    return GENERATOR_USER_PROMPT.format(
        seed_text=case["seed_text"],
        event_scale=case["event_scale"],
        event_controversy=case["event_controversy"],
        event_type=case["event_type"],
        event_summary=case["event_summary"],
        error_feedback=error_feedback or "首次生成，无反馈",
    )


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_type_ok(value: Any) -> bool:
    return value in {"individual", "organization", "group"}


def _validate_event_entities(items: Any, allow_extra: bool) -> tuple[list[str], int]:
    errors: list[str] = []
    valid_fields = 0
    if not isinstance(items, list):
        return ["event_entities 必须是数组"], 0
    if len(items) == 0:
        errors.append("event_entities 不能为空")
        return errors, 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"event_entities[{index}] 不是 object")
            continue
        allowed = {"name", "type", "role"}
        if not allow_extra:
            extra = [key for key in item.keys() if key not in allowed]
            if extra:
                errors.append(f"event_entities[{index}] 多余字段: {', '.join(extra)}")
        if _is_non_empty_str(item.get("name")):
            valid_fields += 1
        else:
            errors.append(f"event_entities[{index}].name 非法")
        if _is_type_ok(item.get("type")):
            valid_fields += 1
        else:
            errors.append(f"event_entities[{index}].type 非法")
        if _is_non_empty_str(item.get("role")):
            valid_fields += 1
        else:
            errors.append(f"event_entities[{index}].role 非法")
    return errors, valid_fields


def _validate_opinion_spreaders(items: Any, entity_names: set[str], allow_extra: bool) -> tuple[list[str], int]:
    errors: list[str] = []
    valid_fields = 0
    if not isinstance(items, list):
        return ["opinion_spreaders 必须是数组"], 0
    if len(items) == 0:
        errors.append("opinion_spreaders 不能为空")
        return errors, 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"opinion_spreaders[{index}] 不是 object")
            continue
        allowed = {"group_name", "related_event_entity", "description", "I", "P", "estimated_percentage"}
        if not allow_extra:
            extra = [key for key in item.keys() if key not in allowed]
            if extra:
                errors.append(f"opinion_spreaders[{index}] 多余字段: {', '.join(extra)}")
        if _is_non_empty_str(item.get("group_name")):
            valid_fields += 1
        else:
            errors.append(f"opinion_spreaders[{index}].group_name 非法")
        related = item.get("related_event_entity")
        if _is_non_empty_str(related):
            valid_fields += 1
            if entity_names and str(related).strip() not in entity_names:
                errors.append(f"opinion_spreaders[{index}].related_event_entity 未引用 event_entities.name")
        else:
            errors.append(f"opinion_spreaders[{index}].related_event_entity 非法")
        if _is_non_empty_str(item.get("description")):
            valid_fields += 1
        else:
            errors.append(f"opinion_spreaders[{index}].description 非法")
        i_value = item.get("I")
        if isinstance(i_value, (int, float)) and 0 <= float(i_value) <= 10:
            valid_fields += 1
        else:
            errors.append(f"opinion_spreaders[{index}].I 非法")
        if item.get("P") in {1, -1}:
            valid_fields += 1
        else:
            errors.append(f"opinion_spreaders[{index}].P 非法")
        percentage = item.get("estimated_percentage")
        if isinstance(percentage, int) and 0 <= percentage <= 100:
            valid_fields += 1
        else:
            errors.append(f"opinion_spreaders[{index}].estimated_percentage 非法")
    return errors, valid_fields


def validate_payload(level_name: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "structural_errors": ["顶层不是 JSON object"],
            "business_errors": [],
            "valid_fields": 0,
            "expected_fields": 0,
            "entity_count": None,
            "spreader_count": None,
            "empty_block": True,
        }

    structural_errors: list[str] = []
    business_errors: list[str] = []
    valid_fields = 0
    expected_fields = 0
    empty_block = False

    event_entities = payload.get("event_entities")
    allow_extra = level_name == "G3"
    entity_errors, entity_valid = _validate_event_entities(event_entities, allow_extra=allow_extra)
    structural_errors.extend(entity_errors)
    valid_fields += entity_valid
    entity_count = len(event_entities) if isinstance(event_entities, list) else None
    if entity_count == 0:
        empty_block = True
    if isinstance(event_entities, list):
        expected_fields += len(event_entities) * 3
    else:
        expected_fields += 3
    entity_names = {
        str(item.get("name")).strip()
        for item in event_entities
        if isinstance(item, dict) and _is_non_empty_str(item.get("name"))
    } if isinstance(event_entities, list) else set()

    spreader_count: int | None = None
    if level_name in {"G2", "G3"}:
        opinion_spreaders = payload.get("opinion_spreaders")
        spreader_errors, spreader_valid = _validate_opinion_spreaders(
            opinion_spreaders, entity_names, allow_extra=allow_extra
        )
        structural_errors.extend(spreader_errors)
        valid_fields += spreader_valid
        spreader_count = len(opinion_spreaders) if isinstance(opinion_spreaders, list) else None
        if spreader_count == 0:
            empty_block = True
        if isinstance(opinion_spreaders, list):
            expected_fields += len(opinion_spreaders) * 6
            total_percentage = sum(
                item.get("estimated_percentage", 0)
                for item in opinion_spreaders
                if isinstance(item, dict) and isinstance(item.get("estimated_percentage"), int)
            )
            if abs(total_percentage - 100) > 5:
                business_errors.append("estimated_percentage 总和未落在 100±5")
            p_values = {
                item.get("P")
                for item in opinion_spreaders
                if isinstance(item, dict)
            }
            if not ({1, -1} <= p_values):
                business_errors.append("未同时存在 P=1 和 P=-1")
        else:
            expected_fields += 6

    if level_name == "G1":
        extra_top_keys = [key for key in payload.keys() if key != "event_entities"]
        if extra_top_keys:
            structural_errors.append(f"顶层多余字段: {', '.join(extra_top_keys)}")
    elif level_name == "G2":
        extra_top_keys = [key for key in payload.keys() if key not in {"event_entities", "opinion_spreaders"}]
        if extra_top_keys:
            structural_errors.append(f"顶层多余字段: {', '.join(extra_top_keys)}")

    return {
        "structural_errors": structural_errors,
        "business_errors": business_errors,
        "valid_fields": valid_fields,
        "expected_fields": expected_fields,
        "entity_count": entity_count,
        "spreader_count": spreader_count,
        "empty_block": empty_block,
    }


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def stddev(values: list[float]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return 0.0
    return statistics.pstdev(values)


def summarize_count(values: list[int | None]) -> dict[str, float | None]:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return {"min": None, "max": None, "mean": None, "std": None}
    return {
        "min": min(clean),
        "max": max(clean),
        "mean": mean(clean),
        "std": stddev(clean),
    }


def aggregate_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    parse_fail_rate = sum(1 for r in records if not r["json_parse_ok"]) / total
    timeout_rate = sum(1 for r in records if r["timeout"]) / total
    structural_rate = sum(1 for r in records if r["json_parse_ok"] and r["structural_fail"]) / total
    business_rate = sum(
        1 for r in records if r["json_parse_ok"] and not r["structural_fail"] and r["business_fail"]
    ) / total
    completeness_values = [r["output_field_completeness"] for r in records if r["json_parse_ok"]]
    retry_counts = [r["retry_count"] for r in records]
    return {
        "parse_fail_rate": parse_fail_rate,
        "timeout_rate": timeout_rate,
        "validator_fail_rate_structural": structural_rate,
        "validator_fail_rate_business": business_rate,
        "output_field_completeness_rate": mean(completeness_values) or 0.0,
        "avg_retry_count": mean(retry_counts) or 0.0,
        "retry_used_rate": sum(1 for r in records if r["retry_count"] > 0) / total,
        "event_entity_count": summarize_count([r["entity_count"] for r in records]),
        "opinion_spreader_count": summarize_count([r["spreader_count"] for r in records]),
        "empty_block_rate": sum(1 for r in records if r["empty_block"]) / total,
    }


def classify_level(metrics: dict[str, Any]) -> str:
    if (
        metrics["parse_fail_rate"] == 0.0
        and metrics["timeout_rate"] == 0.0
        and metrics["validator_fail_rate_structural"] == 0.0
        and metrics["output_field_completeness_rate"] >= 1.0
    ):
        return "stable"
    if metrics["parse_fail_rate"] >= 0.5 or metrics["timeout_rate"] >= 0.5:
        return "collapsed"
    return "degraded"


def build_findings(metrics_by_model: dict[str, dict[str, dict[str, Any]]]) -> tuple[list[str], str]:
    findings: list[str] = []
    g1_stable: list[str] = []
    g2_degraded: list[str] = []
    g3_only_fail: list[str] = []
    g1_unstable: list[str] = []

    for model_name, level_data in metrics_by_model.items():
        statuses = {level: data["status"] for level, data in level_data.items()}
        if statuses["G1"] == "stable":
            g1_stable.append(model_name)
        else:
            g1_unstable.append(model_name)
        if statuses["G1"] == "stable" and statuses["G2"] != "stable":
            g2_degraded.append(model_name)
        if statuses["G1"] == "stable" and statuses["G2"] == "stable" and statuses["G3"] != "stable":
            g3_only_fail.append(model_name)

    findings.append("G1 稳定模型: " + (", ".join(g1_stable) if g1_stable else "无"))
    findings.append("G2 开始退化模型: " + (", ".join(g2_degraded) if g2_degraded else "无"))
    findings.append("仅在 G3 崩溃模型: " + (", ".join(g3_only_fail) if g3_only_fail else "无"))
    findings.append("G1 就不稳定模型: " + (", ".join(g1_unstable) if g1_unstable else "无"))

    if g3_only_fail:
        bottleneck = "production generator schema"
    elif g2_degraded:
        bottleneck = "opinion_spreaders schema layer"
    elif g1_unstable:
        bottleneck = "generator base output layer"
    else:
        bottleneck = "Generator not confirmed as bottleneck; shift to downstream chain integration"
    findings.append(f"P1-A stable + P1-G result => bottleneck location = {bottleneck}")
    return findings, bottleneck


def build_summary_markdown(run_dir_rel: Path, summary_payload: dict[str, Any]) -> str:
    lines = [
        "# P1-G Prompt Probe Summary",
        "",
        f"- generated_at: {summary_payload['generated_at']}",
        f"- baseline_path: `{summary_payload['baseline_path']}`",
        f"- run_dir: `{run_dir_rel.as_posix()}`",
        f"- bottleneck_location: {summary_payload['bottleneck_location']}",
        "",
        "## Model x Level",
        "",
        "| model | level | status | parse_fail | timeout | structural_fail | business_fail | completeness | avg_retry | retry_used | empty_block |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for model_name, level_data in summary_payload["metrics"].items():
        for level_name, metrics in level_data.items():
            lines.append(
                f"| {model_name} | {level_name} | {metrics['status']} | "
                f"{metrics['parse_fail_rate']:.3f} | {metrics['timeout_rate']:.3f} | "
                f"{metrics['validator_fail_rate_structural']:.3f} | {metrics['validator_fail_rate_business']:.3f} | "
                f"{metrics['output_field_completeness_rate']:.3f} | {metrics['avg_retry_count']:.3f} | "
                f"{metrics['retry_used_rate']:.3f} | {metrics['empty_block_rate']:.3f} |"
            )
    lines.extend(["", "## Findings", ""])
    for item in summary_payload["findings"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def run_repeat(
    *,
    model_name: str,
    level_name: str,
    case: dict[str, Any],
    generator_client: LLMClient,
    validator_client: LLMClient,
    max_retry_count: int,
) -> dict[str, Any]:
    error_feedback = ""
    attempt = 0
    final_record: dict[str, Any] | None = None
    attempt_logs: list[dict[str, Any]] = []

    for attempt in range(max_retry_count + 1):
        started = time.perf_counter()
        timeout = False
        generator_success = False
        json_parse_ok = False
        parse_error: str | None = None
        exception_type: str | None = None
        exception_message: str | None = None
        structural_errors: list[str] = []
        business_errors: list[str] = []
        entity_count: int | None = None
        spreader_count: int | None = None
        empty_block = False
        output_field_completeness = 0.0
        review_latency_sec = 0.0

        system_prompt = LEVEL_SPECS[level_name]["system_prompt"]
        if level_name == "G2":
            system_prompt = system_prompt.format(
                event_scale=case["event_scale"],
                event_controversy=case["event_controversy"],
                event_type=case["event_type"],
                event_summary=case["event_summary"],
            )
        user_prompt = build_user_prompt(case, error_feedback)

        try:
            generator_raw_response = generator_client.generate(system=system_prompt, user=user_prompt)
            generator_success = True
            json_parse_ok, parsed_payload, parse_error = parse_json_text(generator_raw_response)
            if json_parse_ok:
                validation = validate_payload(level_name, parsed_payload)
                structural_errors = validation["structural_errors"]
                business_errors = validation["business_errors"]
                entity_count = validation["entity_count"]
                spreader_count = validation["spreader_count"]
                empty_block = validation["empty_block"]
                expected_fields = validation["expected_fields"]
                valid_fields = validation["valid_fields"]
                output_field_completeness = (valid_fields / expected_fields) if expected_fields else 0.0

                validator_started = time.perf_counter()
                validator_system = "你是一位结构审阅器。请只回答 pass=true/false。"
                validator_user = json.dumps(parsed_payload, ensure_ascii=False)
                _ = validator_client.generate(system=validator_system, user=validator_user)
                review_latency_sec = time.perf_counter() - validator_started
        except Exception as exc:
            exception_type = exc.__class__.__name__
            exception_message = str(exc)
            message = str(exc).lower()
            timeout = "timeout" in exception_type.lower() or "timeout" in message or "timed out" in message

        end_to_end_latency_sec = time.perf_counter() - started
        final_record = {
            "timestamp": utc_now_iso(),
            "model_name": model_name,
            "level": level_name,
            "seed_case_id": case["case_id"],
            "attempt": attempt,
            "json_parse_ok": json_parse_ok,
            "timeout": timeout,
            "generator_success": generator_success,
            "parse_error": parse_error,
            "exception_type": exception_type,
            "exception_message": exception_message,
            "structural_errors": structural_errors,
            "business_errors": business_errors,
            "structural_fail": bool(structural_errors),
            "business_fail": bool(business_errors),
            "output_field_completeness": round(output_field_completeness, 6),
            "entity_count": entity_count,
            "spreader_count": spreader_count,
            "empty_block": empty_block,
            "generator_latency_sec": round(end_to_end_latency_sec - review_latency_sec, 6),
            "review_latency_sec": round(review_latency_sec, 6),
            "end_to_end_latency_sec": round(end_to_end_latency_sec, 6),
        }
        attempt_logs.append(
            {
                "attempt": attempt,
                "json_parse_ok": json_parse_ok,
                "timeout": timeout,
                "parse_error": parse_error,
                "structural_errors": structural_errors,
                "business_errors": business_errors,
                "exception_type": exception_type,
            }
        )
        error_items: list[str] = []
        if parse_error:
            error_items.append(parse_error)
        error_items.extend(structural_errors)
        if exception_message:
            error_items.append(exception_message)
        error_feedback = "\n".join(f"- {item}" for item in error_items) if error_items else ""
        if (json_parse_ok and not structural_errors) or timeout:
            break

    if final_record is None:
        raise RuntimeError("repeat did not produce a record")
    final_record["retry_count"] = attempt
    final_record["repeat_attempt_logs"] = attempt_logs
    return final_record


def main() -> int:
    manifest = load_json(BASELINE_MANIFEST_PATH)
    chain_manifest = manifest["chain_benchmark"]
    chain_runner = manifest["chain_runner"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_ROOT / f"run_{timestamp}_p1g_prompt_probe"
    run_dir.mkdir(parents=True, exist_ok=False)
    raw_log_path = run_dir / "p1g_probe_raw_logs.jsonl"
    summary_json_path = run_dir / "p1g_probe_summary.json"
    summary_md_path = run_dir / "p1g_probe_summary.md"

    provider = str(chain_manifest["provider"])
    api_key = str(chain_manifest["api_key"])
    base_url = str(chain_manifest["base_url"])
    generator_temperature = float(chain_manifest["generator_temperature"])
    validator_temperature = float(chain_manifest["validator_temperature"])
    max_tokens = int(chain_manifest["max_tokens"])
    request_timeout = float(chain_runner["timeout_sec"])
    max_retry_count = int(chain_manifest["max_retry_count"])
    validator_model_name = str(chain_manifest["validator_model"])
    cases = [
        case for case in chain_manifest["cases"]
        if case["case_id"] in {
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
        level_metrics: dict[str, dict[str, Any]] = {}
        for level_name in ("G1", "G2", "G3"):
            console.print(f"  [magenta]level:[/magenta] {level_name}")
            level_records: list[dict[str, Any]] = []
            for case in cases:
                for repeat_index in range(REPEATS):
                    record = run_repeat(
                        model_name=model_name,
                        level_name=level_name,
                        case=case,
                        generator_client=generator_client,
                        validator_client=validator_client,
                        max_retry_count=max_retry_count,
                    )
                    record["repeat_index"] = repeat_index
                    records.append(record)
                    level_records.append(record)
            metrics = aggregate_metrics(level_records)
            metrics["status"] = classify_level(metrics)
            level_metrics[level_name] = metrics
        metrics_by_model[model_name] = level_metrics

    raw_text = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
    raw_log_path.write_text(raw_text + ("\n" if raw_text else ""), encoding="utf-8")
    findings, bottleneck = build_findings(metrics_by_model)
    summary_payload = {
        "generated_at": utc_now_iso(),
        "baseline_path": "profiling/output/baseline/v1.2.0_baseline",
        "run_dir": str(run_dir),
        "record_count": len(records),
        "models": TARGET_MODELS,
        "levels": ["G1", "G2", "G3"],
        "repeats": REPEATS,
        "validator_model": validator_model_name,
        "metrics": metrics_by_model,
        "findings": findings,
        "bottleneck_location": bottleneck,
    }
    summary_json_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md_path.write_text(
        build_summary_markdown(run_dir.relative_to(PROJECT_ROOT), summary_payload),
        encoding="utf-8",
    )
    console.print(f"[green]probe completed[/green]: {run_dir}")
    console.print(f"records={len(records)} bottleneck={bottleneck}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
