"""
Phase 1: 实体提取与分类模块（LLM1/2/3 协作架构）
---
通过 LLM1/2/3 三阶段协作，实现实体分类（事件实体 vs 意见传播实体），
并通过迭代校验确保输出质量。

架构流程：
1. LLM1：分析种子材料 → event_temperature + event_intensity
2. LLM2：提取事件实体 + 生成意见传播者
3. LLM3：格式校验（失败则 LLM2 重试）

为什么需要这个模块（Why）：
- v1.1.4 版本区分两种实体类型：事件实体（直接参与）和意见传播实体（评论事件）
- 事件实体作为第一批发言者，参与社交网络的核心传播
- 意见传播实体基于温度/烈度生成，必须关注事件实体才能发言

新增于：v1.1.4
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console

from src.llm_client import get_llm_client
from src.schemas import EntityExtractionOutput, Entity, OpinionSpreader, Relation

console = Console()

# =============================================================================
# LLM1: 设置事件温度和烈度
# =============================================================================

LLM1_SYSTEM_PROMPT = """你是一位资深的社会舆情分析师。你的任务是从一段事件材料中分析并设置两个关键参数。

【事件温度（event_temperature）】
- 0.0 = 冷门事件，几乎无人讨论
- 1.0 = 全网热议，全民关注
- 判断标准：
  - 涉及范围：个人事件(0.2) < 群体事件(0.5) < 全社会事件(0.8)
  - 争议性：事实清晰(0.3) < 存在争议(0.6) < 高度对立(0.9)
  - 社会影响：局部(0.2) < 行业(0.5) < 全国(0.8)
- 综合三个维度取平均值

【事件烈度（event_intensity）】
- 0.0 = 事件烈度极低，只有少量客观网友简单评价
- 1.0 = 事件烈度极高，引发大规模、多样化的舆论反应
- 判断标准：
  - 情绪强度：平和(0.2) < 激动(0.5) < 愤怒(0.8) < 疯狂(1.0)
  - 参与多样性：单一群体(0.2) < 多个群体(0.5) < 全民参与(0.8)
  - 烈度高时会出现多种类型的意见传播者（粉丝、专家、批评者、支持者等）
  - 烈度低时只有少量客观网友评价

请分析以下事件材料，输出 JSON 格式的参数设置：

{{
  "event_temperature": 0.0到1.0之间的浮点数,
  "event_intensity": 0.0到1.0之间的浮点数,
  "event_summary": "一句话概括事件（50字以内）",
  "event_type": "事件类型（如：产品质量危机、校园冲突、政策争议）",
  "reasoning": "简要说明为什么这样设置"
}}

约束：
1. event_temperature 和 event_intensity 必须在 0.0-1.0 之间
2. event_summary 必须简洁，50字以内
"""

LLM1_USER_PROMPT = """请分析以下事件材料：

{seed_text}
"""


# =============================================================================
# LLM2: 提取事件实体 + 生成意见传播者
# =============================================================================

LLM2_SYSTEM_PROMPT = """你是一位资深的事件分析专家。你的任务是从一段事件材料中完成两项工作：
1. 提取事件实体（直接参与事件的核心主体）
2. 基于事件温度和烈度，生成意见传播者（评论事件的人群）

【事件实体特征】
- 直接参与事件本身
- 作为第一批发言者存在
- 例如：当事人、品牌方、机构、媒体等
- 从种子文本中显式提及的实体

【意见传播者特征】
- 不直接参与事件，但会传播意见
- 基于事件温度和烈度生成：
  - event_temperature < 0.3：极端派占比 < 20%
  - event_temperature >= 0.5：极端派占比 30-50%
  - event_intensity 高：多种类型（粉丝、专家、批评者、支持者）
  - event_intensity 低：少量客观网友
- 每个意见传播者必须关联到一个事件实体
- 所有事件实体 + 意见传播者总数 ≤ 15

【参数信息】
- event_temperature: {event_temperature}（0.0-1.0）
- event_intensity: {event_intensity}（0.0-1.0）
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
      "stance_score": 1.0到10.0之间的浮点数（1=强烈支持，10=强烈批评）,
      "susceptibility": 0.0到1.0之间的浮点数,
      "confirmation_bias_level": "none | weak | strong",
      "estimated_percentage": 0到100之间的整数（所有群体之和=100）,
      "communication_style": "该群体的典型说话风格，要多样化",
      "entity_category": "opinion_spreader"
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

【original_statement 提取规则】
- 优先提取带引号的"直接引语"（如："哪位少爺吸了"）
- 如果有多条，提取"引发舆情的那一条"
- 如果没有直接引语但有转述，提取转述内容
- 如果完全没有，设为 null

约束：
1. event_entities + opinion_spreaders 总数 ≤ 15
2. opinion_spreaders 的 estimated_percentage 之和 = 100
3. 至少包含一个 stance_score < 3.0 和一个 > 7.0 的群体
4. 每个 opinion_spreader 必须有 related_event_entity 且在 event_entities 中存在
5. 在输出最终 JSON 之前，必须验证所有 estimated_percentage 之和是否等于 100，如果不等需要调整
"""

LLM2_USER_PROMPT = """请根据以下参数分析事件材料，提取事件实体并生成意见传播者：

【种子文本】
{seed_text}

【已设置的参数】
- event_temperature: {event_temperature}
- event_intensity: {event_intensity}
- event_type: {event_type}
- event_summary: {event_summary}

【上一轮错误反馈】（如果是首次生成则忽略）
{error_feedback}
"""


# =============================================================================
# LLM3: 格式校验
# =============================================================================

LLM3_SYSTEM_PROMPT = """你是一位严格的格式校验专家。你的任务是检查输入的 JSON 是否符合要求。

【校验规则】
1. 必须是合法的 JSON 格式
2. 必须包含 event_entities 和 opinion_spreaders 两个数组
3. event_entities 中的每个元素必须有 entity_category = "event_entity"
4. opinion_spreaders 中的每个元素必须有 entity_category = "opinion_spreader"
5. event_entities + opinion_spreaders 总数 ≤ 15
6. 每个 opinion_spreader 必须有 related_event_entity 字段，且对应的实体在 event_entities 中存在
7. opinion_spreaders 的 estimated_percentage 之和 ≈ 100（允许 ±5 的误差）
8. 至少包含一个 stance_score < 3.0 和一个 > 7.0 的群体
9. event_entities 至少要有 1 个实体
10. relations 字段是可选的，允许存在也可以不存在（不要对 relations 字段报错）

【重要】不要对 relations 字段报错，该字段是可选的。

【can_speak 合理性校验】
- 检查种子材料中是否有"已故"、"去世"、"死亡"、"离世"、"身亡"等关键词
  * 如果有，检查对应实体的 can_speak 是否为 false
  * 如果 can_speak 为 true 而实体已故，报错："XXX 已故，can_speak 应为 false"
- 检查是否有"匿名"、"佚名"、"网友"等匿名表述
  * 如果有，检查对应实体的 can_speak 是否为 false
  * 注意："当事人"、"受害者"等主体可以正常发言（can_speak 可以为 true）

【original_statement 合理性校验】
- 如果 original_statement 不为 null，检查种子材料中是否确实有该发言
- 如果种子材料中没有，提示："original_statement 与种子材料不符，请确认或设为 null"

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

LLM3_USER_PROMPT = """请校验以下 JSON：

【种子材料】
{seed_text}

【待校验 JSON】
{json_content}
"""


# =============================================================================
# LLM1: 设置参数
# =============================================================================

def llm1_set_parameters(seed_text: str) -> Dict[str, Any]:
    """
    LLM1: 分析种子材料，设置 event_temperature 和 event_intensity

    Args:
        seed_text: 种子文本内容

    Returns:
        包含 event_temperature, event_intensity, event_summary, event_type 的字典
    """
    llm = get_llm_client()

    user_prompt = LLM1_USER_PROMPT.format(seed_text=seed_text)

    console.print("[bold cyan]LLM1:[/bold cyan] 正在分析事件参数...")

    result = llm.generate(
        system=LLM1_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,  # LLM1 返回自由 JSON
    )

    # 解析 JSON
    if isinstance(result, str):
        params = json.loads(result)
    else:
        params = result

    console.print(f"  [green]✓[/green] 事件温度: {params.get('event_temperature', 'N/A')}")
    console.print(f"  [green]✓[/green] 事件烈度: {params.get('event_intensity', 'N/A')}")

    return params


# =============================================================================
# LLM2: 生成实体
# =============================================================================

def llm2_generate_entities(
    seed_text: str,
    event_temperature: float,
    event_intensity: float,
    event_type: str,
    event_summary: str,
    error_feedback: str = ""
) -> Dict[str, Any]:
    """
    LLM2: 提取事件实体 + 生成意见传播者

    Args:
        seed_text: 种子文本内容
        event_temperature: 事件温度
        event_intensity: 事件烈度
        event_type: 事件类型
        event_summary: 事件摘要
        error_feedback: 上一轮的错误反馈（用于重试）

    Returns:
        包含 event_entities, opinion_spreaders, relations 的字典
    """
    # LLM2 使用较高的 temperature 使输出更发散
    from src.llm_client import LLMClient
    llm = LLMClient(temperature=0.7)

    user_prompt = LLM2_USER_PROMPT.format(
        seed_text=seed_text,
        event_temperature=event_temperature,
        event_intensity=event_intensity,
        event_type=event_type,
        event_summary=event_summary,
        error_feedback=error_feedback
    )

    console.print("[bold cyan]LLM2:[/bold cyan] 正在提取事件实体与生成意见传播者...")

    result = llm.generate(
        system=LLM2_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,  # LLM2 返回自由 JSON
    )

    # 解析 JSON，增加错误处理
    try:
        if isinstance(result, str):
            # 尝试提取 JSON 部分
            result = result.strip()
            # 处理可能的 markdown 代码块
            if result.startswith("```json"):
                result = result[7:]
            elif result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()
            entities_data = json.loads(result)
        else:
            entities_data = result
    except (json.JSONDecodeError, Exception) as e:
        # JSON 解析失败，抛出错误让上层重试
        raise ValueError(f"LLM2 返回内容无法解析为 JSON: {e}\n原始内容: {result[:200] if result else '空'}")

    event_entities_count = len(entities_data.get('event_entities', []))
    opinion_spreaders_count = len(entities_data.get('opinion_spreaders', []))
    console.print(f"  [green]✓[/green] 事件实体: {event_entities_count}, 意见传播者: {opinion_spreaders_count}")

    return entities_data


# =============================================================================
# LLM3: 格式校验
# =============================================================================

def llm3_validate(json_content: Dict[str, Any], seed_text: str) -> Dict[str, Any]:
    """
    LLM3: 格式校验

    Args:
        json_content: 要校验的 JSON 数据
        seed_text: 种子文本内容（用于校验 can_speak 和 original_statement）

    Returns:
        校验结果 {"pass": bool, "message": str, "errors": List[str]}
    """
    llm = get_llm_client()

    user_prompt = LLM3_USER_PROMPT.format(
        seed_text=seed_text,
        json_content=json.dumps(json_content, ensure_ascii=False)
    )

    console.print("[bold cyan]LLM3:[/bold cyan] 正在校验格式...")

    result = llm.generate(
        system=LLM3_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,  # LLM3 返回自由 JSON
    )

    # 解析 JSON，增加错误处理
    try:
        if isinstance(result, str):
            # 尝试提取 JSON 部分
            result = result.strip()
            # 处理可能的 markdown 代码块
            if result.startswith("```json"):
                result = result[7:]
            elif result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()
            validation = json.loads(result)
        else:
            validation = result
    except json.JSONDecodeError as e:
        # JSON 解析失败，视为校验不通过
        console.print(f"  [yellow]⚠[/yellow] LLM3 返回格式错误，视为校验失败")
        return {
            "pass": False,
            "message": "LLM 返回内容无法解析为 JSON",
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
    带迭代校验的实体提取

    流程：
    1. LLM1：设置 event_temperature + event_intensity
    2. LLM2：提取事件实体 + 生成意见传播者
    3. LLM3：校验格式
    4. 如果不通过，反馈错误给 LLM2，重新生成
    5. 最多重试 MAX_RETRIES 次

    Args:
        seed_text: 种子文本内容

    Returns:
        EntityExtractionOutput: 包含 event_entities, opinion_spreaders 等
    """
    console.print("[bold cyan]Phase 1:[/bold cyan] 开始实体提取与分类（LLM1/2/3 协作）...")

    # Step 1: LLM1 设置参数
    params = llm1_set_parameters(seed_text)
    event_temperature = params["event_temperature"]
    event_intensity = params["event_intensity"]
    event_summary = params["event_summary"]
    event_type = params["event_type"]

    # Step 2-4: LLM2 生成 + LLM3 校验（迭代）
    for attempt in range(MAX_RETRIES):
        # LLM2 生成
        entities_data = llm2_generate_entities(
            seed_text=seed_text,
            event_temperature=event_temperature,
            event_intensity=event_intensity,
            event_type=event_type,
            event_summary=event_summary,
            error_feedback=""
        )

        # LLM3 校验
        validation = llm3_validate(entities_data, seed_text)

        if validation["pass"]:
            # 通过校验，构建输出
            console.print(f"[green]✓[/green] LLM3 校验通过（第 {attempt + 1} 次）")

            # 构建 EntityExtractionOutput
            event_entities = [
                Entity(**e) for e in entities_data.get("event_entities", [])
            ]
            opinion_spreaders = [
                OpinionSpreader(**o) for o in entities_data.get("opinion_spreaders", [])
            ]
            relations = [
                Relation(**r) for r in entities_data.get("relations", [])
            ]

            return EntityExtractionOutput(
                event_summary=event_summary,
                event_temperature=event_temperature,
                event_intensity=event_intensity,
                event_type=event_type,
                event_entities=event_entities,
                opinion_spreaders=opinion_spreaders,
                relations=relations
            )

        # 不通过，收集错误反馈给 LLM2 重试
        errors = validation.get("errors", [])
        error_feedback = "\n".join([f"- {e}" for e in errors])
        console.print(f"[yellow]⚠[/yellow] LLM3 校验失败，准备重试（第 {attempt + 1}/{MAX_RETRIES} 次）...")

        # 在下一次迭代时传入错误反馈
        if attempt < MAX_RETRIES - 1:
            entities_data = llm2_generate_entities(
                seed_text=seed_text,
                event_temperature=event_temperature,
                event_intensity=event_intensity,
                event_type=event_type,
                event_summary=event_summary,
                error_feedback=error_feedback
            )
            validation = llm3_validate(entities_data, seed_text)
            if validation["pass"]:
                break

    # 达到最大重试次数，使用最后一次结果
    console.print(f"[yellow]⚠[/yellow] 达到最大重试次数，使用最后一次结果")

    event_entities = [
        Entity(**e) for e in entities_data.get("event_entities", [])
    ]
    opinion_spreaders = [
        OpinionSpreader(**o) for o in entities_data.get("opinion_spreaders", [])
    ]
    relations = [
        Relation(**r) for r in entities_data.get("relations", [])
    ]

    return EntityExtractionOutput(
        event_summary=event_summary,
        event_temperature=event_temperature,
        event_intensity=event_intensity,
        event_type=event_type,
        event_entities=event_entities,
        opinion_spreaders=opinion_spreaders,
        relations=relations
    )


# =============================================================================
# 兼容函数
# =============================================================================

def extract_entities(seed_text: str) -> EntityExtractionOutput:
    """
    兼容函数：直接调用 extract_entities_with_validation

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
    seed_path = Path(seed_file)

    if not seed_path.exists():
        raise FileNotFoundError(f"种子文件不存在: {seed_file}")

    with open(seed_path, "r", encoding="utf-8") as f:
        seed_text = f.read()

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
        output_path = Path(__file__).parent.parent / "outputs" / "entities_and_relations.json"
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
        console.print(f"    立场: {spreader.stance_score}, 偏差: {spreader.confirmation_bias_level}")

    console.print(f"\n[bold]关系：[/bold]")
    for relation in entities_output.relations:
        console.print(f"  - {relation.source} --[{relation.type}]--> {relation.target}")
