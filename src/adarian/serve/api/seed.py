#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seed intake API."""

from __future__ import annotations

import hashlib

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from adarian.serve.schemas import SeedRequest, error_response

seed_bp = Blueprint("seed", __name__)


@seed_bp.post("/seed")
def save_seed():
    try:
        payload = SeedRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        body, status = error_response("VALIDATION_ERROR", "Invalid seed payload", {"errors": exc.errors()})
        return jsonify(body), status

    if payload.source != "manual":
        body, status = error_response("SOURCE_NOT_SUPPORTED", "v1.5.0b only supports manual seed input", {"source": payload.source})
        return jsonify(body), status
    text = payload.seed_text.strip()
    if not text:
        body, status = error_response("EMPTY_SEED", "seed_text cannot be empty")
        return jsonify(body), status

    digest = hashlib.sha256(f"{payload.task_name}\n{text}".encode("utf-8")).hexdigest()[:16]
    checks = [
        {"label": "事件背景已填写", "note": "可以进入下一步", "status": "passed"},
        {"label": "核心主体识别", "note": "v1.5.0b 暂未接入主体抽取，后续版本启用", "status": "pending"},
        {"label": "时间线可补充", "note": "建议补充首发时间和官方回应时间", "status": "suggested"},
    ]
    seed_id = f"seed_{digest}"
    return jsonify({"id": seed_id, "seed_id": seed_id, "checks": checks})
