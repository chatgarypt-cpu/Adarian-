#!/usr/bin/env python3
"""
Multi-model parallel world batch runner for Adarian.

Adapted from scheduler/run.py (v1.4.0).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass

from adarian import config


DEFAULT_BASE_URL = os.environ.get("LLM_BASE_URL", "http://100.89.3.59:8090/v1")
DEFAULT_MAX_TOKENS = 16384
RUN_TIMEOUT_SECONDS = int(os.environ.get("SCHEDULER_WORLD_TIMEOUT", "1800"))


# ── Data structures ──────────────────────────────────────────────


@dataclass
class WorldSpec:
    """One parallel-world run request."""

    name: str
    model: str
    label: str = ""
    base_url: str = DEFAULT_BASE_URL
    max_tokens: int = DEFAULT_MAX_TOKENS

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "label": self.label or self.model,
            "base_url": self.base_url,
            "max_tokens": self.max_tokens,
        }


@dataclass
class WorldState:
    """Mutable run state for one world."""

    world_id: str
    model_name: str
    label: str
    status: str = "pending"
    output_dir: str = ""
    dataset_path: str = ""
    dataset_exists: bool = False
    primary_types: list[str] = field(default_factory=list)
    primary_types_exists: bool = False
    error_summary: str = ""
    elapsed_seconds: float | None = None
    returncode: int | None = None
    log_tail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "name": self.world_id,
            "model_name": self.model_name,
            "model": self.model_name,
            "label": self.label,
            "status": self.status,
            "output_dir": self.output_dir,
            "dir": self.output_dir,
            "dataset_path": self.dataset_path,
            "dataset_exists": self.dataset_exists,
            "risk_type_classification": {
                "primary_types": self.primary_types,
                "primary_types_exists": self.primary_types_exists,
            },
            "primary_types": self.primary_types,
            "primary_types_exists": self.primary_types_exists,
            "error_summary": self.error_summary,
            "error": self.error_summary or None,
            "elapsed_seconds": self.elapsed_seconds,
            "elapsed": self.elapsed_seconds,
            "returncode": self.returncode,
            "run_log": self.log_tail,
        }


@dataclass
class BatchSession:
    """State and evidence for one scheduler batch."""

    batch_id: str
    batch_dir: Path
    seed_path: Path
    worlds: list[WorldSpec]
    states: dict[str, WorldState]
    status: str = "pending"
    started_at: str = ""
    completed_at: str = ""
    logs: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        for world in self.worlds:
            _merge_filesystem_evidence(self.states[world.name])
        worlds = [self.states[w.name].as_dict() for w in self.worlds]
        summary = summarize_worlds(worlds)
        return {
            "batch_id": self.batch_id,
            "batch_dir": str(self.batch_dir),
            "seed_path": str(self.seed_path),
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "worlds": worlds,
            "summary": summary,
            "logs": self.logs[-120:],
            "report_agent_consumer": {
                "status": "coming_soon",
                "enabled": False,
                "input_contract": "batch_dir or worlds[].dataset_path",
            },
        }

    def log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {message}")


# ── Public API ───────────────────────────────────────────────────


def available_models() -> dict[str, str]:
    from adarian.model_router import CATALOG

    exclude = {"bge-m3", "bge-m3-tke", "deepseek-v4-flash"}
    return {
        model: desc
        for model, desc in CATALOG.items()
        if "❌" not in desc and model not in exclude
    }


def build_worlds(models: list[str], base_url: str = DEFAULT_BASE_URL) -> list[WorldSpec]:
    catalog = available_models()
    worlds: list[WorldSpec] = []
    for index, model in enumerate(models):
        worlds.append(
            WorldSpec(
                name=f"world_{index}",
                model=model,
                label=catalog.get(model, model),
                base_url=base_url,
            )
        )
    return worlds


def start_batch(
    *,
    models: list[str],
    seed_text: str = "",
    seed_path: str = "",
    tag: str = "batch",
    base_url: str = DEFAULT_BASE_URL,
) -> BatchSession:
    """Create a batch session and seed file, but do not execute worlds."""

    if not models:
        raise ValueError("至少需要选择 1 个模型")

    worlds = build_worlds(models, base_url=base_url)
    now = datetime.now()
    date_dir = now.strftime("%Y-%m-%d")
    clean_tag = _safe_tag(tag or "batch")
    batch_id = f"{clean_tag}_{now.strftime('%H%M%S')}"
    batch_dir = config.OUTPUTS_DIR / "runs" / date_dir / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    resolved_seed = _prepare_seed(batch_dir, seed_text=seed_text, seed_path=seed_path)
    _write_batch_config(batch_dir, batch_id, resolved_seed, worlds)

    states = {
        world.name: WorldState(
            world_id=world.name,
            model_name=world.model,
            label=world.label or world.model,
            output_dir=str(batch_dir / world.name),
            dataset_path=str(batch_dir / world.name / "simulation_dataset.json"),
        )
        for world in worlds
    }
    session = BatchSession(
        batch_id=batch_id,
        batch_dir=batch_dir,
        seed_path=resolved_seed,
        worlds=worlds,
        states=states,
        status="pending",
        started_at=now.strftime("%Y-%m-%d %H:%M:%S"),
    )
    session.log(f"Batch created: {batch_dir}")
    session.log(f"Seed: {resolved_seed}")
    session.log(f"Worlds: {', '.join(w.model for w in worlds)}")
    return session


def run_batch(
    *,
    models: list[str],
    seed_text: str = "",
    seed_path: str = "",
    tag: str = "batch",
    base_url: str = DEFAULT_BASE_URL,
    max_concurrent: int | None = None,
) -> BatchSession:
    """Create and execute a full batch synchronously."""

    session = start_batch(
        models=models,
        seed_text=seed_text,
        seed_path=seed_path,
        tag=tag,
        base_url=base_url,
    )
    execute_session(session, max_concurrent=max_concurrent)
    return session


def _phase_from_run_log(world_dir: Path) -> str:
    """Read the latest PHASE START from run.log."""
    log = world_dir / "run.log"
    if not log.exists():
        return "就绪"
    try:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        phase = ""
        for line in reversed(lines):
            if "PHASE START" in line:
                m = re.search(r"name=(\S+)", line)
                if m:
                    phase = m.group(1).replace("_", " ").title()
                    break
            elif "PHASE END" in line:
                break  # 最近的 phase 已结束，继续往前找
        return phase or "就绪"
    except OSError:
        return "就绪"


def _render_worlds_panel(session: BatchSession, elapsed: float) -> Panel:
    """Render all worlds matching the StatusBar design language."""
    t = Table.grid(padding=(0, 1))
    spinner = Spinner("dots", style="cyan")
    done = sum(1 for w in session.worlds if session.states[w.name].status == "success")
    failed = sum(1 for w in session.worlds if session.states[w.name].status == "failed")
    running = sum(1 for w in session.worlds if session.states[w.name].status == "running")
    summary = f"  批量推演  ✓{done} ✗{failed} ▶{running}  ⏱ {elapsed:.0f}s"
    t.add_row(spinner, Text(summary, style="bold"))

    for world in session.worlds:
        state = session.states.get(world.name)
        if not state:
            continue
        wd = session.batch_dir / world.name
        stat = state.status or "pending"

        if stat == "running":
            ws = _world_start.get(world.name)
            elapsed_s = f"{time.perf_counter() - ws:.0f}s" if ws else ""
            phase = _phase_from_run_log(wd)
            t.add_row(Text(""), Text(f"  {world.name}  {world.model[:20]}  ⏱ {phase}  {elapsed_s}"))
        elif stat == "success":
            es = f"{state.elapsed_seconds or 0:.0f}s"
            ds = "✅" if state.dataset_exists else ""
            t.add_row(Text(""), Text(f"  ✓ {world.name}  {world.model[:20]}  {es}  {ds}"))
        elif stat == "failed":
            es = f"{state.elapsed_seconds or 0:.0f}s"
            t.add_row(Text(""), Text(f"  ✗ {world.name}  {world.model[:20]}  {es}"))
        else:
            t.add_row(Text(""), Text(f"     {world.name}  {world.model[:20]}  ⏳等待"))

    return Panel(t, border_style="dim")


def execute_session(session: BatchSession, max_concurrent: int | None = None) -> BatchSession:
    """Run all worlds and update the session in place."""

    session.status = "running"
    session.log("Batch execution started")
    start = time.perf_counter()

    # Start subprocess pool
    workers = max(1, min(max_concurrent or len(session.worlds), len(session.worlds)))
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    futures = {pool.submit(_run_world, session, world): world.name for world in session.worlds}
    done = set()

    # Live monitoring display
    console = Console(stderr=True)
    with Live(console=console, refresh_per_second=1, transient=True) as live:
        while len(done) < len(futures):
            # Check which futures completed
            for fut in list(futures):
                if fut not in done and fut.done():
                    done.add(fut)
                    try:
                        fut.result()
                    except Exception:
                        pass
            elapsed = time.perf_counter() - start
            live.update(_render_worlds_panel(session, elapsed))
            time.sleep(1)

        # Final render after all done
        elapsed = time.perf_counter() - start
        live.update(_render_worlds_panel(session, elapsed))
        time.sleep(1)

    pool.shutdown(wait=False)

    worlds = [state.as_dict() for state in session.states.values()]
    failed = sum(1 for w in worlds if w["status"] == "failed")
    session.status = "failed" if failed else "success"
    session.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session.log(f"Batch execution finished: {session.status}")
    _write_batch_result(session)
    return session


def summarize_worlds(worlds: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(worlds),
        "success": sum(1 for w in worlds if w["status"] == "success"),
        "completed": sum(1 for w in worlds if w["status"] == "success"),
        "failed": sum(1 for w in worlds if w["status"] == "failed"),
        "running": sum(1 for w in worlds if w["status"] == "running"),
        "pending": sum(1 for w in worlds if w["status"] == "pending"),
    }


# ── Internal ─────────────────────────────────────────────────────

_world_start: dict[str, float] = {}


def _run_world(session: BatchSession, world: WorldSpec) -> None:

    state = session.states[world.name]
    world_dir = session.batch_dir / world.name
    world_dir.mkdir(parents=True, exist_ok=True)
    state.status = "running"
    state.output_dir = str(world_dir)
    state.dataset_path = str(world_dir / "simulation_dataset.json")
    _write_world_status(world_dir, state)
    session.log(f"{world.name} started: {world.model}")
    _world_start[world.name] = time.perf_counter()

    env = os.environ.copy()
    env.update(
        {
            "LLM_PROVIDER": "qwen",
            "QWEN_MODEL": world.model,
            "LLM_BASE_URL": world.base_url,
            "PARALLEL_MODE": "true",
            "PARALLEL_BATCH_DIR": str(session.batch_dir),
            "PARALLEL_WORLD_NAME": world.name,
            "PYTHONUNBUFFERED": "1",
        }
    )
    env["MAX_TOKENS"] = str(world.max_tokens)
    if "100.89.3.59" in world.base_url:
        no_proxy = env.get("NO_PROXY", "")
        hosts = ["100.89.3.59", "localhost", "127.0.0.1"]
        merged = ",".join(hosts + ([no_proxy] if no_proxy else []))
        env["NO_PROXY"] = merged
        env["no_proxy"] = merged

    started = time.perf_counter()
    proc: subprocess.CompletedProcess[str] | None = None
    error = ""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "adarian", "run", str(session.seed_path)],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        error = f"timeout after {RUN_TIMEOUT_SECONDS}s"
        state.returncode = 124
        state.log_tail = _trim_tail((exc.stdout or "") + "\n" + (exc.stderr or ""), 80)
    except Exception as exc:
        error = str(exc)
        state.returncode = 1

    elapsed = round(time.perf_counter() - started, 2)
    state.elapsed_seconds = elapsed
    if proc is not None:
        state.returncode = proc.returncode
        state.log_tail = _trim_tail((proc.stdout or "") + "\n" + (proc.stderr or ""), 80)
        if proc.returncode != 0:
            error = _summarize_error(proc.stderr, proc.stdout) or f"exit code {proc.returncode}"

    _merge_filesystem_evidence(state)
    if state.returncode == 0 and state.dataset_exists and state.primary_types_exists:
        state.status = "success"
        state.error_summary = ""
        session.log(f"{world.name} success: primary_types={state.primary_types}")
    else:
        state.status = "failed"
        state.error_summary = error or state.error_summary or "dataset evidence check failed"
        session.log(f"{world.name} failed: {state.error_summary}")
    _write_world_status(world_dir, state)


def _prepare_seed(batch_dir: Path, *, seed_text: str, seed_path: str) -> Path:
    text = (seed_text or "").strip()
    if text:
        path = batch_dir / "seed_event.txt"
        path.write_text(text + "\n", encoding="utf-8")
        return path

    candidate = Path(seed_path or "seeds/test8.txt")
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    if not candidate.exists():
        raise FileNotFoundError(f"种子文件不存在: {candidate}")
    return candidate.resolve()


def _write_batch_config(batch_dir: Path, batch_id: str, seed_path: Path, worlds: list[WorldSpec]) -> None:
    lines = [
        f"batch_id: {batch_id}",
        f"seed_path: {seed_path}",
        f"created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "worlds:",
    ]
    for world in worlds:
        lines.extend(
            [
                f"  - name: {world.name}",
                f"    model: {world.model}",
                f"    label: {_yaml_quote(world.label or world.model)}",
                f"    base_url: {world.base_url}",
                f"    max_tokens: {world.max_tokens}",
            ]
        )
    (batch_dir / "batch_config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_batch_result(session: BatchSession) -> None:
    result = session.as_dict()
    (session.batch_dir / "batch_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (session.batch_dir / "scheduler_batch.log").write_text(
        "\n".join(session.logs) + "\n",
        encoding="utf-8",
    )


def _write_world_status(world_dir: Path, state: WorldState) -> None:
    (world_dir / "scheduler_status.json").write_text(
        json.dumps(state.as_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _safe_tag(tag: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_-]+", "_", tag.strip())
    return clean.strip("_") or "batch"


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _summarize_error(stderr: str, stdout: str) -> str:
    lines = (stderr or stdout or "").splitlines()
    for line in reversed(lines):
        text = line.strip()
        if text:
            return text[:500]
    return ""


def _trim_tail(text: str, lines: int) -> str:
    return "\n".join(text.splitlines()[-lines:])


def _read_text_tail(path: Path, lines: int) -> list[str]:
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    except OSError:
        return []


# ── CLI (direct) ─────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Adarian batch runner")
    parser.add_argument("--models", required=True, help="逗号分隔模型名")
    parser.add_argument("--seed-text", default="")
    parser.add_argument("--seed-path", default="")
    parser.add_argument("--tag", default="batch")
    parser.add_argument("--max-concurrent", type=int, default=None)
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    session = run_batch(
        models=models,
        seed_text=args.seed_text,
        seed_path=args.seed_path,
        tag=args.tag,
        max_concurrent=args.max_concurrent,
    )
    print(json.dumps(session.as_dict(), ensure_ascii=False, indent=2))


# ── Dataset evidence helpers ─────────────────────────────────────


def inspect_dataset(dataset_path: str | Path) -> dict[str, Any]:
    """Read dataset evidence required by the Scheduler MVP contract."""
    path = Path(dataset_path)
    evidence = {
        "dataset_path": str(path),
        "dataset_exists": path.exists(),
        "primary_types": [],
        "primary_types_exists": False,
        "error": "",
    }
    if not path.exists():
        evidence["error"] = "simulation_dataset.json not found"
        return evidence
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        primary_types = (
            data.get("simulation_result", {})
            .get("risk_type_classification", {})
            .get("primary_types", [])
        )
        evidence["primary_types"] = primary_types if isinstance(primary_types, list) else []
        evidence["primary_types_exists"] = bool(evidence["primary_types"])
    except (json.JSONDecodeError, OSError) as exc:
        evidence["error"] = str(exc)
    return evidence


def _merge_filesystem_evidence(state: WorldState) -> None:
    world_dir = Path(state.output_dir)
    dataset = inspect_dataset(world_dir / "simulation_dataset.json")
    state.dataset_path = dataset["dataset_path"]
    state.dataset_exists = bool(dataset["dataset_exists"])
    state.primary_types = list(dataset["primary_types"])
    state.primary_types_exists = bool(dataset["primary_types_exists"])
    if dataset.get("error") and state.dataset_exists:
        state.error_summary = str(dataset["error"])

    run_meta = world_dir / "run_meta.json"
    if run_meta.exists():
        try:
            meta = json.loads(run_meta.read_text(encoding="utf-8"))
            if not state.model_name and meta.get("model"):
                state.model_name = str(meta.get("model"))
            if not state.label and state.model_name:
                state.label = state.model_name
            if not state.elapsed_seconds and meta.get("elapsed_seconds") is not None:
                state.elapsed_seconds = meta.get("elapsed_seconds")
            meta_status = meta.get("status")
            if meta_status == "success" and state.dataset_exists and state.primary_types_exists:
                state.status = "success"
            elif meta_status == "failed":
                state.status = "failed"
            if meta_status == "failed" and not state.error_summary:
                state.error_summary = str(meta.get("error", "run_meta status failed"))
        except (json.JSONDecodeError, OSError):
            pass

    run_log = world_dir / "run.log"
    if run_log.exists():
        tail_lines = _read_text_tail(run_log, 80)
        state.log_tail = "\n".join(tail_lines)
        if not state.error_summary:
            for line in reversed(tail_lines):
                lowered = line.lower()
                if "error" in lowered or "failed" in lowered or "错误" in line:
                    state.error_summary = line.strip()[:500]
                    break
    if state.status == "pending" and state.dataset_exists and state.primary_types_exists:
        state.status = "success"


