"""Minimal report quality checks and assembly."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import appendix_a_path


FORBIDDEN_BODY_TERMS = ("world_0", "world_1", "stance_score", "polarization_index")
OVERVIEW_FORBIDDEN_TERMS = ("模拟", "仿真", "推演", "AI", "模型")
REQUIRED_HEADINGS = ("## 一、舆情概要", "## 二、演化分析", "## 三、风险研判", "## 四、对策意见")


def audit_body(body: str) -> dict[str, Any]:
    fatal: list[str] = []
    high: list[str] = []
    medium: list[str] = []
    if not body.strip():
        fatal.append("报告正文为空")
    for heading in REQUIRED_HEADINGS:
        if heading not in body:
            fatal.append(f"缺少章节标题：{heading}")
    for term in FORBIDDEN_BODY_TERMS:
        if term in body:
            fatal.append(f"正文暴露内部字段：{term}")
    stripped = body.strip()
    if stripped and stripped[-1] not in "。！？.!?）)」』”》`":
        fatal.append("正文疑似被截断")

    overview = _section(body, "## 一、舆情概要", "## 二、演化分析")
    for term in OVERVIEW_FORBIDDEN_TERMS:
        if term in overview:
            high.append(f"第一章暴露系统机制词：{term}")

    return {
        "fatal": len(fatal),
        "high": len(high),
        "medium": len(medium),
        "passed": 1 if not fatal and not high else 0,
        "blocked_reasons": [*fatal, *high],
        "warnings": medium,
    }


def is_blocked(audit: dict[str, Any]) -> bool:
    return int(audit.get("fatal") or 0) > 0 or int(audit.get("high") or 0) > 0


def assemble_report(body: str, appendix_mode: str, appendix_b: dict[str, Any]) -> str:
    if appendix_mode == "none":
        return body.strip() + "\n"
    appendix_a = ""
    path = appendix_a_path()
    if path.exists():
        appendix_a = path.read_text(encoding="utf-8").strip()
    else:
        appendix_a = "# 附录 A：数据说明与方法论\n\n本报告基于 Adarian 仿真数据集生成。"
    appendix_json = json.dumps(appendix_b, ensure_ascii=False, indent=2)
    return f"{body.strip()}\n\n{appendix_a}\n\n## 附录 B\n\n```json\n{appendix_json}\n```\n"


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
