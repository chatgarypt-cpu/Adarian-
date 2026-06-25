#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings API."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from adarian.serve import db
from adarian.serve.paths import OUTPUTS_DIR
from adarian.serve.schemas import SettingsPayload, error_response

settings_bp = Blueprint("settings", __name__)

DEFAULT_SETTINGS = {
    "maxConcurrent": 3,
    "outputDir": "outputs/runs/",
    "retentionDays": 30,
    "technicalMode": False,
}


def _settings() -> dict:
    return db.get_setting("settings", DEFAULT_SETTINGS)


def _system_checks(settings: dict) -> list[dict]:
    output_dir = Path(settings.get("outputDir") or "outputs/runs/")
    if not output_dir.is_absolute():
        output_dir = OUTPUTS_DIR.parent / output_dir
    checks = []
    checks.append(
        {
            "label": "模型接口",
            "status": "pending",
            "message": "请使用模型网关健康检测查看具体服务",
        }
    )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        writable = os.access(output_dir, os.W_OK)
    except OSError:
        writable = False
    checks.append({"label": "任务目录", "status": "ok" if writable else "failed", "message": str(output_dir)})
    checks.append({"label": "报告入口", "status": "pending", "message": "报告依赖已完成 batch 的 simulation_dataset"})
    checks.append({"label": "日志服务", "status": "ok", "message": "通过 run/status 返回 scheduler 日志"})
    return checks


@settings_bp.get("/settings")
def get_settings():
    settings = _settings()
    return jsonify({**settings, "systemChecks": _system_checks(settings)})


@settings_bp.put("/settings")
def put_settings():
    try:
        payload = SettingsPayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        body, status = error_response("VALIDATION_ERROR", "Invalid settings payload", {"errors": exc.errors()})
        return jsonify(body), status
    settings = payload.model_dump()
    db.set_setting("settings", settings)
    return jsonify({**settings, "systemChecks": _system_checks(settings)})
