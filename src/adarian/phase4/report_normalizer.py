"""Markdown normalization pipeline for Phase 4 reports."""

import re
from typing import List

from adarian.schemas import Phase4Output, RiskLevel
from .report_prompts import (
    ENTERPRISE_PR_FORBIDDEN_PHRASES,
    INTERNAL_CODE_OWNED_LABELS,
    METRIC_EXPLANATION_PREFILL,
    QUOTE_FABRICATION_PATTERNS,
    RAW_METRIC_FIELD_NAMES,
)
from .report_title import _ensure_metadata_header, _normalize_report_title_line


PROMPT_INSTRUCTION_LEAKAGE_PHRASES = (
    "Markdown 必须",
    "不得询问用户补充",
    "不得自行改写",
    "不得自行重算",
    "不得重算",
    "唯一数值来源",
    "唯一来源",
    "不得新增其他模拟关键变化点",
    "不得声称存在模拟关键变化点",
    "不得使用其他阈值自行识别",
    "请根据以下数据生成",
    "REPORT_USER_PROMPT_SUFFIX",
    "REPORT_SYSTEM_PROMPT",
)


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
    if phase4_output.audience_mode.value == "generic_government":
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
    if phase4_output.audience_mode.value == "generic_government":
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
        if any(phrase in line for phrase in PROMPT_INSTRUCTION_LEAKAGE_PHRASES):
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
        normalized = re.sub(r"(?<!模拟关键变化点)拐点", "模拟关键变化点", normalized)
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
