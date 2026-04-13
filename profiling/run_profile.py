"""Unified profiling pipeline entry for v1.1.19.

Execution-only orchestrator responsibilities:
- load run_manifest.json
- validate manifest against frozen rules
- freeze manifest into an execution snapshot
- run sidecars in order: freeze -> simple_runner -> chain_runner -> aggregator
- report incomplete runs without inventing data
"""

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
from profiling.aggregate import aggregate_from_paths, write_outputs

console = Console()

PROFILE_ROOT = config.PROJECT_ROOT / "profiling"
OUTPUT_ROOT = PROFILE_ROOT / "output"
RAW_LOG_DIR = OUTPUT_ROOT / "raw_logs"
RUN_MANIFEST_PATH = OUTPUT_ROOT / "run_manifest.json"
MANIFEST_SNAPSHOT_PATH = OUTPUT_ROOT / "run_manifest.snapshot.json"
MODEL_PROFILES_PATH = OUTPUT_ROOT / "model_profiles.json"
PROFILE_SUMMARY_PATH = OUTPUT_ROOT / "profile_summary.md"


def ensure_output_dirs() -> None:
    """Ensure profiling output directories exist."""
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    RAW_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _resolve_models_source(source_path: str) -> Path:
    path = Path(source_path)
    if not path.is_absolute():
        path = config.PROJECT_ROOT / path
    return path.resolve()


def _read_models_from_source(source_path: str) -> list[str]:
    """Read models from modelslist.txt without silent dedupe."""
    resolved = _resolve_models_source(source_path)
    content = resolved.read_text(encoding="utf-8").strip()
    raw_models = [item.strip() for item in content.split("、")] if content else []
    models = [item for item in raw_models if item]
    seen: set[str] = set()
    duplicates: list[str] = []
    for model in models:
        if model in seen and model not in duplicates:
            duplicates.append(model)
        seen.add(model)
    if duplicates:
        duplicate_text = ", ".join(duplicates)
        raise ValueError(f"Duplicate models found in modelslist.txt: {duplicate_text}")
    return models


def load_manifest() -> dict[str, Any]:
    """Load the frozen-rule manifest from disk."""
    if not RUN_MANIFEST_PATH.exists():
        raise FileNotFoundError(f"run_manifest.json not found: {RUN_MANIFEST_PATH}")
    return _load_json(RUN_MANIFEST_PATH)


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate manifest and resolve models from source_path only."""
    errors: list[str] = []

    models_conf = manifest.get("models")
    if not isinstance(models_conf, dict):
        errors.append("manifest.models must be an object")
        models_conf = {}

    source_path = models_conf.get("source_path")
    if not isinstance(source_path, str) or not source_path.strip():
        errors.append("manifest.models.source_path must be a non-empty string")
        source_path = ""

    if "names" in models_conf:
        errors.append("Second source of truth detected: manifest.models.names is not allowed")

    validator_conf = manifest.get("validator")
    if not isinstance(validator_conf, dict):
        errors.append("manifest.validator must be an object")
        validator_conf = {}
    if validator_conf.get("fixed_model") != "minimax":
        errors.append("validator.fixed_model must be minimax")
    if validator_conf.get("allow_override", False):
        errors.append("validator.allow_override must be false")

    test_plan = manifest.get("test_plan")
    if not isinstance(test_plan, dict):
        errors.append("manifest.test_plan must be an object")
        test_plan = {}
    chain_plan = test_plan.get("chain")
    if not isinstance(chain_plan, dict):
        errors.append("manifest.test_plan.chain must be an object")
        chain_plan = {}
    if chain_plan.get("max_retry_count") != 2:
        errors.append("test_plan.chain.max_retry_count must be 2")

    if "simple_benchmark" not in manifest:
        errors.append("manifest.simple_benchmark is required")
    if "chain_benchmark" not in manifest:
        errors.append("manifest.chain_benchmark is required")

    resolved_models: list[str] = []
    resolved_source_path: str | None = None
    if source_path:
        try:
            resolved_source = _resolve_models_source(source_path)
            resolved_source_path = str(resolved_source)
            if not resolved_source.exists():
                errors.append(f"models.source_path does not exist: {resolved_source}")
            else:
                resolved_models = _read_models_from_source(source_path)
                if not resolved_models:
                    errors.append("modelslist.txt is empty after trimming")
        except Exception as exc:
            errors.append(str(exc))

    if errors:
        duplicate_errors = [item for item in errors if "Duplicate models found" in item]
        if duplicate_errors:
            console.print("[red]duplicate models detected:[/red]")
            for item in duplicate_errors:
                console.print(f"  - {item}")
        raise ValueError("\n".join(errors))

    return {
        "models": resolved_models,
        "models_source_path": resolved_source_path,
    }


def freeze_step(manifest: dict[str, Any], validated: dict[str, Any]) -> Path:
    """Create execution snapshot for sidecars.

    The source manifest remains single-source-of-truth for config.
    The snapshot only materializes resolved model names for sidecar execution.
    """
    snapshot = json.loads(json.dumps(manifest, ensure_ascii=False))
    snapshot["run_id"] = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    snapshot["frozen_at"] = _now_iso()
    snapshot["freeze"] = {
        "models_source_path": validated["models_source_path"],
        "resolved_models_count": len(validated["models"]),
    }

    simple_section = snapshot.get("simple_benchmark", {})
    if isinstance(simple_section, dict):
        simple_section["models"] = list(validated["models"])
        snapshot["simple_benchmark"] = simple_section

    chain_section = snapshot.get("chain_benchmark", {})
    if isinstance(chain_section, dict):
        chain_section["models"] = list(validated["models"])
        chain_section["generator_model"] = list(validated["models"])
        chain_section["validator_model"] = "minimax"
        chain_section["max_retry_count"] = 2
        snapshot["chain_benchmark"] = chain_section

    _write_json(MANIFEST_SNAPSHOT_PATH, snapshot)
    return MANIFEST_SNAPSHOT_PATH


def run_simple_runner(manifest_snapshot_path: Path) -> dict[str, Any]:
    """Execute simple sidecar. Failure is recorded, not fatal."""
    try:
        from profiling.simple_benchmark import run_simple_benchmark

        report = run_simple_benchmark(manifest_snapshot_path)
        return {
            "ok": True,
            "raw_log_path": report.meta.get("raw_log_path"),
            "record_count": len(report.records),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "raw_log_path": None,
            "record_count": 0,
        }


def run_chain_runner(manifest_snapshot_path: Path) -> dict[str, Any]:
    """Execute chain sidecar. Failure is recorded, not fatal."""
    try:
        from profiling.chain_benchmark import run_chain_benchmark

        result = run_chain_benchmark(manifest_path=manifest_snapshot_path)
        return {
            "ok": True,
            "raw_log_path": result.get("raw_log_path"),
            "result_count": len(result.get("results", [])),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "raw_log_path": None,
            "result_count": 0,
        }


def run_aggregate(manifest_snapshot_path: Path, raw_log_paths: list[str], runner_failures: list[str]) -> dict[str, Any]:
    """Aggregate even if raw logs are incomplete."""
    existing_paths = [path for path in raw_log_paths if path]
    summary = aggregate_from_paths(
        manifest_path=manifest_snapshot_path,
        raw_log_source=existing_paths if existing_paths else [],
    )

    missing_logs = list(summary.get("missing_logs", []))
    missing_logs.extend(runner_failures)
    model_rows = summary.get("models", [])
    expected_models = summary.get("expected_models", [])
    observed_models = {row.get("model_name") for row in model_rows}
    for model_name in expected_models:
        if model_name not in observed_models:
            missing_logs.append(f"missing model data: {model_name}")

    deduped_missing: list[str] = []
    for item in missing_logs:
        if item not in deduped_missing:
            deduped_missing.append(item)

    summary["missing_logs"] = deduped_missing
    summary["incomplete_profile"] = bool(deduped_missing) or bool(summary.get("has_failures"))
    write_outputs(summary, model_profiles_path=MODEL_PROFILES_PATH, summary_path=PROFILE_SUMMARY_PATH)
    return summary


def report_summary(results: dict[str, Any]) -> None:
    """Print compact execution summary."""
    console.print("")
    console.print("[bold cyan]=== Pipeline Summary ===[/bold cyan]")
    console.print(f"  overall_status: {results['overall_status']}")
    for step_name, step_result in results["steps"].items():
        if step_result["ok"]:
            console.print(f"  {step_name}: [green]ok[/green]")
        else:
            console.print(f"  {step_name}: [red]failed[/red] - {step_result.get('error', 'unknown error')}")

    aggregate_result = results.get("aggregate", {})
    if aggregate_result:
        console.print(f"  incomplete_profile: {aggregate_result.get('incomplete_profile')}")
        missing_logs = aggregate_result.get("missing_logs", [])
        if missing_logs:
            console.print("  missing_logs:")
            for item in missing_logs:
                console.print(f"    - {item}")


def run_pipeline() -> dict[str, Any]:
    """Execute freeze -> simple_runner -> chain_runner -> aggregator."""
    result: dict[str, Any] = {
        "overall_status": "unknown",
        "steps": {},
        "aggregate": {},
    }

    try:
        manifest = load_manifest()
        validated = validate_manifest(manifest)
        manifest_snapshot_path = freeze_step(manifest, validated)
        result["steps"]["freeze"] = {"ok": True, "manifest_snapshot_path": str(manifest_snapshot_path)}
    except Exception as exc:
        result["steps"]["freeze"] = {"ok": False, "error": str(exc)}
        result["overall_status"] = "freeze_failed"
        return result

    simple_result = run_simple_runner(manifest_snapshot_path)
    result["steps"]["simple_runner"] = simple_result

    chain_result = run_chain_runner(manifest_snapshot_path)
    result["steps"]["chain_runner"] = chain_result

    raw_log_paths = [
        simple_result.get("raw_log_path"),
        chain_result.get("raw_log_path"),
    ]
    runner_failures: list[str] = []
    if not simple_result["ok"]:
        runner_failures.append(f"simple_runner failed: {simple_result.get('error', 'unknown error')}")
    if not chain_result["ok"]:
        runner_failures.append(f"chain_runner failed: {chain_result.get('error', 'unknown error')}")

    aggregate_result = run_aggregate(manifest_snapshot_path, raw_log_paths, runner_failures)
    result["aggregate"] = aggregate_result

    if runner_failures:
        result["overall_status"] = "runner_failed"
    elif aggregate_result.get("incomplete_profile"):
        result["overall_status"] = "incomplete"
    else:
        result["overall_status"] = "ok"
    return result


def main() -> int:
    ensure_output_dirs()
    try:
        results = run_pipeline()
    except Exception as exc:
        console.print(f"[red]pipeline aborted:[/red] {exc}")
        return 1

    report_summary(results)
    return 0 if results["overall_status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
