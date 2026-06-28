#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report skill discovery API."""

from __future__ import annotations

from flask import Blueprint, jsonify

from adarian.report.skills_registry import list_report_skills

report_skills_bp = Blueprint("report_skills", __name__)


@report_skills_bp.get("/report/skills")
def report_skills():
    return jsonify(list_report_skills())

