"""Main runner for v1.1.19 model pool profiling."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console

import config

console = Console()

PROFILE_ROOT = config.PROJECT_ROOT / "profiling"
OUTPUT_ROOT = PROFILE_ROOT / "output"
RAW_LOG_DIR = OUTPUT_ROOT / "raw_logs"


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_cases() -> list[dict]:
    """Load frozen profiling cases."""
    payload = _load_json_file(PROFILE_ROOT / "cases.yaml")
    return payload["cases"]


def load_models() -> list[str]:
    """Load models from modelslist.txt based on profiling/models.yaml policy."""
    policy = _load_json_file(PROFILE_ROOT / "models.yaml")
    source_file = config.PROJECT_ROOT / policy["source_file"]
    content = source_file.read_text(encoding="utf-8").strip()
    delimiter = policy.get("delimiter", "、")
    raw_models = [item.strip() for item in content.split(delimiter)] if content else []

    models: list[str] = []
    seen = set()
    for model in raw_models:
        if not model:
            continue
        if policy.get("error_on_duplicate", False) and model in seen:
            raise ValueError(f"Duplicate model found in modelslist.txt: {model}")
        seen.add(model)
        models.append(model)
    return models


def ensure_output_dirs() -> None:
    """Ensure profiling output directories exist."""
    RAW_LOG_DIR.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    """Write JSON payload with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """Write JSONL rows preserving failure samples verbatim."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text(text + ("\n" if text else ""), encoding="utf-8")


def build_run_meta() -> dict:
    """Build meta payload for the profiling run."""
    return {
        "version": "v1.1.19",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "models_source": "modelslist.txt",
        "cases_source": "profiling/cases.yaml",
        "concurrency_levels": [1, 2, 3, 5],
        "simple_rounds": 3,
        "chain_rounds": 3,
        "max_retry_count": 2,
        "subagents_enabled": True,
        "notes": [
            "Do not hide failures.",
            "Do not rewrite review findings as subjective opinions.",
            "Freeze methodology before execution.",
        ],
    }


def main() -> int:
    """Run profiling end-to-end once submodules are available."""
    ensure_output_dirs()
    models = load_models()
    cases = load_cases()
    run_meta = build_run_meta()

    console.print("[bold cyan]Profiling:[/bold cyan] v1.1.19 model pool profiling")
    console.print(f"  [green]✓[/green] models from modelslist.txt: {len(models)}")
    for model in models:
        console.print(f"    - {model}")
    console.print(f"  [green]✓[/green] fixed cases: {len(cases)}")
    for case in cases:
        console.print(f"    - {case['id']}")

    write_json(OUTPUT_ROOT / "run_meta.json", run_meta)
    console.print("  [yellow]⚠[/yellow] runner skeleton ready; benchmarking integration pending submodule wiring")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
