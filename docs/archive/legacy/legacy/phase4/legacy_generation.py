"""
Legacy Phase 4 — 旧生成全路径（pre-v1.3.1 归档）。

v1.3.1 归档说明：
  以下函数原位于 src/phase4/report_agent.py，提供旧路径 LLM 报告生成。
  旧路径的 generate_report_with_llm / generate_fallback_report / run_old_path
  全部依赖旧计算函数，不进入产品主流程。
"""

import json
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

import config
from src.llm_client import get_llm_client
from src.schemas import (
    AudienceMode, EntityExtractionOutput, EmotionTrajectory,
    InflectionPoint, Phase2Output, Phase4Output, RiskLevel, TickLog,
    RISK_LEVEL_LABELS, RISK_TYPE_LABELS,
)
from src.phase4.report_narrative import (
    build_full_report_context as _build_full_report_context_impl,
    generate_report_with_llm_narrative,
)

from .legacy_analytics import (
    assess_risk,
    determine_audience_mode,
    identify_inflection_points,
    risk_level_label_for,
    select_primary_risk_types,
    _build_code_owned_agent_stance_matrix,
    _build_phase4_output,
    _format_code_owned_agent_stance_matrix,
    _format_code_owned_inflection_points,
    _risk_type_labels,
    _max_negative_shift_from_stance_matrix,
    _sensitive_prior_risk_types,
)
from .legacy_markdown import generate_markdown_report

console = Console()


# Module-level cache for legacy / v1.2.x path LLM markdown (diagnostic only).
_llm_generated_markdown: str = ""


# ── compatibility facade ────────────────────────────────────────

def build_full_report_context(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
) -> str:
    """Compatibility façade for the extracted narrative context builder."""
    return _build_full_report_context_impl(
        extraction_output,
        tick_logs,
        x_t_sequence,
        phase2_output=phase2_output,
        format_agent_stance_matrix=_format_code_owned_agent_stance_matrix,
        identify_inflection_points=identify_inflection_points,
        format_inflection_points=_format_code_owned_inflection_points,
    )


# ── LLM generation ──────────────────────────────────────────────

def generate_report_with_llm(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
) -> Phase4Output:
    """使用 LLM 生成报告（旧路径）

    v1.3.1: clean contract block / parse path require simulation_dataset.
    Legacy path synthesizes one from legacy analytics outputs.
    """
    if phase2_output is None:
        from src.phase3 import load_phase2_output
        phase2_output = load_phase2_output()

    from src.phase4.report_agent import (
        _build_code_owned_report_contract_block,
        parse_llm_report_response,
    )

    # Synthesize a minimal simulation_dataset from legacy analytics so the
    # clean consumer-only contract block / parse path can still be driven.
    audience_mode = determine_audience_mode(extraction_output)
    risk_level, risk_assessment = assess_risk(
        x_t_sequence, tick_logs, extraction_output=extraction_output,
    )
    primary_risk_types = select_primary_risk_types(
        audience_mode, risk_assessment, tick_logs,
    )
    inflection_points = identify_inflection_points(tick_logs, phase2_output)
    emotion_trajectory = [
        EmotionTrajectory(
            tick=tl.tick,
            mean_stance=tl.global_metrics.mean_stance,
            std_stance=tl.global_metrics.std_stance,
            polarization_index=tl.global_metrics.polarization_index,
            key_event="",
        )
        for tl in tick_logs
    ]
    from src.schemas import RISK_TYPE_LABELS as _RTL
    risk_type_labels = [_RTL[t] for t in primary_risk_types if t in _RTL]
    audience_mode_str = (
        audience_mode.value if hasattr(audience_mode, "value") else str(audience_mode)
    )
    risk_level_str = (
        risk_level.value if hasattr(risk_level, "value") else str(risk_level)
    )
    simulation_dataset = {
        "run_info": {"audience_mode": audience_mode_str},
        "simulation_result": {
            "risk_verdict": {
                "level": risk_level_str,
                "label": "",
                "basis_text": risk_assessment,
                "signals": {},
            },
            "risk_type_classification": {
                "primary_types": primary_risk_types,
                "type_labels": risk_type_labels,
            },
            "inflection_points": [
                {
                    "tick": p.tick,
                    "agent_id": p.agent_id,
                    "group_name": p.group_name,
                    "pivotal_comment": p.pivotal_comment,
                    "impact_description": p.impact_description,
                }
                for p in inflection_points
            ],
            "emotion_trajectory": [
                {
                    "tick": et.tick,
                    "mean_stance": et.mean_stance,
                    "std_stance": et.std_stance,
                    "polarization_index": et.polarization_index,
                    "key_event": et.key_event,
                }
                for et in emotion_trajectory
            ],
            "agent_stance_matrix": [],
        },
    }

    phase4_output, markdown = generate_report_with_llm_narrative(
        extraction_output,
        tick_logs,
        x_t_sequence,
        phase2_output=phase2_output,
        build_report_context=build_full_report_context,
        build_code_owned_contract_block=_build_code_owned_report_contract_block,
        parse_llm_report_response=parse_llm_report_response,
        get_llm_client_func=get_llm_client,
        simulation_dataset=simulation_dataset,
    )
    return phase4_output


def generate_fallback_report(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
) -> Phase4Output:
    """生成自动报告（当 LLM 失败时）"""
    if phase2_output is None:
        from src.phase3 import load_phase2_output
        phase2_output = load_phase2_output()

    inflection_points = identify_inflection_points(tick_logs, phase2_output)

    risk_level, risk_assessment = assess_risk(
        x_t_sequence,
        tick_logs,
        extraction_output=extraction_output,
    )

    emotion_trajectory = [
        EmotionTrajectory(
            tick=log.tick,
            mean_stance=log.global_metrics.mean_stance,
            std_stance=log.global_metrics.std_stance,
            polarization_index=log.global_metrics.polarization_index,
            key_event=f"Agent #{max(log.entries, key=lambda e: abs(e.stance_delta)).agent_id}: {max(log.entries, key=lambda e: abs(e.stance_delta)).comment[:30]}...",
        )
        for log in tick_logs if log.entries
    ]

    event_entities_str = ", ".join([e.name for e in extraction_output.event_entities])
    spreaders_str = ", ".join([s.group_name for s in extraction_output.opinion_spreaders])
    stakeholder_map = f"事件实体: {event_entities_str} | 传播者: {spreaders_str}"

    return _build_phase4_output(
        extraction_output=extraction_output,
        tick_logs=tick_logs,
        x_t_sequence=x_t_sequence,
        emotion_trajectory=emotion_trajectory,
        inflection_points=inflection_points,
        risk_level=risk_level,
        risk_assessment=risk_assessment,
        stakeholder_map=stakeholder_map,
    )


# ── legacy markdown save (diagnostic only) ──────────────────────

def save_markdown_report(
    phase4_output: Phase4Output,
    extraction_output: EntityExtractionOutput,
    output_path: Path,
):
    """Save legacy fallback markdown (diagnostic only).

    Falls back to ``_llm_generated_markdown`` (the module-level cache) if
    it contains enough content AND has the required five-chapter structure;
    otherwise builds a fresh legacy markdown via
    ``legacy.phase4.legacy_markdown.generate_markdown_report``.
    """
    from .legacy_markdown import generate_markdown_report
    from src.phase4.report_normalizer import (
        _has_required_five_chapter_sections,
        _normalize_saved_markdown,
    )

    markdown = _llm_generated_markdown
    if not markdown or len(markdown) < 100 or not _has_required_five_chapter_sections(markdown):
        markdown = generate_markdown_report(phase4_output, extraction_output)

    md_content = _normalize_saved_markdown(markdown, phase4_output)
    if not _has_required_five_chapter_sections(md_content):
        md_content = _normalize_saved_markdown(
            generate_markdown_report(phase4_output, extraction_output),
            phase4_output,
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)


# ── dual-path wrappers ──────────────────────────────────────────

def run_old_path(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output,
) -> Phase4Output:
    """旧版 Phase 4 消费路径（baseline）。"""
    risk_level, risk_assessment = assess_risk(
        x_t_sequence, tick_logs, extraction_output=extraction_output,
    )
    inflection_points = identify_inflection_points(tick_logs, phase2_output)
    emotion_trajectory = []
    for tl in tick_logs:
        emotion_trajectory.append(EmotionTrajectory(
            tick=tl.tick,
            mean_stance=tl.global_metrics.mean_stance,
            std_stance=tl.global_metrics.std_stance,
            polarization_index=tl.global_metrics.polarization_index,
            key_event="",
        ))
    stakeholder_map = ""
    return _build_phase4_output(
        extraction_output, tick_logs, x_t_sequence,
        emotion_trajectory, inflection_points, risk_level, risk_assessment, stakeholder_map,
    )


def run_new_path(
    simulation_dataset: dict,
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
) -> Phase4Output:
    """新版 Phase 4 消费路径（candidate）。"""
    from src.phase4.report_agent import _build_phase4_output_from_simulation_dataset
    return _build_phase4_output_from_simulation_dataset(
        simulation_dataset,
        extraction_output,
        tick_logs,
        x_t_sequence,
    )


# ── utilities ───────────────────────────────────────────────────

def load_tick_logs(tick_dir: Path = None) -> List[TickLog]:
    """加载 tick 日志"""
    tick_dir = tick_dir or config.TICK_LOGS_DIR

    tick_logs = []
    for tick_file in sorted(tick_dir.glob("tick_*.json"), key=lambda p: int(p.stem.split("_")[1])):
        with open(tick_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            tick_logs.append(TickLog(**data))

    return tick_logs
