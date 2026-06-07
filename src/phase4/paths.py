"""Run directory path construction for Adarian pipeline."""

import os
import shutil
from datetime import datetime
from pathlib import Path

import config


def build_run_paths(seed_file: Path) -> dict:
    """Create the run directory and return all authoritative output paths."""
    now = datetime.now()
    date_dir = now.strftime("%Y-%m-%d")
    batch_id = f"{seed_file.stem}_{now.strftime('%H%M%S')}"
    run_id = f"run_{now.strftime('%f')}_{os.getpid()}"
    batch_dir = config.OUTPUTS_DIR / "runs" / date_dir / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    run_dir = batch_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    whitebox_dir = run_dir / "whitebox"
    whitebox_dir.mkdir(parents=True, exist_ok=True)

    seed_copy = run_dir / "seed_input.txt"
    shutil.copyfile(seed_file, seed_copy)

    outputs = {
        "entities": run_dir / "entities_and_relations.json",
        "social_graph": run_dir / "social_graph.json",
        "tick_logs": run_dir / "tick_logs.json",
        "simulation_dataset": run_dir / "simulation_dataset.json",
        "final_report_json": run_dir / "final_report.json",
        "final_report_md": run_dir / "final_report.md",
        "whitebox_summary": run_dir / "whitebox_summary.json",
        "whitebox_dir": whitebox_dir,
        "run_log": run_dir / "run.log",
        "timing_summary": run_dir / "timing_summary.json",
        "run_meta": run_dir / "run_meta.json",
    }

    return {
        "batch_id": batch_id,
        "batch_dir": batch_dir,
        "run_id": run_id,
        "run_dir": run_dir,
        "seed_copy": seed_copy,
        "outputs": outputs,
    }
