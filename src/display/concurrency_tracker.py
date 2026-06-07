"""线程安全的并发池跟踪器。"""

import threading
import time
from typing import Dict, List, Optional, Tuple


class ConcurrencyTracker:
    """跟踪一组并发 worker 的状态（活跃/完成/耗时）。"""

    def __init__(self, on_change=None) -> None:
        self._lock = threading.Lock()
        self._workers: Dict[str, Dict] = {}  # name -> {"start": float, "elapsed": float | None}
        self._on_change = on_change

    def add(self, name: str) -> None:
        """注册一个 worker。"""
        with self._lock:
            self._workers[name] = {"start": time.time(), "elapsed": None}

    def done(self, name: str, elapsed: float) -> None:
        """标记一个 worker 完成。"""
        with self._lock:
            if name in self._workers:
                self._workers[name]["elapsed"] = elapsed
        if self._on_change:
            self._on_change()

    @property
    def summary(self) -> Dict:
        """返回当前快照。"""
        with self._lock:
            total = len(self._workers)
            done = sum(1 for w in self._workers.values() if w["elapsed"] is not None)
            pending = total - done
            elapsed_list = [
                w["elapsed"] for w in self._workers.values() if w["elapsed"] is not None
            ]
            worker_names = list(self._workers.keys())
            return {
                "total": total,
                "done": done,
                "pending": pending,
                "max_elapsed": max(elapsed_list) if elapsed_list else 0.0,
                "min_elapsed": min(elapsed_list) if elapsed_list else 0.0,
                "workers": worker_names,
            }

    @property
    def raw_workers(self) -> List[Tuple[str, Optional[float]]]:
        """返回 (name, elapsed_or_None) 列表。None 表示仍在跑。"""
        with self._lock:
            return [(k, v["elapsed"]) for k, v in self._workers.items()]

    @property
    def live_workers(self) -> List[Tuple[str, Optional[float]]]:
        """返回 (name, elapsed_or_live) 列表。
        已完成的返回固定耗时，还在跑的返回 time.time() - start（实时跳动）。"""
        now = time.time()
        with self._lock:
            results = []
            for k, v in self._workers.items():
                if v["elapsed"] is not None:
                    results.append((k, v["elapsed"]))
                else:
                    results.append((k, now - v["start"]))
            return results
