"""Skill-aware report quality checks and formal Markdown assembly."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_FORBIDDEN_TERMS = (
    "world_0",
    "world_1",
    "tick",
    "stance_score",
    "polarization_index",
    "appendix_b",
    "simulation_dataset",
    "completed world",
)
DEFAULT_OVERVIEW_FORBIDDEN_TERMS = ("模拟", "仿真", "推演", "AI", "模型")
DEFAULT_REQUIRED_HEADINGS = ("## 一、舆情概要", "## 二、演化分析", "## 三、风险研判", "## 四、对策意见")
DEFAULT_TITLE_MAX_CHARS = 30


def audit_body(body: str, checklist: dict[str, Any] | None = None) -> dict[str, Any]:
    rules = checklist or {}
    blocking = set(rules.get("blocking") or [
        "missing_required_headings",
        "internal_simulation_fields_in_body",
        "system_mechanism_terms_in_overview",
    ])
    warnings = set(rules.get("warning") or [])
    required_headings = tuple(rules.get("required_headings") or DEFAULT_REQUIRED_HEADINGS)
    forbidden_terms = tuple(rules.get("forbidden_terms") or DEFAULT_FORBIDDEN_TERMS)
    overview_forbidden = tuple(rules.get("overview_forbidden_terms") or DEFAULT_OVERVIEW_FORBIDDEN_TERMS)
    filler_terms = tuple(rules.get("filler_terms") or ())
    title_max_chars = int(rules.get("title_max_chars") or DEFAULT_TITLE_MAX_CHARS)

    fatal: list[str] = []
    high: list[str] = []
    medium: list[str] = []
    applied: list[str] = []
    if not body.strip():
        fatal.append("报告正文为空")
    if "title_length" in blocking:
        applied.append("title_length")
        title = _title(body)
        if not title:
            fatal.append("缺少报告标题")
        elif len(title) > title_max_chars:
            fatal.append(f"报告标题超过 {title_max_chars} 字")
    if "missing_required_headings" in blocking:
        applied.append("missing_required_headings")
        for heading in required_headings:
            if heading not in body:
                fatal.append(f"缺少章节标题：{heading}")
    if "internal_simulation_fields_in_body" in blocking:
        applied.append("internal_simulation_fields_in_body")
        for term in forbidden_terms:
            if term.lower() in body.lower():
                fatal.append(f"正文暴露内部语言：{term}")
    stripped = body.strip()
    if stripped and stripped[-1] not in "。！？.!?）)」』”》`":
        fatal.append("正文疑似被截断")

    overview = _section(body, required_headings[0], required_headings[1]) if len(required_headings) > 1 else ""
    if "system_mechanism_terms_in_overview" in blocking:
        applied.append("system_mechanism_terms_in_overview")
        for term in overview_forbidden:
            if term.lower() in overview.lower():
                high.append(f"第一章暴露系统机制词：{term}")
    if "filler_language" in warnings:
        applied.append("filler_language")
        for term in filler_terms:
            if term in body:
                medium.append(f"正文包含填充表达：{term}")

    return {
        "fatal": len(fatal),
        "high": len(high),
        "medium": len(medium),
        "passed": 1 if not fatal and not high else 0,
        "blocked_reasons": [*fatal, *high],
        "warnings": medium,
        "checks_applied": applied,
    }


def is_blocked(audit: dict[str, Any]) -> bool:
    return int(audit.get("fatal") or 0) > 0 or int(audit.get("high") or 0) > 0


def assemble_report(body: str, appendix_mode: str, public_appendix: str = "") -> str:
    content = body.strip()
    if appendix_mode == "included" and public_appendix.strip():
        content = f"{content}\n\n{public_appendix.strip()}"
    return content + "\n"


def write_audit(audit: dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "audit_report.json"
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _section(text: str, start: str, end: str) -> str:
    if start not in text:
        return ""
    part = text.split(start, 1)[1]
    if end in part:
        return part.split(end, 1)[0]
    return part


def _title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""
