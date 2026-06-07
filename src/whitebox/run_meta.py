"""Run metadata and whitebox artifact writers."""

import json
from pathlib import Path

import config


def write_run_meta(run_context: dict, seed_file: Path, status: str, started_at: str, **extra) -> None:
    """Write run metadata for replay and acceptance checks."""
    outputs = run_context["outputs"]
    payload = {
        "batch_id": run_context.get("batch_id"),
        "batch_dir": str(run_context.get("batch_dir")) if run_context.get("batch_dir") else None,
        "run_id": run_context["run_id"],
        "seed_file": str(seed_file),
        "seed_copy": str(run_context["seed_copy"]),
        "run_dir": str(run_context["run_dir"]),
        "started_at": started_at,
        "provider": config.LLM_PROVIDER,
        "model": config.get_model_name(),
        "status": status,
        "outputs": {key: str(path) for key, path in outputs.items()},
    }
    payload.update(extra)
    with open(outputs["run_meta"], "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_whitebox_summary(
    run_context: dict,
    report_completeness: dict,
    artifact_check: dict,
) -> dict:
    """Write the top-level whitebox summary as an index plus status."""
    outputs = run_context["outputs"]
    checks = {
        "report_completeness": {
            "status": report_completeness["status"],
            "path": report_completeness.get("path"),
        },
        "artifact_check": {
            "status": artifact_check["status"],
            "path": artifact_check.get("path"),
        },
    }
    if artifact_check["status"] != "pass":
        status = "fail"
    elif report_completeness["status"] != "pass":
        status = "pass_with_warnings"
    else:
        status = "pass"
    payload = {
        "whitebox_version": "v1.3.1",
        "status": status,
        "checks": checks,
        "raw_sources": artifact_check["raw_sources"],
    }
    with open(outputs["whitebox_summary"], "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def write_whitebox_artifacts(run_context: dict) -> dict:
    """Write whitebox detail artifacts and the top-level index."""
    from src.whitebox import check_run_artifacts, write_artifact_check, write_report_completeness_summary
    run_dir = run_context["run_dir"]
    outputs = run_context["outputs"]
    report_completeness = write_report_completeness_summary(run_dir, outputs["final_report_md"])
    artifact_check = check_run_artifacts(run_dir)
    write_artifact_check(run_dir)
    summary = write_whitebox_summary(run_context, report_completeness, artifact_check)
    return {
        "report_completeness": report_completeness,
        "artifact_check": artifact_check,
        "summary": summary,
    }
