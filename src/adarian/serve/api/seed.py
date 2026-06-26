#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seed intake API."""

from __future__ import annotations

import hashlib

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from adarian.serve.paths import resolve_project_file
from adarian.serve.schemas import SeedRequest, error_response

seed_bp = Blueprint("seed", __name__)


def _checks(source: str) -> list[dict[str, str]]:
    source_note = "可以进入下一步" if source == "manual" else "本地 seed 文件可用于启动推演"
    return [
        {"label": "事件背景已填写", "note": source_note, "status": "passed"},
        {"label": "核心主体识别", "note": "v1.5.0b 暂未接入主体抽取，后续版本启用", "status": "pending"},
        {"label": "时间线可补充", "note": "建议补充首发时间和官方回应时间", "status": "suggested"},
    ]


@seed_bp.post("/seed")
def save_seed():
    try:
        payload = SeedRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        body, status = error_response("VALIDATION_ERROR", "Invalid seed payload", {"errors": exc.errors()})
        return jsonify(body), status

    if payload.source == "manual":
        text = payload.seed_text.strip()
        if not text:
            body, status = error_response("EMPTY_SEED", "seed_text cannot be empty")
            return jsonify(body), status
        digest_source = f"{payload.task_name}\n{text}"
        seed_path = ""
    elif payload.source == "file":
        try:
            resolved = resolve_project_file(payload.seed_path)
        except ValueError:
            body, status = error_response("EMPTY_SEED", "seed_path cannot be empty")
            return jsonify(body), status
        except PermissionError:
            body, status = error_response(
                "SEED_PATH_NOT_ALLOWED",
                "seed_path must stay inside the Adarian project directory",
                {"seed_path": payload.seed_path},
            )
            return jsonify(body), status
        if not resolved.exists() or not resolved.is_file():
            body, status = error_response("SEED_FILE_NOT_FOUND", "seed_path does not exist", {"seed_path": str(resolved)})
            return jsonify(body), status
        digest_source = f"{payload.task_name}\\n{resolved}"
        try:
            file_text = resolved.read_text(encoding="utf-8")
        except Exception:
            body, status = error_response("SEED_FILE_READ_ERROR", "Could not read seed file", {"seed_path": str(resolved)})
            return jsonify(body), status
        text = file_text
        seed_path = str(resolved)
    else:
        body, status = error_response("SOURCE_NOT_SUPPORTED", "seed source is not supported", {"source": payload.source})
        return jsonify(body), status

    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:16]
    seed_id = f"seed_{digest}"
    return jsonify({"id": seed_id, "seed_id": seed_id, "source": payload.source, "seed_path": seed_path, "content": text.strip(), "checks": _checks(payload.source)})
