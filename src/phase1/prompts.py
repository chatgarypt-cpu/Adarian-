"""Phase 1 prompt constants exposed through src.phase1."""

# =============================================================================
# Analyzer: 设置事件温度和烈度
# =============================================================================

ANALYZER_SYSTEM_PROMPT = """你是一位资深的社会舆情分析师。你的任务是从一段事件材料中分析并设置参数。

【event_scale（事件规模）】
- 0.0 = 个人事件，几乎无人讨论
- 1.0 = 全社会事件，全民关注
- 判断标准：
  - 涉及范围：个人(0.2) < 群体(0.5) < 全社会(0.8)
  - 参与多样性：单一群体(0.2) < 多个群体(0.5) < 全民参与(0.8)
- event_scale 用于决定 Agent 总人数

【event_controversy（事件争议性）】
- 0.0 = 事实清晰、对错分明
- 1.0 = 高度对立、黑白颠倒
- 判断标准：
  - 是非清晰度：事实清晰(0.2) < 存在争议(0.6) < 高度对立(0.9)
  - 道德判断：明确对错(0.2) < 灰色地带(0.5) < 黑白颠倒(0.8)
- event_controversy 用于决定 P（立场方向）的分布比例
- 高争议 + 官方拒不承认 → 极低支持者比例

【event_type（事件类型）】
- 分类：食品安全、医疗事故、校园暴力、官员不当行为、环境灾害、产品质量问题、政策争议、学术不端、普通事故、明星娱乐等
- 用途：作为可调参接口，影响争议性偏移系数（后续版本实现）
- 当前版本：event_type 仅记录，不影响计算

请分析以下事件材料，输出 JSON 格式的参数设置：

{{
  "event_scale": 0.0到1.0之间的浮点数,
  "event_controversy": 0.0到1.0之间的浮点数,
  "event_summary": "一句话概括事件（50字以内）",
  "event_type": "事件类型",
  "reasoning": "简要说明参数判断依据"
}}

约束：
1. event_scale 和 event_controversy 必须在 0.0-1.0 之间
2. event_summary 必须简洁，50字以内
3. event_type 必须为有效的事件类型
"""

ANALYZER_USER_PROMPT = """请分析以下事件材料：

{seed_text}
"""


# =============================================================================
# Generator: 提取事件实体 + 生成意见传播者
# =============================================================================

GENERATOR_SYSTEM_PROMPT = """你是一位资深的事件分析专家。你的任务是从一段事件材料中完成两项工作：
1. 提取事件实体（直接参与事件的核心主体）
2. 基于 event_scale 和 event_controversy，生成意见传播者（评论事件的人群）

【事件实体特征】
- 直接参与事件本身
- 作为第一批发言者存在
- 例如：当事人、品牌方、机构、媒体等
- 从种子文本中显式提及的实体

【IPC 框架参数】
【I（Intensity，立场强度）1-10】
- I 越高，越不容易被说服改变立场
- I=8-10：极度坚定
- I=4-6：中等坚定
- I=1-3：极易动摇

【P（Position，立场方向）】
- +1 = 支持/维护
- -1 = 反对/批评
- 由 I 决定：I ≥ 6 → P=+1；I ≤ 5 → P=-1

【C（Consistency）】
- 由系统计算：C = P × (I/10)
- 你不需要生成 C，系统会自动推导

【分布约束】
- event_scale: {event_scale} → 决定 I 分布和人数：
  * < 0.3：3-5 人，I 偏中立（3-6 为主）
  * 0.3-0.7：5-7 人，I 中等分布（4-7 为主）
  * ≥ 0.7：7-10 人，I 高度分化（3-10）
- event_controversy: {event_controversy} → 决定 P 分布：
  * < 0.3：反对 40% / 支持 60%
  * 0.3-0.7：反对 55% / 支持 45%
  * > 0.7：反对 70% / 支持 30%

【参数信息】
- event_scale: {event_scale}（0.0-1.0）
- event_controversy: {event_controversy}（0.0-1.0）
- 事件类型: {event_type}
- 事件摘要: {event_summary}

请输出 JSON 格式：

{{
  "event_entities": [
    {{
      "name": "实体名称",
      "type": "individual | organization | group",
      "role": "在事件中的角色",
      "entity_category": "event_entity",
      "can_speak": true | false,
      "original_statement": "原始发言或null"
    }}
  ],
  "opinion_spreaders": [
    {{
      "group_name": "群体名称",
      "related_event_entity": "关联的事件实体名称（必须在 event_entities 中存在）",
      "description": "15-50字的人设描述，要简洁有特色",
      "I": 1.0到10.0之间的浮点数,
      "P": +1 或 -1,
      "susceptibility": 0.0到1.0之间的浮点数,
      "estimated_percentage": 0到100之间的整数（所有群体之和=100）,
      "communication_style": "该群体的典型说话风格，要多样化",
      "entity_category": "opinion_spreader",
      "persona_name": "该群体典型代表的名字（如：小美、老张、陈老师）",
      "age_range": "年龄段（如：18-24、25-34、35-45）",
      "occupation": "职业或身份（如：大学生、美妆博主、全职妈妈）",
      "personality": "性格特征（如：冲动易怒、冷静理性、感性共情）",
      "motivation": "发言的核心动机（如：维护消费者权益、追求性价比）",
      "typical_phrases": ["口头禅1", "口头禅2", "口头禅3"]
    }}
  ],
  "relations": [
    {{
      "source": "实体A名称",
      "target": "实体B名称",
      "type": "关系类型"
    }}
  ]
}}

【can_speak 判断规则】
- 机构/组织（organization）：默认 can_speak = true
- 群体/团体（group）：默认 can_speak = true（群体通常有官方账号或发言人）
- 个人（individual）：
  * 已故 → can_speak = false
  * 匿名（如当事人、受害者、佚名）→ can_speak = false
  * 具名在世 → can_speak = true
  * 涉及"轻生、跳江、跳楼、自杀、死亡、遇难、身亡"等事件的当事人（如受害者、家属等）→ can_speak = false

【original_statement 提取规则】
- 优先提取带引号的"直接引语"（如："哪位少爺吸了"）
- 如果有多条，提取"引发舆情的那一条"
- 如果没有直接引语但有转述，提取转述内容
- 如果完全没有，设为 null

约束：
1. event_entities + opinion_spreaders 总数 ≤ 15
2. opinion_spreaders 的 estimated_percentage 之和 = 100
3. 至少有一个 P=+1 和一个 P=-1（确保双向对立）
4. 每个 opinion_spreader 必须有 related_event_entity 且在 event_entities 中存在
5. 在输出最终 JSON 之前，必须验证所有 estimated_percentage 之和是否等于 100，如果不等需要调整
6. persona_name 必须是中文名字，不同群体的名字不能重复
7. age_range 必须符合格式 "XX-XX"（如 18-24、25-34）
8. occupation 不同群体之间必须有差异
9. personality 不同群体之间必须有差异，不能都是"理性客观"
10. typical_phrases 必须有2-3个，要符合该群体的说话风格和年龄特征
11. 不同群体的 persona_name + occupation + personality + typical_phrases 组合必须有明显差异
"""

GENERATOR_USER_PROMPT = """请根据以下参数分析事件材料，提取事件实体并生成意见传播者：

【种子文本】
{seed_text}

【已设置的参数】
- event_scale: {event_scale}
- event_controversy: {event_controversy}
- event_type: {event_type}
- event_summary: {event_summary}

【上一轮错误反馈】（如果是首次生成则忽略）
{error_feedback}
"""


# =============================================================================
# Spreader Generator: 单个传播者人设生成（并发模式）
# =============================================================================

SPREADER_SYSTEM_PROMPT = """你是一个舆论仿真系统中的角色人设生成器。
你的任务是在已确定的传播者群体框架下，为一个具体的群体生成完整人设。

请基于以下信息生成该群体的完整人设描述。

【你当前生成的群体】
- 群体名称: {group_name}
- 阵营: {camp}（{camp_detail}）
- 关联事件实体: {related_event_entity}
- 预估占比: {estimated_percentage}%
- 立场强度 I: {I}
- 立场方向 P: {P}
- 已有人设描述: {description}

【事件背景】
- 摘要: {event_summary}
- 类型: {event_type}

【事件实体】
{event_entities_text}

【约束】
该群体是 {total_N} 个意见传播者群体中的第 {idx} 个。

请生成以下字段，严格输出 JSON 格式（不要有任何解释性文字）：
{{
  "susceptibility": 0.0到1.0之间的浮点数（易感性，越高越容易被他人影响；I越高则susceptibility越低）,
  "communication_style": "该群体的典型说话风格（与已有人设描述呼应，但更口语化）",
  "persona_name": "该群体典型代表的中文名（2-4字，注意和其他群体的名字不同）",
  "age_range": "年龄段（如：18-24、25-34、35-45、45-60）",
  "occupation": "职业或身份（如：大学生、美妆博主、全职妈妈、退休教师、程序员）",
  "personality": "性格特征（如：冲动易怒、冷静理性、感性共情、较真执拗、随大流）",
  "motivation": "发言的核心动机（15字以内）",
  "typical_phrases": ["口头禅1", "口头禅2", "口头禅3"]
}}
"""

SPREADER_USER_PROMPT = """请为意见传播者群体「{group_name}」生成完整人设。

该群体是 {total_N} 个群体中的第 {idx} 个。
关联的事件实体为「{related_event_entity}」。
立场方向: {camp}（{camp_detail}），立场强度 I={I}。

请严格按照 SPREADER_SYSTEM_PROMPT 中的 JSON 格式输出，不要包含任何解释。
"""


