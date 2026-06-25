#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simulation config API."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from adarian.serve import db
from adarian.serve.schemas import ConfigPayload, error_response

config_bp = Blueprint("config", __name__)

DEFAULT_CONFIG = {
    "parallel_worlds": 3,
    "ticks": 5,
    "batch_name": "adarian_batch",
    "focuses": [],
    "pending_fields": ["ticks", "focuses"],
}


@config_bp.get("/config")
def get_config():
    return jsonify(db.get_setting("config", DEFAULT_CONFIG))


@config_bp.post("/config")
def save_config():
    try:
        payload = ConfigPayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        body, status = error_response("VALIDATION_ERROR", "Invalid config payload", {"errors": exc.errors()})
        return jsonify(body), status
    data = {
        "parallel_worlds": payload.parallel_worlds,
        "ticks": min(max(payload.ticks, 1), 5),
        "batch_name": payload.batch_name.strip() or "adarian_batch",
        "focuses": payload.focuses,
        "pending_fields": ["ticks", "focuses"],
    }
    db.set_setting("config", data)
    return jsonify(data)
