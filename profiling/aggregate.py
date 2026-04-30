"""Aggregate profiling raw logs into model-level metrics.

This module reads only `run_manifest.json` and raw logs, then emits
JSON-serializable structures for `model_profiles.json` and a readable summary.
It does not depend on runner summary output and does not classify pools inside
the runner.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, median
from typing import Any, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "profiling" / "output"
DEFAULT_MANIFEST_PATH = DEFAULT_OUTPUT_ROOT / "run_manifest.json"
DEFAULT_RAW_LOG_DIR = DEFAULT_OUTPUT_ROOT / "raw_logs"
DEFAULT_MODEL_PROFILES_PATH = DEFAULT_OUTPUT_ROOT / "model_profiles.json"
DEFAULT_SUMMARY_PATH = DEFAULT_OUTPUT_ROOT / "profile_summary.md"

TIMEOUT_RATE_LOW = 0.05
TIMEOUT_RATE_HIGH = 0.15
FINAL_PASS_HIGH = 0.85
FINAL_PASS_MIN = 0.70
RETRY_LOW = 0.5
RETRY_HIGH = 1.0

STABILITY_SCORE = {"high": 2, "medium": 1, "low": 0}
WORKLOAD_SIMPLE = "simple"
WORKLOAD_CHAIN = "chain"
WORKLOAD_UNKNOWN = "unknown"

GROUPING_KEYS = ("request_id", "sample_id", "trace_id", "call_id", "task_id", "run_id", "benchmark_run_id", "conversation_id")
NON_SAMPLE_RECORD_TYPES = {"run_meta", "meta", "summary"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _as_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)


def _load_json_payload(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _maybe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return None if value != value else float(value)
    try:
        text = str(value).strip()
        return None if not text else float(text)
    except (TypeError, ValueError):
        return None


def _maybe_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        text = str(value).strip()
        return None if not text else int(float(text))
    except (TypeError, ValueError):
        return None


def _maybe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _first_non_empty(record: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _load_manifest(manifest: Mapping[str, Any] | str | Path | None) -> dict[str, Any]:
    if manifest is None:
        return _load_json_payload(DEFAULT_MANIFEST_PATH) if DEFAULT_MANIFEST_PATH.exists() else {}
    if isinstance(manifest, (str, Path)):
        return _load_json_payload(_as_path(manifest))
    return dict(manifest)


def _iter_json_objects(text: str) -> list[dict[str, Any]]:
    payload = text.strip()
    if not payload:
        return []
    if payload.startswith("["):
        loaded = json.loads(payload)
        return [item for item in loaded if isinstance(item, dict)] if isinstance(loaded, list) else []
    if payload.startswith("{"):
        loaded = json.loads(payload)
        if isinstance(loaded, dict):
            if isinstance(loaded.get("records"), list):
                return [item for item in loaded["records"] if isinstance(item, dict)]
            return [loaded]
    rows: list[dict[str, Any]] = []
    for line in payload.splitlines():
        line = line.strip()
        if not line:
            continue
        loaded = json.loads(line)
        if isinstance(loaded, dict):
            rows.append(loaded)
    return rows


def load_raw_records(source: str | Path | Sequence[str | Path]) -> list[dict[str, Any]]:
    """Load raw records from a JSON/JSONL file, directory, or a sequence of paths."""
    paths: list[Path] = []
    if isinstance(source, (str, Path)):
        path = _as_path(source)
        if path.is_dir():
            paths.extend(sorted(path.glob("*.jsonl")))
            paths.extend(sorted(path.glob("*.json")))
        else:
            paths.append(path)
    else:
        paths.extend(_as_path(item) for item in source)

    records: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".jsonl":
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                loaded = json.loads(line)
                if isinstance(loaded, dict):
                    records.append(loaded)
        else:
            records.extend(_iter_json_objects(text))
    return records


def _manifest_models(manifest: Mapping[str, Any]) -> list[str]:
    models_conf = manifest.get("models")
    if isinstance(models_conf, Mapping):
        names = models_conf.get("names")
        if isinstance(names, list) and names:
            return [str(item) for item in names if str(item).strip()]
        source_path = models_conf.get("source_path")
        if isinstance(source_path, str) and source_path.strip():
            path = _as_path(source_path)
            if not path.is_absolute():
                path = (PROJECT_ROOT / path).resolve()
            if path.exists():
                content = path.read_text(encoding="utf-8").strip()
                items = [item.strip() for item in content.split("、")] if content else []
                return [item for item in items if item]

    keys = ("models", "model_names", "model_list", "candidate_models", "profiling_models")
    for key in keys:
        value = manifest.get(key)
        if isinstance(value, list) and value:
            return [str(item) for item in value if str(item).strip()]
    return []


def _manifest_cases(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    keys = ("cases", "seed_cases", "profiling_cases")
    for key in keys:
        value = manifest.get(key)
        if isinstance(value, list) and value:
            return [item for item in value if isinstance(item, Mapping)]
    nested = manifest.get("inputs")
    if isinstance(nested, Mapping):
        for key in keys:
            value = nested.get(key)
            if isinstance(value, list) and value:
                return [item for item in value if isinstance(item, Mapping)]
    return []


def _manifest_concurrency_levels(manifest: Mapping[str, Any]) -> list[int]:
    keys = ("concurrency_levels", "concurrency", "levels")
    for key in keys:
        value = manifest.get(key)
        if isinstance(value, list) and value:
            return [level for level in (_maybe_int(item) for item in value) if level and level > 0]
    nested = manifest.get("inputs")
    if isinstance(nested, Mapping):
        for key in keys:
            value = nested.get(key)
            if isinstance(value, list) and value:
                return [level for level in (_maybe_int(item) for item in value) if level and level > 0]
    return []


def _manifest_raw_log_dir(manifest: Mapping[str, Any]) -> Path | None:
    candidate_paths: list[Any] = [
        manifest.get("raw_log_dir"),
        manifest.get("raw_logs_dir"),
        manifest.get("raw_logs"),
        manifest.get("artifact_dir"),
    ]
    nested = manifest.get("output")
    if isinstance(nested, Mapping):
        candidate_paths.extend([nested.get("raw_log_dir"), nested.get("raw_logs_dir"), nested.get("raw_logs"), nested.get("artifact_dir")])
    for item in candidate_paths:
        if not item:
            continue
        path = _as_path(item)
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        return path
    return None


def _extract_workload(record: Mapping[str, Any]) -> str:
    record_type = str(record.get("record_type", "")).strip().lower()
    if record_type in NON_SAMPLE_RECORD_TYPES:
        return WORKLOAD_UNKNOWN
    for key in ("workload", "benchmark_kind", "test_kind", "suite", "stage", "phase", "task_type"):
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip().lower()
        if "simple" in text:
            return WORKLOAD_SIMPLE
        if "chain" in text or "complex" in text or "profile" in text:
            return WORKLOAD_CHAIN
        if "generator" in text or "review" in text or "validator" in text:
            return WORKLOAD_CHAIN
    if any(key in record for key in ("generator_latency_sec", "review_latency_sec", "validator_pass", "estimated_percentage_sum")):
        return WORKLOAD_CHAIN
    if any(key in record for key in ("elapsed_sec", "raw_response", "parsed_payload", "schema_ok")):
        return WORKLOAD_SIMPLE
    mode = str(record.get("mode", "")).strip().lower()
    if mode in {"first_pass", "retry_pass"}:
        return WORKLOAD_CHAIN
    return WORKLOAD_UNKNOWN


def _extract_latency(record: Mapping[str, Any], keys: Sequence[str]) -> float | None:
    return _maybe_float(_first_non_empty(record, keys))


def _series(values: Sequence[float | None]) -> dict[str, Any]:
    clean = [value for value in values if value is not None]
    if not clean:
        return {"count": 0, "min": None, "max": None, "avg": None, "median": None}
    return {"count": len(clean), "min": min(clean), "max": max(clean), "avg": fmean(clean), "median": median(clean)}


def _request_key(record: Mapping[str, Any]) -> Any | None:
    for key in GROUPING_KEYS:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _group_requests(records: Sequence[dict[str, Any]]) -> tuple[list[list[dict[str, Any]]], str | None]:
    counts: Counter[str] = Counter()
    for record in records:
        for key in GROUPING_KEYS:
            if record.get(key) not in (None, "", [], {}):
                counts[key] += 1
                break
    if not counts:
        return [[record] for record in records], None
    key = counts.most_common(1)[0][0]
    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        value = record.get(key)
        grouped[value if value not in (None, "", [], {}) else id(record)].append(record)
    return list(grouped.values()), key


def _request_flags(group: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = list(group)
    first = min(ordered, key=lambda item: (_maybe_int(item.get("retry_count")) or 0, 0 if str(item.get("mode", "")).strip().lower() == "first_pass" else 1))
    final = max(ordered, key=lambda item: _maybe_int(item.get("retry_count")) or 0)

    def passed(item: Mapping[str, Any]) -> bool:
        if _maybe_bool(item.get("timeout")) is True:
            return False
        if _maybe_bool(item.get("empty_response")) is True:
            return False
        if _maybe_bool(item.get("json_parse_ok")) is False:
            return False
        if _maybe_bool(item.get("generator_success")) is False:
            return False
        validator = _maybe_bool(item.get("validator_pass"))
        return bool(validator)

    return {
        "first_pass_success": passed(first) and str(first.get("mode", "")).strip().lower() in {"first_pass", "serial", "concurrent", "simple"},
        "final_pass_success": passed(final),
        "timeout": any(_maybe_bool(item.get("timeout")) is True for item in ordered),
        "retry_count": max((_maybe_int(item.get("retry_count")) or 0) for item in ordered),
    }


def _numeric_timeout_rate(records: Sequence[Mapping[str, Any]]) -> float | None:
    total = len(records)
    if not total:
        return None
    return sum(1 for record in records if _maybe_bool(record.get("timeout")) is True) / total


def _compute_stability(timeout_rate: float | None, final_pass_rate: float | None, avg_retry_count: float | None, schema_error_rate: float | None) -> str:
    if timeout_rate is None:
        return "low"
    if timeout_rate < TIMEOUT_RATE_LOW:
        if (final_pass_rate is None or final_pass_rate >= FINAL_PASS_HIGH) and (avg_retry_count is None or avg_retry_count <= RETRY_LOW) and (schema_error_rate is None or schema_error_rate <= 0.10):
            return "high"
        if (final_pass_rate is None or final_pass_rate >= FINAL_PASS_MIN) and (avg_retry_count is None or avg_retry_count <= RETRY_HIGH):
            return "medium"
    if timeout_rate <= TIMEOUT_RATE_HIGH and (final_pass_rate is None or final_pass_rate >= FINAL_PASS_MIN):
        return "medium"
    return "low"


def _workload_concurrency_profile(records: Sequence[dict[str, Any]], workload: str) -> dict[str, Any]:
    level_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        level = _maybe_int(record.get("concurrency_level") or record.get("concurrency") or record.get("parallelism"))
        if level is not None and level > 0:
            level_map[level].append(record)
    if not level_map:
        return {"workload": workload, "levels": [], "baseline_level": None, "stable_limit": None, "notes": ["No concurrency level field found."]}

    levels = sorted(level_map)
    baseline = level_map[levels[0]]
    previous_latency = _series([_extract_latency(record, ("end_to_end_latency_sec", "elapsed_sec", "latency_sec")) for record in baseline])["avg"]
    previous_pass = None if workload == WORKLOAD_SIMPLE else fmean([1.0 if _maybe_bool(record.get("validator_pass")) is True and _maybe_bool(record.get("timeout")) is not True else 0.0 for record in baseline])
    stable_limit: int | None = None
    rows: list[dict[str, Any]] = []

    for level in levels:
        bucket = level_map[level]
        latency = _series([_extract_latency(record, ("end_to_end_latency_sec", "elapsed_sec", "latency_sec")) for record in bucket])
        timeout_rate = _numeric_timeout_rate(bucket)
        pass_rate = None
        retry_avg = None
        if workload != WORKLOAD_SIMPLE:
            pass_rate = sum(1 for record in bucket if _maybe_bool(record.get("validator_pass")) is True and _maybe_bool(record.get("timeout")) is not True) / len(bucket)
            retry_avg = fmean([_maybe_int(record.get("retry_count")) or 0 for record in bucket])

        stable = timeout_rate is not None and timeout_rate < TIMEOUT_RATE_LOW
        if latency["avg"] is not None and previous_latency not in (None, 0):
            stable = stable and latency["avg"] <= previous_latency * 1.75
        if workload != WORKLOAD_SIMPLE and pass_rate is not None and previous_pass not in (None, 0):
            stable = stable and pass_rate >= previous_pass * 0.9
        if stable:
            stable_limit = level
        if latency["avg"] is not None:
            previous_latency = latency["avg"]
        if workload != WORKLOAD_SIMPLE and pass_rate is not None:
            previous_pass = pass_rate

        rows.append({
            "concurrency_level": level,
            "total_requests": len(bucket),
            "timeout_rate": timeout_rate,
            "latency": latency,
            "pass_rate": pass_rate,
            "avg_retry_count": retry_avg,
        })

    return {"workload": workload, "levels": rows, "baseline_level": levels[0], "stable_limit": stable_limit, "notes": []}


def _recommended_pool(row: Mapping[str, Any], cohort: Mapping[str, float | None]) -> str:
    timeout_rate = _maybe_float(row.get("timeout_rate"))
    final_pass_rate = _maybe_float(row.get("final_pass_rate"))
    avg_retry_count = _maybe_float(row.get("avg_retry_count"))
    stability = str(row.get("stability", "low"))
    concurrency_limit = _maybe_int(row.get("concurrency_limit"))
    simple_latency = _maybe_float(row.get("simple_latency"))
    generator_latency = _maybe_float(row.get("generator_latency"))
    end_to_end_latency = _maybe_float(row.get("end_to_end_latency"))

    if timeout_rate is not None and timeout_rate > TIMEOUT_RATE_HIGH:
        return "fragile"
    if avg_retry_count is not None and avg_retry_count >= RETRY_HIGH:
        return "fragile"
    if final_pass_rate is not None and final_pass_rate < FINAL_PASS_MIN:
        return "fragile"
    if stability == "low":
        return "fragile"

    fast_ok = stability == "high" and (concurrency_limit is None or concurrency_limit >= 3)
    if fast_ok and simple_latency is not None and end_to_end_latency is not None:
        if (cohort["simple_latency"] is None or simple_latency <= cohort["simple_latency"]) and (cohort["end_to_end_latency"] is None or end_to_end_latency <= cohort["end_to_end_latency"] * 1.1):
            return "fast"

    heavy_ok = stability in {"medium", "high"} and (final_pass_rate is None or final_pass_rate >= FINAL_PASS_MIN)
    if heavy_ok:
        if generator_latency is None or cohort["generator_latency"] is None or generator_latency >= cohort["generator_latency"] or (end_to_end_latency is not None and cohort["end_to_end_latency"] is not None and end_to_end_latency >= cohort["end_to_end_latency"]):
            return "heavy"
    return "fast" if fast_ok else "heavy"


def _fallback_target(models: Sequence[Mapping[str, Any]]) -> str:
    if not models:
        return ""

    def sort_key(row: Mapping[str, Any]) -> tuple:
        return (
            STABILITY_SCORE.get(str(row.get("stability", "low")), 0),
            _maybe_float(row.get("final_pass_rate")) or -1.0,
            -(_maybe_float(row.get("timeout_rate")) or 1.0),
            -(_maybe_float(row.get("avg_retry_count")) or 10.0),
            -(_maybe_float(row.get("end_to_end_latency")) or 10**9),
            -(_maybe_float(row.get("simple_latency")) or 10**9),
        )

    return str(sorted(models, key=sort_key, reverse=True)[0].get("model_name", "")).strip()


def _summarize_model(
    *,
    model_name: str,
    model_records: Sequence[dict[str, Any]],
    manifest_cases: Sequence[Mapping[str, Any]],
    manifest_concurrency_levels: Sequence[int],
    warnings: list[str],
) -> dict[str, Any]:
    simple_records = [record for record in model_records if _extract_workload(record) == WORKLOAD_SIMPLE]
    chain_records = [record for record in model_records if _extract_workload(record) == WORKLOAD_CHAIN]
    unknown_records = [record for record in model_records if _extract_workload(record) == WORKLOAD_UNKNOWN]

    if unknown_records:
        warnings.append(f"{model_name}: {len(unknown_records)} records have unknown workload tags.")

    simple_latency = _series([_extract_latency(record, ("elapsed_sec", "latency_sec", "end_to_end_latency_sec")) for record in simple_records])
    generator_latency = _series([_extract_latency(record, ("generator_latency_sec",)) for record in chain_records])
    review_latency = _series([_extract_latency(record, ("review_latency_sec",)) for record in chain_records])
    end_to_end_latency = _series([_extract_latency(record, ("end_to_end_latency_sec", "elapsed_sec", "latency_sec")) for record in chain_records])

    total_records = len(model_records)
    timeout_rate = _numeric_timeout_rate(model_records)
    empty_response_count = sum(1 for record in model_records if _maybe_bool(record.get("empty_response")) is True)
    json_parse_fail_count = sum(1 for record in model_records if _maybe_bool(record.get("json_parse_ok")) is False)
    subprocess_execution_count = sum(1 for record in chain_records if str(record.get("execution_mode", "")).strip().lower() == "subprocess")
    killed_count = sum(1 for record in chain_records if str(record.get("timeout_final_state", "")).strip().lower() == "killed")
    kill_failed_count = sum(1 for record in chain_records if str(record.get("timeout_final_state", "")).strip().lower() == "kill_failed")
    worker_exit_abnormal_count = sum(
        1 for record in chain_records if str(record.get("worker_exit_status", "")).strip().lower() == "abnormal_exit"
    )
    schema_fail_count = sum(
        1
        for record in model_records
        if _maybe_bool(record.get("empty_response")) is True
        or _maybe_bool(record.get("json_parse_ok")) is False
        or _maybe_bool(record.get("validator_pass")) is False
    )
    schema_error_rate = schema_fail_count / total_records if total_records else None

    simple_groups, simple_group_key = _group_requests(simple_records)
    chain_groups, chain_group_key = _group_requests(chain_records)
    if simple_records and simple_group_key is None:
        warnings.append(f"{model_name}: simple metrics are computed at record level because no explicit request identifier exists.")
    if chain_records and chain_group_key is None:
        warnings.append(f"{model_name}: chain metrics are computed at record level because no explicit request identifier exists.")

    if chain_group_key is not None:
        first_pass_rate = sum(1 for group in chain_groups if _request_flags(group)["first_pass_success"]) / len(chain_groups) if chain_groups else None
        final_pass_rate = sum(1 for group in chain_groups if _request_flags(group)["final_pass_success"]) / len(chain_groups) if chain_groups else None
        avg_retry_count = fmean([_request_flags(group)["retry_count"] for group in chain_groups]) if chain_groups else None
    else:
        first_pass_rate = (
            sum(
                1
                for record in chain_records
                if str(record.get("mode", "")).strip().lower() == "first_pass"
                and _maybe_bool(record.get("validator_pass")) is True
                and _maybe_bool(record.get("generator_success")) is not False
                and _maybe_bool(record.get("timeout")) is not True
                and _maybe_bool(record.get("empty_response")) is not True
                and _maybe_bool(record.get("json_parse_ok")) is not False
            )
            / len(chain_records)
            if chain_records
            else None
        )
        final_pass_rate = (
            sum(
                1
                for record in chain_records
                if _maybe_bool(record.get("validator_pass")) is True
                and _maybe_bool(record.get("generator_success")) is not False
                and _maybe_bool(record.get("timeout")) is not True
                and _maybe_bool(record.get("empty_response")) is not True
                and _maybe_bool(record.get("json_parse_ok")) is not False
            )
            / len(chain_records)
            if chain_records
            else None
        )
        avg_retry_count = fmean([_maybe_int(record.get("retry_count")) or 0 for record in chain_records]) if chain_records else None

    simple_concurrency = _workload_concurrency_profile(simple_records, WORKLOAD_SIMPLE) if simple_records else {"workload": WORKLOAD_SIMPLE, "levels": [], "baseline_level": None, "stable_limit": None, "notes": []}
    chain_concurrency = _workload_concurrency_profile(chain_records, WORKLOAD_CHAIN) if chain_records else {"workload": WORKLOAD_CHAIN, "levels": [], "baseline_level": None, "stable_limit": None, "notes": []}
    concurrency_limits = [value for value in (simple_concurrency.get("stable_limit"), chain_concurrency.get("stable_limit")) if isinstance(value, int)]
    concurrency_limit = min(concurrency_limits) if concurrency_limits else None

    return {
        "model_name": model_name,
        "record_counts": {
            "total": total_records,
            "simple": len(simple_records),
            "chain": len(chain_records),
            "manifest_cases": len(manifest_cases),
            "manifest_concurrency_levels": list(manifest_concurrency_levels),
        },
        "simple_latency": simple_latency["avg"],
        "generator_latency": generator_latency["avg"],
        "review_latency": review_latency["avg"],
        "end_to_end_latency": end_to_end_latency["avg"],
        "first_pass_rate": first_pass_rate,
        "final_pass_rate": final_pass_rate,
        "avg_retry_count": avg_retry_count,
        "concurrency_limit": concurrency_limit,
        "timeout_rate": timeout_rate,
        "stability": _compute_stability(timeout_rate, final_pass_rate, avg_retry_count, schema_error_rate),
        "recommended_pool": None,
        "fallback_target": None,
        "breakdown": {
            "simple_latency": simple_latency,
            "generator_latency": generator_latency,
            "review_latency": review_latency,
            "end_to_end_latency": end_to_end_latency,
            "timeout_count": sum(1 for record in model_records if _maybe_bool(record.get("timeout")) is True),
            "subprocess_execution_count": subprocess_execution_count,
            "killed_count": killed_count,
            "kill_failed_count": kill_failed_count,
            "worker_exit_abnormal_count": worker_exit_abnormal_count,
            "empty_response_count": empty_response_count,
            "json_parse_fail_count": json_parse_fail_count,
            "schema_fail_count": schema_fail_count,
            "schema_error_rate": schema_error_rate,
            "concurrency_profiles": {"simple": simple_concurrency, "chain": chain_concurrency},
        },
        "warnings": warnings,
    }


def build_profile_summary_data(
    manifest: Mapping[str, Any] | str | Path | None,
    raw_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a JSON-serializable profiling summary from manifest + raw logs."""
    manifest_payload = _load_manifest(manifest)
    expected_models = _manifest_models(manifest_payload)
    expected_cases = _manifest_cases(manifest_payload)
    expected_concurrency_levels = _manifest_concurrency_levels(manifest_payload)

    normalized_records = [
        dict(record)
        for record in raw_records
        if isinstance(record, Mapping) and str(record.get("record_type", "")).strip().lower() not in NON_SAMPLE_RECORD_TYPES
    ]
    grouped_by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invalid_model_records = 0
    for record in normalized_records:
        model_name = str(record.get("model_name") or record.get("model") or "").strip()
        if not model_name:
            invalid_model_records += 1
            continue
        grouped_by_model[model_name].append(record)

    observed_models = list(grouped_by_model)
    ordered_models = expected_models or observed_models
    warnings: list[str] = []
    if invalid_model_records:
        warnings.append(f"Raw logs contain records without model_name: {invalid_model_records}")
    if expected_models:
        missing = [model for model in expected_models if model not in grouped_by_model]
        extra = [model for model in observed_models if model not in expected_models]
        if missing:
            warnings.append("Missing raw logs for manifest models: " + ", ".join(missing))
        if extra:
            warnings.append("Raw logs contain models not listed in manifest: " + ", ".join(extra))

    model_rows: list[dict[str, Any]] = []
    for model_name in ordered_models:
        before = len(warnings)
        model_row = _summarize_model(
            model_name=model_name,
            model_records=grouped_by_model.get(model_name, []),
            manifest_cases=expected_cases,
            manifest_concurrency_levels=expected_concurrency_levels,
            warnings=warnings.copy(),
        )
        for item in model_row.get("warnings", [])[before:]:
            if item not in warnings:
                warnings.append(item)
        model_rows.append(model_row)

    if not model_rows:
        for model_name, records in grouped_by_model.items():
            before = len(warnings)
            model_row = _summarize_model(
                model_name=model_name,
                model_records=records,
                manifest_cases=expected_cases,
                manifest_concurrency_levels=expected_concurrency_levels,
                warnings=warnings.copy(),
            )
            for item in model_row.get("warnings", [])[before:]:
                if item not in warnings:
                    warnings.append(item)
            model_rows.append(model_row)

    # Keep the top-level warnings list deduplicated while preserving order.
    deduped_warnings: list[str] = []
    for item in warnings:
        if item not in deduped_warnings:
            deduped_warnings.append(item)
    warnings = deduped_warnings

    cohort = {
        "simple_latency": median([row["simple_latency"] for row in model_rows if row.get("simple_latency") is not None]) if any(row.get("simple_latency") is not None for row in model_rows) else None,
        "generator_latency": median([row["generator_latency"] for row in model_rows if row.get("generator_latency") is not None]) if any(row.get("generator_latency") is not None for row in model_rows) else None,
        "end_to_end_latency": median([row["end_to_end_latency"] for row in model_rows if row.get("end_to_end_latency") is not None]) if any(row.get("end_to_end_latency") is not None for row in model_rows) else None,
    }

    for row in model_rows:
        row["recommended_pool"] = _recommended_pool(row, cohort)

    fallback_target = _fallback_target(model_rows)
    for row in model_rows:
        row["fallback_target"] = fallback_target

    pool_counts = Counter(str(row.get("recommended_pool", "fragile")) for row in model_rows)
    stability_counts = Counter(str(row.get("stability", "low")) for row in model_rows)
    execution_hygiene = {
        "subprocess_execution_count": sum(
            int(row.get("breakdown", {}).get("subprocess_execution_count", 0) or 0) for row in model_rows
        ),
        "timeout_count": sum(int(row.get("breakdown", {}).get("timeout_count", 0) or 0) for row in model_rows),
        "killed_count": sum(int(row.get("breakdown", {}).get("killed_count", 0) or 0) for row in model_rows),
        "kill_failed_count": sum(
            int(row.get("breakdown", {}).get("kill_failed_count", 0) or 0) for row in model_rows
        ),
        "worker_exit_abnormal_count": sum(
            int(row.get("breakdown", {}).get("worker_exit_abnormal_count", 0) or 0) for row in model_rows
        ),
    }
    ranked_models = sorted(model_rows, key=lambda row: (
        STABILITY_SCORE.get(str(row.get("stability", "low")), 0),
        _maybe_float(row.get("final_pass_rate")) or -1.0,
        -(_maybe_float(row.get("timeout_rate")) or 1.0),
        -(_maybe_float(row.get("avg_retry_count")) or 10.0),
        -(_maybe_float(row.get("end_to_end_latency")) or 10**9),
    ), reverse=True)

    summary_sections = [
        {
            "title": "Overview",
            "kind": "kv",
            "items": [
                {"label": "generated_at", "value": _now_iso()},
                {"label": "manifest_models", "value": len(expected_models) if expected_models else len(model_rows)},
                {"label": "observed_models", "value": len(observed_models)},
                {"label": "raw_records", "value": len(normalized_records)},
                {"label": "failed_records", "value": sum(1 for record in normalized_records if _maybe_bool(record.get("timeout")) is True or record.get("exception_type") not in (None, "") or (_extract_workload(record) == WORKLOAD_CHAIN and _maybe_bool(record.get("validator_pass")) is False))},
                {"label": "fallback_target", "value": fallback_target},
            ],
        },
        {"title": "Pool Counts", "kind": "kv", "items": [{"label": "fast", "value": pool_counts.get("fast", 0)}, {"label": "heavy", "value": pool_counts.get("heavy", 0)}, {"label": "fragile", "value": pool_counts.get("fragile", 0)}]},
        {"title": "Stability Counts", "kind": "kv", "items": [{"label": "high", "value": stability_counts.get("high", 0)}, {"label": "medium", "value": stability_counts.get("medium", 0)}, {"label": "low", "value": stability_counts.get("low", 0)}]},
        {
            "title": "Execution Hygiene",
            "kind": "kv",
            "items": [
                {"label": "subprocess_execution_count", "value": execution_hygiene["subprocess_execution_count"]},
                {"label": "timeout_count", "value": execution_hygiene["timeout_count"]},
                {"label": "killed_count", "value": execution_hygiene["killed_count"]},
                {"label": "kill_failed_count", "value": execution_hygiene["kill_failed_count"]},
                {"label": "worker_exit_abnormal_count", "value": execution_hygiene["worker_exit_abnormal_count"]},
            ],
        },
        {
            "title": "Model Table",
            "kind": "table",
            "columns": ["model_name", "simple_latency", "generator_latency", "review_latency", "end_to_end_latency", "first_pass_rate", "final_pass_rate", "avg_retry_count", "concurrency_limit", "timeout_rate", "stability", "recommended_pool", "fallback_target"],
            "rows": [
                {key: row.get(key) for key in ["model_name", "simple_latency", "generator_latency", "review_latency", "end_to_end_latency", "first_pass_rate", "final_pass_rate", "avg_retry_count", "concurrency_limit", "timeout_rate", "stability", "recommended_pool", "fallback_target"]}
                for row in ranked_models
            ],
        },
        {"title": "Warnings", "kind": "list", "items": warnings},
    ]

    return {
        "generated_at": _now_iso(),
        "manifest": manifest_payload,
        "expected_models": expected_models,
        "expected_cases": expected_cases,
        "expected_concurrency_levels": expected_concurrency_levels,
        "record_count": len(normalized_records),
        "failed_record_count": sum(1 for record in normalized_records if _maybe_bool(record.get("timeout")) is True or record.get("exception_type") not in (None, "") or (_extract_workload(record) == WORKLOAD_CHAIN and _maybe_bool(record.get("validator_pass")) is False)),
        "model_count": len(model_rows),
        "fallback_target": fallback_target,
        "pool_counts": dict(pool_counts),
        "stability_counts": dict(stability_counts),
        "execution_hygiene": execution_hygiene,
        "models": model_rows,
        "summary_sections": summary_sections,
        "warnings": warnings,
        "cohort_medians": cohort,
    }


def render_profile_summary(summary: Mapping[str, Any]) -> str:
    lines: list[str] = ["# Profiling Summary", ""]
    lines.extend([
        f"- generated_at: {summary.get('generated_at')}",
        f"- fallback_target: {summary.get('fallback_target')}",
        f"- record_count: {summary.get('record_count')}",
        f"- model_count: {summary.get('model_count')}",
        "",
    ])
    for section in summary.get("summary_sections", []):
        lines.append(f"## {section.get('title', 'Section')}")
        kind = section.get("kind")
        if kind == "kv":
            for item in section.get("items", []):
                lines.append(f"- {item.get('label')}: {item.get('value')}")
        elif kind == "table":
            columns = section.get("columns", [])
            lines.append("")
            lines.append("| " + " | ".join(columns) + " |")
            lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
            for row in section.get("rows", []):
                lines.append("| " + " | ".join("" if row.get(column) is None else str(row.get(column)) for column in columns) + " |")
        elif kind == "list":
            items = section.get("items", [])
            if items:
                for item in items:
                    lines.append(f"- {item}")
            else:
                lines.append("- none")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def aggregate_profile(
    manifest: Mapping[str, Any] | str | Path | None = None,
    raw_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate profiling data from a manifest payload and raw records."""
    if raw_records is None:
        manifest_payload = _load_manifest(manifest)
        raw_log_dir = _manifest_raw_log_dir(manifest_payload) or DEFAULT_RAW_LOG_DIR
        raw_records = load_raw_records(raw_log_dir)
        return build_profile_summary_data(manifest_payload, raw_records)
    return build_profile_summary_data(manifest, raw_records)


def _check_raw_logs_completeness(raw_log_source: str | Path | Sequence[str | Path] | None) -> tuple[list[str], list[str], list[Path]]:
    """Check raw log existence/completeness from explicit source.

    Returns (missing, existing, existing_paths).
    """
    missing: list[str] = []
    existing: list[str] = []
    existing_paths: list[Path] = []

    if raw_log_source is None:
        return ["raw log source not provided"], [], []

    if isinstance(raw_log_source, (str, Path)):
        source_path = _as_path(raw_log_source)
        if not source_path.is_absolute():
            source_path = (PROJECT_ROOT / source_path).resolve()
        if source_path.is_dir():
            jsonl_files = sorted(source_path.glob("*.jsonl"))
            if not jsonl_files:
                return [f"raw_logs directory has no jsonl files: {source_path}"], [], []
            for path in jsonl_files:
                if path.stat().st_size == 0:
                    missing.append(f"{path.name} (empty)")
                else:
                    existing.append(path.name)
                    existing_paths.append(path)
            return missing, existing, existing_paths

        if not source_path.exists():
            return [f"{source_path} (absent)"], [], []
        if source_path.stat().st_size == 0:
            return [f"{source_path.name} (empty)"], [], []
        return [], [source_path.name], [source_path]

    for item in raw_log_source:
        path = _as_path(item)
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        if not path.exists():
            missing.append(f"{path} (absent)")
        elif path.stat().st_size == 0:
            missing.append(f"{path.name} (empty)")
        else:
            existing.append(path.name)
            existing_paths.append(path)

    if not existing_paths and not missing:
        missing.append("raw log source resolved to no files")
    return missing, existing, existing_paths


def aggregate_from_paths(
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    raw_log_source: str | Path | Sequence[str | Path] | None = None,
) -> dict[str, Any]:
    manifest_payload = _load_manifest(manifest_path)
    source = raw_log_source if raw_log_source is not None else (_manifest_raw_log_dir(manifest_payload) or DEFAULT_RAW_LOG_DIR)
    missing, existing, existing_paths = _check_raw_logs_completeness(source)

    raw_records = load_raw_records(existing_paths if existing_paths else [])
    summary = build_profile_summary_data(manifest_payload, raw_records)
    has_failures = bool(summary.get("failed_record_count", 0))

    expected_models = summary.get("expected_models", [])
    observed_models = {row.get("model_name") for row in summary.get("models", [])}
    for model_name in expected_models:
        if model_name not in observed_models:
            missing.append(f"missing model data: {model_name}")

    deduped_missing: list[str] = []
    for item in missing:
        if item not in deduped_missing:
            deduped_missing.append(item)

    summary["has_failures"] = has_failures
    summary["incomplete_profile"] = len(deduped_missing) > 0 or has_failures
    summary["missing_logs"] = deduped_missing
    summary["existing_logs"] = existing

    return summary


def write_outputs(
    summary: Mapping[str, Any],
    *,
    model_profiles_path: str | Path = DEFAULT_MODEL_PROFILES_PATH,
    summary_path: str | Path = DEFAULT_SUMMARY_PATH,
) -> None:
    model_profiles_path = _as_path(model_profiles_path)
    summary_path = _as_path(summary_path)
    model_profiles_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    model_profiles_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(render_profile_summary(summary), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate profiling raw logs into model-level metrics.")
    parser.add_argument("--manifest", type=str, default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--raw-logs", type=str, default=None)
    parser.add_argument("--output-json", type=str, default=str(DEFAULT_MODEL_PROFILES_PATH))
    parser.add_argument("--output-md", type=str, default=str(DEFAULT_SUMMARY_PATH))
    args = parser.parse_args(list(argv) if argv is not None else None)

    summary = aggregate_from_paths(args.manifest, args.raw_logs)
    write_outputs(summary, model_profiles_path=args.output_json, summary_path=args.output_md)
    print(json.dumps({"ok": True, "models": summary.get("model_count", 0), "fallback_target": summary.get("fallback_target", "")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
