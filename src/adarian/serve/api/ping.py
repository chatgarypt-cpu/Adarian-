#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Health endpoint for v1.5.0a frontend-backend connectivity."""

from __future__ import annotations

from flask import Blueprint, jsonify

ping_bp = Blueprint("ping", __name__)


@ping_bp.get("/ping")
def ping():
    return jsonify({"status": "ok", "version": "1.5.0a"})
