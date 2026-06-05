#!/usr/bin/env python3
"""
新路径全流程 — 消费 Phase3 模块的 Phase 1-4 流水线。

用法:
    .venv/bin/python tools/run_pipeline_new.py seeds/test8.txt

与 main.py 的区别:
  Phase 3 tick simulation 之后增加 Parser Aggregation 层
  Phase 4 不再调用 report_agent 内联函数，而是消费 Phase3 模块的输出

流程:
  Phase 1 (实体提取, LLM)
  → Phase 2 (拓扑构建)
  → Phase 3 (tick 模拟)
  → Phase 3 Parser (SimulationDatasetParser, 消费所有 Phase3 模块)
  → Phase 4 (报告生成, LLM, 摘掉旧模块)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

_proj = Path(__file__).resolve().parent.parent
if str(_proj) not in sys.path:
    sys.path.insert(0, str(_proj))

import config
from src.llm_client import init_llm_client, get_llm_client
from src.schemas import (
    EntityExtractionOutput, Phase2Output, TickLog,
    Phase4Output, EmotionTrajectory, RISK_LEVEL_LABELS, RISK_TYPE_LABELS,
)


# ── Phase 1-3（与 main.py 共用）─────────────────────────

def run_phase1(seed_file: str):
    from src.phase1 import extract_entities_from_file
    return extract_entities_from_file(seed_file)


def run_phase2(extraction_output):
    from src.phase2 import build_topology_from_extraction
    return build_topology_from_extraction(extraction_output)


def run_phase3_tick(extraction_output, phase2_output, seed_text):
    from src.phase3 import SimulationEngine
    engine = SimulationEngine(extraction_output, phase2_output, seed_text)
    tick_logs = engine.run_simulation(max_ticks=config.MAX_TICKS)
    x_t_sequence = engine.get_x_t_sequence()
    return tick_logs, x_t_sequence


# ── Phase 3 Parser（新路径核心）────────────────────────

def run_phase3_parser(extraction_output, phase2_output, tick_logs, x_t_sequence):
    """
    调用 SimulationDatasetParser，消费所有 Phase3 模块:
      - parser.py              → 编排
      - risk_analyzer.py       → 受众模式 / 风险 / 信号 / 风险类型
      - inflection_detector.py → 拐点检测
      - stance_analyzer.py     → 立场矩阵 + 最大负向迁移
    """
    from src.phase3.parser import SimulationDatasetParser
    parser = SimulationDatasetParser()
    return parser.parse(extraction_output, phase2_output, tick_logs, x_t_sequence)


# ── Phase 4（摘掉旧模块，消费 Phase3 输出）─────────────

def _format_agent_stance_matrix_from_parser(tick_logs, dataset) -> list[str]:
    """从 Phase3 parser 输出的 agent_stance_matrix 生成 markdown 表格。"""
    matrix = dataset["simulation_result"].get("agent_stance_matrix", [])
    if not matrix:
        return ["无可用 opinion spreader 立场矩阵。"]

    lines = [
        "以下表格是 Markdown 报告中最终立场变化的唯一数值来源；不得重算。",
        "| Agent | 群体 | 起始立场 | 结束立场 | Delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in matrix:
        lines.append(
            f"| #{row['agent_id']} | {row['group_name']} | "
            f"{row['initial_stance']:.2f} | {row['final_stance']:.2f} | "
            f"{row.get('max_delta', row['final_stance'] - row['initial_stance']):+.2f} |"
        )
    return lines


def _format_inflection_points_from_parser(dataset) -> list[str]:
    """从 Phase3 parser 输出的 inflection_points 生成 markdown 表格。"""
    points = dataset["simulation_result"].get("inflection_points", [])
    if not points:
        return [
            "本轮模拟未发现显著模拟关键变化点。",
            "Markdown 报告不得声称存在模拟关键变化点，不得使用其他阈值自行识别模拟关键变化点。",
        ]
    lines = [
        "以下表格是 Markdown 报告中模拟关键变化点的唯一来源；不得新增其他模拟关键变化点。",
        "| 轮次 | Agent | Delta |",
        "|---:|---:|---:|",
    ]
    for p in points:
        lines.append(f"| {p.get('tick', '')} | {p.get('agent_id', '')} | {p.get('delta', 0):+.2f} |")
    return lines


def build_report_context_new(
    extraction_output, tick_logs, x_t_sequence, phase2_output, dataset,
) -> str:
    """构建 LLM 报告上下文，消费 Phase3 parser 输出替代内联函数。"""
    lines = []

    # 1. 事件概要（同旧路径）
    lines.append("【事件概要】")
    lines.append(f"事件摘要：{extraction_output.event_summary}")
    lines.append(f"事件类型：{extraction_output.event_type}")

    # 2. 实体图谱（同旧路径）
    lines.append("\n【实体图谱】")
    lines.append(f"事件实体：{len(extraction_output.event_entities)} 个")
    for entity in extraction_output.event_entities:
        lines.append(f"  - {entity.name}（{entity.type}）: {entity.role}")
    lines.append(f"\n意见传播者：{len(extraction_output.opinion_spreaders)} 个")
    for s in extraction_output.opinion_spreaders:
        lines.append(f"  - {s.group_name} | 立场:{s.stance_score} | 占比:{s.estimated_percentage}%")

    # 3. 轮次 0 发言（同旧路径）
    lines.append("\n【轮次 0 事件实体发言】")
    if tick_logs:
        for entry in tick_logs[0].entries:
            if entry.comment:
                lines.append(f"  [{entry.group_name}]: {entry.comment[:80]}...")

    # 4. 模拟立场演化（从 Phase3 parser 输出的 emotion_trajectory）
    sim = dataset["simulation_result"]
    lines.append("\n【模拟立场演化数据】")
    lines.append("轮次 | 模拟立场均值 | 标准差 | 模拟极化指数 | 关键变化")
    lines.append("-" * 70)
    for et in sim.get("emotion_trajectory", []):
        lines.append(f"| {et['tick']} | {et['mean_stance']:.2f} | {et['std_stance']:.2f} | {et['polarization_index']:.2f} | {et.get('key_event', '')} |")

    # 5. 立场矩阵（从 Phase3 parser 输出，而非 inline 构建）
    lines.append("\n【立场矩阵】")
    lines.extend(_format_agent_stance_matrix_from_parser(tick_logs, dataset))

    # 6. 拐点（从 Phase3 parser 输出）
    lines.append("\n【模拟关键变化点】")
    lines.extend(_format_inflection_points_from_parser(dataset))

    # 7. 风险判定（从 Phase3 parser 输出的 risk_verdict）
    rv = sim.get("risk_verdict", {})
    rt = sim.get("risk_type_classification", {})
    lines.append("\n【风险判定】（由 Phase3 RiskAnalyzer 计算）")
    lines.append(f"风险等级: {rv.get('level', 'unknown')}")
    lines.append(f"风险标签: {rv.get('label', '')}")
    lines.append(f"风险依据: {rv.get('basis_text', '')}")
    lines.append(f"风险类型: {', '.join(rt.get('type_labels', []))}")

    # 8. x(t) 序列
    lines.append(f"\n【x(t) 序列】{' → '.join(f'{x:.2f}' for x in x_t_sequence)}")
    if x_t_sequence:
        lines.append(f"起始 x(0): {x_t_sequence[0]:.2f} → 最终 x(t): {x_t_sequence[-1]:.2f}")

    return "\n".join(lines)


def run_phase4_new(
    extraction_output, tick_logs, x_t_sequence, phase2_output, dataset,
    json_output_path=None, markdown_output_path=None,
) -> Phase4Output:
    """新 Phase 4 — 消费 Phase3 parser 输出，跳过 report_agent 内联函数。"""
    from src.phase4.report_narrative import generate_report_with_llm_narrative
    from src.phase4.report_agent import (
        _build_code_owned_report_contract_block,
        parse_llm_report_response,
        save_report,
        save_markdown_report,
    )

    # 构建上下文（使用 Phase3 parser 数据，不调内联函数）
    report_context = build_report_context_new(
        extraction_output, tick_logs, x_t_sequence, phase2_output, dataset,
    )

    phase4_output, markdown = generate_report_with_llm_narrative(
        extraction_output,
        tick_logs,
        x_t_sequence,
        phase2_output=phase2_output,
        build_report_context=lambda *a, **kw: report_context,
        build_code_owned_contract_block=_build_code_owned_report_contract_block,
        parse_llm_report_response=parse_llm_report_response,
        get_llm_client_func=get_llm_client,
    )

    if json_output_path:
        save_report(phase4_output, output_path=json_output_path)
    if markdown_output_path:
        save_markdown_report(phase4_output, extraction_output, output_path=markdown_output_path)

    return phase4_output


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
    tick_logs, x_t_sequence = run_phase3_tick(extraction_output, phase2_output, seed_text)
    t3 = time.time() - t3
    print(f"  √ {t3:.1f}s | {len(tick_logs)} ticks")

    # Phase 3 parser aggregation（新）
    print("[Phase 3 Parser] 聚合分析...")
    t3p = time.time()
    dataset = run_phase3_parser(extraction_output, phase2_output, tick_logs, x_t_sequence)
    t3p = time.time() - t3p
    rv = dataset["simulation_result"]["risk_verdict"]
    print(f"  √ {t3p:.2f}s | risk: {rv['level']} | inflection: {len(dataset['simulation_result']['inflection_points'])} pts")

    # Phase 4（消费 Phase3 输出，摘掉旧模块）
    print("[Phase 4] 报告生成（Phase3 驱动，无旧内联函数）...")
    t4 = time.time()
    out_dir = _proj / "outputs" / "new_phase3"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    prefix = f"{seed_file.stem}_{ts}"

    phase4_output = run_phase4_new(
        extraction_output, tick_logs, x_t_sequence, phase2_output, dataset,
        json_output_path=out_dir / f"{prefix}_report.json",
        markdown_output_path=out_dir / f"{prefix}_report.md",
    )
    t4 = time.time() - t4
    print(f"  √ {t4:.1f}s | risk: {phase4_output.risk_level}")

    # 保存 dataset
    ds_path = out_dir / f"{prefix}_simulation_dataset.json"
    ds_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n输出目录: {out_dir}")
    print(f"  simulation_dataset: {ds_path.name}")
    print(f"  report.json: {prefix}_report.json")
    print(f"  report.md: {prefix}_report.md")
    print("[新路径] 完成")


if __name__ == "__main__":
    main()
