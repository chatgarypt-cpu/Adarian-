#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flask backend for the Adarian web console."""

from __future__ import annotations

import atexit
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

from flask import Flask
from flask_cors import CORS
from rich.console import Console
from rich.panel import Panel

from adarian.serve import db
from adarian.serve.api import register_api
from adarian.serve.schemas import normalize_status
from adarian.serve.static import register_static


def _shutdown_running_batches() -> None:
    """Mark all in-flight batches as 'failed' when the process exits."""
    batch_ids = db.running_batch_ids()
    if not batch_ids:
        return
    now = db.now()
    for batch_id in sorted(batch_ids):
        batch = db.get_batch(batch_id)
        if not batch:
            continue
        existing = normalize_status(batch.get("status"))
        if existing != "running":
            continue
        db.upsert_batch(_patch_batch_status(batch, "failed", completed_at=now))


def _handle_signal(signum: int, _frame: Any) -> None:
    """Signal handler — write failed status then re-raise the signal."""
    _shutdown_running_batches()
    # Allow the original signal behaviour (e.g. SIGTERM → exit)
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


# ── startup recovery ─────────────────────────────────────────────────


def _recover_stale_batches() -> None:
    """On startup, correct batches stuck at 'running' from a prior lifecycle.

    If a batch has no active executor and its status is still 'running', inspect
    each world's run.log on disk to determine the actual outcome. This prevents
    historical tasks from showing as perpetually in-progress after a server restart.
    """
    for batch in db.list_batches():
        if normalize_status(batch.get("status")) != "running":
            continue

        worlds = db.list_worlds(batch["id"])
        if not worlds:
            db.upsert_batch(_patch_batch_status(batch, "failed"))
            continue

        completed = 0
        failed = 0
        for world in worlds:
            run_dir = (world.get("run_dir") or "").strip()
            if not run_dir:
                failed += 1
                continue
            run_log = Path(run_dir) / "run.log"
            if not run_log.exists():
                failed += 1
                continue
            try:
                content = run_log.read_text(encoding="utf-8", errors="replace")
            except OSError:
                failed += 1
                continue
            if "RUN END" in content:
                completed += 1
            else:
                failed += 1

        new_status = "completed" if failed == 0 else "failed"
        db.upsert_batch(_patch_batch_status(batch, new_status))
        # Also update any world that has RUN END but DB still says "running"
        for world in worlds:
            run_dir = (world.get("run_dir") or "").strip()
            if not run_dir:
                continue
            run_log = Path(run_dir) / "run.log"
            if not run_log.exists():
                continue
            try:
                content = run_log.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "RUN END" in content and normalize_status(world.get("status")) == "running":
                world["status"] = "completed"
                world["raw_status"] = "success"
                db.upsert_world(world)


def _patch_batch_status(batch: dict, status: str, *, completed_at: str | None = None) -> dict:
    """Return a minimal upsert dict that only patches status/completed_at."""
    return {
        "id": batch["id"],
        "task_name": batch.get("task_name", batch["id"]),
        "seed_text": batch.get("seed_text", ""),
        "seed_path": batch.get("seed_path", ""),
        "models": batch.get("models", "[]"),
        "tag": batch.get("tag", ""),
        "base_url": batch.get("base_url", ""),
        "batch_dir": batch.get("batch_dir", ""),
        "created_at": batch.get("created_at", ""),
        "completed_at": completed_at or batch.get("completed_at", "") or db.now(),
        "status": status,
        "idempotency_key": batch.get("idempotency_key", ""),
        "config_json": batch.get("config_json", "{}"),
    }


# ── app factory ───────────────────────────────────────────────────────


def create_app() -> Flask:
    """Create the v1.5 web console app."""
    app = Flask(__name__)
    CORS(app)
    db.init_db()
    _recover_stale_batches()
    register_api(app)
    register_static(app)

    # Register signal handlers so that SIGTERM/SIGINT write "failed" before exit
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    atexit.register(_shutdown_running_batches)

    return app


# ── entry point ───────────────────────────────────────────────────────


def _ensure_frontend_built() -> None:
    """Auto-build frontend dist before starting server."""
    from adarian.serve.paths import PROJECT_ROOT

    frontend_dir = PROJECT_ROOT / "frontend"
    if not (frontend_dir / "package.json").exists():
        return  # no frontend source — skip

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
