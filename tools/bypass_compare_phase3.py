#!/usr/bin/env python3
"""
Phase 3 Bypass Comparison — 比较旧路径（report_agent 内联函数）与新路径（Phase3 独立模块）的输出。

用法:
    .venv/bin/python tools/bypass_compare_phase3.py seeds/test8.txt

流程:
  1. 运行 Phase 1 (实体提取, LLM) — 共用
  2. 运行 Phase 2 (社交拓扑) — 共用
  3. 运行 Phase 3 Tick Simulation — 共用
  4. 分两条路径分析同一组数据:
     - 旧路径: report_agent 内联函数 (assess_risk, determine_audience_mode, ...)
     - 新路径: SimulationDatasetParser
       (phase3.parser + risk_analyzer + inflection_detector + stance_analyzer)
  5. 按维度对比输出

注意:
  - Phase 1 需要 LLM API（和 main.py 一样），只会跑一次
  - 新旧路径都是纯计算，不消耗 token
  - 新路径调用 parser.parse()，其内部实例化 RiskAnalyzer / InflectionDetector / StanceAnalyzer
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

# 确保项目根在 sys.path 中
_proj = Path(__file__).resolve().parent.parent
if str(_proj) not in sys.path:
    sys.path.insert(0, str(_proj))

# ── 项目初始化 ──────────────────────────────────────────────
import config
from src.llm_client import init_llm_client

# ── 旧路径（Phase 4 report_agent 内联函数）──────────────
# 这些函数原本在 report_agent.py 中被 Phase 4 的 generate_report_with_llm 调用。
# 新路径的 Phase3 模块是它们的独立重建，功能等价。
from src.phase4.report_agent import (
    assess_risk as old_assess_risk,
    determine_audience_mode as old_determine_audience,
    identify_inflection_points as old_identify_inflection,
    select_primary_risk_types as old_select_risk_types,
)
from src.schemas import RISK_LEVEL_LABELS, RISK_TYPE_LABELS


def run_phase1(seed_file: str) -> Any:
    """执行 Phase 1 实体提取（复用 main.py 的函数）。"""
    from src.phase1 import extract_entities_from_file
    return extract_entities_from_file(seed_file)


def run_phase2(extraction_output: Any) -> Any:
    """执行 Phase 2 社交拓扑构建（复用 main.py 的函数）。"""
    from src.phase2 import build_topology_from_extraction
    return build_topology_from_extraction(extraction_output)


def run_phase3_tick_simulation(
    extraction_output: Any,
    phase2_output: Any,
    seed_text: str,
) -> tuple[list, list[float]]:
    """执行 Phase 3 tick 模拟（复用 main.py 的函数）。"""
    from src.phase3 import SimulationEngine
    engine = SimulationEngine(extraction_output, phase2_output, seed_text)
    tick_logs = engine.run_simulation(max_ticks=config.MAX_TICKS)
    x_t_sequence = engine.get_x_t_sequence()
    return tick_logs, x_t_sequence


# ── 旧路径收集 ──────────────────────────────────────────────

def _collect_old_results(
    extraction_output: Any,
    phase2_output: Any,
    tick_logs: list,
    x_t_sequence: list[float],
) -> dict[str, Any]:
    """
    旧路径：调用 report_agent 的内联函数收集分析结果。

    这些函数原本是 Phase 4 报告生成流程中的纯计算步骤。
    现在与 Phase 3 独立模块作 bypass 对比验证。
    """
    audience_mode = old_determine_audience(extraction_output)
    risk_level, risk_basis = old_assess_risk(
        x_t_sequence, tick_logs,
        extraction_output=extraction_output,
    )
    risk_types = old_select_risk_types(audience_mode, risk_basis, tick_logs)
    inflection_points = old_identify_inflection(tick_logs, phase2_output)

    # 旧路径的 max_negative_shift 在 assess_risk 内部计算，不暴露。
    # 用原文记录，并在新路径侧获取可比的值
    rlv = risk_level.value if hasattr(risk_level, 'value') else str(risk_level)
    amv = audience_mode.value if hasattr(audience_mode, 'value') else str(audience_mode)

    return {
        "risk_level": rlv,
        "risk_level_label": RISK_LEVEL_LABELS.get(rlv, str(risk_level)),
        "risk_basis": risk_basis,
        "audience_mode": amv,
        "risk_types": risk_types,
        "risk_type_labels": [RISK_TYPE_LABELS.get(rt, rt) for rt in risk_types],
        "inflection_count": len(inflection_points),
    }


# ── 新路径收集（消费所有 Phase3 模块）────────────────────

def _collect_new_results(
    extraction_output: Any,
    phase2_output: Any,
    tick_logs: list,
    x_t_sequence: list[float],
) -> dict[str, Any]:
    """
    新路径：使用 Phase3 独立模块分析同一组数据。

    消费以下 Phase3 模块:
      - parser.py              → SimulationDatasetParser（编排）
      - risk_analyzer.py        → RiskAnalyzer（受众模式/风险判定/信号/风险类型）
      - inflection_detector.py  → InflectionDetector（拐点检测）
      - stance_analyzer.py      → StanceAnalyzer（立场矩阵 + max_negative_shift）
    """
    from src.phase3.parser import SimulationDatasetParser
    from src.phase3.stance_analyzer import StanceAnalyzer

    # SimulationDatasetParser 内部实例化 RiskAnalyzer / InflectionDetector / StanceAnalyzer
    parser = SimulationDatasetParser()
    dataset = parser.parse(
        extraction_output,
        phase2_output,
        tick_logs,
        x_t_sequence,
    )

    result = dataset["simulation_result"]
    risk_verdict = result["risk_verdict"]
    risk_type = result["risk_type_classification"]

    # max_negative_shift 需要额外从 StanceAnalyzer 获取
    stance = StanceAnalyzer()
    max_shift = stance.max_negative_shift(tick_logs)

    return {
        "risk_level": risk_verdict["level"],
        "risk_level_label": risk_verdict["label"],
        "risk_basis": risk_verdict.get("basis_text", ""),
        "audience_mode": dataset.get("run_info", {}).get("audience_mode", ""),
        "risk_types": risk_type.get("primary_types", []),
        "risk_type_labels": risk_type.get("type_labels", []),
        "inflection_count": len(result.get("inflection_points", [])),
        "max_negative_shift": max_shift if max_shift is not None else 0.0,
    }


# ── 对比 ────────────────────────────────────────────────────

def compare_dimensions(old: dict, new: dict) -> list[dict]:
    """逐维度对比新旧路径输出。"""
    comps = []

    comps.append({
        "dimension": "risk_level",
        "old_value": old["risk_level"],
        "new_value": new["risk_level"],
        "match": old["risk_level"] == new["risk_level"],
        "detail": "风险等级（high / medium / low）",
    })
    comps.append({
        "dimension": "audience_mode",
        "old_value": old["audience_mode"],
        "new_value": new["audience_mode"],
        "match": old["audience_mode"] == new["audience_mode"],
        "detail": "受众模式判定",
    })
    comps.append({
        "dimension": "primary_risk_types",
        "old_value": old["risk_types"],
        "new_value": new["risk_types"],
        "match": sorted(old["risk_types"]) == sorted(new["risk_types"]),
        "detail": "主要风险类型列表（顺序无关）",
    })
    comps.append({
        "dimension": "risk_type_labels",
        "old_value": old["risk_type_labels"],
        "new_value": new["risk_type_labels"],
        "match": sorted(old["risk_type_labels"]) == sorted(new["risk_type_labels"]),
        "detail": "风险类型中文标签（顺序无关）",
    })
    comps.append({
        "dimension": "inflection_count",
        "old_value": old["inflection_count"],
        "new_value": new["inflection_count"],
        "match": old["inflection_count"] == new["inflection_count"],
        "detail": "拐点数量",
    })
    old_ms = round(old.get("max_negative_shift", 0) or 0, 4)
    new_ms = round(new.get("max_negative_shift", 0) or 0, 4)
    comps.append({
        "dimension": "max_negative_shift",
        "old_value": old_ms,
        "new_value": new_ms,
        "match": abs(old_ms - new_ms) < 0.001,
        "detail": "最大群体负向迁移量（旧路径不暴露此值，新路径从 StanceAnalyzer 获取）",
    })
    # x_t_sequence 不走对比 —— 这是 Phase 3 tick 模拟的输出，新旧路径共用同一份数据
    return comps


def print_report(comparisons: list[dict]) -> None:
    """打印对比报告。"""
    print()
    print("=" * 70)
    print("  Phase 3 Bypass 对比报告")
    print("  旧路径: report_agent 内联函数")
    print("  新路径: Phase3 独立模块（parser + risk_analyzer + inflection_detector + stance_analyzer）")
    print("=" * 70)
    all_pass = True
    for c in comparisons:
        icon = "✅" if c["match"] else "❌"
        if not c["match"]:
            all_pass = False
        print(f"\n  {icon} {c['dimension']}")
        print(f"     旧: {c['old_value']}")
        print(f"     新: {c['new_value']}")
        print(f"     说明: {c['detail']}")
    print()
    print("-" * 70)
    if all_pass:
        print("  ✅ 所有维度通过 — 新旧路径语义等价")
    else:
        print("  ❌ 存在不一致维度")
    print("=" * 70)
    print()


def main():
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <seed-file>")
        sys.exit(1)

    seed_file = Path(sys.argv[1]).resolve()
    if not seed_file.exists():
        print(f"错误: {seed_file} 不存在")
        sys.exit(1)

    seed_text = seed_file.read_text(encoding="utf-8")
    print(f"种子: {seed_file.name} ({len(seed_text)} chars)")

    # 初始化 LLM 客户端（Phase 1 需要）
    init_llm_client()

    # ── Phase 1 ──────────────────────────────────────────────
    print("\n[Phase 1] 实体提取（LLM）...")
    t1 = time.time()
    extraction_output = run_phase1(str(seed_file))
    t1 = time.time() - t1
    print(f"  √ {t1:.1f}s")

    # ── Phase 2 ──────────────────────────────────────────────
    print("[Phase 2] 社交拓扑构建...")
    t2 = time.time()
    phase2_output = run_phase2(extraction_output)
    t2 = time.time() - t2
    print(f"  √ {t2:.1f}s")

    # ── Phase 3 Tick Simulation（共用）───────────────────
    print("[Phase 3] 多轮涌现推演...")
    t3 = time.time()
    tick_logs, x_t_sequence = run_phase3_tick_simulation(
        extraction_output, phase2_output, seed_text,
    )
    t3 = time.time() - t3
    print(f"  √ {t3:.1f}s | {len(tick_logs)} ticks | x(t): {[round(x,2) for x in x_t_sequence]}")

    # ── 双路分析 ──────────────────────────────────────────
    print("[对比] 旧路径 vs 新路径（纯计算，无 LLM）...")
    t4 = time.time()
    old_results = _collect_old_results(extraction_output, phase2_output, tick_logs, x_t_sequence)
    new_results = _collect_new_results(extraction_output, phase2_output, tick_logs, x_t_sequence)
    t4 = time.time() - t4
    print(f"  √ {t4:.2f}s")

    comparisons = compare_dimensions(old_results, new_results)
    print_report(comparisons)

    # ── 保存 ──────────────────────────────────────────────
    out = {
        "seed": str(seed_file),
        "timing_sec": {
            "phase1": round(t1, 1),
            "phase2": round(t2, 1),
            "phase3": round(t3, 1),
            "compare": round(t4, 2),
        },
        "old_path": old_results,
        "new_path": new_results,
        "comparisons": comparisons,
        "all_match": all(c["match"] for c in comparisons),
    }
    out_path = _proj / "outputs" / f"bypass_compare_{seed_file.stem}_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"结果已保存: {out_path}")


if __name__ == "__main__":
    main()
