#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review API based on real batch evidence."""

from __future__ import annotations

from flask import Blueprint, jsonify

from adarian.serve import db
from adarian.serve.observability import build_review_rows
from adarian.serve.schemas import error_response

review_bp = Blueprint("review", __name__)


@review_bp.get("/review/<batch_id>")
def review(batch_id: str):
    batch = db.get_batch(batch_id)
    if not batch:
        body, status = error_response("BATCH_NOT_FOUND", "Batch not found", {"batch_id": batch_id})
        return jsonify(body), status

    complete, rows = build_review_rows(db.list_worlds(batch_id))
    return jsonify({"batch_id": batch_id, "complete": complete, "rows": rows})
