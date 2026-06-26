#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serve-layer artifact readers and observability normalizers.

This is the single place where web APIs read run artifacts. It does not
collect new runtime data and does not replace RuntimeLogger/TokenTracker.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from adarian.serve.schemas import normalize_status

PHASE_LABEL_MAP: dict[str, str] = {
    "phase1_entity_extraction": "Phase 1",
    "phase2_topology_builder": "Phase 2",
    "phase3_tick_simulation": "Phase 3",
    "analysis_aggregation": "分析层",
    "analysis_risk_classifier": "风险分类",
    "phase4_report_agent": "Phase 4",
    "done": "已完成",
}


def read_json(path: str | Path) -> dict[str, Any] | list[Any] | None:
    candidate = Path(path or "")
    if not candidate.exists() or not candidate.is_file():
        return None
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def read_text_lines(path: str | Path, limit: int = 120) -> list[str]:
    candidate = Path(path or "")
    if not candidate.exists() or not candidate.is_file():
        return []
    try:
        lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return lines[-limit:] if limit > 0 else lines


def batch_log_lines(batch: dict[str, Any], limit: int = 120) -> list[str]:
    return read_text_lines(Path(batch.get("batch_dir") or "") / "scheduler_batch.log", limit)


def world_run_dir(world: dict[str, Any]) -> Path:
    return Path(world.get("run_dir") or "")


def world_dataset_path(world: dict[str, Any]) -> Path:
    explicit = Path(world.get("dataset_path") or "")
    if explicit.exists():
        return explicit
    return world_run_dir(world) / "simulation_dataset.json"


def world_artifacts(world: dict[str, Any]) -> dict[str, Path]:
    run_dir = world_run_dir(world)
    return {
        "run_dir": run_dir,
        "dataset": world_dataset_path(world),
        "tick_logs": run_dir / "tick_logs.json",
        "run_log": run_dir / "run.log",
        "run_meta": run_dir / "run_meta.json",
        "report_json": run_dir / "report.json",
        "final_report_json": run_dir / "final_report.json",
        "final_report_md": run_dir / "final_report.md",
    }


def get_world_by_index(worlds: list[dict[str, Any]], world_index: int) -> dict[str, Any] | None:
    for world in worlds:
        if int(world.get("world_index", -1)) == world_index:
            return world
    return None


def dataset_summary(world: dict[str, Any]) -> dict[str, Any]:
    paths = world_artifacts(world)
    dataset = read_json(paths["dataset"])
    if not isinstance(dataset, dict):
        return {
            "available": False,
            "state": "missing",
            "dataset_path": str(paths["dataset"]),
            "event_entities_count": 0,
            "opinions_count": 0,
            "risk_verdict": {},
            "risk_type_classification": {},
            "source_context": {},
        }

    sim = dataset.get("simulation_result", {}) if isinstance(dataset.get("simulation_result"), dict) else {}
    source_context = dataset.get("source_context", {}) if isinstance(dataset.get("source_context"), dict) else {}
    event_entities = source_context.get("event_entities", [])
    opinion_spreaders = source_context.get("opinion_spreaders", [])
    stance_matrix = sim.get("agent_stance_matrix", [])
    return {
        "available": True,
        "state": "available",
        "dataset_path": str(paths["dataset"]),
        "event_entities_count": len(event_entities) if isinstance(event_entities, list) else 0,
        "opinions_count": len(stance_matrix) if isinstance(stance_matrix, list) else (len(opinion_spreaders) if isinstance(opinion_spreaders, list) else 0),
        "risk_verdict": sim.get("risk_verdict", {}) if isinstance(sim.get("risk_verdict"), dict) else {},
        "risk_type_classification": sim.get("risk_type_classification", {}) if isinstance(sim.get("risk_type_classification"), dict) else {},
        "source_context": source_context,
        "agent_stance_matrix": stance_matrix if isinstance(stance_matrix, list) else [],
    }


def world_summary(world: dict[str, Any]) -> dict[str, Any]:
    status = normalize_status(world.get("raw_status") or world.get("status"))
    summary = dataset_summary(world)
    run_meta = read_json(world_artifacts(world)["run_meta"])
    if not isinstance(run_meta, dict):
        run_meta = {}
    return {
        "id": str(world.get("id", "")),
        "batch_id": world.get("batch_id", ""),
        "world_index": world.get("world_index", 0),
        "model": world.get("model_name", ""),
        "status": status,
        "raw_status": world.get("raw_status") or world.get("status"),
        "run_dir": world.get("run_dir", ""),
        "dataset": summary,
        "run_meta": run_meta,
        "elapsed_seconds": world.get("elapsed_seconds") if world.get("elapsed_seconds") is not None else run_meta.get("elapsed_seconds"),
        "error": world.get("error_message") or run_meta.get("error", ""),
    }


def world_progress(world: dict[str, Any]) -> dict[str, Any]:
    """Read run.log to determine live phase and elapsed time."""
    path = world_artifacts(world)["run_log"]
    lines = read_text_lines(path, 0)
    if not lines:
        return {"phase": "等待中", "elapsed_seconds": None}

    run_start_ts = ""
    for line in lines[:5]:
        match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) RUN START", line)
        if match:
            run_start_ts = match.group(1)
            break

    phase_raw = "pending"
    for line in reversed(lines):
        start_m = re.search(r"PHASE START name=(\S+)", line)
        if start_m:
            phase_raw = start_m.group(1)
            break
        end_m = re.search(r"PHASE END name=(\S+)", line)
        if end_m:
            phase_raw = "done"
            break

    elapsed: float | None = None
    if run_start_ts:
        from datetime import datetime
        try:
            start_dt = datetime.strptime(run_start_ts, "%Y-%m-%d %H:%M:%S")
            if phase_raw == "done":
                last_elapsed: float | None = None
                for line in lines:
                    match = re.search(r"PHASE END name=\S+ elapsed=([\d.]+)s", line)
                    if match:
                        last_elapsed = float(match.group(1))
                if last_elapsed is not None:
                    elapsed = last_elapsed
            if elapsed is None:
                elapsed = round((datetime.now() - start_dt).total_seconds(), 1)
        except Exception:
            pass

    return {"phase": PHASE_LABEL_MAP.get(phase_raw, phase_raw), "elapsed_seconds": elapsed}


def review_row(world: dict[str, Any], index: int, complete: bool) -> dict[str, Any]:
    status = normalize_status(world.get("raw_status") or world.get("status"))
    summary = dataset_summary(world)
    risk_type = summary.get("risk_type_classification", {})
    risk_verdict = summary.get("risk_verdict", {})
    labels = risk_type.get("type_labels") if isinstance(risk_type, dict) else []
    risks = "、".join(labels) if isinstance(labels, list) and labels else ""
    level = str(risk_verdict.get("label") or risk_verdict.get("level") or "") if isinstance(risk_verdict, dict) else ""

    if status == "completed" and summary.get("available"):
        risk_text = risks or "风险标签缺失"
        level_text = _risk_level_label(level) if level else "待定"
        level_variant = _risk_variant(level)
    elif status == "completed":
        risk_text = "产物缺失"
        level_text = "待定"
        level_variant = "warn"
    elif status == "failed":
        risk_text = world.get("error_message") or "world 执行失败"
        level_text = "失败"
        level_variant = "bad"
    else:
        risk_text = "待检测"
        level_text = "待定"
        level_variant = "warn"

    evidence_tail = read_text_lines(world_artifacts(world)["run_log"], 20)
    return {
        "world": f"第 {index + 1} 轮",
        "worldIndex": index,
        "batchId": world.get("batch_id", ""),
        "risks": risk_text,
        "level": level_text,
        "levelVariant": level_variant,
        "status": "可用" if status == "completed" else ("失败" if status == "failed" else "运行中"),
        "statusVariant": "ok" if status == "completed" else ("bad" if status == "failed" else "warn"),
        "evidence": summary.get("dataset_path") or world.get("run_dir") or "",
        "evidenceTail": evidence_tail,
        "entities": summary.get("event_entities_count", 0),
        "opinions": summary.get("opinions_count", 0),
        "complete": complete,
    }


def build_review_rows(worlds: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    complete = all(normalize_status(world.get("raw_status") or world.get("status")) in {"completed", "failed"} for world in worlds)
    return complete, [review_row(world, index, complete) for index, world in enumerate(worlds)]


def world_ticks(world: dict[str, Any]) -> dict[str, Any]:
    path = world_artifacts(world)["tick_logs"]
    payload = read_json(path)
    ticks = payload if isinstance(payload, list) else []
    return {
        "world_index": world.get("world_index", 0),
        "model": world.get("model_name", ""),
        "state": "available" if ticks else "missing",
        "tick_logs_path": str(path),
        "ticks": ticks,
    }


def batch_events(batch: dict[str, Any], worlds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for idx, line in enumerate(batch_log_lines(batch, 120)):
        events.append(_event(
            f"batch-log-{idx}",
            "batch",
            "scheduler",
            _line_tone(line),
            "批次日志",
            _strip_timestamp(line),
            timestamp=_timestamp_from_line(line),
        ))

    counts = _world_counts(worlds)
    if not events:
        events.append(_event("batch-state", "batch", "status", "run", "批次状态", f"completed={counts['completed']} running={counts['running']} failed={counts['failed']} pending={counts['pending']}"))
    events.append(_event("batch-summary", "batch", "metrics", "ok" if counts["failed"] == 0 else "warn", "批次汇总", f"共 {counts['total']} 个 world，{counts['completed']} 完成 / {counts['running']} 运行 / {counts['failed']} 失败"))
    return events


def world_events(world: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    paths = world_artifacts(world)
    for idx, line in enumerate(read_text_lines(paths["run_log"], 240)):
        parsed = _parse_run_log_line(line, idx, world)
        if parsed:
            events.append(parsed)

    ticks = world_ticks(world).get("ticks", [])
    for tick in ticks if isinstance(ticks, list) else []:
        tick_num = tick.get("tick", 0) if isinstance(tick, dict) else 0
        entries = tick.get("entries", []) if isinstance(tick, dict) else []
        for entry_index, entry in enumerate(entries if isinstance(entries, list) else []):
            if not isinstance(entry, dict):
                continue
            speaker = entry.get("group_name") or entry.get("agent") or entry.get("speaker") or "agent"
            comment = entry.get("comment") or entry.get("post") or entry.get("content") or ""
            stance = _stance_text(entry)
            events.append(_event(
                f"world-{world.get('world_index', 0)}-tick-{tick_num}-{entry_index}",
                "world",
                "agent",
                "run",
                str(speaker),
                str(comment),
                world_index=world.get("world_index", 0),
                model=world.get("model_name", ""),
                phase="phase3",
                meta={"tick": tick_num, "stance": stance, "role": entry.get("speaker_status") or entry.get("role") or ""},
            ))
    return events


def run_metrics(batch: dict[str, Any], worlds: list[dict[str, Any]]) -> dict[str, Any]:
    counts = _world_counts(worlds)
    world_items = []
    total_tokens = 0
    per_model: dict[str, int] = {}
    per_phase: dict[str, dict[str, Any]] = {}
    for world in worlds:
        paths = world_artifacts(world)
        meta = read_json(paths["run_meta"])
        meta = meta if isinstance(meta, dict) else {}
        log_lines = read_text_lines(paths["run_log"], 400)
        token_summary = _parse_token_summary(log_lines)
        phase_summary = _parse_phase_summary(log_lines)
        model = str(world.get("model_name") or meta.get("model") or "")
        world_tokens = int(token_summary.get("total_tokens", 0) or 0)
        total_tokens += world_tokens
        if model:
            per_model[model] = per_model.get(model, 0) + world_tokens
        for name, value in phase_summary.items():
            phase = per_phase.setdefault(name, {"elapsed_seconds": 0.0, "total_tokens": 0, "calls": 0, "llm_elapsed_seconds": 0.0})
            phase["elapsed_seconds"] = round(float(phase.get("elapsed_seconds", 0.0)) + float(value.get("elapsed_seconds", 0.0)), 2)
        for name, value in token_summary.get("per_phase", {}).items():
            if not isinstance(value, dict):
                continue
            phase = per_phase.setdefault(name, {"elapsed_seconds": 0.0, "total_tokens": 0, "calls": 0, "llm_elapsed_seconds": 0.0})
            phase["total_tokens"] = int(phase.get("total_tokens", 0) or 0) + int(value.get("total_tokens", 0) or 0)
            phase["calls"] = int(phase.get("calls", 0) or 0) + int(value.get("calls", 0) or 0)
            phase["llm_elapsed_seconds"] = round(float(phase.get("llm_elapsed_seconds", 0.0) or 0.0) + float(value.get("elapsed_seconds", 0.0) or 0.0), 2)
        world_items.append({
            "world_index": world.get("world_index", 0),
            "model": model,
            "status": normalize_status(world.get("raw_status") or world.get("status")),
            "elapsed_seconds": world.get("elapsed_seconds") if world.get("elapsed_seconds") is not None else meta.get("elapsed_seconds"),
            "phase_summary": phase_summary,
            "token_summary": token_summary,
        })
    return {
        "batch_id": batch.get("id", ""),
        "status": normalize_status(batch.get("raw_status") or batch.get("status")),
        "elapsed_seconds": _batch_elapsed_seconds(world_items),
        "report_count": _report_count(batch),
        "counts": counts,
        "worlds": world_items,
        "tokens": {
            "total_tokens": total_tokens,
            "per_model": {model: {"total_tokens": tokens} for model, tokens in sorted(per_model.items())},
            "per_phase": per_phase,
        },
    }


def run_errors(batch: dict[str, Any], worlds: list[dict[str, Any]]) -> dict[str, Any]:
    errors = []
    for world in worlds:
        raw = world.get("error_message") or _last_error_line(world)
        if not raw:
            continue
        reason = classify_error(str(raw))
        errors.append({
            "world_index": world.get("world_index", 0),
            "model": world.get("model_name", ""),
            "reason": reason,
            "message": str(raw),
            "suggestion": suggestion_for_error(reason),
        })
    return {"batch_id": batch.get("id", ""), "errors": errors}


def classify_error(message: str) -> str:
    lower = message.lower()
    if "timeout" in lower or "timed out" in lower or "超时" in message:
        return "timeout"
    if "keyboard_interrupt" in lower or "keyboardinterrupt" in lower or "用户中断" in message:
        return "keyboard_interrupt"
    if "401" in lower or "403" in lower or "auth" in lower or "api key" in lower or "unauthorized" in lower:
        return "api_auth"
    if "429" in lower or "rate limit" in lower:
        return "api_rate_limit"
    if "model_not_found" in lower or "model not found" in lower or "404" in lower:
        return "model_not_found"
    if "connection" in lower or "network" in lower or "httpx" in lower or "connecterror" in lower:
        return "api_network"
    if "simulation_dataset" in lower or "dataset" in lower:
        return "dataset_missing"
    if "parser" in lower or "jsondecode" in lower:
        return "parser_failed"
    if "report" in lower:
        return "report_failed"
    return "unknown"


def suggestion_for_error(reason: str) -> str:
    return {
        "timeout": "检查模型服务响应时间，必要时降低并发或重试该 world。",
        "keyboard_interrupt": "该 world 被中断，确认是否需要重新运行。",
        "api_auth": "检查 API Key 或模型服务鉴权配置。",
        "api_network": "检查内网地址、NO_PROXY 和模型服务连通性。",
        "api_rate_limit": "等待限流恢复或降低并发。",
        "model_not_found": "检查模型名称和网关可用模型列表。",
        "dataset_missing": "检查该 world 是否完整产出 simulation_dataset.json。",
        "parser_failed": "检查结构化输出是否可解析。",
        "report_failed": "检查报告生成输入产物和 Phase 4 报错。",
        "unknown": "查看 run.log 尾部定位具体失败点。",
    }.get(reason, "查看 run.log 尾部定位具体失败点。")


def safe_report_file(batch: dict[str, Any], filename: str) -> Path | None:
    if "/" in filename or "\\" in filename or ".." in filename:
        return None
    allowed = {"report.json", "report.md", "final_report.json", "final_report.md"}
    if filename not in allowed:
        return None
    path = Path(batch.get("batch_dir") or "") / filename
    if path.exists() and path.is_file():
        return path
    return None


def completed_dataset_for_batch(worlds: list[dict[str, Any]]) -> Path | None:
    for world in worlds:
        if normalize_status(world.get("raw_status") or world.get("status")) != "completed":
            continue
        dataset = world_dataset_path(world)
        if dataset.exists():
            return dataset
    return None


def _event(
    event_id: str,
    scope: str,
    kind: str,
    tone: str,
    title: str,
    message: str,
    *,
    timestamp: str = "",
    world_index: int | None = None,
    model: str = "",
    phase: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "scope": scope,
        "kind": kind,
        "tone": tone,
        "title": title,
        "message": message,
        "timestamp": timestamp,
        "world_index": world_index,
        "model": model,
        "phase": phase,
        "meta": meta or {},
    }


def _parse_run_log_line(line: str, index: int, world: dict[str, Any]) -> dict[str, Any] | None:
    timestamp = _timestamp_from_line(line)
    message = _strip_timestamp(line)
    kind = ""
    title = ""
    phase = ""
    if "PHASE START" in line:
        kind = "phase_start"
        phase = _match_value(line, "name") or ""
        title = "阶段开始"
    elif "PHASE END" in line:
        kind = "phase_end"
        phase = _match_value(line, "name") or ""
        title = "阶段完成"
    elif "TICK END" in line:
        kind = "tick"
        title = "Tick 完成"
        phase = "phase3"
    elif "LLM START" in line:
        kind = "llm_start"
        title = "LLM 请求"
    elif "LLM END" in line:
        kind = "llm_end"
        title = "LLM 完成"
    elif "RUN START" in line:
        kind = "run_start"
        title = "运行开始"
    elif "RUN END" in line:
        kind = "run_end"
        title = "运行结束"
    elif "ERROR" in line or "错误" in line:
        kind = "error"
        title = "错误"
    else:
        return None
    return _event(
        f"world-{world.get('world_index', 0)}-log-{index}",
        "world",
        kind,
        _line_tone(line),
        title,
        message,
        timestamp=timestamp,
        world_index=world.get("world_index", 0),
        model=world.get("model_name", ""),
        phase=phase,
    )


def _match_value(line: str, key: str) -> str | None:
    match = re.search(rf"{re.escape(key)}=([^\s]+)", line)
    return match.group(1) if match else None


def _timestamp_from_line(line: str) -> str:
    match = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}|\[\d{2}:\d{2}:\d{2}\])", line)
    return match.group(1).strip("[]") if match else ""


def _strip_timestamp(line: str) -> str:
    return re.sub(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}|\[\d{2}:\d{2}:\d{2}\])\s*", "", line).strip()


def _line_tone(line: str) -> str:
    lower = line.lower()
    if "error" in lower or "failed" in lower or "错误" in line or "失败" in line:
        return "bad"
    if "warn" in lower or "timeout" in lower or "waiting" in lower or "等待" in line:
        return "warn"
    if "end" in lower or "completed" in lower or "success" in lower or "完成" in line:
        return "ok"
    return "run"


def _world_counts(worlds: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(worlds), "completed": 0, "running": 0, "failed": 0, "pending": 0}
    for world in worlds:
        status = normalize_status(world.get("raw_status") or world.get("status"))
        if status in counts:
            counts[status] += 1
        else:
            counts["pending"] += 1
    return counts


def _parse_phase_summary(lines: list[str]) -> dict[str, dict[str, float]]:
    phases: dict[str, dict[str, float]] = {}
    for line in lines:
        if "PHASE END" not in line:
            continue
        name = _match_value(line, "name")
        elapsed = _match_value(line, "elapsed")
        if not name or not elapsed:
            continue
        try:
            phases[name] = {"elapsed_seconds": float(elapsed.rstrip("s"))}
        except ValueError:
            continue
    return phases


def _parse_token_summary(lines: list[str]) -> dict[str, Any]:
    summary = {"total_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "llm_elapsed": 0.0, "per_phase": {}}
    in_per_phase = False
    for line in lines:
        stripped = line.strip()
        if stripped == "per_phase:":
            in_per_phase = True
            continue
        if in_per_phase:
            match = re.match(r"^([^:]+):\s*(\d+)\s+calls,\s*(\d+)\s+tokens,\s*([\d.]+)s", stripped)
            if match:
                summary["per_phase"][match.group(1)] = {
                    "calls": int(match.group(2)),
                    "total_tokens": int(match.group(3)),
                    "elapsed_seconds": float(match.group(4)),
                }
                continue
            if stripped and not line.startswith(" "):
                in_per_phase = False
        for key, target in [
            ("total_calls:", "total_calls"),
            ("prompt_tokens:", "prompt_tokens"),
            ("completion_tokens:", "completion_tokens"),
            ("total_tokens:", "total_tokens"),
            ("llm_elapsed:", "llm_elapsed"),
        ]:
            if stripped.startswith(key):
                value = stripped.split(":", 1)[1].strip().rstrip("s")
                try:
                    summary[target] = float(value) if target == "llm_elapsed" else int(float(value))
                except ValueError:
                    pass
    return summary


def _batch_elapsed_seconds(world_items: list[dict[str, Any]]) -> float | None:
    values = [
        float(item["elapsed_seconds"])
        for item in world_items
        if item.get("elapsed_seconds") is not None
    ]
    return round(max(values), 2) if values else None


def _report_count(batch: dict[str, Any]) -> int:
    batch_dir = Path(batch.get("batch_dir") or "")
    return sum(1 for filename in ("report.json", "report.md", "final_report.json", "final_report.md") if (batch_dir / filename).is_file())


def _last_error_line(world: dict[str, Any]) -> str:
    for line in reversed(read_text_lines(world_artifacts(world)["run_log"], 120)):
        if _line_tone(line) == "bad":
            return line.strip()
    return ""


def _stance_text(entry: dict[str, Any]) -> str:
    previous = entry.get("previous_stance")
    current = entry.get("current_stance")
    if previous is not None and current is not None:
        return f"{previous} -> {current}"
    return str(entry.get("stance") or "")


def _risk_level_label(level: str) -> str:
    lower = level.lower()
    if lower in {"low", "低", "低风险"}:
        return "低风险"
    if lower in {"medium", "mid", "中", "中风险"}:
        return "中风险"
    if lower in {"high", "高", "高风险"}:
        return "高风险"
    if lower in {"critical", "severe", "严重"}:
        return "严重"
    return level


def _risk_variant(level: str) -> str:
    lower = level.lower()
    if lower in {"high", "critical", "severe", "高", "高风险", "严重"}:
        return "bad"
    if lower in {"medium", "mid", "中", "中风险"}:
        return "warn"
    return "ok"
