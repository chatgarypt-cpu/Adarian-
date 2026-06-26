#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flask backend for the Adarian web console."""

from __future__ import annotations

import subprocess

from flask import Flask
from flask_cors import CORS
from rich.console import Console
from rich.panel import Panel

from adarian.serve import db
from adarian.serve.api import register_api
from adarian.serve.static import register_static


def create_app() -> Flask:
    """Create the v1.5 web console app."""
    app = Flask(__name__)
    CORS(app)
    db.init_db()
    register_api(app)
    register_static(app)
    return app


def _ensure_frontend_built() -> None:
    """Auto-build frontend dist before starting server."""
    from adarian.serve.paths import PROJECT_ROOT

    frontend_dir = PROJECT_ROOT / "frontend"
    if not (frontend_dir / "package.json").exists():
        return  # no frontend source — skip

    import subprocess, sys
    print("  Building frontend...", end=" ", flush=True)
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(frontend_dir),
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode == 0:
        print("✓")
    else:
        print("✗ — serve will still start, but UI may be stale")
        print(result.stderr[-300:] if result.stderr else "", end="", file=sys.stderr)


def run(host: str = "127.0.0.1", port: int = 9788, open_browser: bool = False) -> None:
    _ensure_frontend_built()
    app = create_app()
    url = f"http://{host}:{port}"
    Console(stderr=True).print(
        Panel(
            f"Adarian 平行世界舆情推演系统\nWeb 控制台: {url}\n浏览器打开上面地址操作推演",
            border_style="dim",
        )
    )
    if open_browser:
        try:
            subprocess.Popen(["open", url])
        except OSError:
            pass
    app.run(host=host, port=port, threaded=True)
