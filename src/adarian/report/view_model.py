"""Convert report artifacts into frontend-safe view models."""

from __future__ import annotations

from pathlib import Path
from typing import Any


PREVIEW_FORMATS = {"md"}


def artifact_format(name: str) -> str:
    suffix = Path(name).suffix.lower().lstrip(".")
    return suffix if suffix in {"md", "pdf", "docx", "html", "json"} else "unknown"


def artifact_metadata(file: dict[str, Any]) -> dict[str, Any]:
    fmt = str(file.get("format") or artifact_format(str(file.get("name") or "")))
    return {
        **file,
        "format": fmt,
        "previewable": bool(file.get("previewable", fmt in PREVIEW_FORMATS and file.get("appendix") != "data")),
    }


def build_report_view(file: dict[str, Any], path: Path) -> dict[str, Any]:
    meta = artifact_metadata(file)
    fmt = str(meta["format"])
    base = {
        "file_id": meta.get("id") or "",
        "name": meta.get("name") or path.name,
        "format": fmt,
        "version": meta.get("version") or "",
        "appendix": meta.get("appendix") or "",
        "raw_available": path.exists(),
        "preview_supported": fmt in PREVIEW_FORMATS,
        "message": "",
        "title": "",
        "sections": [],
    }
    if fmt != "md":
        base["message"] = "该格式仅下载，不支持预览"
        return base
    if not path.exists():
        base["preview_supported"] = False
        base["message"] = "报告文件不存在"
        return base
    return {**base, **parse_markdown_report(path.read_text(encoding="utf-8"))}


def parse_markdown_report(text: str) -> dict[str, Any]:
    title = ""
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    child: dict[str, Any] | None = None
    paragraph: list[str] = []
    list_items: list[str] = []
    table_lines: list[str] = []

    def target() -> dict[str, Any]:
        nonlocal current
        if child is not None:
            return child
        if current is None:
            current = {"heading": "正文", "blocks": [], "children": []}
            sections.append(current)
        return current

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            target()["blocks"].append({"type": "paragraph", "text": " ".join(part.strip() for part in paragraph if part.strip())})
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            target()["blocks"].append({"type": "list", "items": list_items})
            list_items = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            target()["blocks"].append({"type": "preformatted", "text": "\n".join(table_lines)})
            table_lines = []

    def flush_all() -> None:
        flush_paragraph()
        flush_list()
        flush_table()

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_all()
            continue
        if stripped.startswith("# "):
            flush_all()
            title = stripped[2:].strip()
            continue
        if stripped.startswith("## "):
            flush_all()
            current = {"heading": stripped[3:].strip(), "blocks": [], "children": []}
            sections.append(current)
            child = None
            continue
        if stripped.startswith("### "):
            flush_all()
            if current is None:
                current = {"heading": "正文", "blocks": [], "children": []}
                sections.append(current)
            child = {"heading": stripped[4:].strip(), "blocks": [], "children": []}
            current.setdefault("children", []).append(child)
            continue
        if stripped.startswith("|"):
            flush_paragraph()
            flush_list()
            table_lines.append(stripped)
            continue
        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            flush_table()
            list_items.append(stripped[2:].strip())
            continue
        number_sep = stripped.split(" ", 1)[0]
        if number_sep.endswith(".") and number_sep[:-1].isdigit() and " " in stripped:
            flush_paragraph()
            flush_table()
            list_items.append(stripped.split(" ", 1)[1].strip())
            continue
        flush_list()
        flush_table()
        paragraph.append(stripped)

    flush_all()
    return {
        "title": title or "报告正文",
        "sections": sections,
        "preview_supported": True,
        "message": "",
    }

