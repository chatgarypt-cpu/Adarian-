"""Whitebox run artifact existence checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


WHITEBOX_VERSION = "v1.2.5"
DETAIL_FILENAME = "artifact_check.json"

RAW_SOURCES = {
    "seed_input": "seed_input.txt",
    "run_log": "run.log",
    "timing_summary": "timing_summary.json",
    "tick_logs": "tick_logs.json",
    "final_report_md": "final_report.md",
    "final_report_json": "final_report.json",
    "run_meta": "run_meta.json",
    "whitebox_summary": "whitebox_summary.json",
}

REQUIRED_ARTIFACT_PATHS = (
    "seed_input.txt",
    "entities_and_relations.json",
    "social_graph.json",
    "tick_logs.json",
    "final_report.json",
    "final_report.md",
    "run.log",
    "timing_summary.json",
    "run_meta.json",
    "whitebox_summary.json",
)

REQUIRED_ARTIFACTS = {
    relative_path: relative_path
    for relative_path in REQUIRED_ARTIFACT_PATHS
}


def _artifact_state(run_dir: Path, relative_path: str) -> Dict[str, object]:
    path = run_dir / relative_path
    return {
        "path": relative_path,
        "exists": path.exists(),
        "is_file": path.is_file(),
    }


def check_run_artifacts(run_dir: Path) -> Dict[str, object]:
    """Check expected run artifacts without reading or modifying their contents."""
    run_dir = Path(run_dir)
    artifacts = {
        name: _artifact_state(run_dir, relative_path)
        for name, relative_path in REQUIRED_ARTIFACTS.items()
    }
    missing = [
        name
        for name, state in artifacts.items()
        if not state["exists"] or not state["is_file"]
    ]

    return {
        "whitebox_version": WHITEBOX_VERSION,
        "check": "artifact_check",
        "status": "pass" if not missing else "fail",
        "path": "whitebox/artifact_check.json",
        "run_dir_exists": run_dir.exists(),
        "raw_sources": RAW_SOURCES,
        "required_artifacts": artifacts,
        "missing_artifacts": missing,
        "warnings": [],
    }


def write_artifact_check(run_dir: Path) -> Dict[str, object]:
    """Write whitebox/artifact_check.json for a run directory."""
    run_dir = Path(run_dir)
    whitebox_dir = run_dir / "whitebox"
    whitebox_dir.mkdir(parents=True, exist_ok=True)

    payload = check_run_artifacts(run_dir)
    payload["path"] = "whitebox/artifact_check.json"

    with open(whitebox_dir / DETAIL_FILENAME, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return payload
