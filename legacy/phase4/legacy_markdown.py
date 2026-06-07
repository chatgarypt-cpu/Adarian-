"""
Legacy Phase 4 — 旧 Markdown 生成函数（pre-v1.3.1 归档）。

v1.3.1 归档说明：
  以下函数原位于 src/phase4/report_agent.py，用于旧路径手写 Markdown 生成。
  v1.3.0 后产品主流程使用 LLM 生成 Markdown，这些函数仅供 legacy 路径使用。
"""

from typing import List

from src.schemas import (
    AudienceMode, EntityExtractionOutput, Phase4Output,
)
from src.phase4.report_normalizer import (
    _code_owned_risk_section,
    _has_required_five_chapter_sections,
    _normalize_saved_markdown,
)
from src.phase4.report_title import _metadata_header
from src.phase4.report_prompts import (
    METRIC_EXPLANATION_PREFILL,
    SIMULATION_DISCLAIMER,
)

from .legacy_analytics import (
    risk_level_label_for,
    _risk_type_labels,
)


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


def generate_markdown_report(
    phase4_output: Phase4Output,
    extraction_output: EntityExtractionOutput,
) -> str:
    """生成 Markdown 格式报告（旧路径）"""
    from .legacy_analytics import _scale_description, _controversy_description

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
