#!/usr/bin/env python3
"""
Phase 1→3 Pipeline Smoke — 跑 Phase1-3 完整管线到 parser 输出 simulation_dataset.json。

用途：
  - 单独验证 Phase 3 parser 产出是否完整
  - 不调 Phase 4，不生成 final_report
  - 包含白盒系统（run_dir、RuntimeLogger、run_meta、artifact_check）
  - 产出的 simulation_dataset.json 可直接给产品端验证

用法：
    .venv/bin/python tests/midPhaseTest.py seeds/test8.txt

与 main.py 的区别：
  - Phase 1-2-3 tick simulation 逻辑相同
  - 不调 Phase 4 report_agent
  - 输出: parser.py → simulation_dataset.json（含风险判定/拐点/立场矩阵/实体/传播者信息）
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

_proj = Path(__file__).resolve().parent.parent
if str(_proj) not in sys.path:
    sys.path.insert(0, str(_proj))

import config
from src.llm_client import init_llm_client
from src.phase4.paths import build_run_paths
from src.whitebox.run_meta import write_run_meta, write_whitebox_artifacts
from src.utils.runtime_logger import get_runtime_logger


def run_phase1(seed_file: str):
    """Phase 1 实体提取（LLM）。"""
    from src.phase1 import extract_entities_from_file
    return extract_entities_from_file(seed_file)


def run_phase2(extraction_output):
    """Phase 2 社交拓扑构建。"""
    from src.phase2 import build_topology_from_extraction
    return build_topology_from_extraction(extraction_output)


def run_phase3_tick_simulation(extraction_output, phase2_output, seed_text):
    """Phase 3 tick 模拟。"""
    from src.phase3 import SimulationEngine
    engine = SimulationEngine(extraction_output, phase2_output, seed_text)
    tick_logs = engine.run_simulation(max_ticks=config.MAX_TICKS)
    x_t_sequence = engine.get_x_t_sequence()
    return tick_logs, x_t_sequence


def run_phase3_parser(extraction_output, phase2_output, tick_logs, x_t_sequence):
    """
    Phase 3 Parser Aggregation — 新路径的核心。

    调用 SimulationDatasetParser.parse()，其内部消费所有 Phase3 模块:
      - parser.py              → 编排
      - risk_analyzer.py       → 受众模式 / 风险判定 / 信号 / 风险类型
      - inflection_detector.py → 拐点检测
      - stance_analyzer.py     → 立场矩阵 + 最大负向迁移

    返回结构化 simulation_dataset（含 risk_verdict、inflection_points、agent_stance_matrix）。
    """
    from src.phase3.parser import SimulationDatasetParser
    parser = SimulationDatasetParser()
    dataset = parser.parse(
        extraction_output,
        phase2_output,
        tick_logs,
        x_t_sequence,
    )
    return dataset


def main():
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <seed-file>")
        sys.exit(1)

    seed_file = Path(sys.argv[1]).resolve()
    if not seed_file.exists():
        print(f"错误: {seed_file} 不存在")
        sys.exit(1)

    seed_text = seed_file.read_text(encoding="utf-8")
    print(f"[新路径] 种子: {seed_file.name} ({len(seed_text)} chars)")

    init_llm_client()

    # 白盒：构建运行目录
    run_context = build_run_paths(seed_file)
    run_dir = run_context["run_dir"]
    logger = get_runtime_logger()
    logger.configure(run_dir=run_dir)
    started_at = datetime.now().isoformat()
    write_run_meta(run_context, seed_file=seed_file, status="running", started_at=started_at)

    # Phase 1
    logger.log_phase_start("phase1_extraction")
    print("[Phase 1] 实体提取...")
    t1 = time.time()
    extraction_output = run_phase1(str(seed_file))
    t1 = time.time() - t1
    logger.log_phase_end("phase1_extraction", elapsed=t1)
    print(f"  √ {t1:.1f}s")

    # Phase 2
    logger.log_phase_start("phase2_topology")
    print("[Phase 2] 社交拓扑构建...")
    t2 = time.time()
    phase2_output = run_phase2(extraction_output)
    t2 = time.time() - t2
    logger.log_phase_end("phase2_topology", elapsed=t2)
    print(f"  √ {t2:.1f}s")

    # Phase 3 tick simulation
    logger.log_phase_start("phase3_tick_simulation")
    print("[Phase 3] 多轮涌现推演...")
    t3 = time.time()
    tick_logs, x_t_sequence = run_phase3_tick_simulation(
        extraction_output, phase2_output, seed_text,
    )
    t3 = time.time() - t3
    logger.log_phase_end("phase3_tick_simulation", elapsed=t3)
    print(f"  √ {t3:.1f}s | {len(tick_logs)} ticks | x(t): {[round(x,2) for x in x_t_sequence]}")

    # Phase 3 parser aggregation（新路径核心）
    logger.log_phase_start("phase3_parser")
    print("[Phase 3 Parser] 聚合分析（消费所有 Phase3 模块）...")
    t4 = time.time()
    dataset = run_phase3_parser(
        extraction_output, phase2_output, tick_logs, x_t_sequence,
    )
    t4 = time.time() - t4
    logger.log_phase_end("phase3_parser", elapsed=t4)
    print(f"  √ {t4:.2f}s")

    # 输出摘要
    sim = dataset["simulation_result"]
    rv = sim["risk_verdict"]
    rt = sim["risk_type_classification"]
    print(f"\n  风险等级: {rv['level']} ({rv['label']})")
    print(f"  风险类型: {rt['primary_types']}")
    print(f"  拐点数量: {len(sim['inflection_points'])}")
    print(f"  最终 x(t): {sim['final_x']}")
    print(f"  极化指数: {sim['final_polarization_index']:.4f}")

    # 保存 simulation_dataset（结构化目录内）
    dataset_path = run_dir / "simulation_dataset.json"
    dataset_path.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n✅ simulation_dataset 已保存: {dataset_path}")

    # 白盒：验证产物完整性
    logger.log_phase_start("whitebox_artifacts")
    write_whitebox_artifacts(run_context)
    logger.log_phase_end("whitebox_artifacts", elapsed=0)

    # 白盒：写入运行成功标记
    write_run_meta(run_context, seed_file=seed_file, status="success", started_at=started_at)

    total = t1 + t2 + t3 + t4
    print(f"\n总耗时: {total:.1f}s")

if __name__ == "__main__":
    main()
