"""
Legacy Phase 4 — 旧计算函数（pre-v1.3.1 归档）。

v1.3.1 归档说明：
  以下函数原位于 src/phase4/report_agent.py，v1.3.0 中被 Phase3 parser 模块取代。
  保留于此供 tests/tools/dev diagnostic 使用，不进入产品主流程。
"""

from typing import Dict, List, Any

from src.schemas import (
    AudienceMode, EntityExtractionOutput, EmotionTrajectory,
    InflectionPoint, Phase2Output, Phase4Output, RiskLevel, TickLog,
    RISK_LEVEL_LABELS, RISK_TYPE_LABELS,
)

# ── keyword constants ───────────────────────────────────────────

LAW_ENFORCEMENT_KEYWORDS = ("公安", "交警", "派出所", "执法", "警方")
REGULATOR_KEYWORDS = ("市监局", "市场监督管理局", "监管部门", "食药监")
PUBLIC_MANAGEMENT_KEYWORDS = ("教育局", "卫健委", "住建局", "属地政府", "街道办")
SENSITIVE_PRIOR_RISK_TYPES = (
    "law_enforcement_trust_risk",
    "regulatory_accountability_risk",
    "local_governance_pressure_risk",
    "information_opacity_risk",
    "response_delay_risk",
    "rumor_spread_risk",
    "overseas_amplification_risk",
    "group_polarization_risk",
)


# ── helpers ─────────────────────────────────────────────────────

def risk_level_label_for(risk_level: RiskLevel) -> str:
    return RISK_LEVEL_LABELS[risk_level.value]


def _collect_audience_text(
    extraction_output: EntityExtractionOutput,
    risk_assessment: str = "",
) -> str:
    parts = [
        extraction_output.event_summary,
        extraction_output.event_type,
        risk_assessment,
    ]
    for entity in extraction_output.event_entities:
        parts.extend([
            entity.name,
            entity.role,
            entity.original_statement or "",
            entity.can_speak_reason or "",
        ])
    for spreader in extraction_output.opinion_spreaders:
        parts.extend([
            spreader.group_name,
            spreader.related_event_entity,
            spreader.description,
            spreader.communication_style,
        ])
    for relation in extraction_output.relations:
        parts.extend([relation.source, relation.target, relation.type])
    return "\n".join(part for part in parts if part)


def determine_audience_mode(
    extraction_output: EntityExtractionOutput,
    risk_assessment: str = "",
) -> AudienceMode:
    """Determine audience mode using minimal deterministic keyword rules."""
    text = _collect_audience_text(extraction_output, risk_assessment)
    if any(keyword in text for keyword in LAW_ENFORCEMENT_KEYWORDS):
        return AudienceMode.LAW_ENFORCEMENT_FACING
    if any(keyword in text for keyword in REGULATOR_KEYWORDS):
        return AudienceMode.REGULATOR_FACING
    if any(keyword in text for keyword in PUBLIC_MANAGEMENT_KEYWORDS):
        return AudienceMode.PUBLIC_MANAGEMENT_FACING
    return AudienceMode.GENERIC_GOVERNMENT


def select_primary_risk_types(
    audience_mode: AudienceMode,
    risk_assessment: str,
    tick_logs: List[TickLog],
) -> List[str]:
    """Select lightweight whitelisted risk types without a full classifier."""
    selected: List[str] = []

    def add(risk_type: str):
        if risk_type in RISK_TYPE_LABELS and risk_type not in selected:
            selected.append(risk_type)

    if audience_mode == AudienceMode.LAW_ENFORCEMENT_FACING:
        add("law_enforcement_trust_risk")
    elif audience_mode == AudienceMode.REGULATOR_FACING:
        add("regulatory_accountability_risk")
    elif audience_mode == AudienceMode.PUBLIC_MANAGEMENT_FACING:
        add("local_governance_pressure_risk")

    keyword_map = [
        (("事实", "争议", "真相"), "fact_dispute_risk"),
        (("程序", "流程"), "procedure_dispute_risk"),
        (("回应", "滞后", "延迟"), "response_delay_risk"),
        (("信息", "透明", "公开"), "information_opacity_risk"),
        (("负面", "批评", "质疑"), "negative_narrative_risk"),
        (("谣言", "不实"), "rumor_spread_risk"),
        (("境外", "海外"), "overseas_amplification_risk"),
        (("形象", "公信力"), "institution_image_risk"),
    ]
    for keywords, risk_type in keyword_map:
        if any(keyword in risk_assessment for keyword in keywords):
            add(risk_type)

    if tick_logs and tick_logs[-1].global_metrics.polarization_index >= 0.5:
        add("group_polarization_risk")

    if not selected:
        add("negative_narrative_risk")
    return selected[:3]


def _risk_type_labels(primary_risk_types: List[str]) -> List[str]:
    return [RISK_TYPE_LABELS[risk_type] for risk_type in primary_risk_types]


# ── report meta builders (v1.3.1 archived; copied from clean) ──

from datetime import datetime
from pathlib import Path
from src.schemas import ReportMeta, REPORT_TYPE


def _generate_report_timestamp(now=None) -> str:
    current = now or datetime.now().astimezone()
    return current.strftime("%Y年%m月%d日 %H:%M")


def _current_timezone_label(now=None) -> str:
    current = now or datetime.now().astimezone()
    if current.tzinfo is None:
        return "local"
    return current.tzname() or str(current.utcoffset()) or "local"


def _infer_simulation_run_id(output_path=None) -> str:
    if output_path is None:
        return "unknown"
    parent_name = Path(output_path).parent.name
    return parent_name or "unknown"


def build_report_meta(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    output_path=None,
    generated_at: str = None,
) -> ReportMeta:
    return ReportMeta(
        generated_at=generated_at or _generate_report_timestamp(),
        timezone=_current_timezone_label(),
        report_type=REPORT_TYPE,
        event_name=extraction_output.event_summary,
        total_ticks=len(tick_logs),
        simulation_run_id=_infer_simulation_run_id(output_path),
    )


# ── inflection detection ────────────────────────────────────────

def identify_inflection_points(
    tick_logs: List[TickLog], phase2_output: Phase2Output,
) -> List[InflectionPoint]:
    """识别模拟关键变化点"""
    if len(tick_logs) < 2:
        return []

    inflection_points = []
    node_map = {n.id: n for n in phase2_output.nodes}

    for i in range(1, len(tick_logs)):
        prev_pol = tick_logs[i - 1].global_metrics.polarization_index
        curr_pol = tick_logs[i].global_metrics.polarization_index
        pol_delta = abs(curr_pol - prev_pol)

        if pol_delta > 0.1 and tick_logs[i].entries:
            max_entry = max(tick_logs[i].entries, key=lambda e: abs(e.stance_delta))
            node = node_map.get(max_entry.agent_id)

            inflection_points.append(InflectionPoint(
                tick=tick_logs[i].tick,
                agent_id=max_entry.agent_id,
                group_name=node.group_name if node else "未知",
                pivotal_comment=max_entry.comment[:50],
                impact_description=f"模拟极化指数变化 {pol_delta:.2f}，立场偏移 {max_entry.stance_delta:+.1f}",
            ))

    return inflection_points[:3]


# ── stance matrix ──────────────────────────────────────────────

def _build_code_owned_agent_stance_matrix(tick_logs: List[TickLog]) -> List[Dict[str, Any]]:
    """Build the stance matrix used as the only Markdown source for per-agent values."""
    if not tick_logs:
        return []

    start_log = tick_logs[1] if len(tick_logs) >= 2 else tick_logs[0]
    end_log = tick_logs[-1]
    start_entries = {entry.agent_id: entry for entry in start_log.entries}
    end_entries = {entry.agent_id: entry for entry in end_log.entries}

    rows = []
    for agent_id in sorted(set(start_entries) & set(end_entries)):
        start_entry = start_entries[agent_id]
        end_entry = end_entries[agent_id]
        initial = start_entry.current_stance
        final = end_entry.current_stance
        rows.append({
            "agent_id": agent_id,
            "group_name": end_entry.group_name,
            "start_tick": start_log.tick,
            "end_tick": end_log.tick,
            "initial_stance": initial,
            "final_stance": final,
            "delta": final - initial,
        })

    return rows


def _format_code_owned_agent_stance_matrix(tick_logs: List[TickLog]) -> List[str]:
    rows = _build_code_owned_agent_stance_matrix(tick_logs)
    if not rows:
        return ["无可用 opinion spreader 立场矩阵。"]

    lines = [
        "以下表格是 Markdown 报告中最终立场变化的唯一数值来源；不得重算。",
        "| Agent | 群体 | 起始轮次 | 结束轮次 | 起始立场 | 结束立场 | Delta |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| #{row['agent_id']} | {row['group_name']} | {row['start_tick']} | "
            f"{row['end_tick']} | {row['initial_stance']:.2f} | "
            f"{row['final_stance']:.2f} | {row['delta']:+.2f} |"
        )
    return lines


def _format_code_owned_inflection_points(inflection_points: List[InflectionPoint]) -> List[str]:
    if not inflection_points:
        return [
            "本轮模拟未发现显著模拟关键变化点。",
            "Markdown 报告不得声称存在模拟关键变化点，不得使用其他阈值自行识别模拟关键变化点。",
        ]

    lines = [
        "以下表格是 Markdown 报告中模拟关键变化点的唯一来源；不得新增其他模拟关键变化点。",
        "| 轮次 | Agent | 群体 | 影响 |",
        "|---:|---:|---|---|",
    ]
    for point in inflection_points:
        lines.append(
            f"| {point.tick} | #{point.agent_id} | {point.group_name} | "
            f"{point.impact_description} |"
        )
    return lines


# ── risk assessment ─────────────────────────────────────────────

def _max_negative_shift_from_stance_matrix(tick_logs: List[TickLog]) -> float | None:
    if len(tick_logs) < 2:
        return None

    rows = _build_code_owned_agent_stance_matrix(tick_logs)
    if not rows:
        return None

    return max(max(0.0, row["initial_stance"] - row["final_stance"]) for row in rows)


def _sensitive_prior_risk_types(
    extraction_output: EntityExtractionOutput = None,
    tick_logs: List[TickLog] = None,
) -> List[str]:
    if extraction_output is None:
        return []

    audience_mode = determine_audience_mode(extraction_output, "")
    primary_risk_types = select_primary_risk_types(audience_mode, "", tick_logs or [])
    return [
        risk_type
        for risk_type in primary_risk_types
        if risk_type in SENSITIVE_PRIOR_RISK_TYPES and risk_type in RISK_TYPE_LABELS
    ]


def assess_risk(
    x_t_sequence: List[float],
    tick_logs: List[TickLog],
    *,
    extraction_output: EntityExtractionOutput = None,
) -> tuple:
    """评估舆情风险等级，方向上以负向立场压力和群体分化为风险信号。"""
    if not x_t_sequence:
        return RiskLevel.LOW, "数据不足，无法评估"

    start_x = x_t_sequence[0]
    final_x = x_t_sequence[-1]
    negative_pressure = max(0.0, 5.0 - final_x)
    negative_trend = max(0.0, start_x - final_x) if len(x_t_sequence) > 1 else 0.0
    final_pol = tick_logs[-1].global_metrics.polarization_index if tick_logs else 0.0
    max_negative_shift = _max_negative_shift_from_stance_matrix(tick_logs)

    event_scale = extraction_output.event_scale if extraction_output is not None else 0.0
    event_controversy = extraction_output.event_controversy if extraction_output is not None else 0.0
    high_sensitive_prior = event_scale >= 0.7 and event_controversy >= 0.7
    sensitive_risk_types = _sensitive_prior_risk_types(extraction_output, tick_logs)
    sensitive_prior_hit = bool(sensitive_risk_types)

    material_negative_shift = (
        max_negative_shift is not None and max_negative_shift >= 1.2
    )
    strong_negative_shift = (
        max_negative_shift is not None and max_negative_shift >= 2.0
    )
    critical_negative_shift = (
        max_negative_shift is not None and max_negative_shift >= 2.5
    )

    medium_signals = [
        final_x <= 4.7,
        negative_trend >= 0.4,
        final_pol >= 0.30,
        material_negative_shift,
        high_sensitive_prior,
        sensitive_prior_hit,
    ]
    high_signals = [
        final_pol >= 0.45 and (negative_trend >= 0.4 or material_negative_shift),
        strong_negative_shift and sensitive_prior_hit,
        final_x <= 4.0 and negative_trend >= 0.5,
        high_sensitive_prior and final_pol >= 0.40,
    ]
    critical_ready = (
        final_x <= 3.0
        and final_pol >= 0.45
        and critical_negative_shift
        and (
            event_scale >= 0.7
            or event_controversy >= 0.8
            or sensitive_prior_hit
        )
    )

    if critical_ready:
        risk_level = RiskLevel.CRITICAL
    elif any(high_signals):
        risk_level = RiskLevel.HIGH
    elif any(medium_signals):
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    signal_parts = [
        f"模拟立场均值={final_x:.1f}",
        f"负向趋势={negative_trend:.1f}",
        f"模拟极化指数={final_pol:.2f}",
    ]
    if max_negative_shift is not None:
        signal_parts.append(f"关键群体最大负向迁移={max_negative_shift:.1f}")
    else:
        signal_parts.append("关键群体负向迁移数据不足")
    if high_sensitive_prior:
        signal_parts.append("高敏事件先验达到中风险下限")
    if sensitive_prior_hit:
        labels = _risk_type_labels(sensitive_risk_types)
        signal_parts.append(f"敏感风险类型命中：{'、'.join(labels)}")

    if risk_level == RiskLevel.CRITICAL:
        prefix = "重大风险，低模拟立场均值、高模拟极化、关键群体负向迁移和高敏先验同时出现"
    elif risk_level == RiskLevel.HIGH:
        prefix = "高风险，多个负向压力信号叠加，需重点关注"
    elif risk_level == RiskLevel.MEDIUM:
        prefix = "中等风险，已出现负向压力、分化或高敏先验信号"
    else:
        prefix = "低风险，未发现明显负向压力、分化压力、群体跃迁或高敏先验"

    return risk_level, f"{prefix}（{'; '.join(signal_parts)}）"


# ── Phase4Output build helpers ──────────────────────────────────

def _build_phase4_output(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    emotion_trajectory: List[EmotionTrajectory],
    inflection_points: List[InflectionPoint],
    risk_level: RiskLevel,
    risk_assessment: str,
    stakeholder_map: str,
) -> Phase4Output:
    audience_mode = determine_audience_mode(extraction_output, risk_assessment)
    primary_risk_types = select_primary_risk_types(audience_mode, risk_assessment, tick_logs)
    return Phase4Output(
        report_meta=build_report_meta(extraction_output, tick_logs),
        event_summary=extraction_output.event_summary,
        stakeholder_map=stakeholder_map,
        emotion_trajectory=emotion_trajectory,
        inflection_points=inflection_points,
        risk_level=risk_level,
        risk_level_label=risk_level_label_for(risk_level),
        audience_mode=audience_mode,
        primary_risk_types=primary_risk_types,
        risk_type_labels=_risk_type_labels(primary_risk_types),
        risk_assessment=risk_assessment,
        x_t_sequence=x_t_sequence,
    )


# ── presentation helpers (used by legacy markdown) ──────────────

def _scale_description(value: float) -> str:
    if value >= 0.75:
        return "模拟影响范围较广，相关讨论可能跨越单一群体扩散。"
    if value >= 0.45:
        return "模拟影响范围处于中等水平，讨论可能集中在主要相关群体之间。"
    return "模拟影响范围相对有限，讨论更可能停留在直接相关群体内部。"


def _controversy_description(value: float) -> str:
    if value >= 0.75:
        return "争议强度较高，事实认知和处置程序容易成为持续追问点。"
    if value >= 0.45:
        return "争议强度中等，后续回应节奏会影响讨论是否继续升温。"
    return "争议强度相对可控，讨论更依赖后续信息补充。"
