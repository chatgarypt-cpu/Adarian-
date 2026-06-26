#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-world detail APIs."""

from __future__ import annotations

from flask import Blueprint, jsonify

from adarian.serve import db
from adarian.serve.observability import (
    get_world_by_index,
    read_text_lines,
    world_artifacts,
    world_events,
    world_summary,
    world_ticks,
)
from adarian.serve.schemas import error_response, normalize_status

world_bp = Blueprint("world", __name__)


def _batch_and_world(batch_id: str, world_index: int):
    batch = db.get_batch(batch_id)
    if not batch:
        body, status = error_response("BATCH_NOT_FOUND", "Batch not found", {"batch_id": batch_id})
        return None, None, jsonify(body), status
    world = get_world_by_index(db.list_worlds(batch_id), world_index)
    if not world:
        body, status = error_response("WORLD_NOT_FOUND", "World not found", {"batch_id": batch_id, "world_index": world_index})
        return batch, None, jsonify(body), status
    return batch, world, None, None


@world_bp.get("/run/<batch_id>/worlds")
def worlds(batch_id: str):
    batch = db.get_batch(batch_id)
    if not batch:
        body, status = error_response("BATCH_NOT_FOUND", "Batch not found", {"batch_id": batch_id})
        return jsonify(body), status
    rows = db.list_worlds(batch_id)
    return jsonify({
        "batch_id": batch_id,
        "worlds": [
            {
                "id": row.get("id", ""),
                "world_index": row.get("world_index", index),
                "model": row.get("model_name", ""),
                "status": normalize_status(row.get("raw_status") or row.get("status")),
                "run_dir": row.get("run_dir", ""),
                "dataset_path": row.get("dataset_path", ""),
                "elapsed_seconds": row.get("elapsed_seconds"),
                "error": row.get("error_message") or "",
            }
            for index, row in enumerate(rows)
        ],
    })


@world_bp.get("/run/<batch_id>/worlds/<int:world_index>/summary")
def summary(batch_id: str, world_index: int):
    _, world, response, status = _batch_and_world(batch_id, world_index)
    if response is not None:
        return response, status
    return jsonify(world_summary(world))


@world_bp.get("/run/<batch_id>/worlds/<int:world_index>/ticks")
def ticks(batch_id: str, world_index: int):
    _, world, response, status = _batch_and_world(batch_id, world_index)
    if response is not None:
        return response, status
    return jsonify(world_ticks(world))


@world_bp.get("/run/<batch_id>/worlds/<int:world_index>/log")
def log_tail(batch_id: str, world_index: int):
    _, world, response, status = _batch_and_world(batch_id, world_index)
    if response is not None:
        return response, status
    path = world_artifacts(world)["run_log"]
    lines = read_text_lines(path, 120)
    return jsonify({
        "batch_id": batch_id,
        "world_index": world_index,
        "state": "available" if lines else "missing",
        "path": str(path),
        "lines": lines,
    })


@world_bp.get("/run/<batch_id>/worlds/<int:world_index>/events")
def events(batch_id: str, world_index: int):
    _, world, response, status = _batch_and_world(batch_id, world_index)
    if response is not None:
        return response, status
    return jsonify({
        "batch_id": batch_id,
        "world_index": world_index,
        "scope": "world",
        "events": world_events(world),
    })
