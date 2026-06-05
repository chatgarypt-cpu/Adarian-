"""Runtime relay runner for the PM Runtime Communication Substrate MVP."""

from __future__ import annotations

import json
import os
import shutil
import shlex
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_STATES = {
    "not_started",
    "created",
    "dispatch_ready",
    "pre_action_checking",
    "launching",
    "running",
    "healthy_running",
    "slow_but_progressing",
    "waiting_input",
    "permission_blocked",
    "sandbox_denied",
    "suspected_blocked",
    "missing_receipt",
    "missing_report",
    "partial_output",
    "partial_output_recovered",
    "recovering",
    "recovered",
    "rerun_required",
    "aborting",
    "aborted",
    "executor_completed",
    "executor_failed",
    "completed",
    "failed",
    "timeout",
    "artifact_missing",
    "environment_blocked",
    "hold_required",
    "summary_written",
}

FAILURE_CLASSIFICATIONS = {
    "agent_completed",
    "agent_failed",
    "permission_blocked",
    "sandbox_denied",
    "partial_output",
    "json_parse_failed",
    "no_output",
    "timeout_or_abort",
    "process_killed",
    "environment_blocked",
    "missing_receipt",
    "missing_report",
    "artifact_path_missing",
    "role_boundary_violation",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _parse_scalar(value: str) -> Any:
    raw = value.strip()
    if raw in {"", "null", "None", "~"}:
        return None
    if raw in {"true", "True"}:
        return True
    if raw in {"false", "False"}:
        return False
    if raw == "[]":
        return []
    if raw.startswith("[") and raw.endswith("]"):
        inside = raw[1:-1].strip()
        if not inside:
            return []
        return [_parse_scalar(part.strip()) for part in inside.split(",")]
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    try:
        return int(raw)
    except ValueError:
        return raw


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return line[:index]
    return line


def _prepared_yaml_lines(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        without_comment = _strip_comment(raw).rstrip()
        if not without_comment.strip():
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        lines.append((indent, without_comment.strip()))
    return lines


def _parse_yaml_block(
    lines: list[tuple[int, str]], start: int, indent: int
) -> tuple[Any, int]:
    if start >= len(lines):
        return {}, start
    is_list = lines[start][1].startswith("- ")
    if is_list:
        items: list[Any] = []
        index = start
        while index < len(lines):
            line_indent, content = lines[index]
            if line_indent < indent or not content.startswith("- "):
                break
            item_text = content[2:].strip()
            if not item_text:
                value, index = _parse_yaml_block(lines, index + 1, line_indent + 2)
                items.append(value)
            elif ":" in item_text and not item_text.startswith(("'", '"')):
                key, value_text = item_text.split(":", 1)
                item: dict[str, Any] = {}
                if value_text.strip():
                    item[key.strip()] = _parse_scalar(value_text.strip())
                    index += 1
                else:
                    value, index = _parse_yaml_block(lines, index + 1, line_indent + 2)
                    item[key.strip()] = value
                items.append(item)
            else:
                items.append(_parse_scalar(item_text))
                index += 1
        return items, index

    mapping: dict[str, Any] = {}
    index = start
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            index += 1
            continue
        if ":" not in content:
            index += 1
            continue
        key, value_text = content.split(":", 1)
        key = key.strip()
        value_text = value_text.strip()
        if value_text:
            mapping[key] = _parse_scalar(value_text)
            index += 1
        else:
            if index + 1 < len(lines) and lines[index + 1][0] > line_indent:
                value, index = _parse_yaml_block(lines, index + 1, lines[index + 1][0])
                mapping[key] = value
            else:
                mapping[key] = None
                index += 1
    return mapping, index


def load_yaml(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass
    parsed, _ = _parse_yaml_block(_prepared_yaml_lines(text), 0, 0)
    return parsed if isinstance(parsed, dict) else {}


def _quote_yaml(value: str) -> str:
    if value == "":
        return '""'
    if any(char in value for char in [":", "#", "\n", "{", "}", "[", "]"]):
        return json.dumps(value, ensure_ascii=False)
    return value


def to_yaml(value: Any, indent: int = 0) -> str:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, nested in value.items():
            if isinstance(nested, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(to_yaml(nested, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_format_yaml_scalar(nested)}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return f"{prefix}[]"
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(to_yaml(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_format_yaml_scalar(item)}")
        return "\n".join(lines)
    return f"{prefix}{_format_yaml_scalar(value)}"


def _format_yaml_scalar(value: Any) -> str:
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    return _quote_yaml(str(value))


def write_yaml(path: str | Path, data: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(to_yaml(data) + "\n", encoding="utf-8")


def append_registry_event(
    task_dir: str | Path,
    *,
    task_id: str,
    event_type: str,
    reason: str,
    actor: str = "runtime",
    from_runtime_state: str | None = None,
    to_runtime_state: str | None = None,
    evidence_paths: list[str] | None = None,
    session_id: str | None = None,
    round_id: str | None = None,
) -> dict[str, Any]:
    event = {
        "event_id": str(uuid.uuid4()),
        "task_id": task_id,
        "session_id": session_id,
        "round_id": round_id,
        "timestamp": now_iso(),
        "actor": actor,
        "event_type": event_type,
        "from_runtime_state": from_runtime_state,
        "to_runtime_state": to_runtime_state,
        "reason": reason,
        "evidence_paths": evidence_paths or [],
    }
    registry = Path(task_dir) / "runtime" / "registry_events.jsonl"
    registry.parent.mkdir(parents=True, exist_ok=True)
    with registry.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def ensure_task_dirs(config: dict[str, Any]) -> dict[str, Path]:
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    task_dir = Path(str(paths.get("task_dir") or ".")).resolve()
    runtime_dir = Path(str(paths.get("runtime_dir") or task_dir / "runtime")).resolve()
    logs_dir = Path(str(paths.get("logs_dir") or task_dir / "logs")).resolve()
    summary_path = Path(
        str(paths.get("summary_path") or task_dir / "summary" / "pm_runtime_summary.md")
    ).resolve()
    dispatch_path = Path(
        str(paths.get("dispatch_path") or task_dir / "dispatch" / "task_config.yaml")
    ).resolve()
    for directory in [task_dir, runtime_dir, logs_dir, summary_path.parent, dispatch_path.parent]:
        directory.mkdir(parents=True, exist_ok=True)
    return {
        "task_dir": task_dir,
        "runtime_dir": runtime_dir,
        "logs_dir": logs_dir,
        "summary_path": summary_path,
        "dispatch_path": dispatch_path,
    }


def validate_config(config: dict[str, Any]) -> list[str]:
    required = ["task_id", "task_domain", "short_task", "executor_type", "execution_mode"]
    missing = [key for key in required if not config.get(key)]
    paths = config.get("paths")
    if not isinstance(paths, dict) or not paths.get("task_dir"):
        missing.append("paths.task_dir")
    return missing


def write_pre_action_check(
    config: dict[str, Any],
    action_type: str,
    *,
    result: str = "pass",
    hold_reason: str | None = None,
) -> Path:
    dirs = ensure_task_dirs(config)
    scope = config.get("scope") if isinstance(config.get("scope"), dict) else {}
    check = {
        "task_id": config.get("task_id"),
        "session_id": config.get("session_id") or "session-local",
        "round_id": config.get("round_id") or "round-1",
        "action_type": action_type,
        "intended_executor": config.get("executor_type"),
        "task_domain": config.get("task_domain"),
        "task_level": config.get("task_level"),
        "artifact_expected": True,
        "artifact_target_paths": [
            str(dirs["runtime_dir"]),
            str(dirs["logs_dir"]),
            str(dirs["summary_path"]),
        ],
        "role_boundary_checked": True,
        "allowed_by_role": result == "pass",
        "needs_ds_team": False,
        "needs_owner_approval": bool(config.get("owner_control_required")),
        "mcp_or_tool_preflight_required": False,
        "scope_checked": True,
        "allowed_files": scope.get("allowed_files") or [],
        "forbidden_files": scope.get("forbidden_files") or [],
        "result": result,
        "hold_reason": hold_reason,
        "created_at": now_iso(),
    }
    path = dirs["runtime_dir"] / "pre_action_check.yaml"
    write_yaml(path, check)
    return path


def write_heartbeat(
    config: dict[str, Any],
    runtime_state: str,
    *,
    executor_pid: int | None = None,
    heartbeat_seq: int | None = None,
) -> Path:
    dirs = ensure_task_dirs(config)
    path = dirs["runtime_dir"] / "heartbeat.json"
    payload = {
        "task_id": config.get("task_id"),
        "runtime_state": runtime_state,
        "timestamp": now_iso(),
        "runtime_pid": os.getpid(),
        "executor_pid": executor_pid,
        "heartbeat_seq": heartbeat_seq,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    history_path = dirs["runtime_dir"] / "heartbeat_history.jsonl"
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    write_legacy_heartbeat(config, payload)
    return path


def write_progress(config: dict[str, Any], runtime_state: str, message: str) -> Path:
    dirs = ensure_task_dirs(config)
    path = dirs["runtime_dir"] / "progress.yaml"
    write_yaml(
        path,
        {
            "task_id": config.get("task_id"),
            "runtime_state": runtime_state,
            "message": message,
            "updated_at": now_iso(),
        },
    )
    write_legacy_progress(config, runtime_state, message)
    return path


def write_legacy_heartbeat(config: dict[str, Any], heartbeat: dict[str, Any]) -> Path:
    """Write a Hermes-readable heartbeat alias under the task runtime dir."""
    dirs = ensure_task_dirs(config)
    path = dirs["runtime_dir"] / "relay_heartbeat.txt"
    content = [
        "legacy_compat: true",
        "compat_for: hermes_old_relay",
        f"task_id: {heartbeat.get('task_id')}",
        f"runtime_state: {heartbeat.get('runtime_state')}",
        f"timestamp: {heartbeat.get('timestamp')}",
        f"runtime_pid: {heartbeat.get('runtime_pid')}",
        f"executor_pid: {heartbeat.get('executor_pid')}",
        f"heartbeat_seq: {heartbeat.get('heartbeat_seq')}",
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
    return path


def write_legacy_progress(config: dict[str, Any], runtime_state: str, message: str) -> Path:
    """Write a Hermes-readable progress alias under the task runtime dir."""
    dirs = ensure_task_dirs(config)
    path = dirs["runtime_dir"] / "relay_progress.md"
    content = f"""---
legacy_compat: true
compat_for: hermes_old_relay
task_id: {config.get("task_id")}
runtime_state: {runtime_state}
updated_at: {now_iso()}
---

{message}
"""
    path.write_text(content, encoding="utf-8")
    return path


def write_legacy_result(
    config: dict[str, Any],
    *,
    runtime_state: str,
    returncode: int | None,
    classification: dict[str, Any],
    evidence_paths: list[str],
) -> Path:
    """Write a Hermes-readable result alias under the task runtime dir."""
    dirs = ensure_task_dirs(config)
    path = dirs["runtime_dir"] / "result.json"
    payload = {
        "legacy_compat": True,
        "compat_for": "hermes_old_relay",
        "task_id": config.get("task_id"),
        "runtime_state": runtime_state,
        "returncode": returncode,
        "classification": classification.get("classification"),
        "confidence": classification.get("confidence"),
        "requires_independent_review": classification.get("requires_independent_review"),
        "evidence_paths": evidence_paths,
        "closeout_claimed": False,
        "created_at": now_iso(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_task_state(
    config: dict[str, Any],
    runtime_state: str,
    *,
    task_status: str = "running",
    extra: dict[str, Any] | None = None,
) -> Path:
    dirs = ensure_task_dirs(config)
    state = {
        "task_id": config.get("task_id"),
        "task_status": task_status,
        "runtime_state": runtime_state,
        "runtime_states_supported": sorted(RUNTIME_STATES),
        "known_issues": [
            "runtime_state values intentionally overlap task_status for MVP compatibility"
        ],
        "config_path": str(dirs["dispatch_path"]),
        "updated_at": now_iso(),
        "closeout_claimed": False,
    }
    if extra:
        state.update(extra)
    path = dirs["runtime_dir"] / "task_state.yaml"
    write_yaml(path, state)
    return path


def classify_result(
    returncode: int | None,
    stdout_path: Path,
    stderr_path: Path,
    *,
    raw_output_path: Path | None = None,
    expected_receipt_path: Path | None = None,
    expected_report_path: Path | None = None,
    partial_preserved: bool = False,
    role_boundary_violation: bool = False,
    timed_out: bool = False,
    aborted: bool = False,
) -> dict[str, Any]:
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
    evidence = [
        {"path": str(stdout_path), "excerpt_or_summary": stdout[-500:]},
        {"path": str(stderr_path), "excerpt_or_summary": stderr[-500:]},
    ]
    if raw_output_path:
        if raw_output_path.exists():
            raw_excerpt = raw_output_path.read_text(encoding="utf-8", errors="replace")[-500:]
            evidence.append({"path": str(raw_output_path), "excerpt_or_summary": raw_excerpt})
        else:
            evidence.append({"path": str(raw_output_path), "excerpt_or_summary": "missing raw output"})

    if role_boundary_violation:
        classification = "role_boundary_violation"
        confidence = "high"
    elif expected_receipt_path and not expected_receipt_path.exists():
        classification = "missing_receipt"
        confidence = "high"
    elif expected_report_path and not expected_report_path.exists():
        classification = "missing_report"
        confidence = "high"
    elif raw_output_path and not raw_output_path.exists():
        classification = "artifact_path_missing"
        confidence = "high"
    elif raw_output_path and raw_output_path.exists():
        try:
            for raw_line in raw_output_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if raw_line.strip():
                    json.loads(raw_line)
        except json.JSONDecodeError:
            classification = "json_parse_failed"
            confidence = "high"
        else:
            classification = ""
            confidence = ""
    else:
        classification = ""
        confidence = ""

    if classification:
        pass
    elif timed_out or aborted:
        classification = "timeout_or_abort"
        confidence = "high"
    elif partial_preserved and returncode is None:
        classification = "partial_output"
        confidence = "medium"
    elif returncode is None:
        classification = "process_killed"
        confidence = "medium"
    elif "No such file or directory" in stderr or "not found" in stderr.lower():
        classification = "environment_blocked"
        confidence = "medium"
    elif "Operation not permitted" in stderr or "permission denied" in stderr.lower():
        classification = "permission_blocked"
        confidence = "high"
    elif "sandbox" in stderr.lower() and "denied" in stderr.lower():
        classification = "sandbox_denied"
        confidence = "high"
    elif returncode == 0 and (stdout or stderr):
        classification = "agent_completed"
        confidence = "high"
    elif returncode == 0:
        classification = "no_output"
        confidence = "medium"
    else:
        classification = "agent_failed"
        confidence = "high"
    # v0.1.2: returncode=0 but required artifacts missing is not agent_completed
    if classification == "agent_completed":
        if expected_report_path and not expected_report_path.exists():
            classification = "missing_report"
            confidence = "high"
        elif expected_receipt_path and not expected_receipt_path.exists():
            classification = "missing_receipt"
            confidence = "high"
    return {
        "classification": classification,
        "evidence": evidence,
        "confidence": confidence,
        "classified_by": "runtime",
        "requires_independent_review": classification != "agent_completed",
    }


def write_owner_decision_request(
    config: dict[str, Any],
    event_type: str,
    requested_action: str,
    observed_result: str,
    *,
    risk_level: str = "medium",
) -> Path:
    dirs = ensure_task_dirs(config)
    scope = config.get("scope") if isinstance(config.get("scope"), dict) else {}
    request = {
        "task_id": config.get("task_id"),
        "session_id": config.get("session_id") or "session-local",
        "round_id": config.get("round_id") or "round-1",
        "request_id": str(uuid.uuid4()),
        "executor": config.get("executor_type"),
        "event_type": event_type,
        "requested_action": requested_action,
        "affected_files": [],
        "observed_result": observed_result,
        "agent_message": observed_result,
        "risk_level": risk_level,
        "allowed_scope": scope.get("allowed_dirs") or scope.get("allowed_files") or [],
        "forbidden_scope": scope.get("forbidden_files") or [],
        "available_options": [
            "approve_with_scope",
            "reject",
            "abort_task",
            "request_safer_alternative",
            "ask_for_more_context",
        ],
        "recommended_action": requested_action,
        "owner_control_required": True,
        "created_at": now_iso(),
    }
    path = dirs["runtime_dir"] / "owner_decision_request.yaml"
    write_yaml(path, request)
    return path


def write_owner_decision_record_template(config: dict[str, Any]) -> Path:
    dirs = ensure_task_dirs(config)
    record = {
        "task_id": config.get("task_id"),
        "session_id": config.get("session_id") or "session-local",
        "round_id": config.get("round_id") or "round-1",
        "request_id": "",
        "owner_decision": "",
        "decision_source": "unknown",
        "decision_time": "",
        "approved_scope": [],
        "rejected_scope": [],
        "notes": "",
        "next_runtime_action": "",
    }
    path = dirs["runtime_dir"] / "owner_decision_record.yaml"
    write_yaml(path, record)
    return path


def _expected_artifact(config: dict[str, Any], key: str) -> Path | None:
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    options = config.get("executor_options") if isinstance(config.get("executor_options"), dict) else {}
    value = paths.get(key) or options.get(key)
    return Path(str(value)).resolve() if value else None


def write_abort_report(
    config: dict[str, Any],
    abort_reason: str,
    *,
    abort_requested_by: str = "runtime",
) -> Path:
    dirs = ensure_task_dirs(config)
    report = {
        "task_id": config.get("task_id"),
        "session_id": config.get("session_id") or "session-local",
        "round_id": config.get("round_id") or "round-1",
        "abort_reason": abort_reason,
        "abort_requested_by": abort_requested_by,
        "abort_approved_by": "",
        "abort_time": now_iso(),
        "partial_output_preserved": True,
        "stdout_partial_path": str(dirs["logs_dir"] / "stdout.partial.log"),
        "stderr_partial_path": str(dirs["logs_dir"] / "stderr.partial.log"),
        "raw_output_partial_path": str(dirs["logs_dir"] / "raw_output.partial.jsonl"),
        "next_recommendation": "Owner-Control review required before retry",
        "owner_control_required": True,
    }
    path = dirs["runtime_dir"] / "abort_report.yaml"
    write_yaml(path, report)
    return path


@dataclass
class RunResult:
    exit_code: int
    classification: dict[str, Any]
    stdout_path: Path
    stderr_path: Path
    raw_output_path: Path
    summary_path: Path | None = None


def _materialize_task_package(config: dict[str, Any], dirs: dict[str, Path]) -> None:
    """v0.1.2: copy external dispatch/system_prompt into task package for sandbox self-containment."""
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    dispatch_dir = dirs["dispatch_path"].parent

    # Materialize external dispatch file -> dispatch/dispatch.md
    external_dispatch = paths.get("external_dispatch_path")
    if external_dispatch:
        ext_path = Path(str(external_dispatch))
        if ext_path.exists() and ext_path.is_file():
            target = dispatch_dir / "dispatch.md"
            shutil.copyfile(ext_path, target)

    # Materialize system prompt -> dispatch/system_prompt.md
    system_prompt = paths.get("system_prompt_path")
    if system_prompt:
        sp_path = Path(str(system_prompt))
        if sp_path.exists() and sp_path.is_file():
            target = dispatch_dir / "system_prompt.md"
            shutil.copyfile(sp_path, target)


def init_task(config_path: str | Path) -> int:
    config_source = Path(config_path)
    if not config_source.exists():
        raise FileNotFoundError(f"config path not found: {config_source}")
    if not config_source.is_file():
        raise ValueError(f"config_invalid: config path is not a file: {config_source}")
    config = load_yaml(config_path)
    missing = validate_config(config)
    if missing:
        raise ValueError(f"config_invalid: missing {', '.join(missing)}")
    dirs = ensure_task_dirs(config)
    if dirs["dispatch_path"].exists() and dirs["dispatch_path"].is_dir():
        raise ValueError(f"config_invalid: dispatch_path is a directory: {dirs['dispatch_path']}")
    source = config_source.resolve()
    if source != dirs["dispatch_path"]:
        shutil.copyfile(source, dirs["dispatch_path"])
    # v0.1.2: materialize external references into task package (self-containment)
    _materialize_task_package(config, dirs)
    pre_action = write_pre_action_check(config, "create_task")
    write_task_state(config, "created", task_status="approved")
    append_registry_event(
        dirs["task_dir"],
        task_id=str(config.get("task_id")),
        event_type="created",
        reason="task initialized by PM Runtime relay MVP",
        to_runtime_state="created",
        evidence_paths=[str(pre_action), str(dirs["runtime_dir"] / "task_state.yaml")],
        session_id=config.get("session_id") or "session-local",
        round_id=config.get("round_id") or "round-1",
    )
    return 0


def _load_config_from_task_dir(task_dir: str | Path) -> dict[str, Any]:
    base = Path(task_dir).resolve()
    dispatch_config = base / "dispatch" / "task_config.yaml"
    state_path = base / "runtime" / "task_state.yaml"
    if dispatch_config.exists() and dispatch_config.is_file():
        return load_yaml(dispatch_config)
    if dispatch_config.exists() and dispatch_config.is_dir():
        raise ValueError(f"config_invalid: dispatch config path is a directory: {dispatch_config}")
    if state_path.exists():
        state = load_yaml(state_path)
        config_path = state.get("config_path")
        if config_path:
            recorded = Path(str(config_path))
            if recorded.exists() and recorded.is_file():
                return load_yaml(recorded)
            if recorded.exists() and recorded.is_dir():
                raise ValueError(f"config_invalid: recorded config_path is a directory: {recorded}")
            raise FileNotFoundError(f"recorded config_path not found: {recorded}")
    dispatch_dir = base / "dispatch"
    if dispatch_dir.exists():
        yaml_candidates = sorted(
            path for path in dispatch_dir.glob("*.yaml") if path.is_file()
        ) + sorted(path for path in dispatch_dir.glob("*.yml") if path.is_file())
        if len(yaml_candidates) == 1:
            return load_yaml(yaml_candidates[0])
        if len(yaml_candidates) > 1:
            names = ", ".join(str(path) for path in yaml_candidates)
            raise ValueError(f"config_invalid: multiple dispatch YAML candidates: {names}")
    raise FileNotFoundError(f"task_config not found under {base}")


def _executor_command(config: dict[str, Any]) -> list[str]:
    options = config.get("executor_options") if isinstance(config.get("executor_options"), dict) else {}
    executor_type = str(config.get("executor_type") or "local_echo")
    execution_mode = str(config.get("execution_mode") or "local_echo")
    command = options.get("command")
    extra_args = options.get("extra_args")
    if isinstance(command, list) and command and command[0] != "local_echo":
        return [str(item) for item in command]
    if isinstance(command, str) and command != "local_echo":
        return shlex.split(command)
    if executor_type == "shell_command" or execution_mode == "managed_subprocess":
        raise ValueError("config_invalid: managed subprocess requires executor_options.command")
    if executor_type == "codex" or execution_mode == "managed_codex_exec":
        args = [str(item) for item in extra_args] if isinstance(extra_args, list) else []
        return ["codex", *args]
    if executor_type == "claude" or execution_mode == "managed_relay_session":
        args = [str(item) for item in extra_args] if isinstance(extra_args, list) else []
        return ["claude", *args]
    stdout_text = str(options.get("echo_stdout") or "PM Runtime local_echo stdout")
    stderr_text = str(options.get("echo_stderr") or "PM Runtime local_echo stderr")
    script = (
        "import sys; "
        f"print({stdout_text!r}); "
        f"print({stderr_text!r}, file=sys.stderr)"
    )
    return [sys.executable, "-c", script]


def run_task(task_dir: str | Path) -> RunResult:
    config = _load_config_from_task_dir(task_dir)
    dirs = ensure_task_dirs(config)
    task_id = str(config.get("task_id"))
    write_task_state(config, "pre_action_checking")
    pre_action = write_pre_action_check(config, "launch_executor")
    append_registry_event(
        dirs["task_dir"],
        task_id=task_id,
        event_type="pre_action_checked",
        reason="launch pre-action check passed",
        from_runtime_state="created",
        to_runtime_state="pre_action_checking",
        evidence_paths=[str(pre_action)],
        session_id=config.get("session_id") or "session-local",
        round_id=config.get("round_id") or "round-1",
    )
    write_task_state(config, "launching")
    write_progress(config, "launching", "executor launch started")
    append_registry_event(
        dirs["task_dir"],
        task_id=task_id,
        event_type="launched",
        reason="executor process launch requested",
        from_runtime_state="pre_action_checking",
        to_runtime_state="launching",
        evidence_paths=[],
        session_id=config.get("session_id") or "session-local",
        round_id=config.get("round_id") or "round-1",
    )

    stdout_path = dirs["logs_dir"] / "stdout.log"
    stderr_path = dirs["logs_dir"] / "stderr.log"
    raw_output_path = dirs["logs_dir"] / "raw_output.jsonl"
    stdout_partial = dirs["logs_dir"] / "stdout.partial.log"
    stderr_partial = dirs["logs_dir"] / "stderr.partial.log"
    raw_partial = dirs["logs_dir"] / "raw_output.partial.jsonl"
    command = _executor_command(config)
    started_at = time.time()
    timed_out = False
    returncode: int | None = None
    executor_pid: int | None = None
    heartbeat_seq = 0
    current_runtime_state = "launching"
    try:
        timeout_value = None
        control = config.get("runtime_control")
        heartbeat_interval = 30
        progress_interval = 120
        if isinstance(control, dict) and control.get("emergency_max_wall_time_sec"):
            timeout_value = int(control["emergency_max_wall_time_sec"])
        if isinstance(control, dict) and control.get("heartbeat_interval_sec"):
            heartbeat_interval = max(1, int(control["heartbeat_interval_sec"]))
        if isinstance(control, dict) and control.get("progress_check_interval_sec"):
            progress_interval = max(1, int(control["progress_check_interval_sec"]))
        process = subprocess.Popen(
            command,
            cwd=str(dirs["task_dir"]),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        executor_pid = process.pid
        current_runtime_state = "running"
        write_task_state(config, "running", extra={"executor_pid": executor_pid})
        write_progress(config, "running", "executor process started")
        heartbeat_seq += 1
        write_heartbeat(
            config,
            "running",
            executor_pid=executor_pid,
            heartbeat_seq=heartbeat_seq,
        )
        raw_start = {
            "timestamp": now_iso(),
            "event": "process_started",
            "command": command,
            "pid": executor_pid,
        }
        raw_output_path.write_text(json.dumps(raw_start, ensure_ascii=False) + "\n", encoding="utf-8")
        raw_partial.write_text(raw_output_path.read_text(encoding="utf-8"), encoding="utf-8")

        def pump(stream: Any, target: Path, partial: Path, stream_name: str) -> None:
            with target.open("w", encoding="utf-8") as full, partial.open(
                "w", encoding="utf-8"
            ) as part:
                for line in iter(stream.readline, ""):
                    full.write(line)
                    full.flush()
                    part.write(line)
                    part.flush()
                    with raw_output_path.open("a", encoding="utf-8") as raw_handle:
                        raw_handle.write(
                            json.dumps(
                                {
                                    "timestamp": now_iso(),
                                    "event": "stream",
                                    "stream": stream_name,
                                    "text": line,
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                    raw_partial.write_text(
                        raw_output_path.read_text(encoding="utf-8", errors="replace"),
                        encoding="utf-8",
                    )

        threads = [
            threading.Thread(
                target=pump,
                args=(process.stdout, stdout_path, stdout_partial, "stdout"),
                daemon=True,
            ),
            threading.Thread(
                target=pump,
                args=(process.stderr, stderr_path, stderr_partial, "stderr"),
                daemon=True,
            ),
        ]
        for thread in threads:
            thread.start()

        current_runtime_state = "healthy_running"
        write_task_state(config, "healthy_running", extra={"executor_pid": executor_pid})
        write_progress(config, "healthy_running", "executor process running")
        heartbeat_seq += 1
        write_heartbeat(
            config,
            "healthy_running",
            executor_pid=executor_pid,
            heartbeat_seq=heartbeat_seq,
        )
        last_heartbeat_at = time.time()
        last_progress_at = time.time()
        while process.poll() is None:
            now = time.time()
            if timeout_value and time.time() - started_at > timeout_value:
                timed_out = True
                current_runtime_state = "timeout"
                write_task_state(config, "timeout", extra={"executor_pid": executor_pid})
                process.kill()
                write_abort_report(config, "executor timeout")
                break
            if now - last_heartbeat_at >= heartbeat_interval:
                heartbeat_seq += 1
                write_heartbeat(
                    config,
                    current_runtime_state,
                    executor_pid=executor_pid,
                    heartbeat_seq=heartbeat_seq,
                )
                last_heartbeat_at = now
            if now - last_progress_at >= progress_interval:
                current_runtime_state = "slow_but_progressing"
                write_task_state(config, "slow_but_progressing", extra={"executor_pid": executor_pid})
                write_progress(config, "slow_but_progressing", "executor still running")
                last_progress_at = now
            time.sleep(0.05)

        returncode = process.wait()
        for thread in threads:
            thread.join(timeout=2)
    except OSError as exc:
        returncode = None
        stdout_path.write_text("", encoding="utf-8")
        stdout_partial.write_text("", encoding="utf-8")
        stderr_path.write_text(str(exc), encoding="utf-8")
        stderr_partial.write_text(str(exc), encoding="utf-8")

    stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    if not stdout_partial.exists():
        stdout_partial.write_text(stdout, encoding="utf-8")
    if not stderr_partial.exists():
        stderr_partial.write_text(stderr, encoding="utf-8")
    raw_event = {
        "timestamp": now_iso(),
        "event": "process_completed",
        "command": command,
        "returncode": returncode,
        "elapsed_sec": round(time.time() - started_at, 3),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }
    with raw_output_path.open("a", encoding="utf-8") as raw_handle:
        raw_handle.write(json.dumps(raw_event, ensure_ascii=False) + "\n")
    raw_partial.write_text(raw_output_path.read_text(encoding="utf-8"), encoding="utf-8")
    classification = classify_result(
        returncode,
        stdout_path,
        stderr_path,
        raw_output_path=raw_output_path,
        expected_receipt_path=_expected_artifact(config, "expected_receipt_path"),
        expected_report_path=_expected_artifact(config, "expected_report_path"),
        partial_preserved=stdout_partial.exists() or stderr_partial.exists() or raw_partial.exists(),
        role_boundary_violation=bool(config.get("role_boundary_violation")),
        timed_out=timed_out,
    )
    classification_path = dirs["runtime_dir"] / "failure_classification.yaml"
    write_yaml(classification_path, classification)
    if classification["classification"] == "agent_completed":
        final_state = "executor_completed"
        task_status = "completed"
        exit_code = 0
        event_type = "progress"
        reason = "executor completed and output was captured"
    else:
        final_state = "executor_failed"
        task_status = "failed"
        exit_code = 5
        event_type = "blocked"
        reason = f"executor classified as {classification['classification']}"
        write_blocker_report(config, reason, stderr[-1000:])
        write_owner_decision_request(
            config,
            "recovery_requires_approval",
            "request_owner_decision",
            reason,
        )
        write_owner_decision_record_template(config)
    legacy_result_path = write_legacy_result(
        config,
        runtime_state=final_state,
        returncode=returncode,
        classification=classification,
        evidence_paths=[
            str(stdout_path),
            str(stderr_path),
            str(raw_output_path),
            str(classification_path),
        ],
    )
    write_task_state(
        config,
        final_state,
        task_status=task_status,
        extra={
            "classification": classification["classification"],
            "legacy_result_path": str(legacy_result_path),
        },
    )
    heartbeat_seq += 1
    write_heartbeat(config, final_state, executor_pid=executor_pid, heartbeat_seq=heartbeat_seq)
    write_progress(config, final_state, reason)
    append_registry_event(
        dirs["task_dir"],
        task_id=task_id,
        event_type=event_type,
        reason=reason,
        from_runtime_state="healthy_running",
        to_runtime_state=final_state,
        evidence_paths=[
            str(stdout_path),
            str(stderr_path),
            str(raw_output_path),
            str(classification_path),
        ],
        session_id=config.get("session_id") or "session-local",
        round_id=config.get("round_id") or "round-1",
    )
    return RunResult(exit_code, classification, stdout_path, stderr_path, raw_output_path)


def write_blocker_report(config: dict[str, Any], suspected_blocker: str, stderr_tail: str) -> Path:
    dirs = ensure_task_dirs(config)
    report = {
        "task_id": config.get("task_id"),
        "session_id": config.get("session_id") or "session-local",
        "round_id": config.get("round_id") or "round-1",
        "runtime_state": "suspected_blocked",
        "elapsed_seconds": 0,
        "last_heartbeat_at": now_iso(),
        "last_progress_at": now_iso(),
        "stdout_growth": "unknown",
        "stderr_tail": stderr_tail,
        "suspected_blocker": suspected_blocker,
        "recommended_actions": [
            "continue",
            "attach",
            "request_owner_decision",
            "repair_permissions",
            "recover_partial_output",
            "abort",
        ],
        "owner_control_required": True,
    }
    path = dirs["runtime_dir"] / "blocker_report.md"
    content = "---\n" + to_yaml(report) + "\n---\n\nPM Runtime blocker report.\n"
    path.write_text(content, encoding="utf-8")
    return path


def read_registry_events(task_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(task_dir) / "runtime" / "registry_events.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if isinstance(event, dict):
                    events.append(event)
            except json.JSONDecodeError:
                events.append({"event_type": "json_parse_failed", "raw_excerpt": line[:500]})
    return events


def write_pm_runtime_summary(task_dir: str | Path) -> Path:
    config = _load_config_from_task_dir(task_dir)
    dirs = ensure_task_dirs(config)
    events = read_registry_events(dirs["task_dir"])
    state_path = dirs["runtime_dir"] / "task_state.yaml"
    state = load_yaml(state_path) if state_path.exists() else {}
    stdout_path = dirs["logs_dir"] / "stdout.log"
    stderr_path = dirs["logs_dir"] / "stderr.log"
    raw_path = dirs["logs_dir"] / "raw_output.jsonl"
    owner_requests = sorted(str(path) for path in dirs["runtime_dir"].glob("owner_decision_request*.yaml"))
    owner_records = sorted(str(path) for path in dirs["runtime_dir"].glob("owner_decision_record*.yaml"))
    recovery_paths = sorted(str(path) for path in dirs["runtime_dir"].glob("recovery_summary*.md"))
    content = f"""# PM Runtime Summary

## Task Identity
- task_id: {config.get("task_id")}
- task_domain: {config.get("task_domain")}
- short_task: {config.get("short_task")}

## Task Status
- task_status: {state.get("task_status", "unknown")}

## Runtime State
- runtime_state: {state.get("runtime_state", "unknown")}

## Executor Type
- executor_type: {config.get("executor_type")}

## Execution Mode
- execution_mode: {config.get("execution_mode")}

## Dispatch Path
- dispatch_path: {dirs["dispatch_path"]}

## Report Paths
- blocker_report: {dirs["runtime_dir"] / "blocker_report.md"}

## Receipt Paths
- receipt_paths: none recorded by MVP unless executor writes one

## stdout / stderr / raw output paths
- stdout: {stdout_path}
- stderr: {stderr_path}
- raw_output: {raw_path}

## Registry Path
- registry: {dirs["runtime_dir"] / "registry_events.jsonl"}
- registry_event_count: {len(events)}

## Owner Decision Requests / Records
- requests: {owner_requests or []}
- records: {owner_records or []}

## Recovery Actions
- recovery_paths: {recovery_paths or []}

## Process Issues
- runtime_state and task_status overlap is preserved as an MVP known issue.

## Blockers
- none recorded if blocker_report path does not exist.

## Known Issues
- No auto closeout is implemented.
- Concurrent task execution is out of scope.

## Next Recommendation
- Submit this implementation for PM Runtime / Hermes / DS / Owner-Control review.

## No Closeout Boundary
PM Runtime summary is not closeout.
"""
    dirs["summary_path"].parent.mkdir(parents=True, exist_ok=True)
    dirs["summary_path"].write_text(content, encoding="utf-8")
    write_task_state(config, "summary_written", task_status=state.get("task_status", "completed"))
    append_registry_event(
        dirs["task_dir"],
        task_id=str(config.get("task_id")),
        event_type="summary_written",
        reason="PM Runtime summary written; no closeout claimed",
        from_runtime_state=str(state.get("runtime_state", "unknown")),
        to_runtime_state="summary_written",
        evidence_paths=[str(dirs["summary_path"])],
        session_id=config.get("session_id") or "session-local",
        round_id=config.get("round_id") or "round-1",
    )
    return dirs["summary_path"]
