"""Minimal subprocess orchestration for profiling chain workers."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4


@dataclass(frozen=True)
class ExecutionOutcome:
    execution_mode: str
    timeout_triggered: bool
    termination_method: str
    timeout_final_state: str
    worker_exit_code: int | None
    worker_exit_status: str
    result_file_present: bool
    result_payload: dict[str, Any] | None
    cleanup_status: str = "not_attempted"
    cleanup_message: str | None = None
    worker_stdout_tail: str | None = None
    worker_stderr_tail: str | None = None

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, Any]) -> "ExecutionOutcome":
        return cls(
            execution_mode=str(metadata.get("execution_mode", "subprocess")),
            timeout_triggered=bool(metadata.get("timeout_triggered", False)),
            termination_method=str(metadata.get("termination_method", "none")),
            timeout_final_state=str(metadata.get("timeout_final_state", "not_triggered")),
            worker_exit_code=metadata.get("worker_exit_code"),
            worker_exit_status=str(metadata.get("worker_exit_status", "unknown")),
            result_file_present=bool(metadata.get("result_file_present", False)),
            result_payload=None,
        )


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _tail_text(text: str | None, limit: int = 2000) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    return stripped[-limit:]


def _cleanup_temp_dir(temp_dir_path: Path) -> tuple[str, str | None]:
    last_error: Exception | None = None
    for _ in range(4):
        try:
            shutil.rmtree(temp_dir_path)
            return "cleaned", None
        except FileNotFoundError:
            return "cleaned", None
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)

    if temp_dir_path.exists():
        contents = ", ".join(item.name for item in temp_dir_path.iterdir()) if temp_dir_path.is_dir() else ""
        detail = f"{type(last_error).__name__}: {last_error}" if last_error is not None else "unknown cleanup error"
        if contents:
            detail = f"{detail}; remaining={contents}"
        return "cleanup_failed", detail
    return "cleaned", None


def run_chain_in_subprocess(
    payload: Mapping[str, Any],
    *,
    timeout_sec: float,
    project_root: str | Path,
    temp_root: str | Path,
) -> ExecutionOutcome:
    project_root_path = Path(project_root)
    temp_root_path = Path(temp_root)
    temp_root_path.mkdir(parents=True, exist_ok=True)
    worker_path = project_root_path / "profiling" / "chain_worker.py"

    temp_dir_path = temp_root_path / f"chain_worker_{uuid4().hex}"
    temp_dir_path.mkdir(parents=True, exist_ok=True)
    try:
        input_path = temp_dir_path / "input.json"
        result_path = temp_dir_path / "result.json"
        input_path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")

        proc = subprocess.Popen(
            [sys.executable, str(worker_path), "--input", str(input_path), "--output", str(result_path)],
            cwd=str(project_root_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

        timeout_triggered = False
        termination_method = "none"
        timeout_final_state = "not_triggered"
        worker_exit_status = "unknown"
        error_on_kill: Exception | None = None
        stdout_text = ""
        stderr_text = ""

        try:
            stdout_text, stderr_text = proc.communicate(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            timeout_triggered = True
            termination_method = "kill"
            try:
                proc.kill()
                stdout_text, stderr_text = proc.communicate(timeout=5)
                timeout_final_state = "killed"
                worker_exit_status = "killed"
            except Exception as exc:  # pragma: no cover
                error_on_kill = exc
                timeout_final_state = "kill_failed"
                worker_exit_status = "kill_failed"

        worker_exit_code = proc.returncode
        result_payload = _load_json(result_path)
        result_file_present = result_payload is not None

        if not timeout_triggered:
            worker_exit_status = "completed" if worker_exit_code == 0 else "abnormal_exit"
        elif worker_exit_status == "kill_failed" and error_on_kill is not None:
            result_payload = result_payload or {
                "ok": False,
                "error": {
                    "exception_type": type(error_on_kill).__name__,
                    "exception_message": str(error_on_kill),
                    "error_types": ["generator_error:KillFailed"],
                    "timeout": True,
                },
            }

        cleanup_status, cleanup_message = _cleanup_temp_dir(temp_dir_path)
        return ExecutionOutcome(
            execution_mode="subprocess",
            timeout_triggered=timeout_triggered,
            termination_method=termination_method,
            timeout_final_state=timeout_final_state,
            worker_exit_code=worker_exit_code,
            worker_exit_status=worker_exit_status,
            result_file_present=result_file_present,
            result_payload=result_payload,
            cleanup_status=cleanup_status,
            cleanup_message=cleanup_message,
            worker_stdout_tail=_tail_text(stdout_text),
            worker_stderr_tail=_tail_text(stderr_text),
        )
    finally:
        if temp_dir_path.exists():
            _cleanup_temp_dir(temp_dir_path)
