"""Build native report view data and lightweight exports."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any


VERSION_INTENTS = {
    "A": "短版决策摘要",
    "B": "标准研判报告",
    "C": "详细归档版",
}


HEADING_KINDS = {
    "一、舆情概要": "summary",
    "二、演化分析": "judgement",
    "三、风险研判": "risk",
    "四、对策意见": "countermeasure",
}


def build_native_report_view(
    *,
    body: str,
    appendix_b: dict[str, Any],
    audit: dict[str, Any],
    job: dict[str, Any],
    version: str,
    appendix_mode: str,
    model_label: str = "",
) -> dict[str, Any]:
    """Convert the in-memory report body into the frontend reading contract."""

    parsed = _parse_body_sections(body)
    event_name = str(appendix_b.get("meta", {}).get("event_name") or "舆情事件")
    title = parsed["title"] or f"{event_name}舆情风险研判"
    risks = appendix_b.get("risk_assessment", {}).get("risks") or []
    evolution = appendix_b.get("evolution_analysis") or {}
    risk_distribution = _format_distribution(evolution.get("risk_level_distribution"))
    return {
        "id": f"{job['id']}:{version}",
        "job_id": job["id"],
        "batch_id": job.get("batch_id") or "",
        "version": version,
        "title": title,
        "subtitle": f"{VERSION_INTENTS.get(version, '研判报告')}，基于 completed worlds 的 simulation_dataset 生成。",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": {
            "batch_id": job.get("batch_id") or "",
            "completed_worlds": int(job.get("completed_worlds_count") or appendix_b.get("meta", {}).get("worlds_count") or 0),
            "failed_worlds": int(job.get("failed_worlds_count") or 0),
            "dataset_ready": True,
            "model": model_label or job.get("model_config_resolved_from") or "unknown",
            "skill_id": job.get("skill_id") or "default_government",
        },
        "kpis": [
            {
                "label": "综合风险",
                "value": str(evolution.get("worst_reasonable_level_label") or evolution.get("worst_reasonable_level") or "待定"),
                "note": "completed worlds 聚合",
                "tone": _risk_tone(str(evolution.get("worst_reasonable_level") or "")),
            },
            {
                "label": "world 覆盖",
                "value": str(appendix_b.get("meta", {}).get("worlds_count") or 0),
                "note": "completed worlds",
                "tone": "good",
            },
            {
                "label": "确认风险",
                "value": str(len(risks)),
                "note": "appendix_b 摘要",
                "tone": "warn" if risks else "info",
            },
            {
                "label": "质检状态",
                "value": "通过" if int(audit.get("passed") or 0) else "待复核",
                "note": "报告结构检查",
                "tone": "good" if int(audit.get("passed") or 0) else "warn",
            },
        ],
        "sections": parsed["sections"],
        "appendix": {
            "mode": _appendix_display_mode(appendix_mode),
            "event_name": event_name,
            "worlds_count": int(appendix_b.get("meta", {}).get("worlds_count") or 0),
            "confirmed_risks": len(risks),
            "risk_distribution": risk_distribution,
            "references": _references(appendix_b),
        },
        "quality": _quality_items(audit),
    }


def write_report_view(view: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(view, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_report_html(view: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report_html(view), encoding="utf-8")
    return path


def render_report_html(view: dict[str, Any]) -> str:
    sections = "\n".join(_render_section(section) for section in view.get("sections") or [])
    kpis = "\n".join(
        f"<li><span>{html.escape(str(kpi.get('label') or ''))}</span><strong>{html.escape(str(kpi.get('value') or ''))}</strong><small>{html.escape(str(kpi.get('note') or ''))}</small></li>"
        for kpi in view.get("kpis") or []
    )
    title = html.escape(str(view.get("title") or "报告"))
    subtitle = html.escape(str(view.get("subtitle") or ""))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{ margin: 0; padding: 40px; font: 16px/1.72 -apple-system, BlinkMacSystemFont, "Microsoft YaHei", sans-serif; color: #122436; background: #f3f7fa; }}
    main {{ max-width: 920px; margin: 0 auto; background: #fff; border: 1px solid #dce8ef; border-radius: 12px; padding: 44px; }}
    h1 {{ font-size: 42px; line-height: 1.15; margin: 0 0 12px; }}
    h2 {{ margin-top: 34px; border-top: 1px solid #dce8ef; padding-top: 24px; }}
    p {{ margin: 0 0 12px; }}
    ul.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; list-style: none; padding: 0; margin: 24px 0; }}
    ul.kpis li {{ border: 1px solid #dce8ef; border-radius: 10px; padding: 12px; }}
    ul.kpis span, ul.kpis small {{ display: block; color: #607586; }}
    ul.kpis strong {{ display: block; font-size: 24px; margin: 4px 0; }}
    .callout {{ border-left: 4px solid #2589c7; background: #eef8fc; padding: 12px 14px; border-radius: 8px; }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>{subtitle}</p>
    <ul class="kpis">{kpis}</ul>
    {sections}
  </main>
</body>
</html>
"""


def _parse_body_sections(body: str) -> dict[str, Any]:
    title = ""
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    paragraph: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph and current is not None:
            current["blocks"].append({"type": "paragraph", "text": " ".join(item.strip() for item in paragraph if item.strip())})
        paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items and current is not None:
            current["blocks"].append({"type": "list", "items": list_items})
        list_items = []

    def flush_all() -> None:
        flush_paragraph()
        flush_list()

    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            flush_all()
            continue
        if line.startswith("# "):
            flush_all()
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            flush_all()
            heading = line[3:].strip()
            current = {
                "id": _section_id(heading),
                "heading": heading,
                "eyebrow": _eyebrow(heading),
                "kind": HEADING_KINDS.get(heading, "summary"),
                "blocks": [],
            }
            sections.append(current)
            continue
        if current is None:
            current = {"id": "body", "heading": "正文", "eyebrow": "Body", "kind": "summary", "blocks": []}
            sections.append(current)
        if line.startswith(("- ", "* ")):
            flush_paragraph()
            list_items.append(line[2:].strip())
            continue
        number_prefix = line.split(" ", 1)[0]
        if number_prefix.endswith(".") and number_prefix[:-1].isdigit() and " " in line:
            flush_paragraph()
            list_items.append(line.split(" ", 1)[1].strip())
            continue
        flush_list()
        paragraph.append(line)

    flush_all()
    return {"title": title, "sections": sections}


def _render_section(section: dict[str, Any]) -> str:
    heading = html.escape(str(section.get("heading") or ""))
    blocks = []
    for block in section.get("blocks") or []:
        kind = block.get("type")
        if kind == "list":
            items = "".join(f"<li>{html.escape(str(item))}</li>" for item in block.get("items") or [])
            blocks.append(f"<ul>{items}</ul>")
        elif kind == "callout":
            blocks.append(f"<div class=\"callout\"><strong>{html.escape(str(block.get('title') or ''))}</strong><p>{html.escape(str(block.get('text') or ''))}</p></div>")
        else:
            blocks.append(f"<p>{html.escape(str(block.get('text') or ''))}</p>")
    return f"<section><h2>{heading}</h2>{''.join(blocks)}</section>"


def _section_id(heading: str) -> str:
    if "概要" in heading:
        return "summary"
    if "演化" in heading:
        return "evolution"
    if "风险" in heading:
        return "risk"
    if "对策" in heading or "意见" in heading:
        return "countermeasure"
    return "section"


def _eyebrow(heading: str) -> str:
    if "概要" in heading:
        return "Executive Summary"
    if "演化" in heading:
        return "Evolution"
    if "风险" in heading:
        return "Risk Analysis"
    if "对策" in heading or "意见" in heading:
        return "Countermeasures"
    return "Report Section"


def _risk_tone(level: str) -> str:
    if level in {"high", "critical"}:
        return "warn"
    if level == "low":
        return "good"
    return "info"


def _appendix_display_mode(mode: str) -> str:
    if mode == "included":
        return "references"
    return "summary"


def _format_distribution(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "暂无"
    return " / ".join(f"{key}:{count}" for key, count in value.items())


def _references(appendix_b: dict[str, Any]) -> list[str]:
    risks = appendix_b.get("risk_assessment", {}).get("risks") or []
    refs = [str(risk.get("trigger_reason") or risk.get("type_label") or "") for risk in risks if risk]
    if refs:
        return refs[:6]
    return ["completed worlds simulation_dataset.json"]


def _quality_items(audit: dict[str, Any]) -> list[dict[str, str]]:
    blocked = audit.get("blocked_reasons") or []
    if blocked:
        return [{"label": "质量审核", "status": "blocked", "detail": str(item)} for item in blocked]
    return [
        {"label": "结构完整", "status": "passed", "detail": "报告标题和四个核心章节已通过检查。"},
        {"label": "内部字段", "status": "passed", "detail": "未发现禁止暴露的内部运行字段。"},
    ]
