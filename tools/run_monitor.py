#!/usr/bin/env python3
"""
Monitor tool for Adarian MVP runs.

Watches a run directory's whitebox/ artifacts in real-time.
Shows run.log, timing_summary, phase1_report, and status updates as they happen.

Usage:
    .venv/bin/python tools/run_monitor.py                          # latest run
    .venv/bin/python tools/run_monitor.py outputs/runs/2026-06-07/test8_172031/run_xxx/
    .venv/bin/python tools/run_monitor.py --tail                   # tail mode (no panel)
"""

import argparse
import json
import os
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Project path setup ──────────────────────────────────────────
_proj = Path(__file__).resolve().parent.parent
if str(_proj) not in sys.path:
    sys.path.insert(0, str(_proj))

# ── Rich imports (optional, degrade gracefully) ─────────────────
try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.spinner import Spinner
    from rich.table import Table
    from rich.text import Text
    from rich import box

    HAS_RICH = True
    _console = Console()
except ImportError:
    HAS_RICH = False


# ═════════════════════════════════════════════════════════════════
#  Run finder
# ═════════════════════════════════════════════════════════════════

def find_latest_run() -> Optional[Path]:
    """Find the most recent complete run directory."""
    runs_root = _proj / "outputs" / "runs"
    if not runs_root.exists():
        return None

    candidates = []
    for date_dir in sorted(runs_root.iterdir(), reverse=True):
        if not date_dir.is_dir() or not date_dir.name[:4].isdigit():
            continue
        for batch_dir in sorted(date_dir.iterdir(), reverse=True):
            if not batch_dir.is_dir():
                continue
            for run_dir in batch_dir.iterdir():
                if run_dir.is_dir() and (run_dir / "whitebox").exists():
                    candidates.append((run_dir.stat().st_mtime, run_dir))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


# ═════════════════════════════════════════════════════════════════
#  Whitebox readers
# ═════════════════════════════════════════════════════════════════

def read_json(path: Path) -> Dict:
    """Safely read a JSON file, return {} on error."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def read_phase1_report(wb: Path) -> Dict:
    return read_json(wb / "phase1_report.json")


def read_timing_summary(wb: Path) -> Dict:
    return read_json(wb / "timing_summary.json")


def read_run_meta(wb: Path) -> Dict:
    return read_json(wb / "run_meta.json")


def read_run_log(wb: Path, last_pos: int = 0) -> tuple[int, List[str]]:
    """Return (new_position, new_lines_since_last_pos)."""
    log_path = wb / "run.log"
    if not log_path.exists():
        return last_pos, []
    size = log_path.stat().st_size
    if size <= last_pos:
        return last_pos, []
    with open(log_path, "r", encoding="utf-8") as f:
        f.seek(last_pos)
        lines = f.readlines()
    return size, [l.rstrip("\n\r") for l in lines]


# ═════════════════════════════════════════════════════════════════
#  Monitor state
# ═════════════════════════════════════════════════════════════════

class RunMonitor:
    """Poll whitebox artifacts and build a display snapshot."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.whitebox = run_dir / "whitebox"
        self.log_pos = 0
        self.log_buffer: List[str] = []
        self._prev_timing = 0.0
        self._prev_report = 0.0
        self._prev_meta = 0.0

    def poll(self) -> Dict[str, Any]:
        """Read all artifacts, return a snapshot dict."""
        now = time.time()

        # run.log streaming
        self.log_pos, new_lines = read_run_log(self.whitebox, self.log_pos)
        self.log_buffer.extend(new_lines)
        if len(self.log_buffer) > 200:
            self.log_buffer = self.log_buffer[-200:]

        # timing_summary.json (re-read if modified)
        wb = self.whitebox
        ts_path = wb / "timing_summary.json"
        if ts_path.exists() and ts_path.stat().st_mtime > self._prev_timing:
            self._prev_timing = ts_path.stat().st_mtime
        timing = read_timing_summary(wb)
        llm_count = timing.get("llm", {}).get("count", 0)
        phases = timing.get("phases", {})
        ticks_raw = timing.get("ticks", [])

        # phase1_report.json
        rp_path = wb / "phase1_report.json"
        if rp_path.exists() and rp_path.stat().st_mtime > self._prev_report:
            self._prev_report = rp_path.stat().st_mtime
        p1 = read_phase1_report(wb)

        # run_meta.json
        rm_path = wb / "run_meta.json"
        if rm_path.exists() and rm_path.stat().st_mtime > self._prev_meta:
            self._prev_meta = rm_path.stat().st_mtime
        meta = read_run_meta(wb)

        return {
            "run_dir": self.run_dir,
            "log_lines": self.log_buffer[-30:],
            "timing": timing,
            "llm_count": llm_count,
            "phases": phases,
            "ticks": ticks_raw,
            "phase1": p1,
            "meta": meta,
            "updated_at": now,
        }


# ═════════════════════════════════════════════════════════════════
#  Display renderers
# ═════════════════════════════════════════════════════════════════

def render_snapshot(snap: Dict[str, Any]) -> str:
    """Build a plain-text snapshot (fallback when Rich is not available)."""
    lines = []
    run_dir = snap["run_dir"]
    lines.append(f"═══ Run Monitor: {run_dir} ═══")
    lines.append(f"Updated: {datetime.fromtimestamp(snap['updated_at']).strftime('%H:%M:%S')}")

    # Phase summary from meta
    meta = snap.get("meta", {})
    status = meta.get("status", "?")
    lines.append(f"Status: {status}")

    # Phase times
    phases = snap.get("phases", {})
    for pname, pdata in sorted(phases.items()):
        elapsed = pdata.get("elapsed_seconds")
        if elapsed is not None:
            lines.append(f"  {pname}: {elapsed:.1f}s")

    # LLM call count
    lines.append(f"LLM calls: {snap['llm_count']}")

    # Phase 1 report summary
    p1 = snap.get("phase1", {})
    if p1:
        attempts = p1.get("entity_generator", {}).get("attempts", [])
        if attempts:
            success = sum(1 for a in attempts if a.get("outcome") == "success")
            failed = sum(1 for a in attempts if a.get("outcome") != "success")
            lines.append(f"Phase1 EntityGen: {len(attempts)} attempts ({success} ok, {failed} fail)")
        repairs = p1.get("repair_loop", {}).get("actions", [])
        if repairs:
            lines.append(f"Phase1 Repairs: {len(repairs)} ({', '.join(r['type'] for r in repairs)})")
        errors = p1.get("errors", [])
        if errors:
            for e in errors:
                lines.append(f"  Error: {e.get('stage')}: {e.get('message', '')[:100]}")

    # Ticks
    ticks = snap.get("ticks", [])
    if ticks:
        tick_summary = ", ".join(
            f"T{t.get('tick','?')}={t.get('elapsed_seconds',0):.0f}s({t.get('llm_calls',0)}LLM)"
            for t in ticks[-6:]
        )
        lines.append(f"Ticks: {tick_summary}")

    # Recent log
    lines.append("─── Recent log ───")
    for l in snap["log_lines"][-15:]:
        lines.append(f"  {l}")

    return "\n".join(lines)


def render_rich(snap: Dict[str, Any]) -> Panel:
    """Build a Rich Panel for the Live display."""
    from rich.table import Table
    from rich.text import Text

    t = Table.grid(padding=(0, 1))
    spinner = Spinner("dots", style="cyan")

    # Header: Spinner + run_dir + status
    meta = snap.get("meta", {})
    status = meta.get("status", "running")
    status_color = "green" if status == "success" else "yellow" if status == "running" else "red"
    run_name = snap["run_dir"].parent.name + "/" + snap["run_dir"].name
    t.add_row(
        spinner,
        Text(f" {run_name}", style="bold"),
        Text(f" [{status}]", style=status_color),
    )

    # Phase times
    phases = snap.get("phases", {})
    phase_parts = []
    for pname, pdata in sorted(phases.items()):
        elapsed = pdata.get("elapsed_seconds")
        if elapsed is not None:
            short = pname.split("_")[0] if "_" in pname else pname[:6]
            phase_parts.append(f"{short}={elapsed:.0f}s")
    if phase_parts:
        t.add_row(Text(""), Text(f"Phases: {' | '.join(phase_parts)}"))

    # LLM + ticks
    llm_count = snap["llm_count"]
    ticks = snap.get("ticks", [])
    tick_info = f"LLM={llm_count}"
    if ticks:
        last_tick = ticks[-1]
        tick_info += f" | Tick {last_tick.get('tick', '?')}/{len(ticks)}"
    t.add_row(Text(""), Text(tick_info))

    # Phase 1 report
    p1 = snap.get("phase1", {})
    if p1:
        p1_lines = []
        attempts = p1.get("entity_generator", {}).get("attempts", [])
        if attempts:
            ok = sum(1 for a in attempts if a.get("outcome") == "success")
            fail = len(attempts) - ok
            p1_lines.append(f"EntityGen: {len(attempts)}x ({ok}ok{f'/{fail}fail' if fail else ''})")
        repairs = p1.get("repair_loop", {}).get("actions", [])
        if repairs:
            p1_lines.append(f"Repair: {len(repairs)} actions")
        errors = p1.get("errors", [])
        if errors:
            p1_lines.append(f"Errors: {len(errors)}")
            for e in errors[:2]:
                p1_lines.append(f"  {e.get('stage')}: {str(e.get('message', ''))[:60]}")
        if p1_lines:
            t.add_row(Text(""), Text(" | ".join(p1_lines)))

    # Recent log lines (last 8)
    log_lines = snap["log_lines"][-8:]
    if log_lines:
        for line in log_lines[-4:]:
            t.add_row(Text(""), Text(line[:90], style="dim"))

    return Panel(t, border_style="dim", title="[bold]run monitor[/bold]")


# ═════════════════════════════════════════════════════════════════
#  Main
# ═════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Monitor an Adarian run directory.")
    parser.add_argument("run_dir", nargs="?", type=str, help="Path to run directory (default: latest)")
    parser.add_argument("--tail", action="store_true", help="Tail mode: show log lines (no panel)")
    parser.add_argument("--refresh", type=float, default=2.0, help="Poll interval in seconds")
    args = parser.parse_args()

    # Resolve run directory
    if args.run_dir:
        run_dir = Path(args.run_dir).resolve()
    else:
        run_dir = find_latest_run()
        if not run_dir:
            print("No runs found. Run a simulation first.")
            sys.exit(1)

    if not run_dir.exists():
        print(f"Run directory not found: {run_dir}")
        sys.exit(1)

    whitebox = run_dir / "whitebox"
    if not whitebox.exists():
        print(f"Whitebox directory not found: {whitebox}")
        print("The run may still be initializing. Waiting...")
        # Wait a bit for whitebox to appear
        for _ in range(30):
            if whitebox.exists():
                break
            time.sleep(1)
        if not whitebox.exists():
            print("Whitebox still not found. Is the simulation running?")
            sys.exit(1)

    monitor = RunMonitor(run_dir)

    if args.tail:
        # Simple tail mode
        print(f"Tailing: {run_dir}")
        print("-" * 60)
        try:
            while True:
                snap = monitor.poll()
                for line in snap["log_lines"]:
                    print(line)
                time.sleep(args.refresh)
        except KeyboardInterrupt:
            print("\nStopped.")
            return

    if not HAS_RICH:
        print("Rich not available. Falling back to plain-text mode.")
        print(f"Monitoring: {run_dir}")
        try:
            while True:
                snap = monitor.poll()
                os.system("clear" if os.name == "posix" else "cls")
                print(render_snapshot(snap))
                time.sleep(args.refresh)
        except KeyboardInterrupt:
            print("\nStopped.")
            return

    # Rich Live mode
    current_dir = None

    def _render_fn() -> Panel:
        snap = monitor.poll()
        return render_rich(snap)

    try:
        with Live(_render_fn(), refresh_per_second=1 / args.refresh, transient=True, console=_console) as live:
            # Keep alive until Ctrl+C
            while True:
                live.update(_render_fn())
                time.sleep(args.refresh)
    except KeyboardInterrupt:
        print()
        # Final snapshot
        snap = monitor.poll()
        print(render_snapshot(snap))


if __name__ == "__main__":
    main()
