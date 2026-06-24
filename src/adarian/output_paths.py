"""
output_paths.py — 输出路径策略模块（OCP 模式）。

职责：决定运行产物的写入位置和目录结构。
扩展：新增写入策略只需实现 RunPaths 抽象类，不修改现有代码。

策略选择由 PARALLEL_MODE 环境变量决定：
  未设置 / false  → DefaultRunPaths（现有行为）
  true           → ParallelRunPaths（平行世界调度器）
"""

from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from adarian import config


class RunPaths(ABC):
    """输出路径策略基类。"""

    def __init__(self, seed_file: Path):
        self.seed_file = seed_file

    @abstractmethod
    def build(self) -> dict:
        """创建运行目录并返回所有产出路径。

        Returns:
            dict 包含 batch_id / batch_dir / run_id / run_dir / seed_copy / outputs
        """
        ...


class DefaultRunPaths(RunPaths):
    """默认策略：与现有 build_run_paths 行为完全一致。

    目录结构：outputs/runs/YYYY-MM-DD/{seed}_{timestamp}/run_{microsec}_{PID}/
    """

    def build(self) -> dict:
        now = datetime.now()
        date_dir = now.strftime("%Y-%m-%d")
        batch_id = f"{self.seed_file.stem}_{now.strftime('%H%M%S')}"
        run_id = f"run_{now.strftime('%f')}_{os.getpid()}"
        batch_dir = config.OUTPUTS_DIR / "runs" / date_dir / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        run_dir = batch_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=False)

        seed_copy = run_dir / "seed_input.txt"
        shutil.copyfile(self.seed_file, seed_copy)

        outputs = {
            "entities": run_dir / "entities_and_relations.json",
            "social_graph": run_dir / "social_graph.json",
            "tick_logs": run_dir / "tick_logs.json",
            "simulation_dataset": run_dir / "simulation_dataset.json",
            "final_report_json": run_dir / "final_report.json",
            "final_report_md": run_dir / "final_report.md",
            "run_log": run_dir / "run.log",
            "run_meta": run_dir / "run_meta.json",
        }

        return {
            "batch_id": batch_id,
            "batch_dir": batch_dir,
            "run_id": run_id,
            "run_dir": run_dir,
            "seed_copy": seed_copy,
            "outputs": outputs,
        }


class ParallelRunPaths(RunPaths):
    """平行世界策略：由调度器指定输出位置。

    目录结构：{batch_dir}/{world_name}/

    调度器通过环境变量传入：
      PARALLEL_BATCH_DIR  — 批次根目录
      PARALLEL_WORLD_NAME — 本世界名称（如 world_0）
    """

    def __init__(self, seed_file: Path, batch_dir: str | Path, world_name: str):
        super().__init__(seed_file)
        self.batch_dir = Path(batch_dir)
        self.world_name = world_name

    def build(self) -> dict:
        run_dir = self.batch_dir / self.world_name
        run_dir.mkdir(parents=True, exist_ok=True)

        seed_copy = run_dir / "seed_input.txt"
        try:
            shutil.copyfile(self.seed_file, seed_copy)
        except shutil.SameFileError:
            pass

        outputs = {
            "entities": run_dir / "entities_and_relations.json",
            "social_graph": run_dir / "social_graph.json",
            "tick_logs": run_dir / "tick_logs.json",
            "simulation_dataset": run_dir / "simulation_dataset.json",
            "final_report_json": run_dir / "final_report.json",
            "final_report_md": run_dir / "final_report.md",
            "run_log": run_dir / "run.log",
            "run_meta": run_dir / "run_meta.json",
        }

        return {
            "batch_id": self.world_name,
            "batch_dir": self.batch_dir,
            "run_id": self.world_name,
            "run_dir": run_dir,
            "seed_copy": seed_copy,
            "outputs": outputs,
        }


# ── 工厂 ──────────────────────────────────────────────────────────

def create_run_paths(seed_file: Path) -> RunPaths:
    """根据环境变量选择输出路径策略。

    策略选择（按优先级）：
      1. PARALLEL_MODE=true  → ParallelRunPaths
      2. 否则                → DefaultRunPaths
    """
    parallel_mode = os.environ.get("PARALLEL_MODE", "").lower() in ("true", "1", "yes")
    if parallel_mode:
        batch_dir = os.environ.get("PARALLEL_BATCH_DIR", "")
        world_name = os.environ.get("PARALLEL_WORLD_NAME", "world_0")
        if not batch_dir:
            raise ValueError("PARALLEL_MODE=true 但未设置 PARALLEL_BATCH_DIR")
        return ParallelRunPaths(seed_file, batch_dir, world_name)
    return DefaultRunPaths(seed_file)
