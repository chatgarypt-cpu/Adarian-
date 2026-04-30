"""运行时观测日志。"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class RuntimeLogger:
    """最小运行观测器。"""

    def __init__(self) -> None:
        self.run_dir: Optional[Path] = None
        self.log_path: Optional[Path] = None
        self.timing_path: Optional[Path] = None
        self.summary: Dict[str, Any] = {}

    def configure(self, run_dir: Path) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.run_dir / "run.log"
        self.timing_path = self.run_dir / "timing_summary.json"
        self.summary = {
            "run": {
                "start_time": None,
                "end_time": None,
                "elapsed_seconds": None,
                "status": "initialized",
            },
            "phases": {},
            "llm": {
                "count": 0,
                "calls": [],
            },
            "persona": {
                "count": 0,
                "groups": [],
            },
            "ticks": [],
            "errors": [],
        }
        self._write_summary()

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _ensure_summary_shape(self) -> None:
        self.summary.setdefault("run", {})
        self.summary["run"].setdefault("start_time", None)
        self.summary["run"].setdefault("end_time", None)
        self.summary["run"].setdefault("elapsed_seconds", None)
        self.summary["run"].setdefault("status", "initialized")
        self.summary.setdefault("phases", {})
        self.summary.setdefault("llm", {})
        self.summary["llm"].setdefault("count", 0)
        self.summary["llm"].setdefault("calls", [])
        self.summary.setdefault("persona", {})
        self.summary["persona"].setdefault("count", 0)
        self.summary["persona"].setdefault("groups", [])
        self.summary.setdefault("ticks", [])
        self.summary.setdefault("errors", [])

    def _append_log(self, message: str) -> None:
        if not self.log_path:
            return
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{self._timestamp()}] {message}\n")

    def _write_summary(self) -> None:
        if not self.timing_path:
            return
        with open(self.timing_path, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, ensure_ascii=False, indent=2)

    def log_run_start(self, mode: str, seed_file: str, run_dir: str) -> None:
        self._ensure_summary_shape()
        self.summary["run"].update({
            "start_time": self._timestamp(),
            "mode": mode,
            "seed_file": seed_file,
            "run_dir": run_dir,
            "status": "running",
        })
        self._append_log(f"RUN START mode={mode} seed={seed_file} run_dir={run_dir}")
        self._write_summary()

    def log_run_end(self, status: str, elapsed: float) -> None:
        self._ensure_summary_shape()
        self.summary["run"].update({
            "end_time": self._timestamp(),
            "elapsed_seconds": round(elapsed, 2),
            "status": status,
        })
        self._append_log(f"RUN END status={status} elapsed={elapsed:.2f}s")
        self._write_summary()

    def log_phase_start(self, name: str) -> None:
        self._ensure_summary_shape()
        self.summary["phases"].setdefault(name, {})
        self.summary["phases"][name]["start_time"] = self._timestamp()
        self._append_log(f"PHASE START name={name}")
        self._write_summary()

    def log_phase_end(self, name: str, elapsed: float) -> None:
        self._ensure_summary_shape()
        self.summary["phases"].setdefault(name, {})
        self.summary["phases"][name]["end_time"] = self._timestamp()
        self.summary["phases"][name]["elapsed_seconds"] = round(elapsed, 2)
        self._append_log(f"PHASE END name={name} elapsed={elapsed:.2f}s")
        self._write_summary()

    def log_llm_start(self, caller: str, model: str) -> None:
        self._append_log(f"LLM START caller={caller} model={model}")

    def log_llm_end(self, caller: str, model: str, elapsed: float) -> None:
        self._ensure_summary_shape()
        self.summary["llm"]["count"] += 1
        self.summary["llm"]["calls"].append({
            "caller": caller,
            "model": model,
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": self._timestamp(),
        })
        self._append_log(f"LLM END caller={caller} model={model} elapsed={elapsed:.2f}s")
        self._write_summary()

    def log_persona_start(self, group: str) -> None:
        self._append_log(f"PERSONA START group={group}")

    def log_persona_end(self, group: str, elapsed: float) -> None:
        self._ensure_summary_shape()
        self.summary["persona"]["count"] += 1
        self.summary["persona"]["groups"].append({
            "group": group,
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": self._timestamp(),
        })
        self._append_log(f"PERSONA END group={group} elapsed={elapsed:.2f}s")
        self._write_summary()

    def log_tick_start(self, tick: int) -> None:
        self._append_log(f"TICK START tick={tick}")

    def log_speaker_selection(
        self,
        tick: int,
        spreader_count: int,
        computed_num_speakers: int,
        expected_selected_count: int,
        actual_selected_count: int,
        selected_speakers_count: int,
        is_full_selection: bool,
        full_selection_reason: str,
    ) -> None:
        self._ensure_summary_shape()
        payload = {
            "tick": tick,
            "spreader_count": spreader_count,
            "computed_num_speakers": computed_num_speakers,
            "expected_selected_count": expected_selected_count,
            "actual_selected_count": actual_selected_count,
            "selected_speakers_count": selected_speakers_count,
            "is_full_selection": is_full_selection,
            "full_selection_reason": full_selection_reason,
        }
        self._append_log(
            "SPEAKER SELECTION "
            f"tick={tick} "
            f"spreader_count={spreader_count} "
            f"computed_num_speakers={computed_num_speakers} "
            f"expected_selected_count={expected_selected_count} "
            f"actual_selected_count={actual_selected_count} "
            f"selected_speakers_count={selected_speakers_count} "
            f"is_full_selection={is_full_selection} "
            f"full_selection_reason={full_selection_reason}"
        )
        tick_entry = next((entry for entry in self.summary["ticks"] if entry.get("tick") == tick), None)
        if tick_entry is None:
            tick_entry = {"tick": tick}
            self.summary["ticks"].append(tick_entry)
        tick_entry["speaker_selection"] = payload
        self._write_summary()

    def log_tick_end(self, tick: int, elapsed: float, speakers: int, llm_calls: int) -> None:
        self._ensure_summary_shape()
        tick_entry = next((entry for entry in self.summary["ticks"] if entry.get("tick") == tick), None)
        if tick_entry is None:
            tick_entry = {"tick": tick}
            self.summary["ticks"].append(tick_entry)
        tick_entry.update({
            "elapsed_seconds": round(elapsed, 2),
            "speakers": speakers,
            "llm_calls": llm_calls,
            "timestamp": self._timestamp(),
        })
        self._append_log(
            f"TICK END tick={tick} elapsed={elapsed:.2f}s speakers={speakers} llm_calls={llm_calls}"
        )
        self._write_summary()

    def log_error(self, stage: str, error: str) -> None:
        self._ensure_summary_shape()
        self.summary["errors"].append({
            "stage": stage,
            "error": error,
            "timestamp": self._timestamp(),
        })
        self._append_log(f"ERROR stage={stage} error={error}")
        self._write_summary()

    def get_llm_call_count(self) -> int:
        return int(self.summary.get("llm", {}).get("count", 0))


_runtime_logger = RuntimeLogger()


def get_runtime_logger() -> RuntimeLogger:
    return _runtime_logger
