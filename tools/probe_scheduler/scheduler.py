"""scheduler.py — 平行世界探针调度器。

只负责：开 N 个 Terminal 窗口，每个跑 main.py 带不同模型配置 + 输出位置环境变量。
不等待、不收集、不汇总。窗口开了就结束。

每个窗口的 main.py 会读取 PARALLEL_BATCH_DIR / PARALLEL_WORLD_NAME 环境变量，
将全部产物直接写入 batch_dir/world_N/ 下，无需 mv。
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from .probe_config import ProbeConfig, WorldConfig

import config as project_config


def run_probe(cfg: ProbeConfig) -> None:
    """执行一次探针运行：开 N 个 Terminal 窗口就跑。"""
    now = datetime.now()
    date_dir = now.strftime("%Y-%m-%d")
    batch_id = f"{cfg.batch_tag}_{now.strftime('%H%M%S')}"
    batch_dir = (
        project_config.OUTPUTS_DIR / "runs" / date_dir / batch_id
    )
    batch_dir.mkdir(parents=True, exist_ok=True)
    cfg.save_yaml(str(batch_dir / "probe_config.yaml"))

    main_py = Path(__file__).resolve().parent.parent.parent / "main.py"
    seed_abs = str(Path(cfg.seed_path).resolve())
    project_root = str(main_py.parent)
    python = sys.executable

    print(f"批次目录: {batch_dir}")
    print(f"世界数: {len(cfg.worlds)}")
    print()

    for i, wc in enumerate(cfg.worlds):
        world_name = f"world_{i}"
        from adarian.utils.net import is_internal_url
        no_proxy = f"localhost,127.0.0.1" if is_internal_url(wc.base_url) else ""

        # 单行 shell：cd + env（含 PARALLEL 输出路径）→ main.py
        # main.py 读取 PARALLEL_BATCH_DIR / PARALLEL_WORLD_NAME 后直接写到指定位置
        cmd = (
            "cd '" + project_root + "' && "
            f"export LLM_PROVIDER=qwen "
            f"QWEN_MODEL='{wc.model}' "
            f"LLM_BASE_URL='{wc.base_url}' "
            f"NO_PROXY='{no_proxy}' "
            f"no_proxy='{no_proxy}' "
            f"PARALLEL_MODE=true "
            f"PARALLEL_BATCH_DIR='{batch_dir}' "
            f"PARALLEL_WORLD_NAME='{world_name}' && "
            f"'{python}' '{main_py}' '{seed_abs}'"
        )
        subprocess.run([
            "osascript", "-e",
            'tell application "Terminal" to do script "' + cmd + '"',
        ], capture_output=True, timeout=10)

        print(f"  [{i+1}/{len(cfg.worlds)}] {wc.model}")
        time.sleep(0.1)

    print("\n全部窗口已打开。跑完后通知我汇总。")
