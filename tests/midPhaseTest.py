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
    logger = get_runtime_logger()

    # 白盒：构建运行目录
    run_context = build_run_paths(seed_file)
    run_dir = run_context["run_dir"]
    logger.configure(run_dir=run_dir)
    started_at = datetime.now().isoformat()
    write_run_meta(run_context, seed_file=seed_file, status="running", started_at=started_at)

    logger.info("[新路径] 种子: %s (%d chars)", seed_file.name, len(seed_text))
    init_llm_client()

    # Phase 1
    logger.log_phase_start("phase1_extraction")
    logger.info("[Phase 1] 实体提取...")
    t1 = time.time()
    extraction_output = run_phase1(str(seed_file))
    t1 = time.time() - t1
    logger.log_phase_end("phase1_extraction", elapsed=t1)
    logger.info("  √ %.1fs", t1)

    # Phase 2
    logger.log_phase_start("phase2_topology")
    logger.info("[Phase 2] 社交拓扑构建...")
    t2 = time.time()
    phase2_output = run_phase2(extraction_output)
    t2 = time.time() - t2
    logger.log_phase_end("phase2_topology", elapsed=t2)
    logger.info("  √ %.1fs", t2)

    # Phase 3 tick simulation
    logger.log_phase_start("phase3_tick_simulation")
    logger.info("[Phase 3] 多轮涌现推演...")
    t3 = time.time()
    tick_logs, x_t_sequence = run_phase3_tick_simulation(
        extraction_output, phase2_output, seed_text,
    )
    t3 = time.time() - t3
    logger.log_phase_end("phase3_tick_simulation", elapsed=t3)
    x_str = ", ".join(f"{x:.2f}" for x in x_t_sequence)
    logger.info("  √ %.1fs | %d ticks | x(t): [%s]", t3, len(tick_logs), x_str)

    # Phase 3 parser aggregation
    logger.log_phase_start("phase3_parser")
    logger.info("[Phase 3 Parser] 聚合分析...")
    t4 = time.time()
    dataset = run_phase3_parser(
        extraction_output, phase2_output, tick_logs, x_t_sequence,
    )
    t4 = time.time() - t4
    logger.log_phase_end("phase3_parser", elapsed=t4)
    logger.info("  √ %.2fs", t4)

    # 输出摘要
    sim = dataset["simulation_result"]
    rv = sim["risk_verdict"]
    rt = sim["risk_type_classification"]
    logger.info("")
    logger.info("  风险等级: %s (%s)", rv["level"], rv["label"])
    logger.info("  风险类型: %s", rt["primary_types"])
    logger.info("  拐点数量: %d", len(sim["inflection_points"]))
    logger.info("  最终 x(t): %s", sim["final_x"])
    logger.info("  极化指数: %.4f", sim["final_polarization_index"])

    # 保存 simulation_dataset
    dataset_path = run_dir / "simulation_dataset.json"
    dataset_path.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("")
    logger.info("✅ simulation_dataset 已保存: %s", dataset_path)

    # 白盒：验证产物完整性
    logger.log_phase_start("whitebox_artifacts")
    write_whitebox_artifacts(run_context)
    logger.log_phase_end("whitebox_artifacts", elapsed=0)

    # 白盒：写入运行成功标记
    write_run_meta(run_context, seed_file=seed_file, status="success", started_at=started_at)

    total = t1 + t2 + t3 + t4
    logger.info("")
    logger.info("总耗时: %.1fs", total)


if __name__ == "__main__":
    main()
