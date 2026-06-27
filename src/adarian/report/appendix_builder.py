"""Build appendix_b.json from completed simulation datasets."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


RISK_LEVEL_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def load_dataset(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"dataset must be object: {path}")
    return data


def build_appendix_b(datasets: list[dict[str, Any]], event_name: str) -> dict[str, Any]:
    if not datasets:
        raise ValueError("no datasets")

    risk_levels: Counter[str] = Counter()
    risk_types: Counter[str] = Counter()
    source_worlds: list[dict[str, Any]] = []
    scale_values: list[float] = []
    controversy_values: list[float] = []
    trajectories: list[Any] = []
    stance_rows: list[Any] = []
    inflections: list[Any] = []

    first = datasets[0]
    for index, dataset in enumerate(datasets):
        run_info = dataset.get("run_info") or {}
        sim = dataset.get("simulation_result") or {}
        verdict = sim.get("risk_verdict") or {}
        risk_type = sim.get("risk_type_classification") or {}

        if isinstance(run_info.get("event_scale"), (int, float)):
            scale_values.append(float(run_info["event_scale"]))
        if isinstance(run_info.get("event_controversy"), (int, float)):
            controversy_values.append(float(run_info["event_controversy"]))

        level = str(verdict.get("level") or "unknown")
        risk_levels[level] += 1
        for type_id in risk_type.get("primary_types") or []:
            risk_types[str(type_id)] += 1

        source_worlds.append({
            "world_index": index,
            "risk_verdict": verdict,
            "risk_type_classification": risk_type,
        })
        trajectories.append({"world_index": index, "items": sim.get("emotion_trajectory") or []})
        stance_rows.append({"world_index": index, "items": sim.get("agent_stance_matrix") or []})
        inflections.append({"world_index": index, "items": sim.get("inflection_points") or []})

    worst_level = max(risk_levels, key=lambda item: RISK_LEVEL_ORDER.get(item, 0)) if risk_levels else "unknown"
    context = first.get("source_context") or {}
    confirmed_risks = _confirmed_risks(source_worlds, risk_types, worst_level)
    measures = [_measure_for_risk(risk) for risk in confirmed_risks]

    return {
        "meta": {
            "event_name": event_name or first.get("run_info", {}).get("event_name") or context.get("event_summary") or "舆情事件",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "worlds_count": len(datasets),
        },
        "evolution_analysis": {
            "worlds_count": len(datasets),
            "event_scale_avg": _avg(scale_values),
            "event_scale_distribution": scale_values,
            "event_controversy_avg": _avg(controversy_values),
            "event_controversy_distribution": controversy_values,
            "risk_level_distribution": dict(risk_levels),
            "risk_type_frequency": dict(risk_types),
            "worst_reasonable_level": worst_level,
            "worst_reasonable_level_label": _level_label(worst_level),
            "outlier_worlds": [],
            "entities": context.get("event_entities") or [],
            "opinion_spreaders": context.get("opinion_spreaders") or [],
            "emotion_trajectory": trajectories,
            "agent_stance_matrix": stance_rows,
            "inflection_points": inflections,
        },
        "source_evidence": {"worlds": source_worlds},
        "risk_assessment": {
            "risks": confirmed_risks,
            "no_confirmed_risks_reason": "" if confirmed_risks else "completed worlds 未提供足够一致的风险证据。",
        },
        "countermeasures": {"measures": measures},
    }


def write_appendix_b(appendix_b: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(appendix_b, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def _level_label(level: str) -> str:
    return {"low": "低风险", "medium": "中风险", "high": "高风险", "critical": "极高风险"}.get(level, level)


def _confirmed_risks(source_worlds: list[dict[str, Any]], risk_types: Counter[str], worst_level: str) -> list[dict[str, Any]]:
    risks = []
    for type_id, count in risk_types.most_common(3):
        label = _risk_label(source_worlds, type_id)
        risks.append({
            "type_id": type_id,
            "type_label": label,
            "domain": "",
            "domain_label": "",
            "level_id": worst_level,
            "level_label": _level_label(worst_level),
            "trigger_signals": {"world_mentions": count},
            "trigger_reason": f"{count} 个 completed world 将该类型列为主要风险候选。",
            "reality_translation": f"相关讨论可能演化为{label}，需要结合事件主体回应和平台传播情况持续观察。",
        })
    return risks


def _risk_label(source_worlds: list[dict[str, Any]], type_id: str) -> str:
    for world in source_worlds:
        cls = world.get("risk_type_classification") or {}
        ids = cls.get("primary_types") or []
        labels = cls.get("type_labels") or []
        for index, item in enumerate(ids):
            if str(item) == type_id and index < len(labels):
                return str(labels[index])
    return type_id


def _measure_for_risk(risk: dict[str, Any]) -> dict[str, Any]:
    return {
        "risk_type_id": risk["type_id"],
        "risk_label": risk["type_label"],
        "trigger_reason_ref": risk["trigger_reason"],
        "level_id_ref": risk["level_id"],
        "responsible_body": "事件主体与平台方",
        "action_direction": "降低对立、补充事实、稳定讨论秩序",
        "measures": [
            f"围绕“{risk['type_label']}”发布事实口径清晰的回应材料。",
            "对高情绪表达和误读扩散内容进行持续监测，必要时补充说明。",
        ],
    }
