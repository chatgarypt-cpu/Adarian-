#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serve the built Vue SPA from Flask when frontend/dist exists."""

from __future__ import annotations

from flask import Flask, send_from_directory

from adarian.serve.paths import FRONTEND_DIST


def register_static(app: Flask) -> None:
    @app.get("/")
    @app.get("/<path:path>")
    def spa(path: str = "index.html"):
        if path.startswith("api/"):
            return {"code": "NOT_FOUND", "message": "API endpoint not found", "details": {}}, 404
        target = FRONTEND_DIST / path
        if target.exists() and target.is_file():
            return send_from_directory(FRONTEND_DIST, path)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return send_from_directory(FRONTEND_DIST, "index.html")
        return {
            "code": "FRONTEND_NOT_BUILT",
            "message": "frontend/dist is not built; run npm run build in frontend/",
            "details": {"dist": str(FRONTEND_DIST)},
        }, 404
