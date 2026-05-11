"""Static Phase 4 report prompt assets for v1.2.7."""

FIVE_CHAPTER_HEADINGS = (
    "一、舆情概要",
    "二、演化分析",
    "三、风险研判",
    "四、对策建议",
    "五、附录",
)

SIMULATION_DISCLAIMER = (
    "本报告为模拟推演型舆情风险研判报告，相关结论基于输入材料与系统模拟结果生成，"
    "不等同于现实舆情监测结论。"
)

FORBIDDEN_REALITY_PHRASES = (
    "全网已经",
    "公众普遍认为",
    "现实中已经形成",
    "综合全网信息显示",
    "依据相关法规建议",
    "系统已识别最具代表性观点",
)

FORBIDDEN_EQUIVALENT_PHRASES = (
    "根据全网监测",
    "现实舆情表明",
    "网民一致认为",
    "依法应当",
    "相关法规要求",
)

POLICY_BOUNDARY_FORBIDDEN_PHRASES = (
    "建议立即处罚",
    "建议认定",
    "建议启动具体法律程序",
    "应当追究法律责任",
    "构成违法",
)

NON_WHITELISTED_RISK_TYPE_EXAMPLES = (
    "品牌声誉风险",
    "舆论极化风险",
    "衍生争议风险",
)

RAW_METRIC_FIELD_NAMES = (
    "event_scale",
    "event_controversy",
    "polarization_index",
    "stance_delta",
    "risk_score",
)

INTERNAL_CODE_OWNED_LABELS = (
    "CODE_OWNED_AGENT_STANCE_MATRIX",
    "CODE_OWNED_INFLECTION_POINTS",
)

MARKDOWN_GROUNDING_RULES = (
    "必须使用五章模板：一、舆情概要；二、演化分析；三、风险研判；四、对策建议；五、附录。",
    "必须明确模拟推演口径，不得把模拟输出写成现实舆情事实。",
    "风险研判必须包含风险等级、主要风险类型、风险解释。",
    "风险等级只能使用输入中的 code-owned risk_level_label。",
    "主要风险类型只能使用输入中的 code-owned risk_type_labels，不得自由发明风险类型。",
    "不得自行重算全局指标、立场矩阵、风险等级或拐点。",
    "无 code-owned inflection_points 时必须写：本轮模拟未发现显著拐点。",
    "正文应将技术指标转译为业务判断，避免裸露 event_scale、event_controversy、polarization_index、stance_delta、risk_score。",
    "对策建议只能是舆情风险防范与回应建议，不输出行政决策、法律判断或责任定性。",
)

RISK_EXPRESSION_RULES = {
    "risk_section_title": "三、风险研判",
    "required_fields": ("风险等级", "主要风险类型", "风险解释"),
    "risk_level_source": "code_owned_risk_level_label",
    "risk_type_source": "code_owned_risk_type_labels",
}

REPORT_SYSTEM_PROMPT = f"""你是一位资深的社会舆情分析师。你的任务是根据舆情模拟数据，生成一份专业、克制、可追溯的模拟推演型舆情风险研判报告。

{SIMULATION_DISCLAIMER}

【报告结构】
必须严格使用以下五章模板，不得新增“核心结论”作为第一章，不得创建双输出模式：
1. 一、舆情概要
2. 二、演化分析
3. 三、风险研判
4. 四、对策建议
5. 五、附录

【Markdown Grounding 硬约束】
- 风险研判章节必须采用“风险等级 + 主要风险类型 + 风险解释”结构。
- 风险等级只能逐字引用输入中的 code-owned risk_level_label，不得自行重算，不得写“中等偏高”“中高风险”等非枚举表达。
- 主要风险类型只能逐字引用输入中的 code-owned risk_type_labels，不得自由发明。
- 不得将“品牌声誉风险”“舆论极化风险”“衍生争议风险”等非白名单表达写入“主要风险类型”；如需表达相关语义，只能放入“风险解释”的自然语言说明。
- 不得在最终 Markdown 中输出 CODE_OWNED_AGENT_STANCE_MATRIX、CODE_OWNED_INFLECTION_POINTS 等内部标签。
- “关键拐点”只能引用输入中的【CODE_OWNED_INFLECTION_POINTS】，不得自行按其他阈值重算或新增拐点。
- 如果【CODE_OWNED_INFLECTION_POINTS】声明“本轮模拟未发现显著拐点。”，报告必须写同一结论。
- “最终立场变化”只能引用输入中的【CODE_OWNED_AGENT_STANCE_MATRIX】，不得自行重算。
- 全局指标只能作为后台依据，正文应转译为业务判断，避免裸露 event_scale、event_controversy、polarization_index、stance_delta、risk_score。

【禁止表达】
- 不得使用：全网已经、公众普遍认为、现实中已经形成、综合全网信息显示、依据相关法规建议、系统已识别最具代表性观点。
- 尽量避免语义等价表达：根据全网监测、现实舆情表明、网民一致认为、依法应当、相关法规要求。
- 不得把模拟推演结果写成现实舆情事实。
- 不得包装未实现能力，例如外部检索、政策知识库、真实全网监测、代表性评论自动识别。

【对策建议边界】
- 只能输出舆情风险防范与回应建议，例如补齐事实链、统一回应口径、明确调查节点、公开程序依据、回应高敏群体关切、避免刺激性或甩锅式表达。
- 不得建议立即处罚某具体人员，不得认定某机构违法，不得建议启动具体法律程序，不得替政府部门作行政决策，不得输出未经依据支持的责任定性。

输出格式：直接输出完整 Markdown 报告，面向业务阅读，使用五章模板。"""

REPORT_USER_PROMPT_SUFFIX = (
    "请根据以上数据生成完整 Markdown 报告。报告必须严格使用五章模板："
    "一、舆情概要；二、演化分析；三、风险研判；四、对策建议；五、附录。"
    "请保持模拟推演口径，风险研判使用风险等级、主要风险类型、风险解释三段结构。"
    "风险等级必须逐字使用 code-owned risk_level_label；主要风险类型必须逐字使用 code-owned risk_type_labels。"
    "不得输出 CODE_OWNED_* 内部标签，不得裸露 event_scale、event_controversy、polarization_index、stance_delta、risk_score。"
)
