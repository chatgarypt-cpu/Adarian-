"""
Phase 3: 异步时间步推演
---
核心模拟逻辑：让 Agent 在社交网络中进行多轮交互，观察群体情绪的涌现与演化。

发言顺序（v1.1.4）：
- Tick 0：事件实体发言（基于种子文本生成初始声明）
- Tick 1+：意见传播实体发言（必须看到事件实体发言才能发言）

关键输出：x(t) 序列，即全局平均立场分，用于后续 AD/SEIR 模块。

修改于：v1.1.4
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import networkx as nx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table

import config
from src.schemas import (
    Phase2Output, GraphNode, GraphEdge, EntityExtractionOutput,
    Entity, OpinionSpreader,
    TickLog, AgentEntry, GlobalMetrics, NodeRole
)
from src.llm_client import get_llm_client

console = Console()


# =============================================================================
# Prompt 模板
# =============================================================================

# stance 语义定义
STANCE_SEMANTICS = """
【立场分（stance_score）语义定义 - 必须严格遵守】
- 1.0 ~ 3.0：强烈批评（你对品牌/相关方持负面态度，支持维权、质疑品牌）
- 4.0 ~ 6.0：中立观望（你不偏向任何一方，保持理性分析）
- 7.0 ~ 10.0：强烈支持（你对品牌/相关方持正面态度，维护品牌形象）

注意：立场分的高低方向在整个模拟过程中保持不变。
"""

# 确认偏差 Prompt 模板
CONFIRMATION_BIAS_PROMPTS = {
    "strong": """
【确认偏差指令 - 强】
你有极强的确认偏差。
- 如果你看到的发言与你的立场一致，你会更加坚定，立场分可以小幅增强（最多 +0.3）
- 如果你看到的发言与你的立场相反，你会完全忽略甚至反驳，立场分几乎不变（最多 ±0.3）
- 你的立场变化幅度在任何情况下都不超过 ±0.3
""",
    "weak": """
【确认偏差指令 - 弱】
你有轻微的确认偏差。
- 如果你看到的发言与你的立场一致，你会比较认同，立场分可以适度增强
- 如果你看到的发言与你的立场相反，你会有所保留，但可能略微被影响
- 你的立场变化幅度不超过 ±1.0
""",
    "none": """
【确认偏差指令 - 无】
你没有明显的确认偏差，是一个理性的观察者。
- 你会认真考虑你看到的每一条发言，无论是否与你的立场一致
- 如果对方的论点有说服力，你愿意改变自己的看法
- 你的立场变化幅度不超过 ±2.0
"""
}

# stance 变化硬性约束
STANCE_CHANGE_LIMITS = {
    "strong": 0.3,
    "weak": 1.0,
    "none": 2.0
}


# 事件实体发言 Prompt（Tick 0）
EVENT_ENTITY_POST_SYSTEM_PROMPT = """你是一个真实的社会事件参与者。你的发言会被大量网友看到和转发。

【你的身份】
- 名称：**{entity_name}**
- 类型：{entity_type}
- 角色：{entity_role}

【事件背景】
{event_summary}

{seed_text}

请根据你的身份和角色，发布一条代表你立场的初始声明。

输出格式（严格 JSON）：
{{
  "comment": "你的声明内容（100字以内，符合你的身份和角色）",
  "reasoning": "你为什么这样说（30字以内）"
}}

注意：
1. 你是事件的核心参与者，你的发言代表官方立场
2. 评论要符合你的身份（品牌方、主播、当事人等）
3. 你的发言会被意见传播者看到和评论

【重要约束】
- 这条声明应该是"事件起点"，而不是"事后回应"
- 禁止生成"道歉声明"、"澄清说明"、"事后回应"、"已处理"等
- 错误示例："该评论为不当言论，已严肃处理"
- 正确示例：基于你的角色和立场的初始表态
"""


# 意见传播实体发言 Prompt（Tick N）
AGENT_POST_SYSTEM_PROMPT = """你是一个社交媒体用户，你的人设如下：
- 身份：{group_name}
- 关联实体：**{related_entity}**（你必须围绕这个实体展开讨论）
- 性格特征：{description}
- 说话风格：{communication_style}

{stance_semantics}

{confirmation_bias_prompt}

{opinion_pressure_prompt}

你必须严格按照以下 JSON 格式输出：
{{
  "comment": "你的评论（50字以内，必须提及或暗示关联实体**{related_entity}**，符合你的说话风格）",
  "new_stance": 1.0到10.0之间的浮点数,
  "reasoning": "你为什么持这个立场（30字以内）"
}}

注意：
1. new_stance 必须在 1.0-10.0 之间
2. 评论要符合你的人设和说话风格
3. **重要**：你的发言必须提及你的关联实体"**{related_entity}**"
"""

AGENT_POST_USER_PROMPT = """【事件背景】
{event_summary}

【事件实体{event_entity_name}的发言】
{event_entity_post}

你关注的人最近说了这些话：
{followed_agents_comments}

{stance_meaning}

{opinion_pressure_situation}

请根据你的人设，发表你的看法。
"""


# =============================================================================
# 模拟器
# =============================================================================

class SimulationEngine:
    """模拟引擎

    负责管理模拟状态、执行多轮推演。

    修改于：v1.1.4
    - Tick 0：事件实体发言
    - Tick 1+：意见传播实体发言

    修改于：v1.1.7
    - 新增 group_distribution_strategy，用于舆论压力机制
    """

    def __init__(
        self,
        extraction_output: EntityExtractionOutput,
        phase2_output: Phase2Output,
        seed_text: str,
    ):
        self.extraction_output = extraction_output
        self.phase2_output = phase2_output
        self.seed_text = seed_text
        self.event_summary = extraction_output.event_summary
        # v1.1.7 新增：群体分布策略
        self.group_distribution_strategy = getattr(extraction_output, 'group_distribution_strategy', 'normal')

        # 构建 NetworkX 图
        self.G = nx.DiGraph()
        for node in phase2_output.nodes:
            self.G.add_node(node.id, **node.model_dump())
        for edge in phase2_output.edges:
            self.G.add_edge(edge.source, edge.target)

        # 初始化 agent 状态
        self.agent_stances: Dict[int, float] = {
            node.id: node.stance_score for node in phase2_output.nodes
        }

        # 历史记录
        self.tick_logs: List[TickLog] = []
        self.agent_comments: Dict[int, List[str]] = {node.id: [] for node in phase2_output.nodes}

        # 事件实体发言记录（Tick 0）
        self.event_entity_posts: Dict[int, str] = {}  # agent_id -> comment

        # LLM 客户端（差异化温度）
        from src.llm_client import LLMClient
        # 事件实体：温度 0.3，输出更稳定
        self.llm_event_entity = LLMClient(temperature=0.3)
        # 传播者：温度 0.8，输出更多样化
        self.llm_spreader = LLMClient(temperature=0.8)
        # 默认客户端（保持兼容）
        self.llm = get_llm_client()

        # 建立 entity -> agent_id 的映射
        self.entity_to_agent_id: Dict[str, int] = {}
        for node in phase2_output.nodes:
            if node.entity_category == "event_entity":
                self.entity_to_agent_id[node.related_entity] = node.id

        # 按 group 分组的 spreader 信息
        self.spreader_map: Dict[str, OpinionSpreader] = {}
        for spreader in extraction_output.opinion_spreaders:
            self.spreader_map[spreader.group_name] = spreader

    def run_tick_0(self) -> List[AgentEntry]:
        """执行 Tick 0：事件实体发言

        Returns:
            事件实体发言条目列表
        """
        console.print("[bold cyan]Tick 0:[/bold cyan] 事件实体发言")

        entries = []
        event_nodes = [
            n for n in self.phase2_output.nodes
            if n.entity_category == "event_entity"
        ]

        for node in event_nodes:
            # 获取对应的 Entity 信息
            entity = None
            for e in self.extraction_output.event_entities:
                if e.name == node.related_entity:
                    entity = e
                    break

            if not entity:
                continue

            # v1.1.6: 检查 can_speak
            if not entity.can_speak:
                # can_speak=false：不生成发言，标记为被讨论
                reason = entity.original_statement or "（该实体不可发言）"
                self.event_entity_posts[node.id] = reason
                self.agent_comments[node.id].append(reason)

                entry = AgentEntry(
                    agent_id=node.id,
                    group_name=node.group_name,
                    saw_posts_from=[],
                    previous_stance=5.0,
                    current_stance=5.0,
                    stance_delta=0.0,
                    comment=reason,
                    reasoning="实体不可发言",
                )
                entries.append(entry)
                console.print(f"  [dim]○[/dim] {node.group_name}: {reason}")
                continue

            # v1.1.6: 优先使用 original_statement
            if entity.original_statement:
                # 有原始发言，直接使用
                comment = entity.original_statement
                reasoning = "原始发言（从种子材料提取）"
                self.event_entity_posts[node.id] = comment
                self.agent_comments[node.id].append(comment)

                entry = AgentEntry(
                    agent_id=node.id,
                    group_name=node.group_name,
                    saw_posts_from=[],
                    previous_stance=5.0,
                    current_stance=5.0,
                    stance_delta=0.0,
                    comment=comment,
                    reasoning=reasoning,
                )
                entries.append(entry)
                console.print(f"  [green]✓[/green] {node.group_name}: {comment[:30]}... [dim](原始发言)[/dim]")
                continue

            # 构建 Prompt
            system_prompt = EVENT_ENTITY_POST_SYSTEM_PROMPT.format(
                entity_name=entity.name,
                entity_type=entity.type,
                entity_role=entity.role,
                event_summary=self.event_summary,
                seed_text=self.seed_text[:2000] if len(self.seed_text) > 2000 else self.seed_text,
            )

            try:
                # 事件实体使用低温度客户端（输出更稳定）
                response = self.llm_event_entity.generate(
                    system=system_prompt,
                    user="请发布你的声明。",
                    response_model=None,
                )

                # 解析响应
                comment, reasoning = self._parse_event_entity_response(response)

                # 记录发言
                self.event_entity_posts[node.id] = comment
                self.agent_comments[node.id].append(comment)

                entry = AgentEntry(
                    agent_id=node.id,
                    group_name=node.group_name,
                    saw_posts_from=[],
                    previous_stance=5.0,
                    current_stance=5.0,
                    stance_delta=0.0,
                    comment=comment,
                    reasoning=reasoning,
                )
                entries.append(entry)

                console.print(f"  [green]✓[/green] {node.group_name}: {comment[:30]}...")

            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] {node.group_name} 生成发言失败: {e}")
                comment = "（无评论）"
                self.event_entity_posts[node.id] = comment
                self.agent_comments[node.id].append(comment)

                entries.append(AgentEntry(
                    agent_id=node.id,
                    group_name=node.group_name,
                    saw_posts_from=[],
                    previous_stance=5.0,
                    current_stance=5.0,
                    stance_delta=0.0,
                    comment=comment,
                    reasoning="生成失败",
                ))

        return entries

    def get_followed_comments(self, agent_id: int, max_posts: int = None) -> List[Tuple[int, str]]:
        """获取某 agent 关注的节点的最新发言

        Args:
            agent_id: agent ID
            max_posts: 最多获取的发言数

        Returns:
            List of (source_agent_id, comment) tuples
        """
        max_posts = max_posts or config.MAX_POSTS_PER_TICK

        # 获取该 agent 关注的节点（关注的人）
        followers = list(self.G.successors(agent_id))

        comments = []
        for followed_id in followers:
            if followed_id in self.agent_comments and self.agent_comments[followed_id]:
                last_comment = self.agent_comments[followed_id][-1]
                comments.append((followed_id, last_comment))

        return comments[:max_posts]

    def generate_opinion_spreader_post(self, agent: GraphNode) -> Tuple[str, float, str, str]:
        """为意见传播实体生成发言

        Args:
            agent: GraphNode 对象

        Returns:
            (comment, new_stance, reasoning) tuple
        """
        spreader = self.spreader_map.get(agent.group_name)

        # 获取事件实体发言
        event_entity_post = ""
        event_entity_name = ""
        for node in self.phase2_output.nodes:
            if node.entity_category == "event_entity" and node.id in self.event_entity_posts:
                event_entity_name = node.group_name
                event_entity_post = self.event_entity_posts[node.id]
                break

        # 获取关注的发言
        followed = self.get_followed_comments(agent.id)
        followed_text = ""
        if followed:
            followed_lines = []
            for src_id, comment in followed:
                src_node = self.phase2_output.nodes[src_id]
                followed_lines.append(f"- [{src_node.group_name}] {comment}")
            followed_text = "\n".join(followed_lines)
        else:
            followed_text = "（暂无其他关注对象的发言）"

        # stance 语义解释
        stance = self.agent_stances[agent.id]
        if stance <= 3.0:
            stance_meaning = f"你当前立场分为 {stance}，这意味着你【强烈批评/不信任】相关品牌或主播"
        elif stance <= 6.0:
            stance_meaning = f"你当前立场分为 {stance}，这意味着你【中立观望】，尚未明确站队"
        else:
            stance_meaning = f"你当前立场分为 {stance}，这意味着你【强烈支持/信任】相关品牌或主播"

        # 获取确认偏差 prompt
        confirmation_bias = agent.confirmation_bias_level
        confirmation_bias_prompt = CONFIRMATION_BIAS_PROMPTS.get(confirmation_bias, CONFIRMATION_BIAS_PROMPTS["none"])

        # v1.1.7 新增：舆论压力提示（只在 minimal_supporters 策略下启用）
        opinion_pressure_prompt = ""
        opinion_pressure_situation = ""
        if self.group_distribution_strategy == "minimal_supporters":
            # 计算当前全局平均立场
            mean_stance = sum(self.agent_stances.values()) / len(self.agent_stances)
            if mean_stance < 4.0:
                overall_sentiment = "批评主导"
                opinion_pressure_situation = f"""【舆论压力提示】（v1.1.7）
当前舆论整体倾向：{overall_sentiment}（平均立场 {mean_stance:.1f}）
- 舆论整体批评，而你立场较高（{stance:.1f}），你可能感受到孤立和压力
- 在这种舆论环境下，你的立场可能会略微下降"""
            elif mean_stance > 6.0:
                overall_sentiment = "支持主导"
                opinion_pressure_situation = f"""【舆论压力提示】（v1.1.7）
当前舆论整体倾向：{overall_sentiment}（平均立场 {mean_stance:.1f}）
- 舆论整体支持，而你立场较低（{stance:.1f}），你可能更加坚定
- 在这种舆论环境下，你的立场可能会略微上升"""
            else:
                opinion_pressure_situation = ""
        else:
            opinion_pressure_situation = ""

        # 构建 prompt
        system_prompt = AGENT_POST_SYSTEM_PROMPT.format(
            group_name=agent.group_name,
            related_entity=agent.related_entity,
            description=spreader.description if spreader else "",
            communication_style=spreader.communication_style if spreader else "",
            stance_semantics=STANCE_SEMANTICS,
            confirmation_bias_prompt=confirmation_bias_prompt,
            opinion_pressure_prompt=opinion_pressure_prompt,
        )

        user_prompt = AGENT_POST_USER_PROMPT.format(
            event_summary=self.event_summary,
            event_entity_name=event_entity_name,
            event_entity_post=event_entity_post,
            followed_agents_comments=followed_text,
            stance_meaning=stance_meaning,
            opinion_pressure_situation=opinion_pressure_situation,
        )

        try:
            # 传播者使用高温度客户端（输出更多样化）
            response = self.llm_spreader.generate(
                system=system_prompt,
                user=user_prompt,
                response_model=None,
            )

            # 解析 JSON 响应
            comment, proposed_stance, reasoning = self._parse_agent_response(response)

            # 应用 stance 变化硬性约束
            final_stance, change_reason = self.apply_stance_constraint(
                previous_stance=self.agent_stances[agent.id],
                proposed_stance=proposed_stance,
                confirmation_bias_level=confirmation_bias,
                susceptibility=agent.susceptibility,
                group_distribution_strategy=self.group_distribution_strategy,
                mean_stance=sum(self.agent_stances.values()) / len(self.agent_stances),
            )

            return comment, final_stance, reasoning, change_reason

        except Exception as e:
            console.print(f"  [yellow]警告：[/yellow] Agent {agent.id} 生成发言失败: {e}")
            return "（无评论）", self.agent_stances[agent.id], "生成失败", "exception"

    def apply_stance_constraint(
        self,
        previous_stance: float,
        proposed_stance: float,
        confirmation_bias_level: str,
        susceptibility: float,
        group_distribution_strategy: str = "normal",
        mean_stance: float = 5.0,
    ) -> Tuple[float, str]:
        """在代码层面强制约束 stance 变化幅度，接入 susceptibility 调制

        Args:
            previous_stance: 上一轮立场分
            proposed_stance: LLM 提出的新立场分
            confirmation_bias_level: 确认偏差级别
            susceptibility: 该 agent 的易感性（0.0-1.0）
            group_distribution_strategy: 群体分布策略
            mean_stance: 全局平均立场

        Returns:
            (final_stance, change_reason) tuple
            change_reason: "within_effective_delta" | "bounded_by_susceptibility"
        """
        # 1. 基础变化上限
        base_delta_map = {
            "strong": 0.3,
            "weak": 1.0,
            "none": 2.0
        }
        base_delta = base_delta_map.get(confirmation_bias_level, 1.0)

        # 2. susceptibility 调制：高 susceptibility → 更大变化幅度
        # modulation = 1 + 0.5 × (susceptibility - 0.5)
        # susceptibility=1.0 时，modulation = 1.25（变化幅度+25%）
        # susceptibility=0.0 时，modulation = 0.75（变化幅度-25%）
        susceptibility_modulation = 1 + config.SUSCEPTIBILITY_MODULATION_FACTOR * (susceptibility - 0.5)
        effective_delta = base_delta * susceptibility_modulation

        # 3. v1.1.7 新增：舆论压力机制（minimal_supporters 策略下）
        if group_distribution_strategy == "minimal_supporters":
            if mean_stance < 4.0 and previous_stance >= 7.0:
                effective_delta = effective_delta * 1.2  # 增加 20% 的变化幅度

        # 4. 限制变化幅度
        delta = proposed_stance - previous_stance

        if abs(delta) <= effective_delta:
            final_stance = proposed_stance
            change_reason = "within_effective_delta"
        else:
            clipped_delta = effective_delta if delta > 0 else -effective_delta
            final_stance = previous_stance + clipped_delta
            change_reason = "bounded_by_susceptibility"

        final_stance = round(max(1.0, min(10.0, final_stance)), 2)
        return final_stance, change_reason

    def _parse_event_entity_response(self, response: str) -> Tuple[str, str]:
        """解析事件实体发言响应

        Args:
            response: LLM 返回的原始字符串

        Returns:
            (comment, reasoning) tuple
        """
        import re

        # 提取 JSON
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                comment = data.get("comment", "")
                reasoning = data.get("reasoning", "")
                return comment, reasoning
            except (json.JSONDecodeError, ValueError):
                pass

        # 备用解析
        comment_match = re.search(r'"comment":\s*"([^"]*)"', response)
        reasoning_match = re.search(r'"reasoning":\s*"([^"]*)"', response)

        comment = comment_match.group(1) if comment_match else "（解析失败）"
        reasoning = reasoning_match.group(1) if reasoning_match else ""

        return comment, reasoning

    def _parse_agent_response(self, response: str) -> Tuple[str, float, str]:
        """解析 LLM 返回的 JSON

        Args:
            response: LLM 返回的原始字符串

        Returns:
            (comment, new_stance, reasoning) tuple
        """
        import re

        # 提取 JSON
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                comment = data.get("comment", "")
                new_stance = float(data.get("new_stance", 5.0))
                reasoning = data.get("reasoning", "")

                new_stance = max(1.0, min(10.0, new_stance))
                return comment, new_stance, reasoning
            except (json.JSONDecodeError, ValueError):
                pass

        # 备用解析
        comment_match = re.search(r'"comment":\s*"([^"]*)"', response)
        stance_match = re.search(r'"new_stance":\s*([\d.]+)', response)
        reasoning_match = re.search(r'"reasoning":\s*"([^"]*)"', response)

        comment = comment_match.group(1) if comment_match else "（解析失败）"
        new_stance = float(stance_match.group(1)) if stance_match else 5.0
        reasoning = reasoning_match.group(1) if reasoning_match else ""

        new_stance = max(1.0, min(10.0, new_stance))

        return comment, new_stance, reasoning

    def calculate_global_metrics(self) -> GlobalMetrics:
        """计算全局指标

        Returns:
            GlobalMetrics 对象
        """
        import statistics

        stances = list(self.agent_stances.values())
        mean_stance = statistics.mean(stances)
        std_stance = statistics.stdev(stances) if len(stances) > 1 else 0.0

        polarization_index = std_stance / mean_stance if mean_stance > 0 else 0.0

        return GlobalMetrics(
            mean_stance=round(mean_stance, 2),
            std_stance=round(std_stance, 2),
            polarization_index=round(polarization_index, 2),
        )

    def run_tick(self, tick: int) -> TickLog:
        """执行一轮模拟（Tick N：意见传播实体发言）

        Args:
            tick: 轮次编号

        Returns:
            TickLog 对象
        """
        entries = []

        # 只处理意见传播实体
        spreader_nodes = [
            n for n in self.phase2_output.nodes
            if n.entity_category == "opinion_spreader"
        ]

        for node in spreader_nodes:
            previous_stance = self.agent_stances[node.id]

            # 生成发言
            comment, new_stance, reasoning, change_reason = self.generate_opinion_spreader_post(node)

            # 更新立场
            self.agent_stances[node.id] = new_stance
            self.agent_comments[node.id].append(comment)

            # 获取本轮看到的发言者
            saw_posts = list(self.G.successors(node.id))

            entry = AgentEntry(
                agent_id=node.id,
                group_name=node.group_name,
                saw_posts_from=saw_posts,
                previous_stance=previous_stance,
                current_stance=new_stance,
                stance_delta=round(new_stance - previous_stance, 2),
                susceptibility=node.susceptibility,  # 新增 v1.1.9
                change_reason=change_reason,  # 新增 v1.1.9
                comment=comment,
                reasoning=reasoning,
            )
            entries.append(entry)

        # 计算全局指标
        global_metrics = self.calculate_global_metrics()

        return TickLog(
            tick=tick,
            entries=entries,
            global_metrics=global_metrics,
        )

    def run_simulation(self, max_ticks: int = None) -> List[TickLog]:
        """运行完整模拟

        Args:
            max_ticks: 最大轮数，默认从 config 读取

        Returns:
            List[TickLog]，每轮的日志
        """
        max_ticks = max_ticks or config.MAX_TICKS

        console.print(f"[bold]开始模拟：[/bold] {max_ticks} 轮\n")

        # Tick 0: 事件实体发言
        tick_0_entries = self.run_tick_0()

        # Tick 0 也要计算全局指标
        tick_0_metrics = self.calculate_global_metrics()
        tick_0_log = TickLog(
            tick=0,
            entries=tick_0_entries,
            global_metrics=tick_0_metrics,
        )
        self.tick_logs.append(tick_0_log)

        # Tick 1+: 意见传播实体发言
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.completed}/{task.total}"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]模拟进度", total=max_ticks)

            for tick in range(1, max_ticks + 1):
                tick_log = self.run_tick(tick)
                self.tick_logs.append(tick_log)

                progress.update(
                    task,
                    description=f"[cyan]Tick {tick}/{max_ticks}",
                    completed=tick,
                )

                # TODO: 收敛检测暂时禁用，跑满 10 轮
                # if tick > 1:
                #     prev_metrics = self.tick_logs[-2].global_metrics
                #     curr_metrics = tick_log.global_metrics
                #     delta = abs(curr_metrics.polarization_index - prev_metrics.polarization_index)
                #     if delta < config.CONVERGENCE_THRESHOLD:
                #         console.print(f"\n[yellow]检测到收敛，停止模拟（Tick {tick}）[/yellow]")
                #         break

        return self.tick_logs

    def get_x_t_sequence(self) -> List[float]:
        """获取 x(t) 序列

        Returns:
            List[float]，每轮的平均立场分
        """
        return [log.global_metrics.mean_stance for log in self.tick_logs]


def save_tick_logs(tick_logs: List[TickLog], output_dir: Path = None):
    """保存每轮交互日志

    Args:
        tick_logs: TickLog 列表
        output_dir: 输出目录，默认使用 config.TICK_LOGS_DIR
    """
    output_dir = output_dir or config.TICK_LOGS_DIR

    # 清空旧日志
    if output_dir.exists():
        for f in output_dir.glob("tick_*.json"):
            f.unlink()

    for log in tick_logs:
        output_path = output_dir / f"tick_{log.tick}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(log.model_dump(), f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/green] 交互日志已保存至: {output_dir}")


def load_extraction_output(file_path: Path = None) -> EntityExtractionOutput:
    """加载 Phase 1 输出"""
    file_path = file_path or config.OUTPUTS_DIR / "entities_and_relations.json"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return EntityExtractionOutput(**data)


def load_phase2_output(file_path: Path = None) -> Phase2Output:
    """加载 Phase 2 输出"""
    file_path = file_path or config.SOCIAL_GRAPH_PATH

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return Phase2Output(**data)


def print_simulation_summary(tick_logs: List[TickLog]):
    """打印模拟摘要"""
    console.print("\n[bold]模拟结果摘要：[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Tick", style="cyan")
    table.add_column("x(t) 均值", style="green")
    table.add_column("标准差", style="yellow")
    table.add_column("极化指数", style="magenta")
    table.add_column("关键变化", style="red")

    prev_mean = None
    for log in tick_logs:
        if not log.entries:
            continue

        # 找出本轮立场变化最大的 agent
        max_delta_entry = max(log.entries, key=lambda e: abs(e.stance_delta))
        key_change = f"#{max_delta_entry.agent_id} ({max_delta_entry.group_name[:6]}): {max_delta_entry.stance_delta:+.1f}"

        # 检测均值变化方向
        mean_change = ""
        if prev_mean is not None:
            delta = log.global_metrics.mean_stance - prev_mean
            mean_change = f"{delta:+.1f}"
        prev_mean = log.global_metrics.mean_stance

        table.add_row(
            str(log.tick),
            f"{log.global_metrics.mean_stance:.2f}",
            f"{log.global_metrics.std_stance:.2f}",
            f"{log.global_metrics.polarization_index:.2f}",
            f"{key_change} {mean_change}",
        )

    console.print(table)


# =============================================================================
# 主入口（可独立运行）
# =============================================================================

if __name__ == "__main__":
    import sys

    # 确保输出目录存在
    config.ensure_dirs()

    console.print("[bold]Phase 3: 多轮涌现推演[/bold]\n")

    # 加载 Phase 1 和 Phase 2 输出
    extraction_output = load_extraction_output()
    console.print(f"加载实体提取结果：{len(extraction_output.event_entities)} 事件实体, {len(extraction_output.opinion_spreaders)} 意见传播者")

    phase2_output = load_phase2_output()
    console.print(f"加载社交网络拓扑：{len(phase2_output.nodes)} 节点, {len(phase2_output.edges)} 边")

    # 加载种子文本
    seed_file = config.SEEDS_DIR / "example_event.txt"
    with open(seed_file, "r", encoding="utf-8") as f:
        seed_text = f.read()

    # 创建模拟引擎
    engine = SimulationEngine(extraction_output, phase2_output, seed_text)

    # 运行模拟
    tick_logs = engine.run_simulation(max_ticks=config.MAX_TICKS)

    # 打印摘要
    print_simulation_summary(tick_logs)

    # 保存日志
    save_tick_logs(tick_logs)

    # 保存 x(t) 序列
    x_t_sequence = engine.get_x_t_sequence()
    console.print(f"\n[bold]x(t) 序列：[/bold] {[f'{x:.2f}' for x in x_t_sequence]}")
