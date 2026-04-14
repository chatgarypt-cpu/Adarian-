"""Run a reduced-schema chain probe for selected models without touching the profiling pipeline."""

from __future__ import annotations

import json
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

import config
from src.llm_client import LLMClient

CONTROL_DIR = PROJECT_ROOT / "control"
STATE_PATH = CONTROL_DIR / "state.json"
INBOX_PATH = CONTROL_DIR / "inbox.md"
BASELINE_MANIFEST_PATH = (
    PROJECT_ROOT
    / "profiling"
    / "output"
    / "baseline"
    / "v1.2.0_baseline"
    / "run_manifest.snapshot_v1.2.0_baseline.json"
)
PROBE_ROOT = PROJECT_ROOT / "profiling" / "output" / "probes"
TARGET_MODELS = ["qwen3-80b-tke", "qwen35-122b-a10b"]

GENERATOR_SYSTEM_TEMPLATE = """你是一位事件信息压缩助手。你的任务是从事件材料中抽取最小平面结构。

保持和原 chain 相同的分析目标，但不要输出嵌套对象，不要输出复杂约束字段。

【参数信息】
- event_scale: {event_scale}
- event_controversy: {event_controversy}
- event_type: {event_type}
- event_summary: {event_summary}

请只输出严格 JSON，格式固定为：
{{
  "items": [
    {{"id": "e1", "label": "event_entity", "content": "核心事件实体或角色"}},
    {{"id": "o1", "label": "opinion", "content": "一种代表性观点或群体"}},
    {{"id": "r1", "label": "relation", "content": "一个关键关系或冲突"}}
  ]
}}

约束：
1. 只允许一个顶层字段 `items`
2. `items` 必须是数组，长度 3-8
3. 每个元素只允许 `id` / `label` / `content` 三个字段
4. `label` 只允许 `event_entity` / `opinion` / `relation`
5. `content` 用一句中文表达，尽量不超过40字
6. 不要输出解释，不要输出 markdown，不要输出代码块
"""

GENERATOR_USER_TEMPLATE = """请根据以下材料生成 reduced-schema JSON：

【种子文本】
{seed_text}

【上一轮错误反馈】（如果是首次生成则忽略）
{error_feedback}
"""

VALIDATOR_SYSTEM_PROMPT = """你是一位严格的格式校验专家。你的任务是检查输入 JSON 是否符合 reduced-schema 要求。

【校验规则】
1. 必须是合法 JSON
2. 顶层必须只包含 `items`
3. `items` 必须是数组，长度 3-8
4. 每个元素必须且只允许包含 `id`、`label`、`content`
5. `id` 必须是非空字符串
6. `label` 必须是 `event_entity` / `opinion` / `relation`
7. `content` 必须是非空字符串
8. 不允许嵌套对象或数组作为元素字段值

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

VALIDATOR_USER_TEMPLATE = """请校验以下 JSON：

【种子文本】
{seed_text}

【待校验 JSON】
{json_content}
"""


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def build_generator_prompts(case: dict[str, Any], error_feedback: str) -> tuple[str, str]:
    system = GENERATOR_SYSTEM_TEMPLATE.format(
        event_scale=case["event_scale"],
        event_controversy=case["event_controversy"],
        event_type=case["event_type"],
        event_summary=case["event_summary"],
    )
    user = GENERATOR_USER_TEMPLATE.format(
        seed_text=case["seed_text"],
        error_feedback=error_feedback or "首次生成，无反馈",
    )
    return system, user


def build_validator_prompts(seed_text: str, json_content: dict[str, Any]) -> tuple[str, str]:
    user = VALIDATOR_USER_TEMPLATE.format(
        seed_text=seed_text,
        json_content=json.dumps(json_content, ensure_ascii=False),
    )
    return VALIDATOR_SYSTEM_PROMPT, user


def validate_reduced_payload(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["顶层不是 JSON object"]
    if set(payload.keys()) != {"items"}:
        errors.append("顶层字段必须且只允许为 items")
        return errors
    items = payload.get("items")
    if not isinstance(items, list):
        return ["items 必须是数组"]
    if not 3 <= len(items) <= 8:
        errors.append("items 数量必须在 3 到 8 之间")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{index}] 不是 object")
            continue
        if set(item.keys()) != {"id", "label", "content"}:
            errors.append(f"items[{index}] 字段必须且只允许为 id/label/content")
            continue
        if not isinstance(item["id"], str) or not item["id"].strip():
            errors.append(f"items[{index}].id 必须是非空字符串")
        if item["label"] not in {"event_entity", "opinion", "relation"}:
            errors.append(f"items[{index}].label 非法")
        if not isinstance(item["content"], str) or not item["content"].strip():
            errors.append(f"items[{index}].content 必须是非空字符串")
        for key in ("id", "label", "content"):
            if isinstance(item[key], (dict, list)):
                errors.append(f"items[{index}].{key} 不能是嵌套结构")
    return errors


def aggregate_metrics(records: list[dict[str, Any]], model_name: str) -> dict[str, float]:
    model_records = [record for record in records if record["model_name"] == model_name]
    if not model_records:
        return {"parse_fail_rate": 0.0, "timeout_rate": 0.0, "validator_fail_rate": 0.0}

    total = len(model_records)
    parse_fail_count = sum(1 for record in model_records if not record["json_parse_ok"])
    timeout_count = sum(1 for record in model_records if record["timeout"])
    validator_fail_count = sum(
        1 for record in model_records if record["json_parse_ok"] and not record["validator_pass"]
    )
    return {
        "parse_fail_rate": parse_fail_count / total,
        "timeout_rate": timeout_count / total,
        "validator_fail_rate": validator_fail_count / total,
    }


def append_inbox_result(probe_dir: Path, metrics: dict[str, dict[str, float]]) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    def fmt(model: str) -> str:
        item = metrics[model]
        return (
            f"{model}: parse_fail_rate={item['parse_fail_rate']:.3f}, "
            f"timeout_rate={item['timeout_rate']:.3f}, "
            f"validator_fail_rate={item['validator_fail_rate']:.3f}"
        )

    conclusion_parts: list[str] = []
    for model in TARGET_MODELS:
        if metrics[model]["parse_fail_rate"] < 1.0:
            conclusion_parts.append(f"{model} 的 parse fail 明显下降，说明模型可用性受 schema 复杂度影响")
        else:
            conclusion_parts.append(f"{model} 的 parse fail 未下降，说明问题不只是 schema 复杂度")
    line = (
        f"- [{today}] Codex reduced-schema chain probe 完成；"
        f"{fmt(TARGET_MODELS[0])}；{fmt(TARGET_MODELS[1])}；"
        f"{'；'.join(conclusion_parts)}；产物目录：`{probe_dir.relative_to(PROJECT_ROOT)}`"
    )

    inbox_text = INBOX_PATH.read_text(encoding="utf-8")
    marker = "## 待处理"
    if marker not in inbox_text:
        inbox_text = inbox_text.rstrip() + f"\n\n{marker}\n\n{line}\n"
    else:
        inbox_text = inbox_text.replace(marker, marker + f"\n\n{line}", 1)
    INBOX_PATH.write_text(inbox_text, encoding="utf-8")


def main() -> int:
    state = load_json(STATE_PATH)
    manifest = load_json(BASELINE_MANIFEST_PATH)
    chain_manifest = manifest["chain_benchmark"]
    chain_runner = manifest["chain_runner"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    probe_dir = PROBE_ROOT / f"reduced_schema_chain_probe_{timestamp}"
    probe_dir.mkdir(parents=True, exist_ok=False)
    raw_log_path = probe_dir / "probe_raw_logs.jsonl"
    summary_path = probe_dir / "probe_summary.json"

    records: list[dict[str, Any]] = []
    for model_name in TARGET_MODELS:
        console.print(f"[cyan]probe model:[/cyan] {model_name}")
        generator_client = LLMClient(
            provider=chain_manifest["provider"],
            api_key=chain_manifest["api_key"],
            base_url=chain_manifest["base_url"],
            model=model_name,
            temperature=float(chain_manifest["generator_temperature"]),
            max_tokens=int(chain_manifest["max_tokens"]),
            request_timeout=float(chain_runner["timeout_sec"]),
        )
        validator_client = LLMClient(
            provider=chain_manifest["provider"],
            api_key=chain_manifest["api_key"],
            base_url=chain_manifest["base_url"],
            model=chain_manifest["validator_model"],
            temperature=float(chain_manifest["validator_temperature"]),
            max_tokens=int(chain_manifest["max_tokens"]),
            request_timeout=float(chain_runner["timeout_sec"]),
        )

        for case in chain_manifest["cases"]:
            error_feedback = ""
            for attempt in range(int(chain_manifest["max_retry_count"]) + 1):
                started = time.perf_counter()
                generator_system, generator_user = build_generator_prompts(case, error_feedback)
                timeout = False
                empty_response = False
                generator_success = False
                validator_pass = False
                json_parse_ok = False
                validator_errors: list[str] = []
                generator_raw_response: Any = None
                validator_raw_response: Any = None
                exception_type: str | None = None
                exception_message: str | None = None
                review_latency_sec = 0.0
                parse_error: str | None = None

                try:
                    generator_raw_response = generator_client.generate(
                        system=generator_system,
                        user=generator_user,
                    )
                    generator_success = True
                    empty_response = generator_raw_response is None or (
                        isinstance(generator_raw_response, str) and not generator_raw_response.strip()
                    )
                    json_parse_ok, generator_parsed_json, parse_error = parse_json_text(generator_raw_response)
                    if json_parse_ok and isinstance(generator_parsed_json, dict):
                        validator_system, validator_user = build_validator_prompts(
                            case["seed_text"], generator_parsed_json
                        )
                        validator_started = time.perf_counter()
                        validator_raw_response = validator_client.generate(
                            system=validator_system,
                            user=validator_user,
                        )
                        review_latency_sec = time.perf_counter() - validator_started
                        validator_json_ok, validator_json, validator_parse_error = parse_json_text(validator_raw_response)
                        if validator_json_ok and isinstance(validator_json, dict):
                            validator_pass = bool(validator_json.get("pass"))
                            validator_errors = list(validator_json.get("errors", []))
                        elif validator_parse_error:
                            validator_errors = [validator_parse_error]
                        local_errors = validate_reduced_payload(generator_parsed_json)
                        if local_errors:
                            validator_pass = False
                            validator_errors = local_errors
                except Exception as exc:
                    exception_type = exc.__class__.__name__
                    exception_message = str(exc)
                    timeout = "timeout" in exception_type.lower() or "timeout" in exception_message.lower()
                finally:
                    elapsed = time.perf_counter() - started

                record = {
                    "timestamp": utc_now_iso(),
                    "model_name": model_name,
                    "seed_case_id": case["case_id"],
                    "attempt": attempt,
                    "json_parse_ok": json_parse_ok,
                    "timeout": timeout,
                    "validator_pass": validator_pass,
                    "validator_errors": validator_errors,
                    "generator_success": generator_success,
                    "empty_response": empty_response,
                    "generator_latency_sec": round(elapsed - review_latency_sec, 6),
                    "review_latency_sec": round(review_latency_sec, 6),
                    "end_to_end_latency_sec": round(elapsed, 6),
                    "exception_type": exception_type,
                    "exception_message": exception_message,
                    "parse_error": parse_error,
                }
                records.append(record)

                error_feedback_lines: list[str] = []
                if parse_error:
                    error_feedback_lines.append(parse_error)
                error_feedback_lines.extend(validator_errors)
                error_feedback = "\n".join(f"- {item}" for item in error_feedback_lines) if error_feedback_lines else ""

                if validator_pass or timeout:
                    break

    raw_log_text = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
    raw_log_path.write_text(raw_log_text + ("\n" if raw_log_text else ""), encoding="utf-8")

    metrics = {model: aggregate_metrics(records, model) for model in TARGET_MODELS}
    summary_payload = {
        "generated_at": utc_now_iso(),
        "baseline_path": state["baseline_path"],
        "probe_dir": str(probe_dir),
        "models": TARGET_MODELS,
        "metrics": metrics,
        "record_count": len(records),
        "comparison_note": "Compare against baseline where both models had parse_fail_rate=1.0, timeout_rate=0.0, validator_fail_rate=0.0.",
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    append_inbox_result(probe_dir, metrics)

    console.print(f"[green]probe completed[/green]: {probe_dir}")
    for model_name in TARGET_MODELS:
        item = metrics[model_name]
        console.print(
            f"  {model_name}: parse_fail_rate={item['parse_fail_rate']:.3f}, "
            f"timeout_rate={item['timeout_rate']:.3f}, validator_fail_rate={item['validator_fail_rate']:.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
