#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect existing batch directories for dataset evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _ensure_imports():
    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def inspect_world(world_dir: str | Path, model_name: str = "", label: str = "") -> dict[str, Any]:
    """Inspect one world directory from on-disk evidence."""
    from adarian.batch import WorldState, _merge_filesystem_evidence

    path = Path(world_dir)
    state = WorldState(
        world_id=path.name,
        model_name=model_name,
        label=label or model_name,
        output_dir=str(path),
        dataset_path=str(path / "simulation_dataset.json"),
    )
    _merge_filesystem_evidence(state)
    if state.status == "pending" and path.exists():
        state.status = "running"
    return state.as_dict()


def summarize_worlds(worlds: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(worlds),
        "success": sum(1 for w in worlds if w["status"] == "success"),
        "completed": sum(1 for w in worlds if w["status"] == "success"),
        "failed": sum(1 for w in worlds if w["status"] == "failed"),
        "running": sum(1 for w in worlds if w["status"] == "running"),
        "pending": sum(1 for w in worlds if w["status"] == "pending"),
    }


def _batch_status_from_worlds(worlds: list[dict[str, Any]]) -> str:
    if not worlds:
        return "pending"
    if any(w["status"] == "failed" for w in worlds):
        return "failed"
    if all(w["status"] == "success" for w in worlds):
        return "success"
    if any(w["status"] == "running" for w in worlds):
        return "running"
    return "pending"


def inspect_batch(batch_dir: str | Path) -> dict[str, Any]:
    """Inspect an existing batch_dir without relying on in-memory UI state."""
    batch_path = Path(batch_dir)
    worlds = []
    if batch_path.exists():
        for child in sorted(batch_path.iterdir()):
            if child.is_dir() and child.name.startswith("world_"):
                worlds.append(inspect_world(child))
    return {
        "batch_dir": str(batch_path),
        "batch_id": batch_path.name,
        "status": _batch_status_from_worlds(worlds),
        "worlds": worlds,
        "summary": summarize_worlds(worlds),
        "logs": _read_log_tail(batch_path / "scheduler_batch.log", 120),
    }


def _read_log_tail(path: Path, lines: int) -> list[str]:
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    except OSError:
        return []
