"""
Phase 1: 实体提取与分类模块（Analyzer/Generator/Validator 协作架构）
---
通过 Analyzer/Generator/Validator 三阶段协作，实现实体分类（事件实体 vs 意见传播实体），
并通过迭代校验确保输出质量。

架构流程：
1. Analyzer：分析种子材料 → event_scale + event_controversy
2. Generator：提取事件实体 + 生成意见传播者
3. Validator：格式校验（失败则 Generator 重试）

为什么需要这个模块（Why）：
- v1.1.4 版本区分两种实体类型：事件实体（直接参与）和意见传播实体（评论事件）
- 事件实体作为第一批发言者，参与社交网络的核心传播
- 意见传播实体基于规模/争议性生成，必须关注事件实体才能发言

新增于：v1.1.4
修改于：v1.1.10（LLM1/2/3 → Analyzer/Generator/Validator）
"""

# ⚠️ LEGACY FILE — v1.1.14+ 已迁移到 src/phase1/
# 本文件保留用于兼容，新代码请使用 src/phase1/ 模块

import json
import ast
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console

import config
from src.llm_client import get_llm_client
from src.schemas import EntityExtractionOutput, Entity, OpinionSpreader, Relation

console = Console()


def _normalize_unescaped_quotes_inside_string_values(candidate: str) -> str:
    """LLM JSON 容错层：处理字符串 value 内部未转义引号。

    背景（Why）：
    LLM 可能返回 JSON 字符串 value 内部包含未转义英文双引号，如：
    {"event_summary": "深圳公交站引发"裸检"争议"}

    这不是 Unicode/UTF-8 冲突，而是 JSON 语法问题：
    - 外层 JSON 字符串用英文双引号包裹
    - value 内部又出现未转义英文双引号
    - json.loads 会把内部引号误判为字符串结束边界

    处理方式（状态机扫描）：
    - 使用字符级状态机遍历 JSON 文本
    - 区分 key 字符串（冒号前）和 value 字符串（冒号后）
    - 只处理 value 字符串内部的未转义引号
    - 不改变 JSON key 与结构边界
    - 使用启发式判断：value 内部引号后若非 , }] 则替换为单引号

    Args:
        candidate: 待解析的 JSON 字符串

    Returns:
        处理后的 JSON 字符串，value 内部未转义引号已替换为单引号

    新增于：v1.2.0（test7_1 白盒测试收口修复）
    """
    result = []
    i = 0
    n = len(candidate)

    # 状态机变量
    in_string = False          # 当前是否在 JSON 字符串内
    escape = False             # 上一个字符是否是反斜杠
    after_colon = False        # 当前是否在冒号后的 value 区域

    while i < n:
        ch = candidate[i]

        # 处理转义字符
        if escape:
            result.append(ch)
            escape = False
            i += 1
            continue

        if ch == '\\':
            result.append(ch)
            escape = True
            i += 1
            continue

        # 处理双引号（字符串边界或内部引号）
        if ch == '"':
            if not in_string:
                # 进入字符串
                in_string = True
                string_start_pos = i
                result.append(ch)
                # 检查是否在冒号后的 value 区域
                # 回溯找最近的冒号
                j = i - 1
                while j >= 0 and candidate[j] in ' \t\n\r':
                    j -= 1
                if j >= 0 and candidate[j] == ':':
                    after_colon = True
                else:
                    after_colon = False
            else:
                # 在字符串内遇到双引号
                # 判断这是字符串结束还是内部引号
                # 启发式：向后查看下一个有效字符
                j = i + 1
                while j < n and candidate[j] in ' \t\n\r':
                    j += 1

                if j < n and candidate[j] in ',}]':
                    # 这是 value 字符串结束边界
                    in_string = False
                    after_colon = False
                    result.append(ch)
                elif after_colon:
                    # 这是 value 内部未转义引号，替换为单引号
                    result.append("'")
                else:
                    # 这是 key 字符串结束（不应该有内部引号）
                    # 保守处理：保留原字符
                    in_string = False
                    result.append(ch)
            i += 1
            continue

        # 其他字符
        if ch == ':':
            result.append(ch)
            # 冒号后的空白跳过后，下一个字符串是 value
            # 但状态机会在下一个 " 进入时设置 after_colon
        elif ch == ',':
            result.append(ch)
            after_colon = False  # 新 key-value 开始
        elif ch in '{}[]':
            result.append(ch)
            if ch in '{}':
                after_colon = False  # 新对象/数组开始
        else:
            result.append(ch)

        i += 1

    return ''.join(result)


def _normalize_inner_cjk_quotes(candidate: str) -> str:
    """LLM JSON 兼容层：处理字符串值内部的中文弯引号。

    背景（Why）：
    LLM 可能返回包含中文弯引号的 JSON 字符串值，如：
    {"event_summary": "深圳公交站引发"裸检"争议"}

    中文弯引号 " (U+201C) 和 " (U+201D) 在 JSON 字符串值内部是合法字符，
    json.loads 可以正确解析。但如果 JSON 因其他原因失败后，
    fallback 到 ast.literal_eval 时，Python 解析器可能会误判。

    处理方式：
    - 将中文双引号 ""（U+201C/U+201D）替换为普通单引号 '（U+0027）
    - 将中文单引号 ''（U+2018/U+2019）替换为普通单引号 '（U+0027）
    - 不改变 JSON key 和结构边界（使用英文双引号 U+0022）

    Args:
        candidate: 待解析的 JSON 字符串

    Returns:
        处理后的 JSON 字符串，中文弯引号已替换为单引号

    新增于：v1.2.0（test7_1 白盒测试收口修复）
    """
    # 中文双引号：""（U+201C/U+201D）
    LEFT_CJK_DOUBLE_QUOTE = "“"  # "
    RIGHT_CJK_DOUBLE_QUOTE = "”"  # "
    LEFT_CJK_SINGLE_QUOTE = "‘"  # '
    RIGHT_CJK_SINGLE_QUOTE = "’"  # '
    ORDINARY_SINGLE_QUOTE = "'"  # U+0027

    result = candidate.replace(LEFT_CJK_DOUBLE_QUOTE, ORDINARY_SINGLE_QUOTE)
    result = result.replace(RIGHT_CJK_DOUBLE_QUOTE, ORDINARY_SINGLE_QUOTE)
    result = result.replace(LEFT_CJK_SINGLE_QUOTE, ORDINARY_SINGLE_QUOTE)
    result = result.replace(RIGHT_CJK_SINGLE_QUOTE, ORDINARY_SINGLE_QUOTE)
    return result


def _parse_json_candidate(candidate: str) -> Any:
    # 优先路径：直接 json.loads（合法 JSON 不允许被预处理污染）
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # normalization 层：处理常见 LLM 输出问题（保留原始行为）
    normalized = candidate.replace("{{", "{").replace("}}", "}")
    normalized = re.sub(r",(\s*[}\]])", r"\1", normalized)
    normalized = re.sub(r"\bNone\b", "null", normalized)
    normalized = re.sub(r"\bTrue\b", "true", normalized)
    normalized = re.sub(r"\bFalse\b", "false", normalized)

    # 第二次 json.loads 尝试（保留原始行为）
    try:
        return json.loads(normalized)
    except json.JSONDecodeError:
        pass

    # v1.2.0 新增：value 内部未转义引号容错层（状态机扫描）
    # 仅在 json.loads 失败后调用，不影响主路径
    normalized_fixed = _normalize_unescaped_quotes_inside_string_values(normalized)
    try:
        return json.loads(normalized_fixed)
    except json.JSONDecodeError:
        pass

    # v1.2.0 新增：中文弯引号兼容层
    normalized_cjk = _normalize_inner_cjk_quotes(normalized_fixed)
    try:
        return json.loads(normalized_cjk)
    except json.JSONDecodeError:
        pass

    # 末级 fallback：ast.literal_eval（保留原始行为，不强化为主路径）
    python_literal = re.sub(r"\btrue\b", "True", normalized_cjk)
    python_literal = re.sub(r"\bfalse\b", "False", python_literal)
    python_literal = re.sub(r"\bnull\b", "None", python_literal)
    return ast.literal_eval(python_literal)


def _parse_llm_json_payload(result: Any) -> Any:
    """尽量从 LLM 返回中提取顶层 JSON。"""
    if not isinstance(result, str):
        return result

    content = result.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return _parse_json_candidate(content)
    except (json.JSONDecodeError, ValueError, SyntaxError):
        pass

    object_start = content.find("{")
    object_end = content.rfind("}")
    if object_start != -1 and object_end != -1 and object_end > object_start:
        return _parse_json_candidate(content[object_start:object_end + 1])

    list_start = content.find("[")
    list_end = content.rfind("]")
    if list_start != -1 and list_end != -1 and list_end > list_start:
        return _parse_json_candidate(content[list_start:list_end + 1])

    raise json.JSONDecodeError("No JSON object found", content, 0)


def _coerce_top_level_object(payload: Any, source: str) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return payload

    if isinstance(payload, list):
        if len(payload) == 1 and isinstance(payload[0], dict):
            return payload[0]
        for item in payload:
            if isinstance(item, dict) and (
                "event_entities" in item or "opinion_spreaders" in item or "relations" in item or "pass" in item
            ):
                return item

    raise ValueError(f"{source} 返回顶层必须是 JSON object，当前为 {type(payload).__name__}")

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
# Validator: 格式校验
# =============================================================================

VALIDATOR_SYSTEM_PROMPT = """你是一位严格的格式校验专家。你的任务是检查输入的 JSON 是否符合要求。

【校验规则】
1. 必须是合法的 JSON 格式
2. 必须包含 event_entities 和 opinion_spreaders 两个数组
3. event_entities 中的每个元素必须有 entity_category = "event_entity"
4. opinion_spreaders 中的每个元素必须有 entity_category = "opinion_spreader"
5. event_entities + opinion_spreaders 总数 ≤ 15
6. 每个 opinion_spreader 必须有 related_event_entity 字段，且对应的实体在 event_entities 中存在
7. opinion_spreaders 的 estimated_percentage 之和 ≈ 100（允许 ±10 的误差）
8. I 必须为 1.0-10.0 之间的浮点数
9. P 必须为 +1 或 -1
10. susceptibility 必须为 0.0-1.0 之间的浮点数
11. 至少有一个 P=+1 和一个 P=-1（确保双向对立）
12. event_entities 至少要有 1 个实体
13. relations 字段是可选的，允许存在也可以不存在（不要对 relations 字段报错）
14. entity_category 字段：如果缺失，后处理会自动补充

# === v1.1.12 新增校验规则 ===
15. opinion_spreaders 中每个元素必须包含 persona_name、age_range、occupation、personality、motivation、typical_phrases 字段
16. typical_phrases 必须是长度为 2-3 的字符串数组
17. 不同 opinion_spreader 的 persona_name 不能重复
18. age_range 必须符合格式（如：18-24、25-34、35-45、45-60）

【重要】不要对 relations 字段报错，该字段是可选的。

【can_speak 合理性校验】
- 注意：can_speak 的检查由代码级后处理自动完成（_post_process_entities 函数）
- Validator 无需对 can_speak 报错，后处理会自动修正
- 如果发现 can_speak 问题，只需在 message 中提醒，不要作为 errors

【original_statement 合理性校验】
- 注意：original_statement 的检查由代码级后处理自动完成
- 如果 can_speak=false 但 original_statement 非 null，后处理会自动设为 null
- 如果发现问题，只需在 message 中提醒，不要作为 errors

【输出格式】
如果通过：
{{
  "pass": true,
  "message": "校验通过"
}}

如果不通过：
{{
  "pass": false,
  "errors": ["错误描述1", "错误描述2", ...]
}}
"""

VALIDATOR_USER_PROMPT = """请校验以下 JSON：

【种子材料】
{seed_text}

【待校验 JSON】
{json_content}
"""


# =============================================================================
# Analyzer: 设置参数
# =============================================================================

def analyzer_set_parameters(seed_text: str) -> Dict[str, Any]:
    """
    Analyzer: 分析种子材料，设置 event_scale 和 event_controversy

    Args:
        seed_text: 种子文本内容

    Returns:
        包含 event_scale、event_controversy、event_summary、event_type 的字典
    """
    llm = get_llm_client()

    user_prompt = ANALYZER_USER_PROMPT.format(seed_text=seed_text)

    console.print("[bold cyan]Analyzer:[/bold cyan] 正在分析事件参数...")

    result = llm.generate(
        system=ANALYZER_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,  # Analyzer 返回自由 JSON
    )

    try:
        params = _coerce_top_level_object(_parse_llm_json_payload(result), "Analyzer")
    except (json.JSONDecodeError, ValueError) as e:
        console.print(f"  [yellow]⚠[/yellow] Analyzer 返回格式错误: {e}")
        raise

    console.print(f"  [green]✓[/green] 事件规模: {params.get('event_scale', 'N/A')}")
    console.print(f"  [green]✓[/green] 事件争议性: {params.get('event_controversy', 'N/A')}")

    return params


# =============================================================================
# Generator: 生成实体
# =============================================================================

def generator_create_entities(
    seed_text: str,
    event_scale: float,
    event_controversy: float,
    event_type: str,
    event_summary: str,
    error_feedback: str = ""
) -> Dict[str, Any]:
    """
    Generator: 提取事件实体 + 生成意见传播者

    Args:
        seed_text: 种子文本内容
        event_scale: 事件规模
        event_controversy: 事件争议性
        event_type: 事件类型
        event_summary: 事件摘要
        error_feedback: 上一轮的错误反馈（用于重试）

    Returns:
        包含 event_entities, opinion_spreaders, relations 的字典
    """
    # Generator 使用较高的 temperature 使输出更发散
    from src.llm_client import LLMClient
    llm = LLMClient(temperature=0.7)

    user_prompt = GENERATOR_USER_PROMPT.format(
        seed_text=seed_text,
        event_scale=event_scale,
        event_controversy=event_controversy,
        event_type=event_type,
        event_summary=event_summary,
        error_feedback=error_feedback
    )

    console.print("[bold cyan]Generator:[/bold cyan] 正在提取事件实体与生成意见传播者...")

    result = llm.generate(
        system=GENERATOR_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,  # Generator 返回自由 JSON
    )

    try:
        entities_data = _coerce_top_level_object(_parse_llm_json_payload(result), "Generator")
    except (json.JSONDecodeError, ValueError, SyntaxError, TypeError) as e:
        # JSON 解析失败，抛出错误让上层重试
        raise ValueError(f"Generator 返回内容无法解析为 JSON: {e}\n原始内容: {result[:200] if result else '空'}")

    event_entities_count = len(entities_data.get('event_entities', []))
    opinion_spreaders_count = len(entities_data.get('opinion_spreaders', []))
    console.print(f"  [green]✓[/green] 事件实体: {event_entities_count}, 意见传播者: {opinion_spreaders_count}")

    # v1.1.11 后处理：自动修正常见错误
    entities_data = _post_process_entities(entities_data, seed_text)

    return entities_data


def _post_process_entities(
    entities_data: Dict[str, Any],
    seed_text: str
) -> Dict[str, Any]:
    """
    后处理：自动修正 Generator 生成的实体数据中的常见错误

    Args:
        entities_data: Generator 生成的原始数据
        seed_text: 种子文本（用于检查已故关键词）

    Returns:
        修正后的数据
    """
    import re

    # 0. 自动补充缺失的 entity_category 字段
    for entity in entities_data.get("event_entities", []):
        if "entity_category" not in entity:
            entity["entity_category"] = "event_entity"
            console.print(f"  [yellow]⚠[/yellow] 自动补充：{entity.get('name', '未知')} 的 entity_category")

    for spreader in entities_data.get("opinion_spreaders", []):
        if "entity_category" not in spreader:
            spreader["entity_category"] = "opinion_spreader"
            console.print(f"  [yellow]⚠[/yellow] 自动补充：{spreader.get('group_name', '未知')} 的 entity_category")

    # 1. 自动修正 can_speak（检查种子材料中是否有已故关键词）
    death_keywords = ["已故", "去世", "死亡", "离世", "身亡", "逝世", "轻生", "跳江", "跳楼", "自杀", "遇难"]
    seed_lower = seed_text.lower()

    for entity in entities_data.get("event_entities", []):
        entity_name = entity.get("name", "")
        entity_type = entity.get("type", "")
        # 检查实体名称或角色是否包含死亡关键词
        if any(kw in entity_name or kw in entity.get("role", "") for kw in death_keywords):
            if entity.get("can_speak", True):
                console.print(f"  [yellow]⚠[/yellow] 自动修正：{entity_name} 已故，can_speak 设为 false")
                entity["can_speak"] = False
        # 如果实体是个体且名字不在名称/角色中包含死亡关键词
        # 检查种子文本中该实体是否被描述为死亡主体（而非仅出现在死亡上下文中）
        elif entity_type == "individual" and entity.get("can_speak", True):
            # 检查种子文本中是否有"[实体]死亡/去世/..."的模式
            # 即：实体名称 + 死亡动词（0-10字间隔内），或者"已故的[实体]"
            name_escaped = re.escape(entity_name)
            # 模式1：实体名后紧跟死亡动词（0-10字间隔）
            pattern1 = f"{name_escaped}[.　]{{0,10}}(已故|去世|死亡|离世|身亡|逝世|轻生)"
            # 模式2：实体名前有死亡形容词修饰
            pattern2 = f"(已故|去世|死亡|离世|身亡|逝世|轻生)的{entity_name}"
            if re.search(pattern1, seed_text) or re.search(pattern2, seed_text):
                console.print(f"  [yellow]⚠[/yellow] 自动修正：{entity_name} 在种子材料中被描述为已故，can_speak 设为 false")
                entity["can_speak"] = False

    # 2. 自动修正 original_statement（如果 can_speak=false，original_statement 应为 null）
    for entity in entities_data.get("event_entities", []):
        if not entity.get("can_speak", True) and entity.get("original_statement"):
            # 如果实体不可发言，original_statement 应该为 null
            if entity["original_statement"] and len(entity["original_statement"]) > 0:
                console.print(f"  [yellow]⚠[/yellow] 自动修正：{entity.get('name')} 不可发言，original_statement 设为 null")
                entity["original_statement"] = None

    return entities_data


# =============================================================================
# Validator: 格式校验
# =============================================================================

def validator_check_format(
    json_content: Dict[str, Any],
    seed_text: str
) -> Dict[str, Any]:
    """
    Validator: 格式校验

    Args:
        json_content: 要校验的 JSON 数据
        seed_text: 种子文本内容（用于校验 can_speak 和 original_statement）

    Returns:
        校验结果 {"pass": bool, "message": str, "errors": List[str]}
    """
    llm = get_llm_client()

    user_prompt = VALIDATOR_USER_PROMPT.format(
        seed_text=seed_text,
        json_content=json.dumps(json_content, ensure_ascii=False)
    )

    console.print("[bold cyan]Validator:[/bold cyan] 正在校验格式...")

    result = llm.generate(
        system=VALIDATOR_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,  # Validator 返回自由 JSON
    )

    try:
        validation = _coerce_top_level_object(_parse_llm_json_payload(result), "Validator")
    except (json.JSONDecodeError, ValueError, SyntaxError, TypeError) as e:
        # JSON 解析失败，视为校验不通过
        console.print(f"  [yellow]⚠[/yellow] Validator 返回格式错误，视为校验失败")
        return {
            "pass": False,
            "message": "Validator 返回内容无法解析为 JSON",
            "errors": [f"JSON 解析错误: {str(e)}"]
        }

    if validation.get("pass"):
        console.print(f"  [green]✓[/green] {validation.get('message', '校验通过')}")
    else:
        errors = validation.get("errors", [])
        console.print(f"  [yellow]⚠[/yellow] 校验失败: {len(errors)} 个错误")
        for error in errors[:3]:  # 只显示前3个错误
            console.print(f"    - {error}")

    return validation

# =============================================================================
# 主函数：带迭代校验的实体提取
# =============================================================================

MAX_RETRIES = 3


def extract_entities_with_validation(seed_text: str) -> EntityExtractionOutput:
    """
    兼容入口：转发到 v1.1.14 的 Phase 1 Orchestrator。

    Args:
        seed_text: 种子文本内容

    Returns:
        EntityExtractionOutput: 包含 event_entities, opinion_spreaders 等
    """
    params = analyzer_set_parameters(seed_text)
    last_validation: Optional[Dict[str, Any]] = None
    error_feedback = ""

    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            console.print(f"[yellow]重试第 {attempt + 1}/{MAX_RETRIES} 轮...[/yellow]")

        try:
            entities_data = generator_create_entities(
                seed_text=seed_text,
                event_scale=params["event_scale"],
                event_controversy=params["event_controversy"],
                event_type=params["event_type"],
                event_summary=params["event_summary"],
                error_feedback=error_feedback,
            )
        except ValueError as e:
            last_validation = {
                "pass": False,
                "message": "Generator 输出解析失败",
                "errors": [str(e)],
            }
            error_feedback = (
                "上一轮输出未能解析为合法 JSON。"
                "请严格输出单个 JSON object，不要附带解释、不要使用双大括号模板。"
                f"\n- {e}"
            )
            continue

        validation = validator_check_format(entities_data, seed_text)
        last_validation = validation

        if validation.get("pass"):
            merged_output = {
                "event_summary": params["event_summary"],
                "event_scale": params["event_scale"],
                "event_controversy": params["event_controversy"],
                "event_type": params["event_type"],
                "event_entities": entities_data.get("event_entities", []),
                "opinion_spreaders": entities_data.get("opinion_spreaders", []),
                "relations": entities_data.get("relations", []),
            }
            return EntityExtractionOutput(**merged_output)

        errors = validation.get("errors", [])
        error_feedback = "\n".join(f"- {error}" for error in errors)

    raise ValueError(
        "Phase 1 校验失败，超过最大重试次数。"
        f" 最后一次校验结果: {last_validation}"
    )


# =============================================================================
# 兼容函数
# =============================================================================

def extract_entities(seed_text: str) -> EntityExtractionOutput:
    """
    兼容函数：直接调用 orchestrator 入口

    Args:
        seed_text: 种子文本内容

    Returns:
        EntityExtractionOutput
    """
    return extract_entities_with_validation(seed_text)


def extract_entities_from_file(seed_file: str) -> EntityExtractionOutput:
    """
    从种子文件提取实体

    Args:
        seed_file: 种子文件路径

    Returns:
        EntityExtractionOutput 对象
    """
    seed_text = Path(seed_file).read_text(encoding="utf-8")
    return extract_entities_with_validation(seed_text)


def save_entities_output(
    entities_output: EntityExtractionOutput,
    output_path: Optional[str] = None
) -> str:
    """
    保存实体提取结果到 JSON 文件

    Args:
        entities_output: 实体提取结果
        output_path: 输出路径

    Returns:
        保存的文件路径
    """
    if output_path is None:
        output_path = config.ENTITIES_OUTPUT_PATH
    else:
        output_path = Path(output_path)

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(entities_output.model_dump(), f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/green] 实体提取结果已保存至: {output_path}")

    return str(output_path)


# =============================================================================
# 主入口（可独立运行）
# =============================================================================

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 检查是否提供了种子文件路径
    if len(sys.argv) < 2:
        seed_file = Path(__file__).parent.parent / "seeds" / "example_event.txt"
        if not seed_file.exists():
            console.print("[bold red]错误：[/bold red] 未提供种子文件路径，且默认文件不存在")
            console.print(f"请将种子文本文件放入: seeds/")
            sys.exit(1)
    else:
        seed_file = Path(sys.argv[1])

    console.print(f"[bold]读取种子文本：[/bold] {seed_file}")

    # 提取实体
    entities_output = extract_entities_from_file(str(seed_file))

    # 保存结果
    output_path = save_entities_output(entities_output)

    # 打印摘要
    console.print("\n[bold]事件实体：[/bold]")
    for entity in entities_output.event_entities:
        console.print(f"  - {entity.name} ({entity.type}): {entity.role}")

    console.print(f"\n[bold]意见传播者：[/bold]")
    for spreader in entities_output.opinion_spreaders:
        console.print(f"  - {spreader.group_name} (关联: {spreader.related_event_entity})")
        console.print(f"    I={spreader.I}, P={spreader.P}, susceptibility={spreader.susceptibility}")

    console.print(f"\n[bold]关系：[/bold]")
    for relation in entities_output.relations:
        console.print(f"  - {relation.source} --[{relation.type}]--> {relation.target}")
