#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report skill discovery and user import API."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from adarian.report.skills_registry import (
    delete_report_skill,
    import_report_skill,
    list_report_skills,
    skill_locations,
)
from adarian.serve.schemas import error_response

report_skills_bp = Blueprint("report_skills", __name__)


@report_skills_bp.get("/report/skills")
def report_skills():
    return jsonify(list_report_skills())


@report_skills_bp.get("/report/skills/locations")
def report_skill_locations():
    return jsonify(skill_locations())


@report_skills_bp.post("/report/skills/import")
def import_skill():
    upload = request.files.get("file")
    if not upload:
        body, status = error_response("REPORT_SKILL_FILE_REQUIRED", "请选择 Skill Markdown 文件")
        return jsonify(body), status
    if not (upload.filename or "").lower().endswith(".md"):
        body, status = error_response("REPORT_SKILL_INVALID", "Skill 导入仅支持 .md 文件")
        return jsonify(body), status
    try:
        skill = import_report_skill(upload.read(), replace=request.form.get("replace") == "true")
    except FileExistsError as exc:
        body, status = error_response("REPORT_SKILL_EXISTS", str(exc))
        return jsonify(body), status
    except (UnicodeDecodeError, ValueError) as exc:
        body, status = error_response("REPORT_SKILL_INVALID", str(exc))
        return jsonify(body), status
    return jsonify(skill), 201


@report_skills_bp.delete("/report/skills/<skill_id>")
def delete_skill(skill_id: str):
    try:
        delete_report_skill(skill_id)
    except PermissionError as exc:
        body, status = error_response("REPORT_SKILL_READ_ONLY", str(exc))
        return jsonify(body), status
    except FileNotFoundError as exc:
        body, status = error_response("REPORT_SKILL_NOT_FOUND", str(exc))
        return jsonify(body), status
    except ValueError as exc:
        body, status = error_response("REPORT_SKILL_INVALID", str(exc))
        return jsonify(body), status
    return "", 204
