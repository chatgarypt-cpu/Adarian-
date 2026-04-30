"""
Phase 2: 微型社交拓扑构建
---
根据 Phase 1 输出的实体分类结果，构建社交网络拓扑。

拓扑规则（v1.1.4）：
- 事件实体 → Core 节点（archetype_index = -1）
- 意见传播实体 → Periphery 节点（archetype_index = -2）
- Core ↔ Core：事件实体之间互相关注
- Periphery → Core：意见传播实体必须关注事件实体
- Periphery ↔ Periphery：可选连接（30% 概率）
- Agent 个体差异化：Core 扰动 ±5%，Periphery 扰动 ±15%

修改于：v1.1.4
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
import networkx as nx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

import config
from src.schemas import (
    Phase2Output, GraphNode, GraphEdge, EdgeType,
    EntityExtractionOutput, Entity, OpinionSpreader, NodeRole
)

console = Console()


def apply_individual_jitter(agents: List[GraphNode]) -> List[GraphNode]:
    """为 Agent 添加个体差异化随机扰动

    v1.1.3 算法：
    - Core 节点：stance ±5%，susceptibility ±5%
    - Periphery 节点：stance ±15%，susceptibility ±15%

    Args:
        agents: 原始 Agent 列表

    Returns:
        添加扰动后的 Agent 列表
    """
    jittered_agents = []
    for agent in agents:
        if agent.role == NodeRole.CORE:
            jitter_range = 0.05
        else:
            jitter_range = 0.15

        # stance 扰动
        jitter_stance = agent.stance_score * random.uniform(-jitter_range, jitter_range)
        new_stance = round(max(1.0, min(10.0, agent.stance_score + jitter_stance)), 2)

        # susceptibility 扰动
        jitter_susc = agent.susceptibility * random.uniform(-jitter_range, jitter_range)
        new_susc = round(max(0.0, min(1.0, agent.susceptibility + jitter_susc)), 2)

        jittered_agents.append(GraphNode(
            id=agent.id,
            group_name=agent.group_name,
            archetype_index=agent.archetype_index,
            related_entity=agent.related_entity,
            role=agent.role,
            stance_score=new_stance,
            susceptibility=new_susc,
            confirmation_bias_level=agent.confirmation_bias_level,
            entity_category=agent.entity_category,
            persona_name=agent.persona_name,
            age_range=agent.age_range,
            occupation=agent.occupation,
            personality=agent.personality,
            motivation=agent.motivation,
            typical_phrases=agent.typical_phrases,
        ))

    return jittered_agents


def build_topology(
    event_entities: List[Entity],
    opinion_spreaders: List[OpinionSpreader]
) -> Tuple[List[GraphNode], List[GraphEdge]]:
    """构建社交网络拓扑

    v1.1.4 算法：
    1. 事件实体 → Core 节点（archetype_index = -1）
    2. 意见传播实体 → Periphery 节点（archetype_index = -2）
    3. Core ↔ Core：事件实体之间互相关注
    4. Periphery → Core：意见传播实体必须关注关联的事件实体
    5. Periphery ↔ Periphery：可选连接（30% 概率）

    Args:
        event_entities: 事件实体列表
        opinion_spreaders: 意见传播实体列表

    Returns:
        (nodes, edges) 元组
    """
    nodes = []
    edges = []
    agent_id = 0

    # 1. 事件实体 → Core 节点
    event_entity_map: Dict[str, GraphNode] = {}  # name -> node
    for entity in event_entities:
        node = GraphNode(
            id=agent_id,
            group_name=entity.name,
            archetype_index=-1,  # 事件实体用 -1 标记
            related_entity=entity.name,
            role=NodeRole.CORE,
            stance_score=5.0,  # 事件实体默认中立
            susceptibility=0.0,
            confirmation_bias_level="none",
            entity_category="event_entity"
        )
        nodes.append(node)
        event_entity_map[entity.name] = node
        agent_id += 1

    # 2. 意见传播实体 → Periphery 节点
    periphery_nodes = []
    for spreader in opinion_spreaders:
        node = GraphNode(
            id=agent_id,
            group_name=spreader.group_name,
            archetype_index=-2,  # 意见传播实体用 -2 标记
            related_entity=spreader.related_event_entity,
            role=NodeRole.PERIPHERY,
            stance_score=spreader.stance_score,
            susceptibility=spreader.susceptibility,
            confirmation_bias_level=spreader.confirmation_bias_level,
            entity_category="opinion_spreader",
            persona_name=spreader.persona_name,
            age_range=spreader.age_range,
            occupation=spreader.occupation,
            personality=spreader.personality,
            motivation=spreader.motivation,
            typical_phrases=spreader.typical_phrases,
        )
        nodes.append(node)
        periphery_nodes.append(node)
        agent_id += 1

    # 3. 事件实体之间互相关注（Core ↔ Core）
    event_nodes = [n for n in nodes if n.entity_category == "event_entity"]
    for i, core_a in enumerate(event_nodes):
        for core_b in event_nodes[i+1:]:
            # A → B
            edges.append(GraphEdge(
                source=core_a.id,
                target=core_b.id,
                type=EdgeType.FOLLOWS_CORE_CROSS
            ))
            # B → A
            edges.append(GraphEdge(
                source=core_b.id,
                target=core_a.id,
                type=EdgeType.FOLLOWS_CORE_CROSS
            ))

    # 4. 意见传播实体必须关注关联的事件实体
    for periphery in periphery_nodes:
        target_core = event_entity_map.get(periphery.related_entity)
        if target_core:
            edges.append(GraphEdge(
                source=periphery.id,
                target=target_core.id,
                type=EdgeType.FOLLOWS
            ))

    # 5. 意见传播实体之间可选连接（30% 概率）
    for i, peri_a in enumerate(periphery_nodes):
        for peri_b in periphery_nodes[i+1:]:
            if random.random() < 0.3:
                edges.append(GraphEdge(
                    source=peri_a.id,
                    target=peri_b.id,
                    type=EdgeType.FOLLOWS_CROSS_GROUP
                ))

    # 应用个体差异化扰动
    nodes = apply_individual_jitter(nodes)

    return nodes, edges


def build_topology_from_extraction(
    extraction_output: EntityExtractionOutput
) -> Phase2Output:
    """从 EntityExtractionOutput 构建拓扑

    Args:
        extraction_output: Phase 1 输出

    Returns:
        Phase2Output
    """
    nodes, edges = build_topology(
        event_entities=extraction_output.event_entities,
        opinion_spreaders=extraction_output.opinion_spreaders
    )
    return Phase2Output(nodes=nodes, edges=edges)


def validate_topology(phase2_output: Phase2Output) -> bool:
    """验证拓扑结构

    验收标准：
    1. 事件实体作为 Core 节点
    2. 每个 Periphery 至少有 1 条指向事件实体的边
    3. 事件实体之间有互相连接
    4. 图是连通的

    Args:
        phase2_output: Phase2 输出

    Returns:
        验证是否通过
    """
    # 检查事件实体是否为 Core
    event_nodes = [n for n in phase2_output.nodes if n.entity_category == "event_entity"]
    for node in event_nodes:
        if node.role != NodeRole.CORE:
            console.print(f"[red]错误：[/red] 事件实体 '{node.group_name}' 不是 Core 节点")
            return False

    # 检查意见传播实体是否为 Periphery
    spreader_nodes = [n for n in phase2_output.nodes if n.entity_category == "opinion_spreader"]
    for node in spreader_nodes:
        if node.role != NodeRole.PERIPHERY:
            console.print(f"[red]错误：[/red] 意见传播实体 '{node.group_name}' 不是 Periphery 节点")
            return False

    # 检查每个 Periphery 是否关注了事件实体
    event_node_ids = {n.id for n in event_nodes}
    periphery_edges = [e for e in phase2_output.edges if e.type == EdgeType.FOLLOWS]

    for periphery in spreader_nodes:
        # 找到该 Periphery 的出边
        periphery_follows = [e for e in periphery_edges if e.source == periphery.id]
        # 检查是否关注了事件实体
        has_event_target = any(e.target in event_node_ids for e in periphery_follows)
        if not has_event_target:
            console.print(f"[red]错误：[/red] Periphery '{periphery.group_name}' 没有关注任何事件实体")
            return False

    # 检查事件实体之间是否互相关注
    core_cross_edges = [e for e in phase2_output.edges if e.type == EdgeType.FOLLOWS_CORE_CROSS]
    if len(core_cross_edges) < 2:
        console.print(f"[yellow]警告：[/yellow] 事件实体之间连接可能不足")

    # 构建 NetworkX 图检查连通性
    G = nx.DiGraph()
    for node in phase2_output.nodes:
        G.add_node(node.id)
    for edge in phase2_output.edges:
        G.add_edge(edge.source, edge.target)

    # 检查是否是弱连通图
    if not nx.is_weakly_connected(G):
        components = list(nx.weakly_connected_components(G))
        console.print(f"[yellow]警告：[/yellow] 图不是完全连通的，有 {len(components)} 个弱连通分量")

    console.print("[green]✓[/green] 拓扑验证通过")
    return True


def save_social_graph(phase2_output: Phase2Output, output_path: Path = None):
    """保存社交网络拓扑

    Args:
        phase2_output: Phase2 输出
        output_path: 输出路径，默认使用 config.SOCIAL_GRAPH_PATH
    """
    output_path = output_path or config.SOCIAL_GRAPH_PATH

    output_data = phase2_output.model_dump()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/green] 社交网络拓扑已保存至: {output_path}")


def load_social_graph(file_path: Path = None) -> Phase2Output:
    """加载社交网络拓扑

    Args:
        file_path: 拓扑文件路径

    Returns:
        Phase2Output 对象
    """
    file_path = file_path or config.SOCIAL_GRAPH_PATH

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return Phase2Output(**data)


def visualize_topology_stats(phase2_output: Phase2Output):
    """打印拓扑统计信息

    Args:
        phase2_output: Phase2 输出
    """
    from collections import Counter

    # 节点统计
    entity_counts = Counter(n.entity_category for n in phase2_output.nodes)
    role_counts = Counter(n.role for n in phase2_output.nodes)
    group_counts = Counter(n.group_name for n in phase2_output.nodes)

    # 边统计
    edge_count = len(phase2_output.edges)
    edge_type_counts = Counter(e.type.value for e in phase2_output.edges)

    console.print("\n[bold]社交网络拓扑统计：[/bold]")
    console.print(f"  总节点数: {len(phase2_output.nodes)}")
    console.print(f"    - 事件实体（Core）: {entity_counts.get('event_entity', 0)}")
    console.print(f"    - 意见传播实体（Periphery）: {entity_counts.get('opinion_spreader', 0)}")
    console.print(f"  总边数: {edge_count}")
    for edge_type, count in sorted(edge_type_counts.items()):
        console.print(f"    - {edge_type}: {count}")

    console.print("\n[bold]各群体节点数：[/bold]")
    for group, count in sorted(group_counts.items(), key=lambda x: -x[1]):
        console.print(f"  - {group}: {count}")


# =============================================================================
# 主入口（可独立运行）
# =============================================================================

if __name__ == "__main__":
    import sys
    from src.schemas import EntityExtractionOutput

    # 确保输出目录存在
    config.ensure_dirs()

    console.print("[bold]Phase 2: 构建社交网络拓扑[/bold]\n")

    # 加载 Phase 1 输出
    entities_file = config.OUTPUTS_DIR / "entities_and_relations.json"
    if not entities_file.exists():
        console.print(f"[red]错误：[/red] 未找到实体提取结果: {entities_file}")
        console.print("请先运行 Phase 1")
        sys.exit(1)

    with open(entities_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    extraction_output = EntityExtractionOutput(**data)
    console.print(f"加载实体提取结果：{len(extraction_output.event_entities)} 事件实体, {len(extraction_output.opinion_spreaders)} 意见传播者")

    # 构建拓扑
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("[cyan]构建拓扑关系...", total=None)
        phase2_output = build_topology_from_extraction(extraction_output)

    # 验证拓扑
    validate_topology(phase2_output)

    # 打印统计
    visualize_topology_stats(phase2_output)

    # 保存
    save_social_graph(phase2_output)
