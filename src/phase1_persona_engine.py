"""
Phase 1: 动态人群生成器
---
从种子文本和实体提取结果中，生成舆论场中的人群原型 (Archetype)。
再通过收缩算法，将人群原型映射为 5-15 个具体的 Agent 画像。

为什么需要修改（Why）：
- v1.1.0 版本直接让 LLM 凭空想象人群，导致生成的 Agent 与事件脱节
- v1.1.1 通过先提取实体，再基于实体生成 Agent，确保 Agent 与事件强相关

修改于：v1.1.1
修改历史：
- v1.1.0: 初始实现，直接生成 Agent
- v1.1.1: 增加 entities_file 输入，基于实体生成 Agent
"""

import json
from pathlib import Path
from typing import List, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

import config
from src.schemas import Phase1Output, Archetype, GraphNode, NodeRole, EntityExtractionOutput
from src.llm_client import get_llm_client

console = Console()


# =============================================================================
# Prompt 模板
# =============================================================================

PHASE1_SYSTEM_PROMPT = """你是一位资深的社会舆情分析师。你的任务是基于事件的核心实体和关系，
推断出在社交媒体上会参与讨论的典型人群。

事件信息：
- 事件摘要：{event_summary}
- 核心实体：{core_entities}（JSON 列表）
- 实体关系：{relations}（JSON 列表）
- 事件热度：{event_temperature}（0.0=冷门事件，1.0=全网热议）
- 事件类型：{event_type}

你必须严格按照以下规则生成人群画像：

1. 人群必须与核心实体有直接或间接关系
   - 例如：如果实体是"某美妆品牌"，可以生成"品牌死忠粉"、"理性消费者"、"维权消费者"
   - 禁止生成与实体无关的人群（如"海外华人"、"与事件无关的网红"）

2. 人群数量由事件热度决定：
   - event_temperature < 0.3：生成 3-5 个 archetype
   - 0.3 <= event_temperature < 0.7：生成 5-7 个 archetype
   - event_temperature >= 0.7：生成 7-10 个 archetype

3. 极端立场人群（stance_score < 3 或 > 7）的占比由事件热度决定：
   - event_temperature < 0.5：极端派总占比 < 20%
   - event_temperature >= 0.5：极端派总占比 30-50%

4. confirmation_bias_level（确认偏差强度）的分配规则：
   - stance_score < 3 或 > 7（极端立场）且 susceptibility < 0.5 → "strong"
   - stance_score 在 4-6 之间（中立）且 susceptibility > 0.7 → "none"
   - 其他情况 → "weak"

5. 每个 archetype 必须包含 related_entity 字段，值必须是 core_entities 中某个实体的 name

6. **重要**：在输出最终 JSON 之前，必须先计算所有 estimated_percentage 的和。如果不等于 100，必须调整某个或某几个 archetype 的百分比使之和恰好等于 100。

输出格式：
{{
  "event_summary": "事件一句话摘要",
  "conflict_axes": ["冲突轴1", "冲突轴2"],
  "archetypes": [
    {{
      "group_name": "群体名称",
      "related_entity": "关联的实体名称（必须在 core_entities 中）",
      "description": "50字以内的人设描述",
      "stance_score": 1.0到10.0之间的浮点数,
      "susceptibility": 0.0到1.0之间的浮点数,
      "confirmation_bias_level": "none | weak | strong",
      "estimated_percentage": 0到100之间的整数,
      "communication_style": "该群体的典型说话风格"
    }}
  ]
}}

约束条件：
1. archetypes 数量必须符合上述规则 2
2. 所有 estimated_percentage 之和必须等于 100
3. 至少包含一个 stance_score < 3.0 的群体和一个 > 7.0 的群体
4. 极端派占比必须符合上述规则 3
5. confirmation_bias_level 的分配必须符合上述规则 4
6. 每个 archetype 的 related_entity 必须在 core_entities 中存在
"""

PHASE1_USER_PROMPT = """请分析以下事件材料：

{seed_text}
"""


# =============================================================================
# 辅助函数
# =============================================================================

def determine_archetype_count(event_temperature: float) -> Tuple[int, int]:
    """
    根据事件热度确定 archetype 数量范围

    Args:
        event_temperature: 事件热度参数

    Returns:
        (min_count, max_count) 元组
    """
    if event_temperature < 0.3:
        return 3, 5
    elif event_temperature < 0.7:
        return 5, 7
    else:
        return 7, 10


def determine_extreme_ratio(event_temperature: float) -> float:
    """
    根据事件热度确定极端派占比上限

    Args:
        event_temperature: 事件热度参数

    Returns:
        极端派占比上限（0.0-1.0）
    """
    if event_temperature < 0.5:
        return 0.2  # < 20%
    else:
        return 0.5  # 30-50%


# =============================================================================
# 收缩算法
# =============================================================================

def shrink_to_agents(archetypes: List[Archetype], max_agents: int = None) -> List[Tuple[Archetype, int]]:
    """收缩算法：将人群原型映射为具体 Agent 数量

    算法：
    1. 对每个 archetype: agent_count = max(1, round(MAX_AGENTS * estimated_percentage / 100))
    2. 如果总数 > MAX_AGENTS，按比例缩减
    3. 如果总数 < MIN_AGENTS，补充到 MIN_AGENTS

    为什么需要修改（Why）：
    - v1.1.1 版本会根据 event_temperature 动态决定 Agent 总数范围

    修改于：v1.1.1

    Args:
        archetypes: 人群原型列表
        max_agents: 最大 Agent 数，默认根据 event_temperature 动态决定

    Returns:
        List of (Archetype, agent_count) tuples
    """
    if max_agents is None:
        # 从 archetypes 中获取 event_temperature 来决定范围
        # 这里用平均值作为参考
        max_agents = config.MAX_AGENTS

    min_agents = config.MIN_AGENTS

    # 第一步：计算初始 agent 数量
    raw_counts = []
    for arch in archetypes:
        count = max(1, round(max_agents * arch.estimated_percentage / 100))
        raw_counts.append(count)

    total_raw = sum(raw_counts)

    # 第二步：调整总数
    if total_raw > max_agents:
        # 超出上限，按比例缩减
        scale = max_agents / total_raw
        adjusted_counts = []
        remaining = max_agents
        for i, count in enumerate(raw_counts[:-1]):
            adjusted = max(1, round(count * scale))
            adjusted_counts.append(adjusted)
            remaining -= adjusted
        adjusted_counts.append(remaining)  # 最后一个填满剩余
        final_counts = adjusted_counts

    elif total_raw < min_agents:
        # 低于下限，补充到最小值
        # 优先补充到 susceptibility 最高的群体（更容易受影响，更有趣）
        sorted_indices = sorted(range(len(archetypes)), key=lambda i: archetypes[i].susceptibility, reverse=True)
        final_counts = raw_counts.copy()
        remaining = min_agents - total_raw
        for idx in sorted_indices:
            if remaining <= 0:
                break
            final_counts[idx] += 1
            remaining -= 1
    else:
        final_counts = raw_counts

    # 确保每个 archetype 至少有 1 个 agent
    for i in range(len(final_counts)):
        if final_counts[i] < 1:
            final_counts[i] = 1

    return list(zip(archetypes, final_counts))


# =============================================================================
# Phase 1 主流程
# =============================================================================

def parse_seed_text_with_entities(
    seed_text: str,
    entities_output: EntityExtractionOutput,
) -> Phase1Output:
    """基于实体提取结果，生成人群原型

    为什么需要这个函数（Why）：
    - v1.1.1 版本需要先有实体信息，再基于实体生成 Agent
    - 这样生成的 Agent 更贴合事件，与核心利益相关方对齐

    修改于：v1.1.1

    Args:
        seed_text: 种子文本内容
        entities_output: Phase 0 实体提取结果

    Returns:
        Phase1Output Pydantic 模型
    """
    llm = get_llm_client()

    # 构建实体信息
    core_entities_json = json.dumps(
        [e.model_dump() for e in entities_output.core_entities],
        ensure_ascii=False,
        indent=2
    )
    relations_json = json.dumps(
        [r.model_dump() for r in entities_output.relations],
        ensure_ascii=False,
        indent=2
    )

    # 替换 prompt 中的占位符
    system_prompt = PHASE1_SYSTEM_PROMPT.format(
        event_summary=entities_output.event_summary,
        core_entities=core_entities_json,
        relations=relations_json,
        event_temperature=entities_output.event_temperature,
        event_type=entities_output.event_type,
    )

    user_prompt = PHASE1_USER_PROMPT.format(seed_text=seed_text)

    console.print("[bold cyan]Phase 1:[/bold cyan] 正在调用 LLM 生成 Agent 画像...")

    result = llm.generate(
        system=system_prompt,
        user=user_prompt,
        response_model=Phase1Output,
    )

    # 验证 related_entity 是否都在 core_entities 中
    entity_names = {e.name for e in entities_output.core_entities}
    for arch in result.archetypes:
        if arch.related_entity not in entity_names:
            console.print(f"[yellow]警告：[/yellow] archetype '{arch.group_name}' 的 related_entity '{arch.related_entity}' 不在 core_entities 中")

    console.print(f"[green]✓[/green] 画像生成完成：识别出 {len(result.archetypes)} 类人群原型")
    console.print(f"  事件摘要：{result.event_summary[:50]}...")
    console.print(f"  冲突轴：{', '.join(result.conflict_axes)}")

    return result


def generate_personas(
    seed_file: str,
    entities_file: str,
) -> Phase1Output:
    """
    基于事件实体生成 Agent 画像

    为什么需要修改（Why）：
    - v1.1.0 版本直接生成 Agent，缺少事件结构化信息
    - v1.1.1 通过先提取实体，再基于实体生成 Agent，确保 Agent 与事件强相关

    修改于：v1.1.1

    Args:
        seed_file: 种子文本文件路径
        entities_file: Phase 0 实体提取结果 JSON 文件路径

    Returns:
        Phase1Output Pydantic 模型
    """
    # 加载种子文本
    seed_path = Path(seed_file)
    with open(seed_path, "r", encoding="utf-8") as f:
        seed_text = f.read()

    # 加载实体提取结果
    entities_path = Path(entities_file)
    with open(entities_path, "r", encoding="utf-8") as f:
        entities_data = json.load(f)
    entities_output = EntityExtractionOutput(**entities_data)

    return parse_seed_text_with_entities(seed_text, entities_output)


def build_agent_profiles(phase1_output: Phase1Output) -> List[GraphNode]:
    """构建 Agent 画像列表

    根据 Phase1Output 和收缩算法，生成具体的 Agent 列表。

    Args:
        phase1_output: Phase1 的输出

    Returns:
        GraphNode 列表，每个代表一个具体的 Agent
    """
    archetype_with_counts = shrink_to_agents(phase1_output.archetypes)

    agents = []
    agent_id = 0

    for archetype, count in archetype_with_counts:
        for _ in range(count):
            # 第一个（susceptibility 最低的）标记为 core
            role = NodeRole.CORE if len([a for a in agents if a.group_name == archetype.group_name]) == 0 else NodeRole.PERIPHERY

            node = GraphNode(
                id=agent_id,
                group_name=archetype.group_name,
                archetype_index=phase1_output.archetypes.index(archetype),
                related_entity=archetype.related_entity,
                role=role,
                stance_score=archetype.stance_score,
                susceptibility=archetype.susceptibility,
                confirmation_bias_level=archetype.confirmation_bias_level,
            )
            agents.append(node)
            agent_id += 1

    console.print(f"[green]✓[/green] 收缩完成：生成了 {len(agents)} 个 Agent")

    return agents


def run_phase1(seed_text: str, entities_output: EntityExtractionOutput) -> Tuple[Phase1Output, List[GraphNode]]:
    """运行 Phase 1 完整流程

    Args:
        seed_text: 种子文本
        entities_output: Phase 0 实体提取结果

    Returns:
        (Phase1Output, List[GraphNode]) 元组
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: 基于实体生成画像
        progress.add_task("[cyan]生成 Agent 画像...", total=None)
        phase1_output = parse_seed_text_with_entities(seed_text, entities_output)

        # Step 2: 构建 Agent 画像
        progress.add_task("[cyan]收缩算法映射...", total=None)
        agents = build_agent_profiles(phase1_output)

    return phase1_output, agents


def save_phase1_output(
    phase1_output: Phase1Output,
    agents: List[GraphNode],
    output_path: Path = None,
):
    """保存 Phase 1 输出

    Args:
        phase1_output: Phase1 输出
        agents: Agent 画像列表
        output_path: 输出路径，默认使用 config.AGENTS_PROFILE_PATH
    """
    output_path = output_path or config.AGENTS_PROFILE_PATH

    # 转换为可序列化的 dict
    output_data = {
        "phase1_output": phase1_output.model_dump(),
        "agents": [agent.model_dump() for agent in agents],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/green] 输出已保存至: {output_path}")


def load_seed_text(file_path: Path) -> str:
    """加载种子文本文件

    Args:
        file_path: 种子文件路径

    Returns:
        文件内容字符串
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# =============================================================================
# 主入口（可独立运行）- 保留向后兼容
# =============================================================================

if __name__ == "__main__":
    import sys

    # 确保输出目录存在
    config.ensure_dirs()

    # 检查是否提供了种子文件路径
    if len(sys.argv) < 2:
        # 默认使用 example_event.txt
        seed_file = config.SEEDS_DIR / "example_event.txt"
        if not seed_file.exists():
            console.print("[bold red]错误：[/bold red] 未提供种子文件路径，且默认文件不存在")
            console.print(f"请将种子文本文件放入: {config.SEEDS_DIR}")
            sys.exit(1)
    else:
        seed_file = Path(sys.argv[1])

    # 检查是否有实体文件
    entities_file = config.OUTPUTS_DIR / "entities_and_relations.json"
    if not entities_file.exists():
        console.print("[bold red]错误：[/bold red] 未找到实体提取结果，请先运行 Phase 0")
        console.print(f"请运行: python src/phase0_entity_extraction.py {seed_file}")
        sys.exit(1)

    console.print(f"[bold]读取种子文本：[/bold] {seed_file}")
    console.print(f"[bold]读取实体文件：[/bold] {entities_file}")

    seed_text = load_seed_text(seed_file)

    # 运行 Phase 1
    phase1_output, agents = run_phase1(seed_text, entities_file)

    # 保存输出
    save_phase1_output(phase1_output, agents)

    # 打印摘要
    console.print("\n[bold]Agent 画像摘要：[/bold]")
    for arch, count in shrink_to_agents(phase1_output.archetypes):
        console.print(f"  - {arch.group_name} ({arch.related_entity}): {count} 个, 立场={arch.stance_score}, 偏差={arch.confirmation_bias_level}")
