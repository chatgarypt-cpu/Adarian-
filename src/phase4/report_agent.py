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
    METRIC_EXPLANATION_PREFILL,
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


def _build_code_owned_report_contract_block(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
) -> str:
    risk_level, risk_assessment = assess_risk(
        x_t_sequence,
        tick_logs,
        extraction_output=extraction_output,
    )
    audience_mode = determine_audience_mode(extraction_output, risk_assessment)
    primary_risk_types = select_primary_risk_types(audience_mode, risk_assessment, tick_logs)
    risk_type_labels = _risk_type_labels(primary_risk_types)
    return "\n".join([
        "【CODE_OWNED_REPORT_CONTRACT】",
        f"risk_level_label: {risk_level_label_for(risk_level)}",
        f"risk_type_labels: {'、'.join(risk_type_labels) if risk_type_labels else '负面叙事聚合风险'}",
        f"audience_mode: {audience_mode.value}",
        f"primary_risk_types: {', '.join(primary_risk_types) if primary_risk_types else 'negative_narrative_risk'}",
        f"risk_assessment: {risk_assessment}",
        "以上字段为代码侧结果，Markdown 必须逐字使用 risk_level_label 与 risk_type_labels，不得询问用户补充，不得自行改写。",
    ])


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
    subject = _normalize_title_subject_for_controversy(subject, controversy, event_name)
    title = _compose_report_title(subject, controversy)
    if len(title) <= TITLE_MAX_CHARS:
        return title

    connector = _title_controversy_connector(subject, controversy)
    available = max(2, TITLE_MAX_CHARS - len(connector) - len(REPORT_TITLE_SUFFIX))
    return f"{subject[:available]}{connector}{REPORT_TITLE_SUFFIX}"


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


def _normalize_title_subject_for_controversy(subject: str, controversy: str, event_name: str) -> str:
    text = re.sub(r"\s+", "", event_name or "")
    if controversy == "营销争议" and "营销" in text:
        prefix = text.split("营销", 1)[0]
        prefix = re.sub(r"(文案|海报|广告|内容)+$", "", prefix)
        candidate = re.split(r"[，,。；;：:、（）()【】\[\]\s]", prefix + "营销", maxsplit=1)[0]
        candidate = re.sub(r"(文案|海报|广告|内容|事件|争议)+$", "", candidate)
        if candidate:
            return candidate[:10]
    return subject


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


def _title_controversy_connector(subject: str, controversy: str) -> str:
    stems = {
        "营销争议": "营销",
        "执法争议": "执法",
        "产品质量争议": "产品质量",
        "校园治理争议": "校园治理",
        "安全事件": "安全",
        "人事争议": "人事",
        "舆情回应争议": "舆情回应",
        "舆情争议": "舆情",
    }
    stem = stems.get(controversy, "")
    if subject.endswith(controversy):
        return ""
    if stem and subject.endswith(stem):
        if controversy.endswith("争议"):
            return "争议"
        if controversy.endswith("事件"):
            return "事件"
    return controversy


def _compose_report_title(subject: str, controversy: str) -> str:
    return f"{subject}{_title_controversy_connector(subject, controversy)}{REPORT_TITLE_SUFFIX}"


def _ensure_metadata_header(markdown: str, phase4_output: Phase4Output) -> str:
    generated_at = phase4_output.report_meta.generated_at
    if generated_at in markdown[:800]:
        return markdown
    return _metadata_header(phase4_output) + markdown.lstrip()


def _normalize_report_title_line(markdown: str, phase4_output: Phase4Output) -> str:
    title = _normalized_report_title(phase4_output.report_meta.event_name)
    normalized_lines = []
    h1_seen = False
    for line in markdown.splitlines():
        if re.match(r"^#\s+", line):
            if not h1_seen:
                normalized_lines.append(f"# {title}")
                h1_seen = True
            continue
        normalized_lines.append(line)
    if h1_seen:
        return "\n".join(normalized_lines)
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
        "### （一）矛盾焦点分析",
        "",
    ])
    risk_lines.extend(_conflict_focus_lines(phase4_output))
    risk_lines.append("")
    risk_lines.extend(_structural_risk_point_lines(phase4_output))
    risk_lines.extend([
        "",
        "### （五）短中期态势判断",
        "",
        _short_mid_term_risk_judgment(phase4_output),
    ])
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
    skipping_contract_block = False
    for line in markdown.splitlines():
        if "CODE_OWNED_REPORT_CONTRACT" in line:
            skipping_contract_block = True
            continue
        if skipping_contract_block:
            if not line.strip():
                skipping_contract_block = False
            continue
        if any(label in line for label in INTERNAL_CODE_OWNED_LABELS):
            continue
        lines.append(line)
    return "\n".join(lines)


def _replace_raw_metric_field_names(markdown: str) -> str:
    replacements = {
        "event_scale": "模拟影响范围",
        "event_controversy": "模拟争议强度",
        "polarization_index": "模拟群体分化水平",
        "stance_delta": "立场变化幅度",
        "risk_score": "综合风险判断",
    }
    normalized = markdown
    for field_name in RAW_METRIC_FIELD_NAMES:
        normalized = normalized.replace(field_name, replacements[field_name])
    return normalized


def _replace_report_metric_terms(markdown: str) -> str:
    """Map legacy metric wording in the readable body while keeping appendix fields stable."""
    appendix_match = re.search(r"(?m)^##\s*五[、.．]\s*附录\s*$", markdown)
    if appendix_match:
        body = markdown[:appendix_match.start()]
        appendix = markdown[appendix_match.start():]
    else:
        body = markdown
        appendix = ""

    def replace_terms(text: str) -> str:
        normalized = text
        normalized = normalized.replace("情绪均值", "模拟立场均值")
        normalized = normalized.replace("x(t)均值", "模拟立场均值")
        normalized = normalized.replace("x(t)", "模拟立场均值")
        normalized = re.sub(r"(?<!模拟)立场均值", "模拟立场均值", normalized)
        normalized = re.sub(r"(?<!模拟)极化指数", "模拟极化指数", normalized)
        normalized = normalized.replace("关键拐点", "模拟关键变化点")
        normalized = re.sub(r"(?<!模拟)关键变化点", "模拟关键变化点", normalized)
        normalized = normalized.replace("拐点", "模拟关键变化点")
        normalized = normalized.replace("Tick", "轮次")
        return normalized

    body = replace_terms(body)
    appendix = replace_terms(appendix)
    return body + appendix


def _replace_reality_claims_about_inflection(markdown: str) -> str:
    boundary = (
        "本轮模拟显示出值得关注的模拟关键变化点。"
        "该节点仅代表本轮模拟设定下的演化特征，不等同于现实舆情传播中的真实转折。"
    )
    reality_patterns = (
        r"现实舆情已经出现拐点",
        r"现实舆情出现拐点",
        r"全网舆情发生转折",
        r"全网舆情已经转向",
        r"公众态度已经改变",
        r"公众态度发生转折",
        r"舆情已经发生转折",
        r"传播拐点已经出现",
        r"真实舆情拐点",
        r"现实传播拐点",
        r"第[一二三四五六七八九十\d]+轮出现现实舆情拐点",
        r"第[一二三四五六七八九十\d]+轮公众态度已经改变",
        r"第[一二三四五六七八九十\d]+轮现实舆情已经出现拐点",
    )
    normalized = markdown
    for pattern in reality_patterns:
        normalized = re.sub(pattern, boundary, normalized)
    return normalized


def _remove_metric_explanation_sections(markdown: str) -> str:
    metric_heading_pattern = (
        r"(?m)^###\s*(?:模拟参数说明|指标解释|指标说明|模拟指标说明|模拟参数解释)\s*$"
    )
    next_heading_pattern = r"(?m)^#{2,6}\s+"
    normalized = markdown
    while True:
        match = re.search(metric_heading_pattern, normalized)
        if not match:
            return normalized
        next_match = re.search(next_heading_pattern, normalized[match.end():])
        section_end = match.end() + next_match.start() if next_match else len(normalized)
        normalized = normalized[:match.start()].rstrip() + "\n\n" + normalized[section_end:].lstrip()


def _ensure_metric_explanation_prefill(markdown: str) -> str:
    normalized = _remove_metric_explanation_sections(markdown)
    if METRIC_EXPLANATION_PREFILL in normalized:
        return normalized

    appendix_match = re.search(r"(?m)^##\s*五[、.．]\s*附录\s*$", normalized)
    metric_block = f"### 指标解释\n\n{METRIC_EXPLANATION_PREFILL}\n\n"
    if appendix_match:
        insert_at = appendix_match.end()
        return normalized[:insert_at] + "\n\n" + metric_block + normalized[insert_at:].lstrip()
    return normalized.rstrip() + "\n\n## 五、附录\n\n" + metric_block.rstrip()


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
    return markdown.replace("待评估", "本轮模拟未发现显著模拟关键变化点")


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
    normalized = _replace_reality_claims_about_inflection(normalized)
    normalized = _replace_quote_fabrication_patterns(normalized)
    normalized = _replace_enterprise_pr_phrases(normalized)
    normalized = _replace_raw_metric_field_names(normalized)
    normalized = _replace_risk_section_with_code_owned(normalized, phase4_output)
    normalized = _replace_report_metric_terms(normalized)
    normalized = _ensure_metric_explanation_prefill(normalized)
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

    # 3. 轮次 0 发言
    lines.append("\n【轮次 0 事件实体发言】")
    tick_0_log = tick_logs[0] if tick_logs else None
    if tick_0_log:
        for entry in tick_0_log.entries:
            if entry.comment:
                lines.append(f"  [{entry.group_name}]: {entry.comment[:80]}...")

    # 4. 模拟立场演化数据
    lines.append("\n【模拟立场演化数据】")
    lines.append("轮次 | 模拟立场均值 | 标准差 | 模拟极化指数 | 关键变化")
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

    # 5. 模拟极化演化轨迹
    lines.append("\n【模拟极化演化轨迹】")
    pol_sequence = [f"{log.global_metrics.polarization_index:.2f}" for log in tick_logs if log.entries]
    lines.append(" → ".join(pol_sequence))
    if len(pol_sequence) >= 2:
        first_pol = float(pol_sequence[0])
        last_pol = float(pol_sequence[-1])
        change_pct = (last_pol - first_pol) / first_pol * 100 if first_pol > 0 else 0
        direction = "下降" if change_pct < 0 else "上升"
        lines.append(f"模拟极化指数从 {pol_sequence[0]} 变化到 {pol_sequence[-1]}，{direction} {abs(change_pct):.0f}%")

    # 6. code-owned grounding blocks
    lines.append("\n【CODE_OWNED_AGENT_STANCE_MATRIX】")
    lines.extend(_format_code_owned_agent_stance_matrix(tick_logs))

    lines.append("\n【CODE_OWNED_INFLECTION_POINTS】")
    inflection_points = identify_inflection_points(tick_logs, phase2_output) if phase2_output else []
    lines.extend(_format_code_owned_inflection_points(inflection_points))

    # 7. 模拟立场均值序列
    lines.append(f"\n【模拟立场均值序列】：{' → '.join([f'{x:.2f}' for x in x_t_sequence])}")

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
    """识别模拟关键变化点

    算法：
    1. 计算每轮的极化指数变化
    2. 极化指数变化最大的轮次为模拟关键变化点
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

        # 如果极化指数变化超过阈值，认为是模拟关键变化点
        if pol_delta > 0.1 and tick_logs[i].entries:
            # 找出本轮立场变化最大的 Agent
            max_entry = max(tick_logs[i].entries, key=lambda e: abs(e.stance_delta))

            node = node_map.get(max_entry.agent_id)

            inflection_points.append(InflectionPoint(
                tick=tick_logs[i].tick,
                agent_id=max_entry.agent_id,
                group_name=node.group_name if node else "未知",
                pivotal_comment=max_entry.comment[:50],
                impact_description=f"模拟极化指数变化 {pol_delta:.2f}，立场偏移 {max_entry.stance_delta:+.1f}",
            ))

    # 限制最多 3 个模拟关键变化点
    return inflection_points[:3]


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
    code_owned_contract_block = _build_code_owned_report_contract_block(
        extraction_output,
        tick_logs,
        x_t_sequence,
    )

    user_prompt = f"""请根据以下数据生成舆情风险研判报告：

{code_owned_contract_block}

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
    risk_level, risk_assessment = assess_risk(
        x_t_sequence,
        tick_logs,
        extraction_output=extraction_output,
    )

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
    risk_level, risk_assessment = assess_risk(
        x_t_sequence,
        tick_logs,
        extraction_output=extraction_output,
    )

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


def _primary_entity_name(extraction_output: EntityExtractionOutput) -> str:
    if extraction_output.event_entities:
        return extraction_output.event_entities[0].name
    return "相关主体"


def _spreader_group_names(extraction_output: EntityExtractionOutput) -> List[str]:
    return [spreader.group_name for spreader in extraction_output.opinion_spreaders]


def _representative_groups(extraction_output: EntityExtractionOutput) -> str:
    groups = _spreader_group_names(extraction_output)
    if not groups:
        return "高敏感质疑群体、等待事实补充的中间群体"
    return "、".join(groups[:3])


def _evolution_subject_structure_lines(
    phase4_output: Phase4Output,
    extraction_output: EntityExtractionOutput,
) -> List[str]:
    entity_name = _primary_entity_name(extraction_output)
    groups = _representative_groups(extraction_output)
    if phase4_output.audience_mode == AudienceMode.GENERIC_GOVERNMENT:
        return [
            f"本轮模拟中，{entity_name}是事件触发主体，但报告判断重点不放在主体声誉修复，而放在公共讨论如何从个案评价外溢为价值议题、行业规范或平台传播议题。依据是意见传播者已围绕{groups}形成不同理解路径，说明事件解释权不再只由触发主体掌握。",
            "其机制在于，企业、学校、协会或个人事件一旦被公共价值框架重新解释，外部发声主体、二次传播素材和围观群体会共同改变议题边界。治理含义是政府侧宜观察解释权是否继续外移，尤其关注行业组织、平台热点账号、关联机构等节点是否把事件推向更宽的公共规范讨论。",
        ]
    return [
        f"本轮模拟中，{entity_name}既是事件触发主体，也是潜在治理承压主体。主体与发声结构的核心变化，不是单一回应是否充分，而是处置程序、公开节点和协同口径是否被纳入公众审视。依据是{groups}围绕事实链和程序边界形成持续关注。",
        "其机制在于，涉及执法、监管或公共管理行为的事件更容易从个案事实转向治理能力评价。治理含义是相关部门需要观察上级部门、属地部门、行业主管部门之间是否出现口径差异，并把回应重点放在程序可核验、节点可追踪和边界可解释上。",
    ]


def _evolution_group_change_lines(
    phase4_output: Phase4Output,
    extraction_output: EntityExtractionOutput,
) -> List[str]:
    groups = _spreader_group_names(extraction_output)
    amplifier = groups[0] if groups else "高敏感质疑群体"
    buffer_group = groups[1] if len(groups) > 1 else "等待事实补充的中间群体"
    swing_group = groups[2] if len(groups) > 2 else "围观与二次传播群体"
    if not phase4_output.emotion_trajectory:
        trend_text = "当前缺少足够轨迹数据，群体变化只能作为持续观察项。"
    else:
        last = phase4_output.emotion_trajectory[-1]
        if last.polarization_index >= 0.5:
            trend_text = "模拟后段群体分化已经较为明显，风险放大器与缓冲层之间的解释差距扩大。"
        elif last.polarization_index >= 0.3:
            trend_text = "模拟后段群体分化处于中等水平，摇摆变量仍可能随新增信息改变判断。"
        else:
            trend_text = "模拟后段群体分化相对温和，缓冲层仍能吸收部分负向叙事。"
    return [
        f"{trend_text}其中，{amplifier}更可能承担风险放大器角色，推动事件从事实讨论转向责任、价值或程序判断；{buffer_group}更像缓冲层，其态度取决于事实链是否补齐、回应是否稳定；{swing_group}则是摇摆变量，可能在二创素材、外部表态或平台推荐机制影响下改变扩散方向。",
        "这一结构说明，治理观察不能只盯最终均值变化，而要识别哪些群体在改变议题解释框架。后续信号包括：风险放大器是否持续负向聚合，缓冲层是否被卷入站队，摇摆变量是否通过截图、短视频、话题标签等形式推动二次传播。",
    ]


def _evolution_stage_lines(phase4_output: Phase4Output) -> List[str]:
    if not phase4_output.emotion_trajectory:
        return [
            "第一阶段：输入信息不足期。当前模拟缺少足够轨迹数据，暂不形成阶段性扩散判断。治理含义是先补齐事实链和观察样本，避免过早定性；后续观察信号是新增主体发声是否改变事件解释框架。",
            "",
            "第二阶段：持续观察期。政府侧可关注后续新增信息是否改变群体分化结构，并预置必要的风险提示口径。若外部节点继续介入，应从一般监测转向协调研判，防止个案被重新包装为公共价值争议。",
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
        "第一阶段：争议触发期。事件进入模拟后，关注点首先集中在触发事实、责任边界和回应预期上。关键群体通常是直接受影响或高度敏感的讨论者；其机制在于初始信息不足会放大解释空间。治理含义是尽早识别公共风险焦点，避免讨论从事实疑问滑向价值对立；观察信号是外部主体是否开始替事件重新命名。",
        "",
        f"第二阶段：群体分化期。{second_feature}关键群体包括质疑方、等待事实补充的缓冲群体和可能推动二次传播的围观群体。{second_governance}后续观察信号是缓冲群体是否继续保持观望，还是被外部表态推向明确站队。",
        "",
        "第三阶段：外溢观察期。模拟后段需要判断争议是否从个案扩展到行业规范、平台传播或公共价值议题。治理含义是监测外溢路径、提示相关部门保持口径一致，并避免政府侧对企业或个人个案作过度介入；观察信号是二次传播素材、行业组织表态或跨平台话题是否重新激活讨论。",
    ]


def _key_insight_lines(
    phase4_output: Phase4Output,
    extraction_output: EntityExtractionOutput,
) -> List[str]:
    entity_name = _primary_entity_name(extraction_output)
    groups = _representative_groups(extraction_output)
    risk_types = "、".join(phase4_output.risk_type_labels) if phase4_output.risk_type_labels else "负面叙事聚合风险"
    return [
        f"1. 洞察：事件解释权可能从{entity_name}外移。依据：模拟中{groups}围绕同一触发事实形成差异化理解。机制：外部发声和二次传播会把个案重新解释为公共价值或程序边界问题。治理含义：政府侧应观察解释权是否继续外移，而不是替触发主体作声誉修复。",
        f"2. 洞察：主要风险类型需要被放回具体传播结构中理解。依据：代码侧风险标签为{risk_types}，但标签本身不能解释风险如何升级。机制：风险升级通常由高敏群体负向聚合、缓冲层失效和摇摆群体二次扩散共同推动。治理含义：监测重点应放在群体结构变化和触发信号上。",
        "3. 洞察：公共治理边界比单点回应更重要。依据：企业或非政府主体事件也可能触发公共价值讨论，但并不天然构成政府直接处置对象。机制：政府侧过度介入容易让个案行政化，介入不足又可能错过外溢预警。治理含义：宜采取监测、提示、协调和边界说明的轻量治理动作。",
        "4. 洞察：后续风险取决于新增节点是否改变叙事方向。依据：模拟轨迹中的阶段变化显示，讨论焦点会随关键群体和外部节点变化而迁移。机制：行业协会、平台热点账号、关联机构或主管部门表态都可能成为新的解释锚点。治理含义：应把新增发声主体作为观察信号，判断是否需要从常规监测转为协同研判。",
    ]


def _inflection_markdown_lines(phase4_output: Phase4Output) -> List[str]:
    if not phase4_output.inflection_points:
        return ["本轮模拟未发现显著模拟关键变化点。"]

    lines = [
        "本轮模拟中，以下变化点来自代码侧模拟关键变化点识别结果，仅用于解释模拟轨迹：",
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


def _conflict_focus_lines(phase4_output: Phase4Output) -> List[str]:
    if phase4_output.audience_mode == AudienceMode.GENERIC_GOVERNMENT:
        return [
            "1. 冲突双方：消费者、青年群体与触发事件的表达主体。核心争议：个案表达是否突破一般商业表达边界并触发公共价值不适。外溢风险：讨论可能从个案评价转向公序良俗、行业规范和平台传播责任。政府侧关注理由：该类争议虽不宜行政化处理，但需要监测价值议题是否跨圈层聚合。",
            "2. 冲突双方：行业规范期待与商业传播惯性。核心争议：商业传播是否把敏感价值符号作为注意力工具。外溢风险：同类行业或平台内容可能被连带审视，导致议题从单一主体扩展为行业风气讨论。政府侧关注理由：主管部门需要判断是否存在行业性风险提示需求，而不是替单一主体修复声誉。",
            "3. 冲突双方：多主体发声与事件解释权。核心争议：谁来定义事件性质、责任边界和公共意义。外溢风险：外部主体、热点账号和二次传播素材可能造成叙事碎片化。政府侧关注理由：解释权持续外移时，政府侧需要预置监测和协调机制，避免被动卷入。",
        ]
    return [
        "1. 冲突双方：直接处置主体与程序质疑群体。核心争议：处置依据、程序节点和回应节奏是否充分。外溢风险：个案事实争议可能转化为治理能力质疑。政府侧关注理由：涉及公共管理行为时，程序可解释性本身就是风险缓释条件。",
        "2. 冲突双方：属地回应节奏与公众透明预期。核心争议：信息公开是否及时、口径是否一致、责任边界是否清楚。外溢风险：回应滞后会放大信息不透明风险。政府侧关注理由：协同部门之间的口径差异可能成为新的争议触发点。",
        "3. 冲突双方：个案处置边界与公共治理评价。核心争议：公众是否把单一事件上升为制度性或区域性治理能力判断。外溢风险：讨论可能向上级部门、同类领域或其他公共管理场景传导。政府侧关注理由：需要提前判断是否从事实说明转入协同处置和节点公开。",
    ]


def _structural_risk_point_lines(phase4_output: Phase4Output) -> List[str]:
    risk_types = "、".join(phase4_output.risk_type_labels) if phase4_output.risk_type_labels else "负面叙事聚合风险"
    if phase4_output.audience_mode == AudienceMode.GENERIC_GOVERNMENT:
        first_name = "个案争议向公共价值议题外溢"
        first_focus = "事件从单一主体争议扩展为行业规范、公序良俗或平台传播议题"
        second_name = "多群体讨论导致叙事碎片化"
        second_focus = "不同群体围绕事实链、态度表达和责任边界形成分化理解"
        third_name = "二次传播重新激活低烈度风险"
        third_focus = "截图、短视频、二创话题或外部主体表态把已降温讨论重新推回公共视野"
    else:
        first_name = "程序性争议向治理能力质疑延展"
        first_focus = "事件被纳入执法、监管或公共管理程序是否充分的讨论框架"
        second_name = "属地回应时序不一致放大治理压力"
        second_focus = "多个部门或层级回应节奏不一致，导致公众对处置依据和责任边界继续追问"
        third_name = "个案处置争议向同类治理场景传导"
        third_focus = "公众把单一事件与同类执法、监管或公共管理场景进行类比，形成跨场景质疑"

    return [
        f"### （二）结构性风险点一：{first_name}",
        "",
        f"风险判断：本轮主要风险类型为{risk_types}，其具体表现之一是{first_name}。",
        f"触发机制：{first_focus}，并与本轮主要风险类型形成对应。",
        "关键群体：高敏感质疑群体、等待事实补充的中间群体，以及可能推动二次传播的围观群体。",
        "升级路径：如果事实链补充不足，讨论可能由个案评价扩展为公共价值站队或治理能力评价。",
        "缓释条件：政府侧保持关注和研判，协调相关主管部门提示信息披露边界，预置回应口径并监测外溢。",
        "政府侧观察信号：跨平台话题是否开始使用价值判断、行业规范或治理能力等更高层级框架重新命名事件。",
        "",
        f"### （三）结构性风险点二：{second_name}",
        "",
        f"风险判断：第二类风险表现为{second_name}，会提高后续沟通和风险提示难度。",
        f"触发机制：{second_focus}，使讨论从事实判断转向叙事竞争。",
        "关键群体：持续追问程序透明度的群体、情绪化扩散群体和具有缓冲作用的理性观察群体。",
        "升级路径：叙事碎片化后，单一说明难以覆盖多元关切，风险可能沿平台二次传播和跨圈层转述继续扩散。",
        "缓释条件：政府侧跟踪关键群体关切，协调信息口径，督促信息链条补齐可核验事实，并引导讨论回到事实和程序边界。",
        "政府侧观察信号：是否出现互不兼容的话题标签、剪辑素材、外部评论或多头表态。",
        "",
        f"### （四）结构性风险点三：{third_name}",
        "",
        f"风险判断：第三类风险表现为{third_name}，其危险不在单次声量，而在争议可被反复调用。",
        f"触发机制：{third_focus}，使原本可控的讨论获得新的传播理由。",
        "关键群体：平台二次创作者、关注公共价值议题的扩散群体、仍在等待事实补充的中间群体。",
        "升级路径：若新增节点继续带入情绪化标签，事件可能从短周期讨论转入反复复燃状态。",
        "缓释条件：政府侧保持轻量监测，必要时协调主管部门提示相关方统一事实边界，避免碎片信息持续制造误读。",
        "政府侧观察信号：旧素材是否被重新剪辑传播，关联主体是否继续发声，讨论是否跨入行业或公共管理议题。",
    ]


def _short_mid_term_risk_judgment(phase4_output: Phase4Output) -> str:
    if phase4_output.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        short_term = "短期内，争议仍可能围绕事实链、回应节奏和责任边界继续扩散。"
        mid_term = "中期看，如外部主体继续介入或平台二次传播形成固定标签，风险可能从单一事件转向公共价值、行业规范或治理能力评价。"
    elif phase4_output.risk_level == RiskLevel.MEDIUM:
        short_term = "短期内，事件处于可控但需持续观察的状态，新增信息会直接影响缓冲群体判断。"
        mid_term = "中期看，如事实补充不足或外部节点重新定义议题，风险可能从局部质疑转向更宽的公共讨论。"
    else:
        short_term = "短期内，事件整体仍处于低烈度观察阶段，重点是防止局部误读被重复传播。"
        mid_term = "中期看，如未出现新的外部表态或二次传播素材，风险大概率维持在常规监测范围。"
    return (
        f"{short_term}{mid_term}"
        "当出现青年或高敏群体持续负向聚合、行业协会或主管部门继续发声、平台二创素材扩散、"
        "争议被重新包装为行业伦理或公共治理议题等信号时，应从常规监测转向协调研判和风险提示。"
    )


def _governance_recommendation_lines(phase4_output: Phase4Output) -> List[str]:
    if phase4_output.audience_mode == AudienceMode.GENERIC_GOVERNMENT:
        return [
            "1. 治理动作：建立公共议题外溢监测清单，重点观察事件是否从个案争议扩展为行业规范、平台传播或价值观讨论。触发条件：跨平台话题开始使用公序良俗、行业伦理、价值冒犯等框架重新命名事件。介入边界：政府侧只做风险研判和提示，不替涉事主体解释商业表达。预期效果：及早识别公共价值议题外溢，减少后续被动卷入。",
            "2. 治理动作：跟踪高敏感群体、缓冲群体和摇摆群体的立场变化，形成阶段性研判。触发条件：高敏群体持续负向聚合，或缓冲群体由观望转向明确批评。介入边界：不把群体情绪直接等同于现实舆情结论，只作为模拟预警信号。预期效果：避免只看总体热度而忽略群体结构变化。",
            "3. 治理动作：协调行业主管或属地公共管理部门提示相关方补齐事实说明和信息边界。触发条件：外部主体继续发声、多头表态造成事实链混乱，或二次传播素材反复引用不完整信息。介入边界：协调对象是信息秩序和公共风险，不替企业、学校或协会写公关口径。预期效果：降低叙事碎片化，减少误读空间。",
            "4. 治理动作：预置政府侧风险提示口径，明确模拟推演属性、公共治理边界和后续观察重点。触发条件：争议被要求行政化处理，或公众开始把个案上升为行业治理责任。介入边界：不直接作责任判断，不启动超出事实基础的处置表态。预期效果：稳定政府侧表达边界，避免治理动作被误解为替主体背书或处罚。",
            "5. 治理动作：引导讨论回到事实链、程序边界和公共风险识别，必要时提示平台关注恶意剪辑、断章取义和情绪化标签。触发条件：旧素材被重新剪辑传播，或话题从事实讨论滑向对立站队。介入边界：不压制正常批评，不将企业个案泛化为行政事件。预期效果：降低价值议题过度外溢，维护理性讨论空间。",
        ]
    return [
        "1. 治理动作：关注程序争议的扩散方向，研判其是否从个案处置问题外溢为治理能力质疑。触发条件：讨论开始集中追问处置依据、公开节点或裁量边界。介入边界：先补齐程序解释，不抢先作责任判断。预期效果：把争议控制在事实和程序可核验范围内。",
        "2. 治理动作：跟踪关键群体对回应时序和信息透明度的追问，形成升级节点提示。触发条件：高敏群体持续要求公开材料，或中间群体开始认为回应不一致。介入边界：不以笼统安抚替代事实说明。预期效果：减少回应滞后引发的信息不透明风险。",
        "3. 治理动作：协调相关部门统一口径，补齐程序说明、公开节点和事实边界。触发条件：属地、上级或协同部门之间出现多头表态或口径差异。介入边界：只统一已核验事实和程序边界，不扩展到未核实个体责任判断。预期效果：降低口径冲突导致的治理压力。",
        "4. 治理动作：督促信息发布链条保持可核验、可追溯，必要时明确后续公开时间表。触发条件：平台讨论集中质疑材料缺失、节点模糊或回应延迟。介入边界：公开节奏服从事实核查，不为平息声量而仓促发布不完整结论。预期效果：缓释程序性质疑，稳定公众预期。",
        "5. 治理动作：在必要时推动上级指导和协同处置，建立跨部门通报机制。触发条件：个案讨论开始向同类治理场景或上级部门形象传导。介入边界：避免过度介入未核实个体责任，不把模拟研判直接等同现实处置结论。预期效果：防止局部程序争议扩散为更大范围的治理能力评价。",
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
        "### （一）主体与发声结构分析",
        "",
    ])

    lines.extend(_evolution_subject_structure_lines(phase4_output, extraction_output))

    lines.extend([
        "",
        "### （二）关键群体变化分析",
        "",
    ])

    lines.extend(_evolution_group_change_lines(phase4_output, extraction_output))

    lines.extend([
        "",
        "### （三）阶段演化分析",
        "",
    ])

    lines.extend(_evolution_stage_lines(phase4_output))

    lines.extend([
        "",
        "### （四）关键洞察",
        "",
    ])

    lines.extend(_key_insight_lines(phase4_output, extraction_output))

    lines.extend([
        "",
        "### 关键变化点",
        "",
    ])

    lines.extend(_inflection_markdown_lines(phase4_output))

    lines.extend([
        "",
        _code_owned_risk_section(phase4_output),
    ])

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
        "### 指标解释",
        "",
        METRIC_EXPLANATION_PREFILL,
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
        "- 模拟关键变化点表达以代码侧识别结果为准，不在正文中重新计算或补造模拟关键变化点。",
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
