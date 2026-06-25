#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""History API."""

from __future__ import annotations

import json

from flask import Blueprint, jsonify

from adarian.serve import db
from adarian.serve.schemas import normalize_status

history_bp = Blueprint("history", __name__)


@history_bp.get("/history")
def history():
    rows = []
    for batch in db.list_batches():
        models = json.loads(batch.get("models") or "[]")
        worlds = db.list_worlds(batch["id"])
        completed = sum(1 for world in worlds if normalize_status(world.get("raw_status") or world.get("status")) == "completed")
        failed = sum(1 for world in worlds if normalize_status(world.get("raw_status") or world.get("status")) == "failed")
        rows.append(
            {
                "batchId": batch["id"],
                "name": batch.get("task_name") or batch.get("tag") or batch["id"],
                "createdAt": batch.get("created_at", ""),
                "status": normalize_status(batch.get("status")),
                "risk": f"{completed} 完成 / {failed} 失败 / {len(models)} 模型",
            }
        )
    return jsonify(rows)
