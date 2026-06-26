#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Path helpers for the Adarian web console."""

from __future__ import annotations

from pathlib import Path

from adarian import config

PROJECT_ROOT = config.PROJECT_ROOT
OUTPUTS_DIR = config.OUTPUTS_DIR
RUNS_DIR = OUTPUTS_DIR / "runs"
SERVE_DB_PATH = OUTPUTS_DIR / "serve.sqlite3"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


def ensure_runtime_dirs() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def resolve_project_file(path: str) -> Path:
    """Resolve a user-supplied project-local file path."""
    raw_path = path.strip()
    if not raw_path:
        raise ValueError("empty path")
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise PermissionError(str(resolved)) from exc
    return resolved
