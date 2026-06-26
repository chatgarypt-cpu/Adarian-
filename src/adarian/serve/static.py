#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serve the built Vue SPA from Flask when frontend/dist exists."""

from __future__ import annotations

from flask import Flask, redirect, send_from_directory

from adarian.serve.paths import FRONTEND_DIST


def register_static(app: Flask) -> None:
    @app.get("/")
    @app.get("/<path:path>")
    def spa(path: str = "index.html"):
        if path.startswith("api/"):
            return {"code": "NOT_FOUND", "message": "API endpoint not found", "details": {}}, 404
        target = FRONTEND_DIST / path
        if target.exists() and target.is_file():
            resp = send_from_directory(FRONTEND_DIST, path)
            resp.headers["Cache-Control"] = "no-store, must-revalidate"
            return resp
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            resp = send_from_directory(FRONTEND_DIST, "index.html")
            resp.headers["Cache-Control"] = "no-store, must-revalidate"
            return resp
        # Dev mode — redirect to Vite dev server
        return redirect("http://localhost:5173/", 302)
