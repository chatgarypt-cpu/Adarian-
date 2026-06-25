#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review API based on real batch evidence."""

from __future__ import annotations

from flask import Blueprint, jsonify

from adarian.serve import db
from adarian.serve.schemas import error_response, normalize_status

review_bp = Blueprint("review", __name__)


@review_bp.get("/review/<batch_id>")
def review(batch_id: str):
    batch = db.get_batch(batch_id)
    if not batch:
        body, status = error_response("BATCH_NOT_FOUND", "Batch not found", {"batch_id": batch_id})
        return jsonify(body), status

    worlds = db.list_worlds(batch_id)
    rows = []
    complete = True
    for index, world in enumerate(worlds):
        status = normalize_status(world.get("raw_status") or world.get("status"))
        if status not in {"completed", "failed"}:
            complete = False
        risk_text = "暂无真实风险产物"
        level = "待定"
        if status == "completed":
            risk_text = "已生成 simulation_dataset，可进入报告阶段"
            level = "可用"
        elif status == "failed":
            risk_text = world.get("error_message") or "world 执行失败"
            level = "失败"
        rows.append(
            {
                "world": f"第 {index + 1} 轮",
                "risks": risk_text,
                "level": level,
                "levelVariant": "bad" if status == "failed" else ("ok" if status == "completed" else "warn"),
                "status": "可用" if status == "completed" else ("失败" if status == "failed" else "运行中"),
                "statusVariant": "ok" if status == "completed" else ("bad" if status == "failed" else "warn"),
                "evidence": world.get("dataset_path") or world.get("run_dir") or "",
                "complete": complete,
            }
        )
    return jsonify({"batch_id": batch_id, "complete": complete, "rows": rows})
