"""Convert report artifacts into frontend-safe view models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote


PREVIEW_FORMATS = {"md", "json"}
DOWNLOAD_FORMATS = {"md", "html", "docx", "pdf"}


def artifact_format(name: str) -> str:
    suffix = Path(name).suffix.lower().lstrip(".")
    return suffix if suffix in {"md", "pdf", "docx", "html", "json"} else "unknown"


def artifact_metadata(file: dict[str, Any]) -> dict[str, Any]:
    fmt = str(file.get("format") or artifact_format(str(file.get("name") or "")))
    appendix = file.get("appendix")
    internal = bool(file.get("internal") or appendix == "data")
    return {
        **file,
        "format": fmt,
        "internal": internal,
        "previewable": bool(file.get("previewable", fmt in PREVIEW_FORMATS and not internal)),
        "downloadable": bool(file.get("downloadable", fmt in DOWNLOAD_FORMATS and not internal and bool(file.get("url")))),
        "state": str(file.get("state") or "ready"),
        "label": str(file.get("label") or _artifact_label(fmt, str(file.get("name") or ""))),
    }


def build_artifact_manifest(files: list[dict[str, Any]], output_dir: str | Path = "") -> list[dict[str, Any]]:
    """Return user-facing export artifacts only."""

    root = Path(output_dir) if output_dir else None
    manifest: list[dict[str, Any]] = []
    ready_formats: set[str] = set()
    for file in files:
        meta = artifact_metadata(file)
        fmt = str(meta.get("format") or "unknown")
        if meta.get("internal") or fmt not in DOWNLOAD_FORMATS:
            continue
        if root:
            filename = _filename_from_file(meta)
            path = root / filename if filename else None
            if path and path.exists():
                meta["size_bytes"] = path.stat().st_size
        manifest.append({
            "id": meta.get("id") or fmt,
            "label": meta.get("label") or _artifact_label(fmt, str(meta.get("name") or "")),
            "format": fmt,
            "state": meta.get("state") or "ready",
            "previewable": bool(meta.get("previewable")),
            "downloadable": bool(meta.get("downloadable")),
            "url": meta.get("url") or "",
            "size_bytes": meta.get("size_bytes"),
            "source_view_id": meta.get("source_view_id") or "",
            "note": meta.get("note") or "",
        })
        ready_formats.add(fmt)
    for fmt in ("docx", "pdf"):
        if fmt not in ready_formats:
            manifest.append({
                "id": f"planned_{fmt}",
                "label": _artifact_label(fmt, ""),
                "format": fmt,
                "state": "planned",
                "previewable": False,
                "downloadable": False,
                "url": "",
                "size_bytes": None,
                "source_view_id": "",
                "note": "计划中",
            })
    return manifest


def load_native_report_view(job: dict[str, Any], version: str = "") -> dict[str, Any] | None:
    """Load the persisted report_view.json for the job."""

    try:
        files = json.loads(job.get("files_json") or "[]")
    except json.JSONDecodeError:
        return None
    candidates = []
    for file in files:
        meta = artifact_metadata(file)
        if str(meta.get("id") or "").startswith("report_view") or meta.get("kind") == "report_view":
            if version and meta.get("version") != version:
                continue
            candidates.append(meta)
    if not candidates:
        return None
    output_dir = Path(job.get("output_dir") or "")
    if not output_dir:
        return None
    filename = _filename_from_file(candidates[0])
    if not filename:
        return None
    root = output_dir.resolve()
    path = (root / filename).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    if not path.exists() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


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


def _artifact_label(fmt: str, name: str) -> str:
    labels = {"md": "Markdown", "html": "HTML", "docx": "DOCX", "pdf": "PDF", "json": "JSON"}
    return labels.get(fmt) or name or "Artifact"


def _filename_from_file(file: dict[str, Any]) -> str:
    if file.get("path"):
        return str(file["path"])
    url = str(file.get("url") or "")
    marker = "/files/"
    if marker in url:
        return unquote(url.split(marker, 1)[1])
    return str(file.get("name") or "")


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
