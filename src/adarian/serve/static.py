#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serve the built Vue SPA from Flask when frontend/dist exists."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, abort, redirect, request, send_from_directory

from adarian.serve.paths import FRONTEND_DIST


def _spa_index() -> str | None:
    """Return the dist index path if it exists, else None."""
    index = FRONTEND_DIST / "index.html"
    return str(index) if index.exists() else None


def register_static(app: Flask) -> None:
    # Direct static file serving (not catch-all)
    @app.get("/")
    def index():
        if target := _spa_index():
            resp = send_from_directory(FRONTEND_DIST, "index.html")
            resp.headers["Cache-Control"] = "no-store, must-revalidate"
            return resp
        return redirect("http://localhost:5173/", 302)

    @app.get("/assets/<path:filename>")
    def assets(filename: str):
        assets_dir = FRONTEND_DIST / "assets"
        if not assets_dir.exists():
            abort(404)
        return send_from_directory(assets_dir, filename)

    # SPA fallback — only reached when no app or blueprint route matched
    @app.errorhandler(404)
    def spa_fallback(e):
        if request.path.startswith("/api/"):
            return {"code": "NOT_FOUND", "message": "API endpoint not found", "details": {}}, 404
        if request.path.startswith("/assets/"):
            return {"code": "NOT_FOUND", "message": "Static asset not found", "details": {}}, 404
        if target := _spa_index():
            resp = send_from_directory(FRONTEND_DIST, "index.html")
            resp.headers["Cache-Control"] = "no-store, must-revalidate"
            return resp
        return redirect("http://localhost:5173/", 302)
