"""Rich Live 底部状态栏。

用法：
    from src.display import StatusBar, ConcurrencyTracker

    with StatusBar() as bar:
        bar.set_phase("Phase 1 实体提取")
        ct = bar.set_concurrency()
        # ... concurrent work ...
        ct.add("群体A")
        ct.add("群体B")
        ct.done("群体A", 12.3)

可从任意位置获取当前 bar：
    from src.display import get_bar
    bar = get_bar()
"""

import threading
import time
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from .concurrency_tracker import ConcurrencyTracker
from .phase_tracker import PhaseTracker

_console = Console()
_current_bar: Optional["StatusBar"] = None


def get_bar() -> Optional["StatusBar"]:
    """获取当前激活的 StatusBar（可从任意线程调用）。"""
    return _current_bar


class StatusBar:
    """Rich Live 底部状态栏上下文管理器。"""

    def __init__(self) -> None:
        self.phase = PhaseTracker()
        self.phase.start("就绪")
        self._concurrency: Optional[ConcurrencyTracker] = None
        self._live: Optional[Live] = None
        self._stop = False
        self._thread: Optional[threading.Thread] = None

    # ── 外部接口 ──────────────────────────────────────────────

    def set_phase(self, name: str) -> None:
        """切换当前阶段。"""
        self.phase.start(name)

    def set_concurrency(self) -> ConcurrencyTracker:
        """创建一个新的并发池跟踪器并激活。返回跟踪器以便外部调用。"""
        self._concurrency = ConcurrencyTracker(on_change=self.refresh)
        return self._concurrency

    @property
    def concurrency(self) -> Optional[ConcurrencyTracker]:
        return self._concurrency

    # ── 面板渲染 ──────────────────────────────────────────────

    def _render(self) -> Panel:
        from rich.table import Table
        from rich.text import Text

        t = Table.grid(padding=(0, 1))
        spinner = Spinner("dots", style="cyan")

        # 第一行：Spinner + 阶段名 + 时间 + 并发概览
        con_str = f""
        if self._concurrency:
            s = self._concurrency.summary
            con_str = f"并发 {s['total']}"
            if s["done"]:
                con_str += f"  ✓{s['done']}"
            if s["pending"]:
                con_str += f"  ⏳{s['pending']}"
            if s["max_elapsed"]:
                con_str += f"  最慢 {s['max_elapsed']:.1f}s"

        t.add_row(
            spinner,
            Text(f" {self.phase.name} ", style="bold"),
            Text(f"⏱ {self.phase.elapsed_str}", style="cyan"),
            Text(f"  ┃ {con_str}" if con_str else ""),
        )

        # 第二行+：每个 worker
        if self._concurrency:
            raw = dict(self._concurrency.raw_workers)  # name -> elapsed_or_None
            live = dict(self._concurrency.live_workers) if self._concurrency.live_workers else {}
            if raw:
                parts = []
                for name in raw:
                    elapsed = live.get(name, 0.0)
                    if raw[name] is not None:
                        parts.append(f"  {name} [green]✓[/green] {elapsed:.1f}s")
                    else:
                        parts.append(f"  {name} [cyan]⏱[/cyan] {elapsed:.1f}s")
                for i in range(0, len(parts), 3):
                    t.add_row(Text(""), Text(""), Text(""), Text.from_markup("".join(parts[i:i + 3])))

        panel = Panel(t, border_style="cyan", title="[bold]仿真引擎[/bold]")
        return panel

    # ── 生命周期 ──────────────────────────────────────────────

    def __enter__(self) -> "StatusBar":
        global _current_bar
        _current_bar = self

        self._live = Live(
            self._render(),
            refresh_per_second=4,
            transient=False,
            console=_console,
        )
        self._live.start()
        self._stop = False
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *args) -> None:
        global _current_bar
        self._stop = True
        if self._thread:
            self._thread.join(timeout=2)
        if self._live:
            self._live.stop()
        _current_bar = None
        _console.print()

    def refresh(self) -> None:
        """状态变更后调用（如 worker 完成），触发面板刷新。"""
        if self._live:
            self._live.update(self._render())

    def _refresh_loop(self) -> None:
        """后台线程：每秒刷新一次（让计时器和 Spinner 走动）。"""
        while not self._stop:
            time.sleep(1)
            try:
                if self._live:
                    self._live.update(self._render())
            except Exception:
                pass
