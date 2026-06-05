#!/usr/bin/env python3
"""
New Phase 3 Pipeline — 独立进程，消费所有 Phase3 模块。

用法:
    .venv/bin/python tools/run_phase3_new.py seeds/test8.txt

与 main.py 的区别:
  - Phase 1-2-3 tick simulation 逻辑相同
  - 不调 Phase 4 report_agent，改调 Phase3 模块
  - 输出: parser.py → simulation_dataset.json（含风险判定/拐点/立场矩阵）
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_proj = Path(__file__).resolve().parent.parent
if str(_proj) not in sys.path:
    sys.path.insert(0, str(_proj))

import config
from src.llm_client import init_llm_client


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

    # Phase 1
    print("[Phase 1] 实体提取...")
    t1 = time.time()
    extraction_output = run_phase1(str(seed_file))
    t1 = time.time() - t1
    print(f"  √ {t1:.1f}s")

    # Phase 2
    print("[Phase 2] 社交拓扑构建...")
    t2 = time.time()
    phase2_output = run_phase2(extraction_output)
    t2 = time.time() - t2
    print(f"  √ {t2:.1f}s")

    # Phase 3 tick simulation
    print("[Phase 3] 多轮涌现推演...")
    t3 = time.time()
    tick_logs, x_t_sequence = run_phase3_tick_simulation(
        extraction_output, phase2_output, seed_text,
    )
    t3 = time.time() - t3
    print(f"  √ {t3:.1f}s | {len(tick_logs)} ticks | x(t): {[round(x,2) for x in x_t_sequence]}")

    # Phase 3 parser aggregation（新路径核心）
    print("[Phase 3 Parser] 聚合分析（消费所有 Phase3 模块）...")
    t4 = time.time()
    dataset = run_phase3_parser(
        extraction_output, phase2_output, tick_logs, x_t_sequence,
    )
    t4 = time.time() - t4
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

    # 保存
    out_dir = _proj / "outputs" / "new_phase3"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    out_path = out_dir / f"simulation_dataset_{Path(seed_file).stem}_{ts}.json"
    out_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n输出: {out_path}")
    print("[新路径] 完成")


if __name__ == "__main__":
    main()
