"""Focused checks for the v1.2.5 whitebox artifact shell."""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import write_whitebox_summary
from src.whitebox import (
    check_report_completeness,
    check_run_artifacts,
    write_artifact_check,
    write_report_completeness_summary,
)
from src.whitebox.artifact_check import REQUIRED_ARTIFACTS, RAW_SOURCES


def _create_run_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for name, relative_path in REQUIRED_ARTIFACTS.items():
        (path / relative_path).write_text(f"fixture for {name}\n", encoding="utf-8")


def test_whitebox_imports() -> None:
    assert callable(check_report_completeness)
    assert callable(write_report_completeness_summary)
    assert callable(check_run_artifacts)
    assert callable(write_artifact_check)


def test_artifact_check_temp_run_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        _create_run_dir(run_dir)

        result = check_run_artifacts(run_dir)

        assert result["status"] == "pass"
        assert result["missing_artifacts"] == []
        assert result["raw_sources"] == RAW_SOURCES
        for state in result["required_artifacts"].values():
            assert state["exists"] is True
            assert state["is_file"] is True


def test_artifact_check_does_not_modify_business_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        _create_run_dir(run_dir)
        before = {
            relative_path: (run_dir / relative_path).read_text(encoding="utf-8")
            for relative_path in REQUIRED_ARTIFACTS.values()
        }

        result = write_artifact_check(run_dir)

        after = {
            relative_path: (run_dir / relative_path).read_text(encoding="utf-8")
            for relative_path in REQUIRED_ARTIFACTS.values()
        }
        assert result["status"] == "pass"
        assert before == after
        assert (run_dir / "whitebox" / "artifact_check.json").is_file()


def test_whitebox_summary_index_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        run_context = {
            "outputs": {
                "whitebox_summary": run_dir / "whitebox_summary.json",
            },
        }
        report_completeness = {
            "status": "pass",
            "path": "whitebox/report_completeness.json",
        }
        artifact_check = {
            "status": "pass",
            "path": "whitebox/artifact_check.json",
            "raw_sources": RAW_SOURCES,
        }

        summary = write_whitebox_summary(
            run_context,
            report_completeness,
            artifact_check,
        )
        written = json.loads((run_dir / "whitebox_summary.json").read_text(encoding="utf-8"))

        assert summary == written
        assert written["whitebox_version"] == "v1.2.5"
        assert written["status"] == "pass"
        assert set(written.keys()) == {
            "whitebox_version",
            "status",
            "checks",
            "raw_sources",
        }
        assert written["checks"] == {
            "report_completeness": {
                "status": "pass",
                "path": "whitebox/report_completeness.json",
            },
            "artifact_check": {
                "status": "pass",
                "path": "whitebox/artifact_check.json",
            },
        }
        assert written["raw_sources"] == {
            "seed_input": "seed_input.txt",
            "run_log": "run.log",
            "timing_summary": "timing_summary.json",
            "tick_logs": "tick_logs.json",
            "final_report_md": "final_report.md",
            "final_report_json": "final_report.json",
            "run_meta": "run_meta.json",
            "whitebox_summary": "whitebox_summary.json",
        }


def main() -> None:
    test_whitebox_imports()
    test_artifact_check_temp_run_dir()
    test_artifact_check_does_not_modify_business_files()
    test_whitebox_summary_index_shape()


if __name__ == "__main__":
    main()
