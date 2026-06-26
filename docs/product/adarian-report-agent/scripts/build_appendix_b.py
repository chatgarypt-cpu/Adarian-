#!/usr/bin/env python3
"""build_appendix_b.py — Adarian 仿真数据预处理脚本。

Usage:
  python build_appendix_b.py --mode evolution --input <input.json> --output <appendix_b.json>
  python build_appendix_b.py --mode risk       --input <input.json> --output <appendix_b.json>

Modes:
  evolution  读取 N 个 simulation_dataset.json → 聚合 → 白名单过滤 → 写入
             appendix_b.json（meta + evolution_analysis + source_evidence）
  risk       校验已有 appendix_b.json 是否已包含 risk_assessment + countermeasures

Note:
  --mode risk is validate-only. T2 risk assessment and countermeasure
  generation are performed by the LLM in context; this script must not
  generate or overwrite those branches.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

# Unicode categories to strip: Cc (control), Cf (format), Cs (surrogate), Zl/Zp (line/paragraph separator)
def _is_control_or_format(ch: str) -> bool:
    """Check if a character is a Unicode control, format, surrogate, or line/paragraph separator."""
    cat = unicodedata.category(ch)
    return cat in ("Cc", "Cf", "Cs", "Zl", "Zp")

# Windows filesystem-illegal characters (replaced with underscore)
_ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|]')

_FALLBACK_SLUG = "untitled_event"


def build_safe_event_slug(event_name: str) -> str:
    """将 event_name 转为安全的文件/目录名。

    - 剔除 Unicode 控制字符、格式字符、零宽字符
    - 替换 Windows 非法字符 ``/ \\ : * ? " < > |`` 为 ``_``
    - 所有空白字符（空格、制表、换行、回车、垂直制表等）折叠为 ``_``
    - 连续下划线折叠为一个
    - 去除首尾下划线
    - 限长 80 字符
    - 空结果回退为 ``untitled_event``
    """
    result = "".join(ch for ch in event_name if not _is_control_or_format(ch))
    result = _ILLEGAL_CHARS.sub("_", result)

    # Collapse all whitespace and consecutive underscores into single _
    cleaned: List[str] = []
    prev_underscore = False
    for ch in result:
        if ch == "_" or ch.isspace():
            if not prev_underscore:
                cleaned.append("_")
                prev_underscore = True
        else:
            cleaned.append(ch)
            prev_underscore = False

    result = "".join(cleaned).strip("_")

    if not result:
        return _FALLBACK_SLUG
    return result[:80]


# ---------------------------------------------------------------------------
# T0 helpers
# ---------------------------------------------------------------------------

def parse_input_json(path: str) -> Dict[str, Any]:
    """读取并校验上游输入 JSON 文件。

    Returns:
        dict with keys: event_name (str), seed_input_path (str), worlds (non-empty list)

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: JSON 格式不合法 或 schema 校验失败
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input JSON not found: {path}")
    try:
        with open(p, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    # --- schema validation ---
    if not isinstance(data, dict):
        raise ValueError("Input JSON must be a dict/object")

    # event_name
    if "event_name" not in data:
        raise ValueError("Input JSON missing required key: 'event_name'")
    if not isinstance(data["event_name"], str):
        raise ValueError("'event_name' must be a string")

    # seed_input_path
    if "seed_input_path" not in data:
        raise ValueError("Input JSON missing required key: 'seed_input_path'")
    if not isinstance(data["seed_input_path"], str):
        raise ValueError("'seed_input_path' must be a string")

    # worlds
    if "worlds" not in data:
        raise ValueError("Input JSON missing required key: 'worlds'")
    worlds = data["worlds"]
    if not isinstance(worlds, list):
        raise ValueError("'worlds' must be a list")
    if len(worlds) == 0:
        raise ValueError("'worlds' must contain at least 1 world")

    for i, w in enumerate(worlds):
        if not isinstance(w, dict):
            raise ValueError(f"worlds[{i}] must be a dict/object")
        if "label" not in w:
            raise ValueError(f"worlds[{i}] missing required key: 'label'")
        if "simulation_dataset_path" not in w:
            raise ValueError(f"worlds[{i}] missing required key: 'simulation_dataset_path'")

    return data


# ---------------------------------------------------------------------------
# T1 helpers
# ---------------------------------------------------------------------------

def load_simulation_datasets(
    worlds: List[Dict[str, str]], base_dir: str
) -> List[Dict[str, Any]]:
    """读取所有 world 的 simulation_dataset.json。

    Args:
        worlds: [{"label": "...", "simulation_dataset_path": "..."}, ...]
        base_dir: input JSON 所在目录，用于解析相对路径

    Returns:
        与 worlds 等长的 dict 列表

    Raises:
        FileNotFoundError: 任一 dataset 文件不存在
        ValueError: JSON 格式不合法
    """
    base = Path(base_dir)
    datasets: List[Dict[str, Any]] = []
    for w in worlds:
        ds_path = Path(w["simulation_dataset_path"])
        if not ds_path.is_absolute():
            ds_path = base / ds_path
        if not ds_path.exists():
            raise FileNotFoundError(
                f"Simulation dataset not found: {ds_path}"
            )
        try:
            with open(ds_path, "r", encoding="utf-8-sig") as fh:
                dataset = json.load(fh)
                dataset["_world_label"] = w["label"]
                datasets.append(dataset)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {ds_path}: {exc}") from exc
    return datasets


def _parse_scalar(value: str) -> Any:
    """Parse the tiny scalar subset used in reference YAML."""
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value.strip('"').strip("'")


def load_aggregation_config(path: Path) -> Dict[str, Any]:
    """Load the tiny YAML subset used by aggregation_config.yaml.

    PyYAML is intentionally not required. This parser only supports the
    structures this Skill owns.
    """
    if not path.exists():
        return {}

    config: Dict[str, Any] = {
        "version": 1,
        "numeric_metrics": [],
        "frequency_metrics": {},
        "risk_level_order": {},
        "bounded_source_evidence": {},
        "evolution_source_fields": [],
    }
    mode = ""
    current_numeric: Optional[Dict[str, Any]] = None
    current_frequency = ""
    current_evidence_section = ""

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()

        if not line.startswith(" ") and stripped.startswith("version:"):
            _, value = stripped.split(":", 1)
            config["version"] = _parse_scalar(value.strip())
            continue

        if stripped == "numeric_metrics:":
            mode = "numeric"
            current_numeric = None
            current_frequency = ""
            continue
        if stripped == "frequency_metrics:":
            mode = "frequency"
            current_numeric = None
            current_frequency = ""
            current_evidence_section = ""
            continue
        if stripped == "risk_level_order:":
            mode = "risk_order"
            current_numeric = None
            current_frequency = ""
            current_evidence_section = ""
            continue
        if stripped == "bounded_source_evidence:":
            mode = "bounded_evidence"
            current_numeric = None
            current_frequency = ""
            current_evidence_section = ""
            continue
        if stripped == "evolution_source_fields:":
            mode = "evolution_sources"
            current_numeric = None
            current_frequency = ""
            current_evidence_section = ""
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            mode = ""
            continue

        if mode == "numeric":
            if stripped.startswith("- "):
                current_numeric = {}
                config["numeric_metrics"].append(current_numeric)
                stripped = stripped[2:].strip()
            if current_numeric is not None and ":" in stripped:
                key, value = stripped.split(":", 1)
                current_numeric[key.strip()] = _parse_scalar(value.strip())
            continue

        if mode == "frequency":
            if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
                current_frequency = stripped[:-1]
                config["frequency_metrics"][current_frequency] = {}
                continue
            if current_frequency and ":" in stripped:
                key, value = stripped.split(":", 1)
                config["frequency_metrics"][current_frequency][key.strip()] = _parse_scalar(
                    value.strip()
                )

        if mode == "risk_order":
            if line.startswith("  ") and not line.startswith("    ") and ":" in stripped:
                key, value = stripped.split(":", 1)
                config["risk_level_order"][key.strip()] = _parse_scalar(value.strip())
            continue

        if mode == "bounded_evidence":
            if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
                current_evidence_section = stripped[:-1]
                config["bounded_source_evidence"][current_evidence_section] = []
                continue
            if current_evidence_section and stripped.startswith("- "):
                config["bounded_source_evidence"][current_evidence_section].append(
                    stripped[2:].strip()
                )
            continue

        if mode == "evolution_sources":
            if stripped.startswith("- "):
                config["evolution_source_fields"].append(stripped[2:].strip())
            continue

    return config


def _get_path(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Read a dotted path from a nested dict."""
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _mean(values: List[Any]) -> float:
    """Return mean of numeric values; non-numeric values are ignored."""
    nums = [v for v in values if isinstance(v, (int, float))]
    return sum(nums) / len(nums) if nums else 0


def _count_scalar_values(values: List[Any]) -> Dict[str, int]:
    """Count scalar values and return a stable plain dict."""
    counts: Counter[str] = Counter()
    for value in values:
        if value is None:
            continue
        counts[str(value)] += 1
    return dict(counts)


def _count_list_values(values: List[Any]) -> Dict[str, int]:
    """Count values from a list-valued field across worlds."""
    counts: Counter[str] = Counter()
    for value in values:
        if not isinstance(value, list):
            continue
        for item in value:
            if item is not None:
                counts[str(item)] += 1
    return dict(counts)


def _pick_keys(data: Any, keys: List[str]) -> Dict[str, Any]:
    """Copy selected keys from a dict, skipping absent keys."""
    if not isinstance(data, dict):
        return {}
    return {key: data[key] for key in keys if key in data}


def _bounded_world_evidence(
    dataset: Dict[str, Any],
    evidence_config: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Extract bounded risk evidence from one simulation dataset."""
    sim = dataset.get("simulation_result", {})
    evidence_config = evidence_config or {
        "risk_verdict": ["level", "label", "basis_text", "signals"],
        "risk_type_classification": [
            "primary_types",
            "type_labels",
            "primary_domain",
            "primary_domain_label",
        ],
    }
    return {
        "label": dataset.get("_world_label", ""),
        "risk_verdict": _pick_keys(
            sim.get("risk_verdict"),
            evidence_config.get("risk_verdict", []),
        ),
        "risk_type_classification": _pick_keys(
            sim.get("risk_type_classification"),
            evidence_config.get("risk_type_classification", []),
        ),
    }


def _risk_summary(
    datasets: List[Dict[str, Any]], risk_level_order: Dict[str, Any]
) -> Dict[str, Any]:
    """Compute the worst reasonable level and outlier worlds."""
    order = risk_level_order or {"low": 1, "medium": 2, "high": 3, "critical": 4}
    entries: List[Dict[str, Any]] = []
    for dataset in datasets:
        verdict = _get_path(dataset, "simulation_result.risk_verdict", {})
        if not isinstance(verdict, dict):
            continue
        level = verdict.get("level")
        if level is None or str(level) not in order:
            continue
        entries.append(
            {
                "world": dataset.get("_world_label", ""),
                "level": str(level),
                "label": verdict.get("label", ""),
                "rank": order[str(level)],
            }
        )

    if not entries:
        return {
            "worst_reasonable_level": "",
            "worst_reasonable_level_label": "",
            "outlier_worlds": [],
        }

    worst = max(entries, key=lambda item: item["rank"])
    counts = Counter(entry["level"] for entry in entries)
    worst_count = counts[worst["level"]]
    outlier_worlds = []
    if worst_count <= len(entries) / 2:
        outlier_worlds = [
            entry["world"]
            for entry in entries
            if entry["level"] == worst["level"] and entry["world"]
        ]

    return {
        "worst_reasonable_level": worst["level"],
        "worst_reasonable_level_label": worst["label"],
        "outlier_worlds": outlier_worlds,
    }


# ---------------------------------------------------------------------------
# M-2: module-level defaults for aggregate_multi_world.
# MUST stay in sync with references/aggregation_config.yaml for output_prefix
# and source_path.  aggregate is intentionally omitted — only mean is supported.
# When the config file is available these are NOT used; they exist only as a
# safe fallback for environments where the YAML file is unreadable.
# ---------------------------------------------------------------------------
_DEFAULT_NUMERIC_METRICS = [
    {"output_prefix": "event_scale", "source_path": "run_info.event_scale"},
    {"output_prefix": "event_controversy", "source_path": "run_info.event_controversy"},
]

_DEFAULT_FREQUENCY_METRICS = {
    "risk_level_distribution": {"source_path": "simulation_result.risk_verdict.level"},
    "risk_type_frequency": {"source_path": "simulation_result.risk_type_classification.primary_types"},
}

_EVOLUTION_OUTPUT_KEYS = {
    "source_context.event_entities": "entities",
    "source_context.opinion_spreaders": "opinion_spreaders",
    "simulation_result.emotion_trajectory": "emotion_trajectory",
    "simulation_result.agent_stance_matrix": "agent_stance_matrix",
    "simulation_result.inflection_points": "inflection_points",
}


def _append_configured_evolution_sources(
    result: Dict[str, Any],
    datasets: List[Dict[str, Any]],
    source_fields: List[str],
) -> None:
    """Append configured source fields to the aggregation result."""
    first = datasets[0]
    fields = source_fields or list(_EVOLUTION_OUTPUT_KEYS.keys())
    for source_path in fields:
        known = source_path in _EVOLUTION_OUTPUT_KEYS
        output_key = _EVOLUTION_OUTPUT_KEYS.get(source_path, source_path.split(".")[-1])
        if not known:
            print(
                f"WARNING: evolution source field '{source_path}' not in "
                f"_EVOLUTION_OUTPUT_KEYS; output key defaults to '{output_key}'.",
                file=sys.stderr,
            )
        if source_path.startswith("source_context."):
            result[output_key] = _get_path(first, source_path, [])
        else:
            result[output_key] = [_get_path(d, source_path, []) for d in datasets]


def aggregate_multi_world(
    datasets: List[Dict[str, Any]], config: Dict[str, Any]
) -> Dict[str, Any]:
    """多 world 聚合计算。

    对数值指标取均值 + 分布 + 最坏合理等级。
    config 为 aggregation_config.yaml 解析后的 dict。

    Args:
        datasets: load_simulation_datasets 的返回值
        config: 聚合规则配置

    Returns:
        聚合后的扁平 dict，含 _avg / _distribution 后缀字段
    """
    if not datasets:
        return {}

    result: Dict[str, Any] = {}
    result["worlds_count"] = len(datasets)

    numeric_metrics = config.get("numeric_metrics") or _DEFAULT_NUMERIC_METRICS
    for metric in numeric_metrics:
        prefix = metric["output_prefix"]
        values = [_get_path(d, metric["source_path"], 0) for d in datasets]
        result[f"{prefix}_avg"] = _mean(values)
        if metric.get("keep_distribution", True):
            result[f"{prefix}_distribution"] = values

    frequency_metrics = config.get("frequency_metrics") or _DEFAULT_FREQUENCY_METRICS
    for output_key, metric in frequency_metrics.items():
        values = [_get_path(d, metric["source_path"]) for d in datasets]
        if any(isinstance(value, list) for value in values):
            result[output_key] = _count_list_values(values)
        else:
            result[output_key] = _count_scalar_values(values)

    result.update(_risk_summary(datasets, config.get("risk_level_order", {})))
    _append_configured_evolution_sources(
        result, datasets, config.get("evolution_source_fields", [])
    )
    result["world_evidence"] = [
        _bounded_world_evidence(d, config.get("bounded_source_evidence", {}))
        for d in datasets
    ]

    return result


def filter_by_schema(
    data: Dict[str, Any], schema: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """按白名单 schema 递归过滤 dict。

    仅测试用，生产路径 main() 调用 filter_by_schema_paths()。

    schema 为 None 时原样返回 data。
    schema 的 key 层级定义了白名单结构，不在 schema 中的 key 会被剔除。
    """
    if schema is None:
        return data
    if not isinstance(data, dict) or not isinstance(schema, dict):
        return data

    result: Dict[str, Any] = {}
    for key, sub_schema in schema.items():
        if key in data:
            if isinstance(sub_schema, dict) and isinstance(data[key], dict):
                result[key] = filter_by_schema(data[key], sub_schema)
            else:
                result[key] = data[key]
    return result


def load_appendix_b_schema_paths(path: Path) -> Set[str]:
    """Load output paths declared in appendix_b_schema.yaml."""
    if not path.exists():
        return set()

    paths: Set[str] = set()
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("- path: "):
            paths.add(stripped.split(":", 1)[1].strip())
    return paths


def load_risk_mapping(path: Path) -> Optional[Dict[str, Dict[str, str]]]:
    """Load risk type labels and domains from the project-owned YAML subset.

    Returns None when the file doesn't exist (caller should skip mapping
    validation in that case).  The parser only handles the simple flat YAML
    subset used by references/risk_mapping.yaml: top-level ``domains:`` and
    ``risk_types:`` sections with ``- id:`` / ``key: value`` entries at a
    fixed 4-space indent.  Do not add nested mappings, sequences, quoted
    strings, or multi-line values to the sections this function reads.
    """
    if not path.exists():
        return None

    domains: Dict[str, str] = {}
    risk_types: Dict[str, Dict[str, str]] = {}
    section = ""
    current: Optional[Dict[str, str]] = None

    def _save_current() -> None:
        if not current or "id" not in current:
            return
        if section == "domains" and current.get("label"):
            domains[current["id"]] = current["label"]
        elif section == "risk_types" and current.get("label") and current.get("domain"):
            risk_types[current["id"]] = {
                "label": current["label"],
                "domain": current["domain"],
            }

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in ("domains:", "risk_types:"):
            _save_current()
            section = stripped[:-1]
            current = None
            continue
        if section and stripped.startswith("- id:"):
            _save_current()
            current = {"id": stripped.split(":", 1)[1].strip()}
            continue
        if current is not None and line.startswith("    ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = _parse_scalar(value.strip())

    _save_current()
    for entry in risk_types.values():
        entry["domain_label"] = domains.get(entry["domain"], "")
    return risk_types


def load_risk_policy(path: Path) -> Dict[str, Any]:
    """Load risk rules for risk-mode validation.

    Parses ``candidate_layer:``, ``evidence_layer:``, ``domain_bias:``, and
    ``level_selection:`` sections from references/risk_rules.yaml.
    Same simple-YAML-subset constraint as load_risk_mapping().
    """
    policy: Dict[str, Any] = {
        "min_confirmed_risks": 1,
        "max_confirmed_risks": 3,
        "allow_no_confirmed_risks_with_reason": False,
        "evidence_layer": {},
        "domain_bias": {},
        "level_selection": {
            "prefer_upstream_level": True,
            "fallback_level_id": "medium",
            "fallback_level_label": "中风险",
        },
    }
    if not path.exists():
        return policy

    in_candidate_layer = False
    in_evidence_layer = False
    in_domain_bias = False
    in_level_selection = False
    current_dimension = ""
    in_any_list = False
    current_condition: Optional[Dict[str, Any]] = None
    current_domain = ""
    evidence_layer: Dict[str, Any] = {}
    domain_bias: Dict[str, List[str]] = {}
    level_selection: Dict[str, Any] = {}

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        # --- section headers ---
        if not line.startswith(" ") and stripped.endswith(":"):
            in_candidate_layer = stripped == "candidate_layer:"
            in_evidence_layer = stripped == "evidence_layer:"
            in_domain_bias = stripped == "domain_bias:"
            in_level_selection = stripped == "level_selection:"
            if in_evidence_layer:
                current_dimension = ""
                in_any_list = False
                current_condition = None
            if in_domain_bias:
                current_domain = ""
            continue

        # --- candidate_layer (unchanged) ---
        if in_candidate_layer and line.startswith("  ") and not line.startswith("    ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            if key.strip() in policy:
                policy[key.strip()] = _parse_scalar(value.strip())

        # --- evidence_layer ---
        if in_evidence_layer:
            # dimension header, e.g. "  high_pressure:"
            if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
                current_dimension = stripped[:-1]
                evidence_layer[current_dimension] = {"any": []}
                in_any_list = False
                continue
            # "    any:"
            if current_dimension and stripped == "any:":
                in_any_list = True
                continue
            # "      - source: ..."
            if in_any_list and stripped.startswith("- source:"):
                current_condition = {"source": stripped.split(":", 1)[1].strip()}
                evidence_layer[current_dimension]["any"].append(current_condition)
                continue
            # "        contains: high" etc.
            if current_condition is not None and line.startswith("        ") and ":" in stripped:
                key, value = stripped.split(":", 1)
                current_condition[key.strip()] = _parse_scalar(value.strip())
            continue

        # --- domain_bias ---
        if in_domain_bias:
            # domain header, e.g. "  communication_evolution:"
            if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
                current_domain = stripped[:-1]
                domain_bias[current_domain] = []
                continue
            # "    - spread_pressure"
            if current_domain and stripped.startswith("- "):
                domain_bias[current_domain].append(stripped[2:].strip())
            continue

        # --- level_selection ---
        if in_level_selection and line.startswith("  ") and not line.startswith("    ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            level_selection[key.strip()] = _parse_scalar(value.strip())

    policy["evidence_layer"] = evidence_layer
    policy["domain_bias"] = domain_bias
    policy["level_selection"] = level_selection
    return policy


def load_countermeasure_contract(path: Path) -> Dict[str, str]:
    """Load measure-to-risk reference fields from the project-owned YAML subset.

    Parses the ``pair_references:`` section of references/countermeasure_templates.yaml.
    Same simple-YAML-subset constraint as load_risk_mapping().
    """
    contract = {
        "trigger_reason_ref": "trigger_reason",
        "level_id_ref": "level_id",
    }
    if not path.exists():
        return contract

    loaded: Dict[str, str] = {}
    in_pair_references = False
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "pair_references:":
            in_pair_references = True
            continue
        if in_pair_references and line.startswith("    ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            loaded[key.strip()] = value.strip()
            continue
        if in_pair_references and line.startswith("  ") and not line.startswith("    "):
            in_pair_references = False
    return loaded or contract


def filter_by_schema_paths(data: Dict[str, Any], allowed_paths: Set[str]) -> Dict[str, Any]:
    """Filter a nested dict by dotted output paths."""
    if not allowed_paths:
        return data

    def _copy(current: Any, prefix: str) -> Any:
        if not isinstance(current, dict):
            return current
        result: Dict[str, Any] = {}
        for key, value in current.items():
            path = f"{prefix}.{key}" if prefix else key
            child_allowed = {
                allowed
                for allowed in allowed_paths
                if allowed == path or allowed.startswith(f"{path}.")
            }
            if path in allowed_paths:
                result[key] = value
            elif child_allowed and isinstance(value, dict):
                filtered = _copy(value, path)
                if filtered != {}:
                    result[key] = filtered
        return result

    return _copy(data, "")


_REQUIRED_RISK_FIELDS = [
    "type_id",
    "type_label",
    "domain",
    "domain_label",
    "level_id",
    "level_label",
    "trigger_signals",
    "trigger_reason",
    "reality_translation",
]

_REQUIRED_MEASURE_FIELDS = [
    "risk_type_id",
    "risk_label",
    "responsible_body",
    "action_direction",
    "measure",
]


def _check_condition(value: Any, op: str, expected: Any) -> bool:
    """Evaluate a single evidence condition against a resolved value."""
    if value is None:
        return False
    if op == "contains":
        if isinstance(value, list):
            return expected in value
        if isinstance(value, dict):
            return expected in value or str(expected) in str(value)
        return expected in str(value)
    if op == "equals":
        return value == expected
    if op == "gte":
        try:
            return float(value) >= float(expected)
        except (TypeError, ValueError):
            return False
    if op == "contains_gte":
        if isinstance(value, list):
            return any(
                isinstance(v, (int, float)) and float(v) >= float(expected)
                for v in value
            )
        return False
    return False


def _evaluate_evidence_condition(condition: Dict[str, Any], appendix: Dict[str, Any]) -> bool:
    """Check whether a single evidence-layer condition is met by the appendix data."""
    source = condition.get("source", "")
    op = next((k for k in ("contains", "equals", "gte", "contains_gte") if k in condition), None)
    if op is None:
        return False
    expected = condition[op]

    if "[]" in source:
        parts = source.split("[].")
        list_path = parts[0]  # e.g. "source_evidence.worlds"
        field_path = parts[1] if len(parts) > 1 else ""
        worlds = _get_path(appendix, list_path)
        if not isinstance(worlds, list):
            return False
        for world in worlds:
            value = _get_path(world, field_path) if field_path else world
            if _check_condition(value, op, expected):
                return True
        return False

    value = _get_path(appendix, source)
    return _check_condition(value, op, expected)


def _validate_evidence_for_risk(
    risk: Dict[str, Any],
    appendix: Dict[str, Any],
    evidence_layer: Dict[str, Any],
    domain_bias: Dict[str, List[str]],
) -> Optional[str]:
    """Check that a risk satisfies its domain's required evidence dimensions.

    Returns an error message or None if all conditions are met.
    """
    domain = risk.get("domain", "")
    required_dims = domain_bias.get(domain, [])
    if not required_dims:
        return None  # domain not in domain_bias → skip evidence check

    for dim_name in required_dims:
        dim = evidence_layer.get(dim_name)
        if not isinstance(dim, dict):
            return (
                f"risk_assessment risk '{risk.get('type_id')}': "
                f"evidence dimension '{dim_name}' not defined in evidence_layer."
            )
        conditions = dim.get("any", [])
        if not conditions:
            continue

        met = any(
            _evaluate_evidence_condition(cond, appendix) for cond in conditions
        )
        if not met:
            return (
                f"risk_assessment risk '{risk.get('type_id')}' "
                f"(domain={domain}): evidence dimension '{dim_name}' unsatisfied. "
                f"None of {len(conditions)} condition(s) were met."
            )

    return None


def _validate_level_consistency(
    risk: Dict[str, Any],
    appendix: Dict[str, Any],
    level_selection: Dict[str, Any],
) -> Optional[str]:
    """Check risk level_id consistency with upstream levels when prefer_upstream_level is true."""
    if not level_selection.get("prefer_upstream_level", False):
        return None
    worlds = _get_path(appendix, "source_evidence.worlds")
    if not isinstance(worlds, list):
        return None
    upstream_levels = {
        _get_path(w, "risk_verdict.level") for w in worlds
        if isinstance(w, dict) and _get_path(w, "risk_verdict.level") is not None
    }
    risk_level = risk.get("level_id")
    if risk_level is not None and risk_level not in upstream_levels:
        return (
            f"risk_assessment risk '{risk.get('type_id')}': "
            f"level_id '{risk_level}' does not match any upstream level "
            f"{sorted(upstream_levels)}."
        )
    return None


def validate_risk_sections(
    appendix: Dict[str, Any],
    risk_mapping: Optional[Dict[str, Dict[str, str]]] = None,
    risk_policy: Optional[Dict[str, Any]] = None,
    countermeasure_contract: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """Validate T2 risk and countermeasure contracts without mutating data."""
    risks = _get_path(appendix, "risk_assessment.risks")
    measures = _get_path(appendix, "countermeasures.measures")
    if not isinstance(risks, list) or not isinstance(measures, list):
        return (
            "Existing risk_assessment.risks and countermeasures.measures "
            "must be present before validation."
        )

    no_risk_reason = _get_path(appendix, "risk_assessment.no_confirmed_risks_reason")
    policy = risk_policy if risk_policy is not None else {
        "min_confirmed_risks": 1,
        "max_confirmed_risks": 3,
        "allow_no_confirmed_risks_with_reason": False,
    }
    pair_references = countermeasure_contract if countermeasure_contract is not None else {
        "trigger_reason_ref": "trigger_reason",
        "level_id_ref": "level_id",
    }
    if not risks:
        if (
            policy.get("allow_no_confirmed_risks_with_reason")
            and isinstance(no_risk_reason, str)
            and no_risk_reason.strip()
            and not measures
        ):
            return None
        return "risk_assessment.risks must be non-empty unless no_confirmed_risks_reason is provided."

    if isinstance(no_risk_reason, str) and no_risk_reason.strip():
        return "no_confirmed_risks_reason is only allowed when risks and measures are both empty."
    if len(risks) < int(policy["min_confirmed_risks"]):
        return f"risk_assessment.risks must contain at least {policy['min_confirmed_risks']} item(s)."
    if len(risks) > int(policy["max_confirmed_risks"]):
        return f"risk_assessment.risks must contain at most {policy['max_confirmed_risks']} item(s)."

    risk_by_id: Dict[str, Dict[str, Any]] = {}
    for index, risk in enumerate(risks):
        if not isinstance(risk, dict):
            return f"risk_assessment.risks[{index}] must be an object."
        missing = [field for field in _REQUIRED_RISK_FIELDS if not risk.get(field)]
        if missing:
            return f"risk_assessment.risks[{index}] missing required fields: {', '.join(missing)}."
        trigger_signals = risk["trigger_signals"]
        if not isinstance(trigger_signals, (list, dict)) or not trigger_signals:
            return f"risk_assessment.risks[{index}].trigger_signals must be a non-empty list or object."
        reality_translation = risk["reality_translation"]
        if not isinstance(reality_translation, str) or not reality_translation.strip():
            return f"risk_assessment.risks[{index}].reality_translation must be a non-empty string."
        risk_type_id = str(risk["type_id"])
        expected = (risk_mapping or {}).get(risk_type_id)
        if risk_mapping is not None:
            if expected is None:
                return f"risk_assessment.risks[{index}].type_id is not defined in risk_mapping.yaml."
            for field in ("type_label", "domain", "domain_label"):
                expected_value = expected[field.replace("type_", "")]
                if risk[field] != expected_value:
                    return f"risk_assessment.risks[{index}].{field} does not match risk_mapping.yaml."
        risk_by_id[risk_type_id] = risk

        # H-1: evidence-layer validation (machine-enforced)
        evidence_err = _validate_evidence_for_risk(
            risk, appendix,
            policy.get("evidence_layer", {}),
            policy.get("domain_bias", {}),
        )
        if evidence_err:
            return evidence_err

        level_err = _validate_level_consistency(
            risk, appendix, policy.get("level_selection", {})
        )
        if level_err:
            return level_err

    measure_counts: Counter[str] = Counter()
    for index, measure in enumerate(measures):
        if not isinstance(measure, dict):
            return f"countermeasures.measures[{index}] must be an object."
        missing = [field for field in _REQUIRED_MEASURE_FIELDS if not measure.get(field)]
        if missing:
            return f"countermeasures.measures[{index}] missing required fields: {', '.join(missing)}."
        risk_type_id = str(measure["risk_type_id"])
        paired_risk = risk_by_id.get(risk_type_id)
        if paired_risk is None and not measure.get("supporting_measure"):
            return (
                f"countermeasures.measures[{index}].risk_type_id does not match "
                "any confirmed risk."
            )
        if paired_risk is not None:
            if measure["risk_label"] != paired_risk["type_label"]:
                return (
                    f"countermeasures.measures[{index}].risk_label "
                    f'expected "{paired_risk["type_label"]}" '
                    f'but got "{measure["risk_label"]}".'
                )
            for measure_field, risk_field in pair_references.items():
                if measure.get(measure_field) != paired_risk.get(risk_field):
                    return (
                        f"countermeasures.measures[{index}].{measure_field} "
                        f'expected "{paired_risk[risk_field]}" '
                        f'but got "{measure[measure_field]}".'
                    )
            measure_counts[risk_type_id] += 1

    missing_measures = sorted(risk_id for risk_id in risk_by_id if measure_counts[risk_id] == 0)
    if missing_measures:
        return f"Missing countermeasure for risk type(s): {', '.join(missing_measures)}."

    return None


# ---------------------------------------------------------------------------
# T1 / T2 输出
# ---------------------------------------------------------------------------

def write_appendix_b(data: Dict[str, Any], output_path: str) -> None:
    """将数据写入 appendix_b.json。

    自动创建父目录。

    Raises:
        TypeError: data 不是 dict
    """
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict, got {type(data).__name__}")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main(
    mode: str = "evolution",
    input_path: str = "",
    output_path: str = "",
) -> int:
    """CLI 入口。

    Args:
        mode: "evolution" 或 "risk"
        input_path: 上游 input JSON 路径
        output_path: appendix_b.json 输出路径

    Returns:
        0 成功，非零失败
    """
    if mode not in ("evolution", "risk"):
        print(f"ERROR: unknown mode '{mode}'. Must be 'evolution' or 'risk'.", file=sys.stderr)
        return 1

    try:
        input_data = parse_input_json(input_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    base_dir = str(Path(input_path).parent)

    try:
        if mode == "evolution":
            datasets = load_simulation_datasets(input_data["worlds"], base_dir)
            config_path = (
                Path(__file__).resolve().parent.parent
                / "references"
                / "aggregation_config.yaml"
            )
            aggregated = aggregate_multi_world(
                datasets, load_aggregation_config(config_path)
            )

            output: Dict[str, Any] = {
                "meta": {
                    "event_name": input_data["event_name"],
                    "generated_at": datetime.now(timezone.utc)
                    .replace(microsecond=0)
                    .isoformat(),
                    "worlds_count": len(datasets),
                },
                "evolution_analysis": {
                    key: value
                    for key, value in aggregated.items()
                    if key != "world_evidence"
                },
                "source_evidence": {"worlds": aggregated.get("world_evidence", [])},
            }
            schema_path = (
                Path(__file__).resolve().parent.parent
                / "references"
                / "appendix_b_schema.yaml"
            )
            output = filter_by_schema_paths(
                output, load_appendix_b_schema_paths(schema_path)
            )
            write_appendix_b(output, output_path)

        elif mode == "risk":
            if not Path(output_path).exists():
                print(
                    f"ERROR: appendix_b.json not found at {output_path}. "
                    "Run --mode evolution first.",
                    file=sys.stderr,
                )
                return 1
            try:
                with open(output_path, "r", encoding="utf-8-sig") as fh:
                    appendix = json.load(fh)
            except json.JSONDecodeError as exc:
                print(f"ERROR: corrupt appendix_b.json at {output_path}: {exc}", file=sys.stderr)
                return 1
            references_dir = Path(__file__).resolve().parent.parent / "references"
            validation_error = validate_risk_sections(
                appendix,
                load_risk_mapping(references_dir / "risk_mapping.yaml"),
                load_risk_policy(references_dir / "risk_rules.yaml"),
                load_countermeasure_contract(
                    references_dir / "countermeasure_templates.yaml"
                ),
            )
            if validation_error:
                print(
                    f"ERROR: --mode risk is validate-only. {validation_error}",
                    file=sys.stderr,
                )
                return 1

    except (FileNotFoundError, ValueError, KeyError, TypeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Adarian 仿真数据预处理"
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["evolution", "risk"],
        help="'evolution': 演化分析 + 证据提取 | 'risk': 校验已生成的风险与对策分支",
    )
    parser.add_argument(
        "--input", required=True, help="上游 input JSON 路径"
    )
    parser.add_argument(
        "--output", required=True, help="appendix_b.json 输出路径"
    )
    args = parser.parse_args()
    sys.exit(main(mode=args.mode, input_path=args.input, output_path=args.output))
