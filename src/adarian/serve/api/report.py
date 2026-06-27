#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report generation API."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request, send_from_directory
from pydantic import ValidationError

from adarian.report import create_job, run_job, status_response
from adarian.serve import db
from adarian.serve.api.model_gateways import _env_gateway
from adarian.serve.observability import safe_report_file
from adarian.serve.schemas import ReportPayload, error_response

report_bp = Blueprint("report", __name__)
_EXECUTOR = ThreadPoolExecutor(max_workers=2)


def _request_session_id(payload: ReportPayload | None = None) -> str:
    return (
        (payload.client_session_id if payload else "")
        or request.args.get("client_session_id")
        or request.headers.get("X-Adarian-Client-Session")
        or ""
    ).strip()


def _payload_dict(payload: ReportPayload) -> dict[str, Any]:
    data = payload.model_dump()
    if data.get("type") == "risk_assessment" and not data.get("versions"):
        data["versions"] = ["B"]
    return data


@report_bp.post("/report")
def generate_report():
    """Compatibility endpoint: create and run a report job synchronously."""
    try:
        payload = ReportPayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        body, status = error_response("VALIDATION_ERROR", "Invalid report payload", {"errors": exc.errors()})
        return jsonify(body), status
    if not db.get_batch(payload.batch_id):
        body, status = error_response("BATCH_NOT_FOUND", "Batch not found", {"batch_id": payload.batch_id})
        return jsonify(body), status
    job = create_job(_payload_dict(payload), _request_session_id(payload))
    final = run_job(job["id"])
    response = status_response(final)
    if response["status"] in {"blocked", "failed"}:
        body, status = error_response(response["error_code"] or "REPORT_WRITE_FAILED", response["error_message"] or "报告生成失败", response)
        return jsonify(body), status
    return jsonify(response)


@report_bp.post("/report/jobs")
def create_report_job():
    try:
        payload = ReportPayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        body, status = error_response("VALIDATION_ERROR", "Invalid report payload", {"errors": exc.errors()})
        return jsonify(body), status
    if not db.get_batch(payload.batch_id):
        body, status = error_response("BATCH_NOT_FOUND", "Batch not found", {"batch_id": payload.batch_id})
        return jsonify(body), status
    job = create_job(_payload_dict(payload), _request_session_id(payload))
    _EXECUTOR.submit(run_job, job["id"])
    return jsonify(status_response(db.get_report_job(job["id"]) or job)), 202


@report_bp.get("/report/jobs/<job_id>/status")
def report_job_status(job_id: str):
    job = db.get_report_job(job_id)
    if not job:
        body, status = error_response("NOT_FOUND", "Report job not found", {"job_id": job_id})
        return jsonify(body), status
    return jsonify(status_response(job))


@report_bp.get("/report/jobs/active")
def active_report_job():
    session_id = _request_session_id()
    if not session_id:
        return jsonify({"active": False, "job": None})
    job = db.latest_report_job_for_session(session_id)
    return jsonify({"active": bool(job), "job": status_response(job) if job else None})


@report_bp.get("/report/jobs/<job_id>/files/<path:filename>")
def download_report_job_file(job_id: str, filename: str):
    job = db.get_report_job(job_id)
    if not job:
        body, status = error_response("NOT_FOUND", "Report job not found", {"job_id": job_id})
        return jsonify(body), status
    file_path = _safe_job_file(job, filename)
    if not file_path:
        body, status = error_response("REPORT_FILE_FORBIDDEN", "Report filename is not allowed", {"filename": filename})
        return jsonify(body), status
    if not file_path.exists() or not file_path.is_file():
        body, status = error_response("REPORT_FILE_NOT_FOUND", "Report file not found", {"filename": filename})
        return jsonify(body), status
    return send_from_directory(file_path.parent, file_path.name, as_attachment=True)


@report_bp.get("/report/<batch_id>/files/<path:filename>")
def download_report_file(batch_id: str, filename: str):
    """Compatibility file endpoint: find the latest job for the batch."""
    batch = db.get_batch(batch_id)
    if not batch:
        body, status = error_response("BATCH_NOT_FOUND", "Batch not found", {"batch_id": batch_id})
        return jsonify(body), status
    legacy = safe_report_file(batch, filename)
    if legacy:
        return send_from_directory(legacy.parent, legacy.name, as_attachment=True)
    job = _latest_job_for_batch(batch_id)
    if not job:
        body, status = error_response("REPORT_FILE_NOT_FOUND", "Report file not found", {"filename": filename})
        return jsonify(body), status
    return download_report_job_file(job["id"], filename)


@report_bp.get("/report/models")
def report_models():
    env = _env_gateway()
    return jsonify({
        "gateways": [env],
        "default": {
            "gateway_id": "env-default",
            "model_id": "",
            "configured": bool(env.get("baseUrl") and env.get("hasApiKey")),
        },
    })


def _safe_job_file(job: dict[str, Any], filename: str) -> Path | None:
    if filename.startswith("/") or "\\" in filename or ".." in filename:
        return None
    output_dir = Path(job.get("output_dir") or "")
    if not output_dir:
        return None
    root = output_dir.resolve()
    candidate = (root / filename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _latest_job_for_batch(batch_id: str) -> dict[str, Any] | None:
    db.init_db()
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM report_jobs WHERE batch_id = ? ORDER BY created_at DESC LIMIT 1",
            (batch_id,),
        ).fetchone()
    return dict(row) if row else None
