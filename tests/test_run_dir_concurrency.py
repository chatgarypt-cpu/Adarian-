"""Focused checks for concurrent-safe grouped run directory naming."""

import sys
from datetime import datetime as RealDatetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import config
import main
from src.phase4.paths import build_run_paths


class FixedSecondDatetime:
    counter = 0

    @classmethod
    def now(cls):
        cls.counter += 1
        return RealDatetime(2026, 5, 15, 12, 34, 56, cls.counter)


def test_build_run_paths_uses_unique_run_dirs_for_rapid_calls(tmp_path, monkeypatch):
    seed_file = tmp_path / "test8.txt"
    seed_file.write_text("test seed", encoding="utf-8")
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path / "outputs")
    FixedSecondDatetime.counter = 0
    monkeypatch.setattr(main, "datetime", FixedSecondDatetime)

    contexts = [build_run_paths(seed_file) for _ in range(5)]

    run_ids = [context["run_id"] for context in contexts]
    run_dirs = [context["run_dir"] for context in contexts]
    batch_dirs = [context["batch_dir"] for context in contexts]

    assert len(run_ids) == len(set(run_ids))
    assert len(run_dirs) == len(set(run_dirs))
    assert len(batch_dirs) == 5
    assert len({str(batch_dir) for batch_dir in batch_dirs}) == 1
    assert all(run_dir.parent == batch_dirs[0] for run_dir in run_dirs)
    assert all(run_dir.is_dir() for run_dir in run_dirs)
    assert all((run_dir / "seed_input.txt").read_text(encoding="utf-8") == "test seed" for run_dir in run_dirs)
    assert batch_dirs[0].name.startswith("test8_")
    assert all(run_id.startswith("run_") for run_id in run_ids)
