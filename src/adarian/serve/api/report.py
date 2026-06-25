#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report generation API."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from adarian.serve import db
from adarian.serve.schemas import ReportPayload, error_response, normalize_status

report_bp = Blueprint("report", __name__)


def _find_dataset(batch_id: str) -> Path | None:
    for world in db.list_worlds(batch_id):
        if normalize_status(world.get("raw_status") or world.get("status")) != "completed":
            continue
        candidate = Path(world.get("dataset_path") or "")
        if candidate.exists():
            return candidate
        run_dir = Path(world.get("run_dir") or "")
        candidate = run_dir / "simulation_dataset.json"
        if candidate.exists():
            return candidate
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
    dataset_path = _find_dataset(payload.batch_id)
    if not dataset_path:
        body, status = error_response(
            "REPORT_SOURCE_NOT_FOUND",
            "No completed simulation_dataset.json found for this batch",
            {"batch_id": payload.batch_id},
        )
        return jsonify(body), status

    try:
        from adarian.phase4.report_agent import parse_llm_report_response, save_report

        data = json.loads(dataset_path.read_text(encoding="utf-8"))
        phase4 = parse_llm_report_response("", data)
        output_path = Path(batch.get("batch_dir") or dataset_path.parent.parent) / "report.json"
        save_report(phase4, output_path=output_path)
    except Exception as exc:
        body, status = error_response("REPORT_GENERATION_FAILED", "Could not generate report", {"error": str(exc)})
        return jsonify(body), status

    return jsonify(
        {
            "report_id": f"{payload.batch_id}:report",
            "batch_id": payload.batch_id,
            "files": [{"id": "report-json", "name": "report.json", "url": str(output_path), "path": str(output_path)}],
        }
    )
