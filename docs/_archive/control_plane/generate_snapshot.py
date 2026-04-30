"""Generate a minimal Chinese control snapshot from state + inbox + baseline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTROL_DIR = PROJECT_ROOT / "control"
STATE_PATH = CONTROL_DIR / "state.json"
INBOX_PATH = CONTROL_DIR / "inbox.md"
SNAPSHOT_PATH = CONTROL_DIR / "snapshot.md"


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def format_metric(value: float) -> str:
    return f"{value:.3f}"


def extract_adopted_items(inbox_text: str) -> list[str]:
    items: list[str] = []
    current_section = ""
    for raw_line in inbox_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current_section = line[3:].strip()
            continue
        if current_section == "已采纳" and line.startswith("- "):
            items.append(line)
    return items[-3:]


def build_snapshot(
    state: dict,
    baseline_profile: dict,
    baseline_summary: str,
    adopted_items: list[str],
) -> str:
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    failure_summary = state["failure_summary"]
    execution_hygiene = baseline_profile.get("execution_hygiene", {})
    profiling = state.get("profiling", {})
    p1a_probe = profiling.get("p1a_analyzer_probe", {})

    lines: list[str] = [
        "# Snapshot",
        "",
        f"- 生成时间: {generated_at}",
        f"- 当前焦点: {state['current_focus']}",
        f"- 当前状态: {state['status']}",
        f"- Baseline 路径: `{state['baseline_path']}`",
        f"- 最新 Run 路径: `{state['latest_run_path']}`",
        "",
        "## 状态总览",
        "",
        "- 当前 profiling 决策只认 baseline。",
        "- `runs` 是实验记录，不替代 baseline。",
        "- `logs` 是诊断噪声，只有排障时才进入主视图。",
        "",
        "## 进展",
        "",
        "- 已建立最小控制层：`state.json -> inbox.md -> snapshot.md`",
        "- 已锁定当前可信 baseline：`profiling/output/baseline/v1.2.0_baseline`",
        "- 已完成 80b / 122b 的简版 failure matrix 收口",
        "- P1-A Analyzer probe 已确认：Analyzer 不是当前瓶颈",
        "",
        "## 风险提示",
        "",
        "- `qwen3-80b-tke` 与 `qwen35-122b-a10b` 当前主要表现为 parse fail，而不是 timeout。",
        f"- baseline 仍是 incomplete_profile={baseline_profile.get('incomplete_profile', 'unknown')}。",
        f"- execution_hygiene: timeout_count={execution_hygiene.get('timeout_count', 'unknown')}, killed_count={execution_hygiene.get('killed_count', 'unknown')}。",
        "",
        "## 最新反馈",
        "",
    ]

    if adopted_items:
        lines.extend(adopted_items)
    else:
        lines.append("- 暂无")

    if p1a_probe:
        lines.extend(
            [
                "",
                "## 已确认事实",
                "",
                f"- P1-A Analyzer probe 状态: {p1a_probe.get('status', 'unknown')}",
                f"- P1-A run: `{p1a_probe.get('run_path', 'unknown')}`",
            ]
        )
        for item in p1a_probe.get("conclusion", []):
            lines.append(f"- {item}")
        implication = p1a_probe.get("implication")
        if implication:
            lines.append(f"- implication: {implication}")

    lines.extend(
        [
            "",
            "## Profiling 口径",
            "",
            "- baseline: `profiling/output/baseline/*`",
            "- runs: `profiling/output/runs/*`, `profiling/output/final_profile/*/runs/*`",
            "- logs: `profiling/output/concurrent_logs*`, `profiling/output/raw_logs/_worker_tmp*`, `profiling/output/small_profile_run_output.txt`",
            "",
            "## Baseline 概览",
            "",
            f"- 生成时间: {baseline_profile.get('generated_at', 'unknown')}",
            f"- 模型数: {baseline_profile.get('model_count', 'unknown')}",
            f"- 记录数: {baseline_profile.get('record_count', 'unknown')}",
            f"- incomplete_profile: {baseline_profile.get('incomplete_profile', 'unknown')}",
            "",
            "## Failure Matrix",
            "",
            "| 模型 | parse_fail_rate | timeout_rate | validator_fail_rate |",
            "| --- | --- | --- | --- |",
        ]
    )

    for model_key, metrics in failure_summary.items():
        lines.append(
            f"| {model_key} | {format_metric(metrics['parse_fail_rate'])} | "
            f"{format_metric(metrics['timeout_rate'])} | {format_metric(metrics['validator_fail_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## 待决策问题",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in state["open_decisions"])
    lines.extend(
        [
            "",
            "## 建议下一步",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in state["next_actions"])
    lines.extend(
        [
            "",
            "## Baseline 摘要附录",
            "",
            "```md",
            baseline_summary.strip(),
            "```",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    state = load_json(STATE_PATH)
    inbox_text = INBOX_PATH.read_text(encoding="utf-8")
    adopted_items = extract_adopted_items(inbox_text)

    baseline_root = PROJECT_ROOT / state["baseline_path"]
    baseline_profile_path = baseline_root / "model_profiles_v1.2.0_baseline.json"
    baseline_summary_path = baseline_root / "profile_summary_v1.2.0_baseline.md"

    baseline_profile = load_json(baseline_profile_path)
    baseline_summary = baseline_summary_path.read_text(encoding="utf-8")
    snapshot = build_snapshot(state, baseline_profile, baseline_summary, adopted_items)
    SNAPSHOT_PATH.write_text(snapshot, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
