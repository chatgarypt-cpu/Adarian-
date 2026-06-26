#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report generation API."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory
from pydantic import ValidationError

from adarian.serve import db
from adarian.serve.observability import safe_report_file
from adarian.serve.schemas import ReportPayload, error_response

report_bp = Blueprint("report", __name__)

def _file_response(batch_id: str, path: Path) -> dict[str, object]:
    return {
        "report_id": f"{batch_id}:report",
        "batch_id": batch_id,
        "files": [{
            "id": path.stem,
            "name": path.name,
            "url": f"/api/report/{batch_id}/files/{path.name}",
            "path": str(path),
        }],
    }


def _existing_report(batch: dict[str, str]) -> Path | None:
    for filename in ("report.json", "final_report.json", "report.md", "final_report.md"):
        path = safe_report_file(batch, filename)
        if path:
            return path
    return None


@report_bp.post("/report")
def generate_report():
    try:
        payload = ReportPayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        body, status = error_response("VALIDATION_ERROR", "Invalid report payload", {"errors": exc.errors()})
        return jsonify(body), status
    batch = db.get_batch(payload.batch_id)
    if not batch:
        body, status = error_response("BATCH_NOT_FOUND", "Batch not found", {"batch_id": payload.batch_id})
        return jsonify(body), status
    existing = _existing_report(batch)
    if existing:
        return jsonify(_file_response(payload.batch_id, existing))
    body, status = error_response(
        "REPORT_GENERATION_DEFERRED",
        "报告生成将在 v1.5.2 重构；当前仅支持下载已有报告文件。",
        {"batch_id": payload.batch_id, "next_version": "v1.5.2"},
    )
    return jsonify(body), 409


@report_bp.get("/report/<batch_id>/files/<filename>")
def download_report_file(batch_id: str, filename: str):
    batch = db.get_batch(batch_id)
    if not batch:
        body, status = error_response("BATCH_NOT_FOUND", "Batch not found", {"batch_id": batch_id})
        return jsonify(body), status
    if "/" in filename or "\\" in filename or ".." in filename:
        body, status = error_response("REPORT_FILE_FORBIDDEN", "Report filename is not allowed", {"filename": filename})
        return jsonify(body), status
    file_path = safe_report_file(batch, filename)
    if not file_path:
        body, status = error_response("REPORT_FILE_NOT_FOUND", "Report file not found", {"filename": filename})
        return jsonify(body), status
    return send_from_directory(file_path.parent, file_path.name, as_attachment=True)
