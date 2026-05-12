"""
Phase 4: 宏观洞察生成器
---
根据 Phase 3 的模拟结果，生成舆情演化洞察报告。

v1.1.8 变化：
- 重构报告结构（概要 → 实体 → 拐点 → 演化 → 洞察 → 风险）
- 增加 Tick 0 发言展示
- 增加关键拐点识别（以 identify_inflection_points() 的 code-owned 输出为准）
- 增加 Tick 1-N 演化展示
- 增加最终立场变化表格
- 增加极化演化轨迹
- 增加关键洞察生成（3-6 条）
- 增加舆论态势判断

修改于：v1.1.8
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

import config
from src.schemas import (
    EntityExtractionOutput, Phase2Output, TickLog,
    AudienceMode, Phase4Output, EmotionTrajectory, InflectionPoint,
    ReportMeta, RiskLevel, REPORT_TYPE, RISK_LEVEL_LABELS, RISK_TYPE_LABELS
)
from src.llm_client import get_llm_client
from .report_prompts import (
    ENTERPRISE_PR_FORBIDDEN_PHRASES,
    INTERNAL_CODE_OWNED_LABELS,
    QUOTE_FABRICATION_PATTERNS,
    RAW_METRIC_FIELD_NAMES,
    REPORT_SYSTEM_PROMPT,
    REPORT_USER_PROMPT_SUFFIX,
    SIMULATION_DISCLAIMER,
)

console = Console()


LAW_ENFORCEMENT_KEYWORDS = ("公安", "交警", "派出所", "执法", "警方")
REGULATOR_KEYWORDS = ("市监局", "市场监督管理局", "监管部门", "食药监")
PUBLIC_MANAGEMENT_KEYWORDS = ("教育局", "卫健委", "住建局", "属地政府", "街道办")
REPORT_TITLE_SUFFIX = "舆情风险研判报告"
TITLE_MAX_CHARS = 25


def _generate_report_timestamp(now: datetime = None) -> str:
    """Generate code-owned report timestamp."""
    current = now or datetime.now().astimezone()
    return current.strftime("%Y年%m月%d日 %H:%M")


def _current_timezone_label(now: datetime = None) -> str:
    current = now or datetime.now().astimezone()
    if current.tzinfo is None:
        return "local"
    return current.tzname() or str(current.utcoffset()) or "local"


def _infer_simulation_run_id(output_path: Path = None) -> str:
    if output_path is None:
        return "unknown"
    parent_name = Path(output_path).parent.name
    return parent_name or "unknown"


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


def risk_level_label_for(risk_level: RiskLevel) -> str:
    return RISK_LEVEL_LABELS[risk_level.value]


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


def build_report_meta(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    output_path: Path = None,
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


def _align_report_meta_to_output_path(phase4_output: Phase4Output, output_path: Path = None) -> Phase4Output:
    run_id = _infer_simulation_run_id(output_path)
    if run_id != "unknown":
        phase4_output.report_meta.simulation_run_id = run_id
    return phase4_output


def _metadata_header(phase4_output: Phase4Output) -> str:
    meta = phase4_output.report_meta
    return "\n".join([
        f"# {_normalized_report_title(meta.event_name)}",
        "",
        f"报告类型：{meta.report_type}",
        f"生成时间：{meta.generated_at}",
        f"模拟轮次：{meta.total_ticks}轮",
        f"风险等级：{phase4_output.risk_level_label}",
        f"阅读模式：{phase4_output.audience_mode.value}",
        "",
        "---",
        "",
    ])


def _normalized_report_title(event_name: str) -> str:
    """Create a short government-report title without changing report_meta."""
    subject = _extract_title_subject(event_name)
    controversy = _infer_title_controversy(event_name)
    title = f"{subject}{controversy}{REPORT_TITLE_SUFFIX}"
    if len(title) <= TITLE_MAX_CHARS:
        return title

    available = max(2, TITLE_MAX_CHARS - len(controversy) - len(REPORT_TITLE_SUFFIX))
    return f"{subject[:available]}{controversy}{REPORT_TITLE_SUFFIX}"


def _extract_title_subject(event_name: str) -> str:
    text = re.sub(r"\s+", "", event_name or "")
    text = re.sub(r"^\d{4}年?\d{0,2}月?\d{0,2}日?", "", text)
    for delimiter in ("因", "就", "在", "发布", "回应", "被", "引发", "涉嫌", "出现", "发生"):
        if delimiter in text:
            text = text.split(delimiter, 1)[0]
            break
    text = re.split(r"[，,。；;：:、（）()【】\[\]\s]", text, maxsplit=1)[0]
    text = re.sub(r"(事件|争议|舆情|相关|问题)+$", "", text)
    if not text:
        return "相关事件"
    return text[:8]


def _infer_title_controversy(event_name: str) -> str:
    text = event_name or ""
    rules = [
        (("营销", "海报", "广告", "母亲节"), "营销争议"),
        (("执法", "劝烟", "公安", "交警", "处罚"), "执法争议"),
        (("质量", "产品", "消费", "投诉"), "产品质量争议"),
        (("学校", "校园", "教育"), "校园治理争议"),
        (("食品", "安全", "事故"), "安全事件"),
        (("人事", "招聘", "裁员"), "人事争议"),
        (("回应", "声明", "道歉"), "舆情回应争议"),
    ]
    for keywords, label in rules:
        if any(keyword in text for keyword in keywords):
            return label
    return "舆情争议"


def _ensure_metadata_header(markdown: str, phase4_output: Phase4Output) -> str:
    generated_at = phase4_output.report_meta.generated_at
    if generated_at in markdown[:800]:
        return markdown
    return _metadata_header(phase4_output) + markdown.lstrip()


def _normalize_report_title_line(markdown: str, phase4_output: Phase4Output) -> str:
    title = _normalized_report_title(phase4_output.report_meta.event_name)
    if re.search(r"(?m)^#\s+", markdown):
        return re.sub(r"(?m)^#\s+.*$", f"# {title}", markdown, count=1)
    return f"# {title}\n\n{markdown.lstrip()}"


def _code_owned_risk_section(phase4_output: Phase4Output) -> str:
    risk_lines = [
        "## 三、风险研判",
        "",
        f"风险等级：{phase4_output.risk_level_label}",
        "",
        "主要风险类型：",
    ]
    for index, risk_type in enumerate(phase4_output.risk_type_labels, start=1):
        risk_lines.append(f"{index}. {risk_type}")
    if not phase4_output.risk_type_labels:
        risk_lines.append("1. 负面叙事聚合风险")

    risk_lines.extend([
        "",
        "风险解释：",
        _risk_explanation(phase4_output),
        "",
    ])
    risk_lines.extend(_structural_risk_point_lines(phase4_output))
    return "\n".join(risk_lines)


def _replace_risk_section_with_code_owned(markdown: str, phase4_output: Phase4Output) -> str:
    risk_section = _code_owned_risk_section(phase4_output)
    risk_heading_pattern = r"(?m)^##\s*三[、.．]\s*风险研判\s*$"
    next_heading_pattern = r"(?m)^##\s*四[、.．]\s*对策建议\s*$"
    risk_match = re.search(risk_heading_pattern, markdown)

    if risk_match:
        next_match = re.search(next_heading_pattern, markdown[risk_match.end():])
        if next_match:
            next_start = risk_match.end() + next_match.start()
            return markdown[:risk_match.start()] + risk_section + "\n\n" + markdown[next_start:]
        return markdown[:risk_match.start()] + risk_section

    next_match = re.search(next_heading_pattern, markdown)
    if next_match:
        return markdown[:next_match.start()] + risk_section + "\n\n" + markdown[next_match.start():]

    return markdown.rstrip() + "\n\n" + risk_section


def _strip_internal_code_owned_labels(markdown: str) -> str:
    lines = []
    for line in markdown.splitlines():
        if any(label in line for label in INTERNAL_CODE_OWNED_LABELS):
            continue
        lines.append(line)
    return "\n".join(lines)


def _replace_raw_metric_field_names(markdown: str) -> str:
    replacements = {
        "event_scale": "模拟影响范围",
        "event_controversy": "模拟争议强度",
        "polarization_index": "群体分化水平",
        "stance_delta": "立场变化幅度",
        "risk_score": "综合风险判断",
    }
    normalized = markdown
    for field_name in RAW_METRIC_FIELD_NAMES:
        normalized = normalized.replace(field_name, replacements[field_name])
    return normalized


def _replace_enterprise_pr_phrases(markdown: str) -> str:
    replacements = {
        "建议OPPO": "建议政府侧关注相关主体",
        "建议品牌方": "建议政府侧协调相关主管部门",
        "建议品牌": "建议政府侧协调相关主管部门",
        "建议企业": "建议政府侧协调相关主管部门",
        "建议涉事企业": "建议政府侧协调相关主管部门",
        "建议学校公关": "建议教育主管部门关注校园治理沟通",
        "危机公关": "风险回应",
        "品牌修复": "事实说明与风险缓释",
        "形象修复": "公共沟通修正",
        "舆情洗白": "事实澄清",
        "贵司": "相关主体",
        "贵校": "相关学校",
    }
    normalized = markdown
    for phrase in ENTERPRISE_PR_FORBIDDEN_PHRASES:
        normalized = normalized.replace(phrase, replacements[phrase])
    normalized = re.sub(
        r"建议(涉事主体|品牌方|品牌|企业|学校|协会|当事人)",
        "建议政府侧协调相关主管部门",
        normalized,
    )
    return normalized


def _replace_quote_fabrication_patterns(markdown: str) -> str:
    normalized = markdown
    for pattern in QUOTE_FABRICATION_PATTERNS:
        normalized = normalized.replace(pattern, "模拟显示：")
    return normalized


def _replace_placeholder_residue(markdown: str) -> str:
    return markdown.replace("待评估", "本轮模拟未发现显著拐点")


def _has_required_five_chapter_sections(markdown: str) -> bool:
    section_patterns = (
        r"舆情概要",
        r"演化分析",
        r"风险研判",
        r"对策建议",
        r"附录",
    )
    for section_name in section_patterns:
        pattern = rf"(?m)^\s*(?:#{{1,6}}\s*)?(?:[一二三四五][、.．]\s*)?{section_name}\s*$"
        if not re.search(pattern, markdown):
            return False
    return True


def _normalize_saved_markdown(markdown: str, phase4_output: Phase4Output) -> str:
    normalized = _ensure_metadata_header(markdown, phase4_output)
    normalized = _normalize_report_title_line(normalized, phase4_output)
    normalized = _strip_internal_code_owned_labels(normalized)
    normalized = _replace_placeholder_residue(normalized)
    normalized = _replace_quote_fabrication_patterns(normalized)
    normalized = _replace_enterprise_pr_phrases(normalized)
    normalized = _replace_raw_metric_field_names(normalized)
    normalized = _replace_risk_section_with_code_owned(normalized, phase4_output)
    return normalized


def build_full_report_context(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
) -> str:
    """构建完整的报告上下文数据

    Args:
        extraction_output: 实体提取结果
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        格式化的上下文字符串
    """
    lines = []

    # 1. 事件概要
    lines.append("【事件概要】")
    lines.append(f"事件摘要：{extraction_output.event_summary}")
    lines.append(f"事件类型：{extraction_output.event_type}")
    lines.append(f"事件规模：{extraction_output.event_scale:.2f}（0-1，1=全社会）")
    lines.append(f"事件争议性：{extraction_output.event_controversy:.2f}（0-1，1=高度对立）")

    # 2. 实体图谱
    lines.append("\n【实体图谱】")
    lines.append(f"事件实体（直接参与者）：{len(extraction_output.event_entities)} 个")
    for entity in extraction_output.event_entities:
        lines.append(f"  - {entity.name}（{entity.type}）: {entity.role} | can_speak={entity.can_speak}")
        if entity.original_statement:
            lines.append(f"    原始发言：{entity.original_statement[:50]}...")

    lines.append(f"\n意见传播者（评论者）：{len(extraction_output.opinion_spreaders)} 个")
    for spreader in extraction_output.opinion_spreaders:
        lines.append(f"  - {spreader.group_name}")
        lines.append(f"    关联实体：{spreader.related_event_entity}，立场：{spreader.stance_score}，偏差：{spreader.confirmation_bias_level}，占比：{spreader.estimated_percentage}%")

    # 3. Tick 0 发言
    lines.append("\n【Tick 0 事件实体发言】")
    tick_0_log = tick_logs[0] if tick_logs else None
    if tick_0_log:
        for entry in tick_0_log.entries:
            if entry.comment:
                lines.append(f"  [{entry.group_name}]: {entry.comment[:80]}...")

    # 4. 情绪演化数据
    lines.append("\n【情绪演化数据】")
    lines.append("Tick | x(t)均值 | 标准差 | 极化指数 | 关键变化")
    lines.append("-" * 70)
    prev_pol = None
    for log in tick_logs:
        if not log.entries:
            continue
        max_entry = max(log.entries, key=lambda e: abs(e.stance_delta))
        pol = log.global_metrics.polarization_index
        pol_change = ""
        if prev_pol is not None:
            pol_change = f"({pol - prev_pol:+.2f})"
        lines.append(f"{log.tick:4d} | {log.global_metrics.mean_stance:5.2f} | {log.global_metrics.std_stance:5.2f} | {pol:5.2f} {pol_change:8s} | #{max_entry.agent_id} {max_entry.group_name[:10]}: {max_entry.stance_delta:+.1f}")
        prev_pol = pol

    # 5. 极化演化轨迹
    lines.append("\n【极化演化轨迹】")
    pol_sequence = [f"{log.global_metrics.polarization_index:.2f}" for log in tick_logs if log.entries]
    lines.append(" → ".join(pol_sequence))
    if len(pol_sequence) >= 2:
        first_pol = float(pol_sequence[0])
        last_pol = float(pol_sequence[-1])
        change_pct = (last_pol - first_pol) / first_pol * 100 if first_pol > 0 else 0
        direction = "下降" if change_pct < 0 else "上升"
        lines.append(f"极化指数从 {pol_sequence[0]} 变化到 {pol_sequence[-1]}，{direction} {abs(change_pct):.0f}%")

    # 6. code-owned grounding blocks
    lines.append("\n【CODE_OWNED_AGENT_STANCE_MATRIX】")
    lines.extend(_format_code_owned_agent_stance_matrix(tick_logs))

    lines.append("\n【CODE_OWNED_INFLECTION_POINTS】")
    inflection_points = identify_inflection_points(tick_logs, phase2_output) if phase2_output else []
    lines.extend(_format_code_owned_inflection_points(inflection_points))

    # 7. x(t) 序列
    lines.append(f"\n【x(t) 序列】：{' → '.join([f'{x:.2f}' for x in x_t_sequence])}")

    return "\n".join(lines)


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
        "| Agent | 群体 | 起始 Tick | 结束 Tick | 起始立场 | 结束立场 | Delta |",
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
            "本轮模拟未发现显著拐点。",
            "Markdown 报告不得声称存在拐点，不得使用其他阈值自行识别拐点。",
        ]

    lines = [
        "以下表格是 Markdown 报告中关键拐点的唯一来源；不得新增其他拐点。",
        "| Tick | Agent | 群体 | 影响 |",
        "|---:|---:|---|---|",
    ]
    for point in inflection_points:
        lines.append(
            f"| {point.tick} | #{point.agent_id} | {point.group_name} | "
            f"{point.impact_description} |"
        )
    return lines


def build_entity_distribution(extraction_output: EntityExtractionOutput) -> str:
    """构建实体分布文本

    Args:
        extraction_output: 实体提取结果

    Returns:
        格式化分布字符串
    """
    lines = ["事件实体（直接参与者）："]
    for entity in extraction_output.event_entities:
        lines.append(f"  - {entity.name} ({entity.type}): {entity.role}")

    lines.append("\n意见传播者（评论者）：")
    for spreader in extraction_output.opinion_spreaders:
        lines.append(f"  - {spreader.group_name}")
        lines.append(f"    关联实体: {spreader.related_event_entity}, 立场: {spreader.stance_score}, 偏差: {spreader.confirmation_bias_level}")

    return "\n".join(lines)


def identify_inflection_points(tick_logs: List[TickLog], phase2_output: Phase2Output) -> List[InflectionPoint]:
    """识别拐点

    算法：
    1. 计算每轮的极化指数变化
    2. 极化指数变化最大的轮次为拐点
    3. 找出该轮次中立场变化最大的 Agent

    Args:
        tick_logs: TickLog 列表
        phase2_output: Phase2 输出

    Returns:
        InflectionPoint 列表
    """
    if len(tick_logs) < 2:
        return []

    inflection_points = []
    node_map = {n.id: n for n in phase2_output.nodes}

    # 计算每轮的极化指数变化
    for i in range(1, len(tick_logs)):
        prev_pol = tick_logs[i - 1].global_metrics.polarization_index
        curr_pol = tick_logs[i].global_metrics.polarization_index
        pol_delta = abs(curr_pol - prev_pol)

        # 如果极化指数变化超过阈值，认为是拐点
        if pol_delta > 0.1 and tick_logs[i].entries:
            # 找出本轮立场变化最大的 Agent
            max_entry = max(tick_logs[i].entries, key=lambda e: abs(e.stance_delta))

            node = node_map.get(max_entry.agent_id)

            inflection_points.append(InflectionPoint(
                tick=tick_logs[i].tick,
                agent_id=max_entry.agent_id,
                group_name=node.group_name if node else "未知",
                pivotal_comment=max_entry.comment[:50],
                impact_description=f"极化指数变化 {pol_delta:.2f}，立场偏移 {max_entry.stance_delta:+.1f}",
            ))

    # 限制最多 3 个拐点
    return inflection_points[:3]


def assess_risk(x_t_sequence: List[float], tick_logs: List[TickLog]) -> tuple:
    """评估舆情风险等级

    算法：
    1. x(t) 持续上升 > 7.0 → 高风险
    2. x(t) > 5.0 且极化指数 > 0.5 → 中高风险
    3. x(t) > 5.0 → 中风险
    4. x(t) < 5.0 → 低风险

    Args:
        x_t_sequence: x(t) 序列
        tick_logs: TickLog 列表

    Returns:
        (risk_level, risk_assessment) tuple
    """
    if not x_t_sequence:
        return RiskLevel.LOW, "数据不足，无法评估"

    final_x = x_t_sequence[-1]
    final_pol = tick_logs[-1].global_metrics.polarization_index if tick_logs else 0

    # 计算趋势
    trend = final_x - x_t_sequence[0] if len(x_t_sequence) > 1 else 0

    if final_x > 7.5 or (final_x > 7.0 and trend > 1.0):
        return RiskLevel.CRITICAL, f"舆情危机状态，x(t)达{final_x:.1f}，极化严重"
    elif final_x > 6.5 or (final_x > 5.5 and final_pol > 0.5):
        return RiskLevel.HIGH, f"高风险舆情，x(t)={final_x:.1f}，需重点关注"
    elif final_x > 5.0 or (final_x > 4.5 and trend > 0.5):
        return RiskLevel.MEDIUM, f"中等风险，x(t)={final_x:.1f}，趋势需关注"
    else:
        return RiskLevel.LOW, f"舆情平稳，x(t)={final_x:.1f}，风险较低"


# 模块级变量，用于存储 LLM 生成的 Markdown 报告
_llm_generated_markdown: str = ""


def generate_report_with_llm(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
) -> Phase4Output:
    """使用 LLM 生成报告

    v1.1.8: 直接生成 Markdown 格式报告

    Args:
        extraction_output: 实体提取结果
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        Phase4Output 对象
    """
    global _llm_generated_markdown

    llm = get_llm_client()

    if phase2_output is None:
        from src.phase3 import load_phase2_output
        phase2_output = load_phase2_output()

    # 构建完整上下文
    report_context = build_full_report_context(
        extraction_output,
        tick_logs,
        x_t_sequence,
        phase2_output=phase2_output,
    )

    user_prompt = f"""请根据以下数据生成舆情风险研判报告：

{report_context}

{REPORT_USER_PROMPT_SUFFIX}"""

    console.print("[cyan]正在调用 LLM 生成报告...[/cyan]")

    response = llm.generate(
        system=REPORT_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,
    )

    # 保存 LLM 生成的 Markdown
    _llm_generated_markdown = response

    # 解析响应并构建 Phase4Output
    phase4_output = parse_llm_report_response(
        response,
        extraction_output,
        tick_logs,
        x_t_sequence,
        phase2_output=phase2_output,
    )

    return phase4_output


def parse_llm_report_response(
    response: str,
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
) -> Phase4Output:
    """解析 LLM 报告响应

    v1.1.8: LLM 直接生成 Markdown，解析失败时使用 fallback

    Args:
        response: LLM 返回的原始字符串
        extraction_output: 实体提取结果
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        Phase4Output 对象
    """
    # 检查响应是否有效
    if not response or len(response) < 100:
        console.print("[yellow]警告：[/yellow] LLM 报告过短，使用自动分析")
        return generate_fallback_report(
            extraction_output,
            tick_logs,
            x_t_sequence,
            phase2_output=phase2_output,
        )

    # 构建情绪轨迹
    emotion_trajectory = [
        EmotionTrajectory(
            tick=log.tick,
            mean_stance=log.global_metrics.mean_stance,
            std_stance=log.global_metrics.std_stance,
            polarization_index=log.global_metrics.polarization_index,
            key_event=f"Agent #{max(log.entries, key=lambda e: abs(e.stance_delta)).agent_id} 发言",
        )
        for log in tick_logs if log.entries
    ]

    # 识别拐点
    if phase2_output is None:
        from src.phase3 import load_phase2_output
        phase2_output = load_phase2_output()
    inflection_points = identify_inflection_points(tick_logs, phase2_output)

    # 风险评估
    risk_level, risk_assessment = assess_risk(x_t_sequence, tick_logs)

    # 利益相关方图谱
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


def generate_fallback_report(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
) -> Phase4Output:
    """生成自动报告（当 LLM 失败时）

    Args:
        extraction_output: 实体提取结果
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        Phase4Output 对象
    """
    if phase2_output is None:
        from src.phase3 import load_phase2_output
        phase2_output = load_phase2_output()

    # 识别拐点
    inflection_points = identify_inflection_points(tick_logs, phase2_output)

    # 风险评估
    risk_level, risk_assessment = assess_risk(x_t_sequence, tick_logs)

    # 构建情绪轨迹
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

    # 利益相关方图谱
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


def _trajectory_description(phase4_output: Phase4Output) -> str:
    if not phase4_output.emotion_trajectory:
        return "本轮模拟缺少足够的演化轨迹，暂不形成趋势判断。"

    first = phase4_output.emotion_trajectory[0]
    last = phase4_output.emotion_trajectory[-1]
    stance_change = last.mean_stance - first.mean_stance
    polarization_change = last.polarization_index - first.polarization_index

    if stance_change > 0.3:
        stance_text = "整体态度在模拟后段呈缓和方向移动。"
    elif stance_change < -0.3:
        stance_text = "整体态度在模拟后段呈更谨慎或更质疑的方向移动。"
    else:
        stance_text = "整体态度在模拟过程中变化不大。"

    if polarization_change > 0.1:
        polarization_text = "不同群体之间的立场分化有所加深，需要关注负面叙事聚合。"
    elif polarization_change < -0.1:
        polarization_text = "不同群体之间的分化有所收敛，讨论张力出现缓和迹象。"
    else:
        polarization_text = "不同群体之间的分化水平整体保持稳定。"

    return f"{stance_text}{polarization_text}"


def _evolution_stage_lines(phase4_output: Phase4Output) -> List[str]:
    if not phase4_output.emotion_trajectory:
        return [
            "第一阶段：输入信息不足期。当前模拟缺少足够轨迹数据，暂不形成阶段性扩散判断。治理含义是先补齐事实链和观察样本，避免过早定性。",
            "",
            "第二阶段：持续观察期。政府侧可关注后续新增信息是否改变群体分化结构，并预置必要的风险提示口径。",
        ]

    first = phase4_output.emotion_trajectory[0]
    last = phase4_output.emotion_trajectory[-1]
    polarization_change = last.polarization_index - first.polarization_index

    if last.polarization_index >= 0.5 or polarization_change > 0.1:
        second_feature = "群体分化加深，质疑型群体更容易围绕事实链、程序透明度和回应节奏形成持续追问。"
        second_governance = "治理含义是从单点回应转向群体结构监测，跟踪负面叙事是否继续聚合。"
    else:
        second_feature = "群体分化保持在可控区间，讨论更多取决于后续事实补充是否稳定。"
        second_governance = "治理含义是保持低强度跟踪，避免过度介入导致个案被再次放大。"

    return [
        "第一阶段：争议触发期。事件进入模拟后，关注点首先集中在触发事实、责任边界和回应预期上。关键群体通常是直接受影响或高度敏感的讨论者；其机制在于初始信息不足会放大解释空间。治理含义是尽早识别公共风险焦点，避免讨论从事实疑问滑向价值对立。",
        "",
        f"第二阶段：群体分化期。{second_feature}关键群体包括质疑方、等待事实补充的缓冲群体和可能推动二次传播的围观群体。{second_governance}",
        "",
        "第三阶段：外溢观察期。模拟后段需要判断争议是否从个案扩展到行业规范、平台传播或公共价值议题。治理含义是监测外溢路径、提示相关部门保持口径一致，并避免政府侧对企业或个人个案作过度介入。",
    ]


def _inflection_markdown_lines(phase4_output: Phase4Output) -> List[str]:
    if not phase4_output.inflection_points:
        return ["本轮模拟未发现显著拐点。"]

    lines = [
        "本轮模拟中，以下变化点来自代码侧拐点识别结果，仅用于解释模拟轨迹：",
        "",
        "| 轮次 | 群体 | 模拟变化说明 |",
        "|------|------|--------------|",
    ]
    for point in phase4_output.inflection_points:
        lines.append(f"| 第{point.tick}轮 | {point.group_name} | {point.impact_description} |")
    return lines


def _stance_summary_lines(phase4_output: Phase4Output) -> List[str]:
    if not phase4_output.emotion_trajectory:
        return ["- 暂无足够轨迹数据形成群体分化判断。"]

    last = phase4_output.emotion_trajectory[-1]
    if last.polarization_index >= 0.5:
        return [
            "- 模拟后段群体分化较为明显，负面叙事存在继续聚合的风险。",
            "- 回应节奏和事实链完整度将影响后续讨论是否继续围绕责任、程序和透明度展开。",
        ]
    if last.polarization_index >= 0.3:
        return [
            "- 模拟后段群体分化处于中等水平，核心争议仍可能随新增信息变化。",
            "- 需要避免回应口径前后不一致，防止讨论焦点从事实争议转向程序质疑。",
        ]
    return [
        "- 模拟后段群体分化相对温和，当前更适合通过事实补充降低误解空间。",
        "- 后续应继续观察高敏群体关切，避免局部质疑被放大。",
    ]


def _risk_explanation(phase4_output: Phase4Output) -> str:
    risk_types = "、".join(phase4_output.risk_type_labels) if phase4_output.risk_type_labels else "负面叙事聚合风险"
    if phase4_output.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        return (
            f"本轮模拟显示，事件讨论可能围绕{risk_types}继续扩散。"
            "若后续事实链补充不足或回应节奏滞后，相关讨论可能进一步转向程序透明度、责任主体和公信力问题。"
        )
    if phase4_output.risk_level == RiskLevel.MEDIUM:
        return (
            f"本轮模拟显示，事件已出现{risk_types}相关苗头。"
            "当前风险尚未进入失控状态，但仍需要通过稳定、透明、可核验的回应降低误读空间。"
        )
    return (
        f"本轮模拟显示，事件暂处于{risk_types}可控阶段。"
        "后续重点是持续补充事实信息，避免局部疑问演化为更大范围的程序争议。"
    )


def _structural_risk_point_lines(phase4_output: Phase4Output) -> List[str]:
    risk_types = "、".join(phase4_output.risk_type_labels) if phase4_output.risk_type_labels else "负面叙事聚合风险"
    if phase4_output.audience_mode == AudienceMode.GENERIC_GOVERNMENT:
        first_name = "个案争议向公共价值议题外溢"
        first_focus = "事件从单一主体争议扩展为行业规范、公序良俗或平台传播议题"
        second_name = "多群体讨论导致叙事碎片化"
        second_focus = "不同群体围绕事实链、态度表达和责任边界形成分化理解"
    else:
        first_name = "程序性争议向治理能力质疑延展"
        first_focus = "事件被纳入执法、监管或公共管理程序是否充分的讨论框架"
        second_name = "属地回应时序不一致放大治理压力"
        second_focus = "多个部门或层级回应节奏不一致，导致公众对处置依据和责任边界继续追问"

    return [
        f"结构性风险点一：{first_name}",
        f"触发机制：{first_focus}，并与本轮 code-owned 主要风险类型（{risk_types}）形成对应。",
        "关键群体：高敏感质疑群体、等待事实补充的中间群体，以及可能推动二次传播的围观群体。",
        "升级路径：如果事实链补充不足，讨论可能由个案评价扩展为公共价值站队或治理能力评价。",
        "缓释条件：政府侧保持关注和研判，协调相关主管部门提示信息披露边界，预置回应口径并监测外溢。",
        "",
        f"结构性风险点二：{second_name}",
        f"触发机制：{second_focus}，使讨论从事实判断转向叙事竞争。",
        "关键群体：持续追问程序透明度的群体、情绪化扩散群体和具有缓冲作用的理性观察群体。",
        "升级路径：叙事碎片化后，单一说明难以覆盖多元关切，风险可能沿平台二次传播和跨圈层转述继续扩散。",
        "缓释条件：政府侧跟踪关键群体关切，协调信息口径，督促信息链条补齐可核验事实，并引导讨论回到事实和程序边界。",
    ]


def _governance_recommendation_lines(phase4_output: Phase4Output) -> List[str]:
    if phase4_output.audience_mode == AudienceMode.GENERIC_GOVERNMENT:
        return [
            "1. 关注公共议题外溢方向，研判事件是否从个案争议扩展为行业规范、平台传播或价值观讨论。",
            "2. 跟踪高敏感群体与缓冲群体的立场变化，监测二次传播素材是否重新激活争议。",
            "3. 协调行业主管或属地公共管理部门提示相关方补齐事实说明，避免多头表态造成信息混乱。",
            "4. 预置政府侧风险提示和回应口径，明确本报告为模拟推演，不替涉事主体作公关表达。",
            "5. 引导讨论回到事实链、程序边界和公共风险识别，避免过度介入企业或个人个案。",
        ]
    return [
        "1. 关注程序争议的扩散方向，研判其是否从个案处置问题外溢为治理能力质疑。",
        "2. 跟踪关键群体对处置依据、回应时序和信息透明度的追问，提示风险升级节点。",
        "3. 协调相关部门统一口径，补齐程序说明、公开节点和事实边界，减少口径冲突。",
        "4. 督促信息发布链条保持可核验、可追溯，避免回应滞后放大程序性质疑。",
        "5. 在必要时推动上级指导和协同处置，同时避免过度介入未核实的个体责任判断。",
    ]


def generate_markdown_report(phase4_output: Phase4Output, extraction_output: EntityExtractionOutput) -> str:
    """生成 Markdown 格式报告

    Args:
        phase4_output: Phase4 输出
        extraction_output: 实体提取结果

    Returns:
        Markdown 格式字符串
    """
    speaking_entities = [e for e in extraction_output.event_entities if e.can_speak]
    discussed_entities = [e for e in extraction_output.event_entities if not e.can_speak]
    risk_types = "、".join(phase4_output.risk_type_labels) if phase4_output.risk_type_labels else "未归类风险"

    lines = [
        "## 一、舆情概要",
        "",
        SIMULATION_DISCLAIMER,
        "",
        "### 事件概况",
        "",
        extraction_output.event_summary,
        f"事件类型：{extraction_output.event_type}",
        _scale_description(extraction_output.event_scale),
        _controversy_description(extraction_output.event_controversy),
        "",
        "### 涉及主体",
        "",
    ]

    if speaking_entities:
        for entity in speaking_entities:
            statement = entity.original_statement if entity.original_statement else "暂无可引用原始表述"
            lines.append(f"- {entity.name}（{entity.role}）：{statement}")
    else:
        lines.append("- 本轮输入中未提供可直接发言的事件主体。")

    if discussed_entities:
        lines.append("")
        lines.append("### 被讨论主体")
        lines.append("")
        for entity in discussed_entities:
            reason = entity.can_speak_reason if entity.can_speak_reason else "作为被讨论对象进入模拟"
            lines.append(f"- {entity.name}（{entity.role}）：{reason}")

    lines.extend([
        "",
        "## 二、演化分析",
        "",
        "### 阶段性演化判断",
        "",
    ])

    lines.extend(_evolution_stage_lines(phase4_output))

    lines.extend([
        "",
        "### 群体分化观察",
        "",
    ])

    lines.extend(_stance_summary_lines(phase4_output))

    lines.extend([
        "",
        "### 关键变化点",
        "",
    ])

    lines.extend(_inflection_markdown_lines(phase4_output))

    lines.extend([
        "",
        "## 三、风险研判",
        "",
        f"风险等级：{phase4_output.risk_level_label}",
        "",
        "主要风险类型：",
    ])

    for index, risk_type in enumerate(phase4_output.risk_type_labels, start=1):
        lines.append(f"{index}. {risk_type}")

    lines.extend([
        "",
        "风险解释：",
        _risk_explanation(phase4_output),
        "",
    ])

    lines.extend(_structural_risk_point_lines(phase4_output))

    lines.extend([
        "",
        "## 四、对策建议",
        "",
    ])

    lines.extend(_governance_recommendation_lines(phase4_output))

    lines.extend([
        "",
        "## 五、附录",
        "",
        "### 模拟口径说明",
        "",
        SIMULATION_DISCLAIMER,
        "",
        "### 数据来源边界",
        "",
        "- 本报告仅使用输入材料、模拟轨迹和代码侧结构化结果。",
        "- 未接入外部检索、政策知识库或真实全网监测数据。",
        "- 风险等级和主要风险类型来自代码侧结果，正文只做解释性表达。",
        "- 拐点表达以代码侧识别结果为准，不在正文中重新计算或补造拐点。",
        "",
        "### 传播者分组参考",
        "",
    ])

    if extraction_output.opinion_spreaders:
        for spreader in extraction_output.opinion_spreaders:
            lines.append(f"- {spreader.group_name}：关注{spreader.related_event_entity}，表达风格为{spreader.communication_style}。")
    else:
        lines.append("- 本轮输入中未提供意见传播者分组。")

    lines.extend([
        "",
        "### 风险类型来源",
        "",
        f"本轮报告使用的主要风险类型为：{risk_types}。",
        "",
        "---",
        "",
        "*本报告由 Adarian 多智能体舆情预判系统基于模拟结果自动生成。*",
    ])

    return _metadata_header(phase4_output) + "\n".join(lines)


def save_report(phase4_output: Phase4Output, output_path: Path = None):
    """保存报告

    Args:
        phase4_output: Phase4 输出
        output_path: 输出路径，默认使用 config.FINAL_REPORT_PATH.with_suffix(".json")
    """
    output_path = output_path or config.FINAL_REPORT_PATH.with_suffix(".json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    phase4_output = _align_report_meta_to_output_path(phase4_output, output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(phase4_output.model_dump(), f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/green] JSON 报告已保存至: {output_path}")


def save_markdown_report(
    phase4_output: Phase4Output,
    extraction_output: EntityExtractionOutput,
    output_path: Path = None,
):
    """保存 Markdown 格式报告

    Args:
        phase4_output: Phase4 输出
        extraction_output: 实体提取结果
        output_path: 输出路径，默认使用 config.FINAL_REPORT_PATH.with_suffix(".md")
    """
    global _llm_generated_markdown

    md_path = output_path or config.FINAL_REPORT_PATH.with_suffix(".md")
    phase4_output = _align_report_meta_to_output_path(phase4_output, md_path)

    # 如果有 LLM 生成的 Markdown（长度 > 100），优先使用；残缺报告会回退到 code-owned fallback。
    if _llm_generated_markdown and len(_llm_generated_markdown) > 100:
        md_content = _llm_generated_markdown
    else:
        md_content = generate_markdown_report(phase4_output, extraction_output)
    md_content = _normalize_saved_markdown(md_content, phase4_output)
    if not _has_required_five_chapter_sections(md_content):
        md_content = generate_markdown_report(phase4_output, extraction_output)
        md_content = _normalize_saved_markdown(md_content, phase4_output)

    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    console.print(f"[green]✓[/green] Markdown 报告已保存至: {md_path}")


def load_tick_logs(tick_dir: Path = None) -> List[TickLog]:
    """加载 tick 日志"""
    from src.schemas import TickLog

    tick_dir = tick_dir or config.TICK_LOGS_DIR

    tick_logs = []
    for tick_file in sorted(tick_dir.glob("tick_*.json"), key=lambda p: int(p.stem.split("_")[1])):
        with open(tick_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            tick_logs.append(TickLog(**data))

    return tick_logs


# =============================================================================
# 主入口（可独立运行）
# =============================================================================

if __name__ == "__main__":
    import sys

    # 确保输出目录存在
    config.ensure_dirs()

    console.print("[bold]Phase 4: 生成舆情洞察报告[/bold]\n")

    # 加载数据
    from src.phase3 import load_extraction_output, load_phase2_output

    extraction_output = load_extraction_output()
    phase2_output = load_phase2_output()

    # 检查是否有 tick 日志
    if not config.TICK_LOGS_DIR.exists() or not list(config.TICK_LOGS_DIR.glob("tick_*.json")):
        console.print("[yellow]错误：[/yellow] 未找到 tick 日志，请先运行 Phase 3")
        sys.exit(1)

    tick_logs = load_tick_logs()

    # 提取 x(t) 序列
    x_t_sequence = [log.global_metrics.mean_stance for log in tick_logs]

    # 生成报告
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("[cyan]生成报告...", total=None)
        phase4_output = generate_report_with_llm(extraction_output, tick_logs, x_t_sequence)

    # 保存
    save_report(phase4_output)
    save_markdown_report(phase4_output, extraction_output)

    # 打印摘要
    console.print(f"\n[bold green]报告生成完成！[/bold green]")
    console.print(f"  风险等级: {phase4_output.risk_level.value.upper()}")
    console.print(f"  x(t) 序列: {[f'{x:.2f}' for x in x_t_sequence]}")
