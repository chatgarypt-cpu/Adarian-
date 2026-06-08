#!/usr/bin/env python3
"""
run_world.py — 单世界入口。

在隔离 env 下调 main.py，跑完整 pipeline。
main.py 产生什么，这里就产生什么。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="单世界入口（调 main.py 子进程）")
    parser.add_argument("--seed-path", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--world-name", required=True)
    parser.add_argument("--batch-dir", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    main_py = project_root / "main.py"
    seed_path = Path(args.seed_path).resolve()

    if not main_py.exists():
        print(json.dumps({"status": "failed", "error": f"main.py 不存在: {main_py}"}))
        sys.exit(1)

    # 输出目录：main.py 会建 outputs/runs/YYYY-MM-DD/xxx/
    # 跑完后把产物 mv 到 batch_dir/world_name/
    world_dir = Path(args.batch_dir) / args.world_name

    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(main_py), str(seed_path)],
        env=os.environ,
        capture_output=True, text=True,
        timeout=600,
    )
    elapsed = time.perf_counter() - t0

    # 找 main.py 刚写的最后一次 run 目录
    my_pid = os.getpid()
    runs_dir = project_root / "outputs" / "runs"
    latest_run = _find_latest_run(runs_dir, my_pid)

    if proc.returncode == 0 and latest_run:
        # 将 main.py 的产物 mv 到 world_dir
        world_dir.parent.mkdir(parents=True, exist_ok=True)
        if world_dir.exists():
            shutil.rmtree(world_dir)
        shutil.move(str(latest_run), str(world_dir))

        result = {
            "status": "completed",
            "elapsed": elapsed,
            "world_dir": str(world_dir),
            "error": None,
        }
    else:
        error_msg = proc.stderr[-300:] if proc.stderr else f"exit code {proc.returncode}"
        result = {
            "status": "failed",
            "elapsed": elapsed,
            "world_dir": str(world_dir) if world_dir.exists() else "",
            "error": error_msg,
        }

    print(json.dumps(result, ensure_ascii=False))
    if result["status"] == "failed":
        sys.exit(1)


def _find_latest_run(runs_dir: Path, my_pid: int) -> Path | None:
    """找到 outputs/runs/YYYY-MM-DD/ 里属于本进程的最新 run 目录。"""
    if not runs_dir.exists():
        return None
    today = runs_dir / time.strftime("%Y-%m-%d")
    if not today.exists():
        return None
    # 按修改时间倒序，找目录名包含本进程 PID 的
    batches = sorted(today.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for batch in batches:
        if not batch.is_dir():
            continue
        runs = sorted(batch.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for run in runs:
            if run.is_dir() and f"_{my_pid}" in run.name:
                return run
    # fallback: 找最新的完整 run
    for batch in batches:
        if not batch.is_dir():
            continue
        for run in sorted(batch.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if run.is_dir() and (run / "simulation_dataset.json").exists():
                return run
    return None


if __name__ == "__main__":
    main()
