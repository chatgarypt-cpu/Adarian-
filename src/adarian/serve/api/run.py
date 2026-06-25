#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch run and status APIs."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from adarian import config as adarian_config
from adarian.serve import db
from adarian.serve.schemas import RunPayload, error_response, normalize_status

run_bp = Blueprint("run", __name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=3)
_ACTIVE: dict[str, Any] = {}


def _idempotency_key(payload: RunPayload, base_url: str, tag: str) -> str:
    text = json.dumps(
        {
            "seed_text": payload.seed_text.strip(),
            "seed_path": payload.seed_path.strip(),
            "models": sorted(payload.models),
            "tag": tag,
            "base_url": base_url,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _world_rows_from_session(session) -> list[dict[str, Any]]:
    rows = []
    for index, world in enumerate(session.worlds):
        state = session.states[world.name]
        rows.append(
            {
                "id": f"{session.batch_id}:{world.name}",
                "batch_id": session.batch_id,
                "world_index": index,
                "model_name": state.model_name,
                "status": normalize_status(state.status),
                "raw_status": state.status,
                "run_dir": state.output_dir,
                "dataset_path": state.dataset_path,
                "error_message": state.error_summary or "",
                "log_tail": state.log_tail or "",
                "started_at": session.started_at,
                "completed_at": session.completed_at,
                "elapsed_seconds": state.elapsed_seconds,
            }
        )
    return rows


def _write_session(session, *, status: str | None = None) -> None:
    raw_status = status or session.status
    db.upsert_batch(
        {
            "id": session.batch_id,
            "task_name": session.batch_id,
            "seed_text": "",
            "seed_path": str(session.seed_path),
            "models": json.dumps([w.model for w in session.worlds], ensure_ascii=False),
            "tag": session.batch_id,
            "base_url": session.worlds[0].base_url if session.worlds else "",
            "batch_dir": str(session.batch_dir),
            "created_at": session.started_at or db.now(),
            "completed_at": session.completed_at or "",
            "status": normalize_status(raw_status),
            "idempotency_key": "",
            "config_json": "{}",
        }
    )
    for row in _world_rows_from_session(session):
        db.upsert_world(row)


def _finish_session(session) -> None:
    try:
        from adarian.batch import execute_session

        execute_session(session)
    except Exception as exc:
        session.status = "failed"
        session.completed_at = db.now()
        session.log(f"Batch execution failed: {exc}")
    finally:
        _write_session(session)
        _ACTIVE.pop(session.batch_id, None)


def _batch_response(batch: dict[str, Any], worlds: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    raw = batch.get("raw_status") or batch.get("status")
    mapped = normalize_status(raw)
    api_worlds = [_world_response(row, index) for index, row in enumerate(worlds or [])]
    return {
        "batch_id": batch["id"],
        "status": mapped,
        "raw_status": raw,
        "all_completed": bool(api_worlds) and all(w["status"] in {"completed", "failed"} for w in api_worlds),
        "worlds": api_worlds,
        "logs": _read_scheduler_logs(batch),
    }


def _world_response(row: dict[str, Any], index: int) -> dict[str, Any]:
    status = normalize_status(row.get("raw_status") or row.get("status"))
    rows = [
        {"label": "模型", "value": row.get("model_name", "")},
        {"label": "状态", "value": status},
    ]
    if row.get("dataset_path"):
        rows.append({"label": "数据集", "value": row.get("dataset_path", "")})
    if row.get("elapsed_seconds") is not None:
        rows.append({"label": "耗时", "value": f"{row.get('elapsed_seconds')}s"})
    return {
        "id": str(row.get("id", "")),
        "round": f"第 {index + 1} 轮",
        "model": row.get("model_name", ""),
        "status": status,
        "raw_status": row.get("raw_status") or row.get("status"),
        "rows": rows,
        "errorSummary": row.get("error_message") or "",
        "logTail": row.get("log_tail") or "",
    }


def _read_scheduler_logs(batch: dict[str, Any]) -> list[str]:
    from pathlib import Path

    path = Path(batch.get("batch_dir") or "") / "scheduler_batch.log"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8", errors="replace").splitlines()[-120:]
        except OSError:
            return []
    return []


@run_bp.post("/run")
def start_run():
    try:
        payload = RunPayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        body, status = error_response("VALIDATION_ERROR", "Invalid run payload", {"errors": exc.errors()})
        return jsonify(body), status

    models = [model.strip() for model in payload.models if model.strip()]
    if not models:
        body, status = error_response("NO_MODELS", "At least one model is required")
        return jsonify(body), status
    if not payload.seed_text.strip() and not payload.seed_path.strip():
        body, status = error_response("EMPTY_SEED", "seed_text or seed_path is required")
        return jsonify(body), status

    base_url = payload.base_url.strip() or adarian_config.LLM_BASE_URL or ""
    tag = (payload.tag or payload.config.get("batch_name") or "adarian_batch").strip() or "adarian_batch"
    idem = _idempotency_key(payload, base_url, tag)
    existing = db.get_batch_by_key(idem)
    if existing:
        return jsonify(_batch_response(existing, db.list_worlds(existing["id"])))

    try:
        from adarian.batch import start_batch

        session = start_batch(
            models=models,
            seed_text=payload.seed_text,
            seed_path=payload.seed_path,
            tag=tag,
            base_url=base_url,
        )
    except ValueError as exc:
        body, status = error_response("NO_MODELS", str(exc))
        return jsonify(body), status
    except Exception as exc:
        body, status = error_response("RUN_START_FAILED", "Could not start batch", {"error": str(exc)})
        return jsonify(body), status

    db.upsert_batch(
        {
            "id": session.batch_id,
            "task_name": tag,
            "seed_text": payload.seed_text,
            "seed_path": str(session.seed_path),
            "models": json.dumps(models, ensure_ascii=False),
            "tag": tag,
            "base_url": base_url,
            "batch_dir": str(session.batch_dir),
            "created_at": session.started_at,
            "completed_at": "",
            "status": "running",
            "idempotency_key": idem,
            "config_json": json.dumps(payload.config, ensure_ascii=False),
        }
    )
    for row in _world_rows_from_session(session):
        row["status"] = "running"
        row["raw_status"] = "running"
        db.upsert_world(row)

    _ACTIVE[session.batch_id] = _EXECUTOR.submit(_finish_session, session)
    return jsonify(_batch_response(db.get_batch(session.batch_id) or {"id": session.batch_id, "status": "running"}, db.list_worlds(session.batch_id))), 202


@run_bp.get("/run/<batch_id>/status")
def run_status(batch_id: str):
    batch = db.get_batch(batch_id)
    if not batch:
        body, status = error_response("BATCH_NOT_FOUND", "Batch not found", {"batch_id": batch_id})
        return jsonify(body), status
    return jsonify(_batch_response(batch, db.list_worlds(batch_id)))
