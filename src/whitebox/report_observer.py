"""Whitebox observer for Phase 4 report completeness."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from .report_completeness import check_report_completeness


WHITEBOX_VERSION = "v1.2.5"
DETAIL_FILENAME = "report_completeness.json"


def _relative_to_run_dir(path: Path, run_dir: Path) -> str:
    try:
        return path.relative_to(run_dir).as_posix()
    except ValueError:
        return path.as_posix()


def write_report_completeness_summary(run_dir: Path, final_report_path: Path) -> Dict[str, object]:
    """Check final_report.md and write whitebox/report_completeness.json."""
    run_dir = Path(run_dir)
    final_report_path = Path(final_report_path)
    whitebox_dir = run_dir / "whitebox"
    whitebox_dir.mkdir(parents=True, exist_ok=True)

    with open(final_report_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    result = check_report_completeness(markdown_text)
    status = "fail" if result["report_truncated"] else "pass"
    detail_path = whitebox_dir / DETAIL_FILENAME
    payload = {
        "whitebox_version": WHITEBOX_VERSION,
        "check": "report_completeness",
        "status": status,
        "raw_source": _relative_to_run_dir(final_report_path, run_dir),
        "path": _relative_to_run_dir(detail_path, run_dir),
        "result": result,
    }

    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    run_log_path = run_dir / "run.log"
    if run_log_path.exists():
        with open(run_log_path, "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                "REPORT COMPLETENESS "
                f"report_truncated={str(result['report_truncated']).lower()} "
                f"score={result['report_completeness_score']} "
                f"char_count={result['report_char_count']}\n"
            )

    return payload
