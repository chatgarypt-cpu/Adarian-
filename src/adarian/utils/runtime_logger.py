"""运行时观测日志，基于 logging 库。"""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

_LOG = logging.getLogger("runtime")

# 保存原有的 excepthook，避免覆盖第三方工具的 hook
_orig_sys_excepthook: Any = None
_orig_threading_excepthook: Any = None


def _make_sys_excepthook(log_path: Path):
    """构造 sys.excepthook 替代函数，将未捕获异常写入 run.log。"""
    def _hook(exc_type, exc_value, exc_tb):
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        _LOG.error("未捕获异常 (sys.excepthook):\n%s", tb_text)
        if _orig_sys_excepthook:
            _orig_sys_excepthook(exc_type, exc_value, exc_tb)
    return _hook


def _make_threading_excepthook(log_path: Path):
    """构造 threading.excepthook 替代函数，将线程池中的未捕获异常写入 run.log。"""
    def _hook(args: threading.ExceptHookArgs):
        tb_text = "".join(traceback.format_exception(
            args.exc_type, args.exc_value, args.exc_traceback,
        ))
        thread_name = args.thread.name if args.thread else "unknown"
        _LOG.error("未捕获异常 (threading.excepthook) thread=%s:\n%s", thread_name, tb_text)
        if _orig_threading_excepthook:
            _orig_threading_excepthook(args)
    return _hook


class RuntimeLogger:
    """最小运行观测器，所有输出通过 logging 库统一管理。"""

    def __init__(self) -> None:
        self.run_dir: Optional[Path] = None
        self.log_path: Optional[Path] = None
        self.summary: Dict[str, Any] = {}
        self._configured = False
        self._excepthooks_installed = False

    def configure(self, run_dir: Path) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.run_dir / "run.log"

        # Initialize logger: file + console, no duplicate logs on reconfigure
        _LOG.setLevel(logging.INFO)
        _LOG.handlers.clear()

        fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        # File handler（接所有日志，含 error 级别）
        fh = logging.FileHandler(self.log_path, mode="a", encoding="utf-8")
        fh.setFormatter(fmt)
        _LOG.addHandler(fh)

        # Console handler (stdout)
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        _LOG.addHandler(ch)

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

        # 安装异常钩子（只在首次 configure 时安装一次）
        if not self._excepthooks_installed:
            self._install_excepthooks()
            self._excepthooks_installed = True

        self._write_summary()
        self._configured = True

    def _install_excepthooks(self) -> None:
        """安装 sys.excepthook + threading.excepthook，未捕获异常也进 run.log。"""
        global _orig_sys_excepthook, _orig_threading_excepthook
        _orig_sys_excepthook = sys.excepthook
        sys.excepthook = _make_sys_excepthook(self.log_path)
        _orig_threading_excepthook = threading.excepthook
        threading.excepthook = _make_threading_excepthook(self.log_path)

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

    def _write_summary(self) -> None:
        # 仍在内存中维护 summary dict（供其他模块读），不再写独立文件
        pass

    def log_run_start(self, mode: str, seed_file: str, run_dir: str) -> None:
        self._ensure_summary_shape()
        self.summary["run"].update({
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mode": mode,
            "seed_file": seed_file,
            "run_dir": run_dir,
            "status": "running",
        })
        _LOG.info("RUN START mode=%s seed=%s run_dir=%s", mode, seed_file, run_dir)

    def log_run_end(self, status: str, elapsed: float) -> None:
        self._ensure_summary_shape()
        self.summary["run"].update({
            "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": round(elapsed, 2),
            "status": status,
        })
        _LOG.info("RUN END status=%s elapsed=%.2fs", status, elapsed)

    def log_phase_start(self, name: str) -> None:
        self._ensure_summary_shape()
        self.summary["phases"].setdefault(name, {})
        self.summary["phases"][name]["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _LOG.info("PHASE START name=%s", name)

    def log_phase_end(self, name: str, elapsed: float) -> None:
        self._ensure_summary_shape()
        self.summary["phases"].setdefault(name, {})
        self.summary["phases"][name]["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.summary["phases"][name]["elapsed_seconds"] = round(elapsed, 2)
        _LOG.info("PHASE END name=%s elapsed=%.2fs", name, elapsed)

    def log_llm_start(self, caller: str, model: str) -> None:
        _LOG.info("LLM START caller=%s model=%s", caller, model)

    def log_llm_end(self, caller: str, model: str, elapsed: float) -> None:
        self._ensure_summary_shape()
        self.summary["llm"]["count"] += 1
        self.summary["llm"]["calls"].append({
            "caller": caller,
            "model": model,
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        _LOG.info("LLM END caller=%s model=%s elapsed=%.2fs", caller, model, elapsed)

    def log_persona_start(self, group: str) -> None:
        _LOG.info("PERSONA START group=%s", group)

    def log_persona_end(self, group: str, elapsed: float) -> None:
        self._ensure_summary_shape()
        self.summary["persona"]["count"] += 1
        self.summary["persona"]["groups"].append({
            "group": group,
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        _LOG.info("PERSONA END group=%s elapsed=%.2fs", group, elapsed)

    def log_tick_start(self, tick: int) -> None:
        _LOG.info("TICK START tick=%d", tick)

    def log_speaker_selection(
        self, tick: int, spreader_count: int, computed_num_speakers: int,
        expected_selected_count: int, actual_selected_count: int,
        selected_speakers_count: int, is_full_selection: bool,
        full_selection_reason: str,
    ) -> None:
        self._ensure_summary_shape()
        _LOG.info(
            "SPEAKER SELECTION tick=%d spreader_count=%d "
            "computed_num_speakers=%d expected_selected_count=%d "
            "actual_selected_count=%d selected_speakers_count=%d "
            "is_full_selection=%s full_selection_reason=%s",
            tick, spreader_count, computed_num_speakers,
            expected_selected_count, actual_selected_count,
            selected_speakers_count, is_full_selection, full_selection_reason,
        )
        tick_entry = next((e for e in self.summary["ticks"] if e.get("tick") == tick), None)
        if tick_entry is None:
            tick_entry = {"tick": tick}
            self.summary["ticks"].append(tick_entry)
        tick_entry["speaker_selection"] = {
            "tick": tick,
            "spreader_count": spreader_count,
            "computed_num_speakers": computed_num_speakers,
            "expected_selected_count": expected_selected_count,
            "actual_selected_count": actual_selected_count,
            "selected_speakers_count": selected_speakers_count,
            "is_full_selection": is_full_selection,
            "full_selection_reason": full_selection_reason,
        }

    def log_tick_end(self, tick: int, elapsed: float, speakers: int, llm_calls: int) -> None:
        self._ensure_summary_shape()
        tick_entry = next((e for e in self.summary["ticks"] if e.get("tick") == tick), None)
        if tick_entry is None:
            tick_entry = {"tick": tick}
            self.summary["ticks"].append(tick_entry)
        tick_entry.update({
            "elapsed_seconds": round(elapsed, 2),
            "speakers": speakers,
            "llm_calls": llm_calls,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        _LOG.info("TICK END tick=%d elapsed=%.2fs speakers=%d llm_calls=%d", tick, elapsed, speakers, llm_calls)

    def log_error(self, stage: str, error: str) -> None:
        self._ensure_summary_shape()
        self.summary["errors"].append({
            "stage": stage,
            "error": error,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        _LOG.error("ERROR stage=%s error=%s", stage, error)

    def get_summary(self) -> Dict[str, Any]:
        """返回当前运行时摘要 dict。"""
        return dict(self.summary)

    def get_llm_call_count(self) -> int:
        return int(self.summary.get("llm", {}).get("count", 0))

    def info(self, msg: str, *args) -> None:
        """Public interface for pipeline scripts to log info messages."""
        _LOG.info(msg, *args)


_runtime_logger = RuntimeLogger()


def get_runtime_logger() -> RuntimeLogger:
    return _runtime_logger
