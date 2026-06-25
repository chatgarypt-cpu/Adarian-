#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flask backend for the Adarian web console."""

from __future__ import annotations

import subprocess

from flask import Flask
from flask_cors import CORS
from rich.console import Console
from rich.panel import Panel

from adarian.serve.api import register_api


def create_app() -> Flask:
    """Create the v1.5 web console app."""
    app = Flask(__name__)
    CORS(app)
    register_api(app)
    return app


def run(host: str = "127.0.0.1", port: int = 9788, open_browser: bool = False) -> None:
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
