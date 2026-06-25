#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Built-in model catalog API."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

models_bp = Blueprint("models", __name__)


@models_bp.get("/models")
def list_models():
    from adarian.batch import available_models

    selected = set((request.args.get("selected") or "").split(","))
    models = [
        {
            "id": model_id,
            "name": model_id,
            "description": description,
            "selected": model_id in selected,
            "available": True,
            "latency": "",
            "advice": "内置 catalog，可用于 batch.run_batch",
        }
        for model_id, description in available_models().items()
    ]
    return jsonify(models)


@models_bp.post("/models/health")
def model_health():
    """Real health check: sends hi to each model and reports status."""
    from adarian import config as adarian_config
    from adarian.serve.schemas import hello_model

    payload = request.get_json(silent=True) or {}
    ids = payload.get("models") or []
    base_url = adarian_config.LLM_BASE_URL or ""
    api_key = adarian_config.LLM_API_KEY or ""
    results = []
    for model_id in ids:
        result = hello_model(model_id, base_url, api_key)
        latency_ms = round(result.get("elapsed", 0) * 1000) if result.get("status") == "ok" else None
        results.append({
            "id": model_id,
            "status": result["status"],
            "latency_ms": latency_ms,
            "message": result.get("error", ""),
        })
    return jsonify(results)
