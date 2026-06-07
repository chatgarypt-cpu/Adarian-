"""run.log 尾部摘要写入器。

单一职责：在运行结束后，将各模块收集的 summary dict 拼成
稳定 section heading 的纯文本块，追加到 run.log 尾部。
不自产数据，不落其他文件。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def append_run_summary(
    log_path: str | Path,
    *,
    run_status: str,
    run_started_at: Optional[str] = None,
    run_elapsed: Optional[float] = None,
    seed_name: Optional[str] = None,
    model_name: Optional[str] = None,
    runtime_summary: Optional[Dict[str, Any]] = None,
    token_summary: Optional[Dict[str, Any]] = None,
    extra_lines: Optional[list[str]] = None,
) -> None:
    """将运行摘要追加到 run.log 尾部。

    Args:
        log_path: run.log 路径
        run_status: success / failed / interrupted
        run_started_at: 启动时间
        run_elapsed: 总耗时（秒）
        seed_name: 种子文件名
        model_name: 模型名称
        runtime_summary: RuntimeLogger.get_summary() 返回的运行时摘要
        token_summary: TokenTracker.get_summary() 返回的 token 摘要
        extra_lines: 额外行（如产物完整性信息）
    """
    log_path = Path(log_path)
    lines: list[str] = []

    _sep(lines)
    _heading(lines, "RUN SUMMARY")
    lines.append(f"status:         {run_status}")
    if run_started_at:
        lines.append(f"started_at:     {run_started_at}")
    if run_elapsed is not None:
        lines.append(f"duration:       {run_elapsed:.1f}s")
    if seed_name:
        lines.append(f"seed:           {seed_name}")
    if model_name:
        lines.append(f"model:          {model_name}")

    # ── Phase 耗时 ──────────────────────────────────────────
    if runtime_summary:
        phases = runtime_summary.get("phases", {})
        if phases:
            lines.append("")
            _heading(lines, "PHASE SUMMARY")
            max_name = max(len(n) for n in phases) if phases else 10
            for name in sorted(phases):
                p = phases[name]
                elapsed = p.get("elapsed_seconds", 0)
                label = f"  {name:<{max_name}}  {elapsed:>8.1f}s"
                lines.append(label)

        # ── Tick 简况 ────────────────────────────────────────
        ticks = runtime_summary.get("ticks", [])
        if ticks:
            lines.append("")
            _heading(lines, "TICK SUMMARY")
            total_llm = sum(t.get("llm_calls", 0) for t in ticks)
            lines.append(f"  ticks:    {len(ticks)}")
            lines.append(f"  llm_calls: {total_llm}")

    # ── Token ───────────────────────────────────────────────
    if token_summary:
        lines.append("")
        _heading(lines, "TOKEN SUMMARY")
        lines.append(f"  total_calls:    {token_summary.get('total_calls', 0)}")
        lines.append(f"  prompt_tokens:  {token_summary.get('total_prompt_tokens', 0)}")
        lines.append(f"  completion_tokens: {token_summary.get('total_completion_tokens', 0)}")
        lines.append(f"  total_tokens:   {token_summary.get('total_tokens', 0)}")
        lines.append(f"  llm_elapsed:    {token_summary.get('total_elapsed_seconds', 0):.1f}s")

        per_phase = token_summary.get("per_phase", {})
        if per_phase:
            lines.append("")
            lines.append("  per_phase:")
            for pname in sorted(per_phase):
                p = per_phase[pname]
                lines.append(
                    f"    {pname}: {p['calls']} calls, "
                    f"{p['total_tokens']} tokens, "
                    f"{p['elapsed_seconds']:.1f}s"
                )

    # ── 错误 ────────────────────────────────────────────────
    if runtime_summary:
        errors = runtime_summary.get("errors", [])
        if errors:
            lines.append("")
            _heading(lines, "ERROR SUMMARY")
            for err in errors:
                lines.append(f"  stage: {err.get('stage', '?')}")
                lines.append(f"  error: {err.get('error', '?')}")
                lines.append("")

    # ── 额外行 ──────────────────────────────────────────────
    if extra_lines:
        lines.append("")
        _heading(lines, "ARTIFACT CHECK")
        lines.extend(extra_lines)

    _sep(lines)

    # 追加写盘
    text = "\n".join(lines) + "\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(text)


# ── 内部辅助 ──────────────────────────────────────────────────

_SEP = "=" * 55


def _sep(lines: list[str]) -> None:
    lines.append("")
    lines.append(_SEP)
    lines.append("")


def _heading(lines: list[str], title: str) -> None:
    lines.append(f"===== {title} =====")
