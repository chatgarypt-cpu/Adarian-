"""Phase 1 lifecycle reporter — 记录每次执行的报错、修复、耗时。"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class Phase1Reporter:
    """收集 Phase 1 全生命周期的诊断数据，写入 phase1_report.json。"""

    _current: Optional["Phase1Reporter"] = None

    @classmethod
    def get_current(cls) -> Optional["Phase1Reporter"]:
        return cls._current

    def __init__(self) -> None:
        self.reset()
        Phase1Reporter._current = self

    def close(self) -> None:
        Phase1Reporter._current = None

    def reset(self) -> None:
        self._data: Dict[str, Any] = {
            "analyzer": {},
            "entity_generator": {"attempts": []},
            "concurrent_spreaders": {},
            "compiler": {"normalizations": [], "fixes": []},
            "repair_loop": {"triggered": False, "actions": []},
            "errors": [],
        }

    def record_analyzer(self, elapsed: float) -> None:
        self._data["analyzer"]["elapsed_seconds"] = round(elapsed, 2)

    def record_entity_gen_attempt(self, attempt: int, elapsed: float, outcome: str, errors: Optional[List[str]] = None) -> None:
        entry: Dict[str, Any] = {
            "attempt": attempt,
            "elapsed_seconds": round(elapsed, 2),
            "outcome": outcome,
        }
        if errors:
            entry["errors"] = errors
        self._data["entity_generator"]["attempts"].append(entry)

    def record_spreaders_concurrent(self, count: int, workers: List[Dict[str, Any]]) -> None:
        self._data["concurrent_spreaders"] = {
            "count": count,
            "workers": workers,
        }

    def record_compiler_normalization(self, field: str, from_val: Any, to_val: Any) -> None:
        self._data["compiler"]["normalizations"].append({
            "field": field,
            "from": from_val,
            "to": to_val,
        })

    def record_compiler_fix(self, fix_type: str, spreader: str, **details) -> None:
        entry: Dict[str, Any] = {"type": fix_type, "spreader": spreader}
        entry.update(details)
        self._data["compiler"]["fixes"].append(entry)

    def record_repair_action(self, action_type: str, **details) -> None:
        self._data["repair_loop"]["triggered"] = True
        entry: Dict[str, Any] = {"type": action_type}
        entry.update(details)
        self._data["repair_loop"]["actions"].append(entry)

    def record_error(self, stage: str, message: str) -> None:
        self._data["errors"].append({"stage": stage, "message": message})

    def record_total_time(self, elapsed: float) -> None:
        self._data["total_elapsed_seconds"] = round(elapsed, 2)

    @property
    def data(self) -> Dict[str, Any]:
        return dict(self._data)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
