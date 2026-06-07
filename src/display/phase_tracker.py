"""阶段跟踪：当前阶段名 + 计时。"""

import time


class PhaseTracker:
    """记录当前阶段名称、起始时间、已用时间。"""

    def __init__(self) -> None:
        self._name = "启动"
        self._start = 0.0

    def start(self, name: str) -> None:
        self._name = name
        self._start = time.time()

    @property
    def elapsed(self) -> float:
        if self._start == 0.0:
            return 0.0
        return time.time() - self._start

    @property
    def name(self) -> str:
        return self._name

    @property
    def elapsed_str(self) -> str:
        e = self.elapsed
        mins, secs = divmod(int(e), 60)
        return f"{mins:02d}:{secs:02d}"
