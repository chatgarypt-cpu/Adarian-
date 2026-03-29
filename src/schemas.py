"""
Pydantic 数据模型定义
---
Phase 1-4 所有模块间传递的数据结构必须在这里定义。
Why: 保证模块间数据流的可靠性，所有 LLM 输出必须经过校验。

修改历史：
- v1.1.0: 初始实现，Phase 1-4 数据模型
- v1.1.1: 新增 Phase 0 数据模型（Entity, Relation, EntityExtractionOutput），
         修改 Archetype 增加 related_entity 和 confirmation_bias_level 字段
- v1.1.3: GraphNode 增加 confirmation_bias_level 字段，EdgeType 增加跨圈层边类型
- v1.1.4: 实体分类：新增 EntityCategory 枚举、OpinionSpreader 模型，
         EntityExtractionOutput 改为 event_entities + opinion_spreaders 双列结构
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Literal, Any
from enum import Enum


# =============================================================================
# 实体类别枚举（v1.1.4 新增）
# =============================================================================

class EntityCategory(str, Enum):
    """实体类别"""
    EVENT_ENTITY = "event_entity"           # 事件实体（直接参与，第一批发言）
    OPINION_SPREADER = "opinion_spreader"   # 意见传播实体（评论事件实体）


# =============================================================================
# Phase 1: 实体提取（v1.1.4 重构：LLM1/2/3 协作）
# =============================================================================

class Entity(BaseModel):
    """
    事件实体（Event Entity）

    直接参与事件本身，作为第一批发言者存在。

    修改于：v1.1.4
    - 新增 entity_category 字段
    """
    name: str = Field(..., description="实体名称")
    type: Literal["individual", "organization", "group"] = Field(
        ..., description="实体类型：individual=个人, organization=组织机构, group=群体"
    )
    role: str = Field(..., description="在事件中的角色")
    entity_category: Literal["event_entity"] = Field(
        default="event_entity", description="固定为 event_entity"
    )

    # v1.1.6 新增
    can_speak: bool = Field(..., description="是否可以发言：true=可以，false=不可（如已故/匿名）")
    original_statement: Optional[str] = Field(
        default=None,
        description="从种子材料提取的原始发言（带引号的直接引语），无原始发言则为 None"
    )


class OpinionSpreader(BaseModel):
    """
    意见传播实体（Opinion Spreader）

    不直接参与事件，但会传播意见。基于事件温度和烈度生成。

    新增于：v1.1.4
    """
    group_name: str = Field(..., description="群体名称，如'花西子死忠粉'、'理性消费者'")
    related_event_entity: str = Field(
        ..., description="关联的事件实体名称（必须在 event_entities 中存在）"
    )
    description: str = Field(..., max_length=100, description="50字以内的人设描述")
    stance_score: float = Field(
        ..., ge=1.0, le=10.0,
        description="初始立场分。1=强烈支持，10=强烈批评"
    )
    susceptibility: float = Field(
        ..., ge=0.0, le=1.0,
        description="易感性。越高越容易被他人发言影响"
    )
    confirmation_bias_level: Literal["none", "weak", "strong"] = Field(
        ..., description="确认偏差强度：none=无偏差，weak=弱偏差，strong=强偏差"
    )
    estimated_percentage: int = Field(
        ..., ge=0, le=100,
        description="该群体在意见传播者中的占比，所有群体之和=100"
    )
    communication_style: str = Field(
        ..., max_length=100,
        description="该群体的典型说话风格"
    )
    entity_category: Literal["opinion_spreader"] = Field(
        default="opinion_spreader", description="固定为 opinion_spreader"
    )

    @field_validator('stance_score')
    @classmethod
    def validate_stance_score(cls, v):
        if not 1.0 <= v <= 10.0:
            raise ValueError('stance_score must be between 1.0 and 10.0')
        return v

    @field_validator('susceptibility')
    @classmethod
    def validate_susceptibility(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('susceptibility must be between 0.0 and 1.0')
        return v

    @field_validator('estimated_percentage')
    @classmethod
    def validate_percentage(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('estimated_percentage must be between 0 and 100')
        return v


class Relation(BaseModel):
    """
    实体间关系
    """
    source: str = Field(..., description="关系起点实体名称")
    target: str = Field(..., description="关系终点实体名称")
    type: str = Field(..., description="关系类型（如：雇佣、监管、言论关联）")


class EntityExtractionOutput(BaseModel):
    """
    Phase 1 输出：实体提取结果（v1.1.4 重构）

    采用 LLM1/2/3 协作架构：
    - LLM1：设置 event_temperature + event_intensity
    - LLM2：提取事件实体 + 生成意见传播者
    - LLM3：格式校验，失败则 LLM2 重试

    修改于：v1.1.4
    - 从 core_entities 改为 event_entities + opinion_spreaders 双列结构
    - 新增 event_intensity 字段
    """
    event_summary: str = Field(..., description="事件摘要")
    event_temperature: float = Field(
        ..., ge=0.0, le=1.0,
        description="事件热度参数：0.0=冷门事件，1.0=全网热议"
    )
    event_intensity: float = Field(
        ..., ge=0.0, le=1.0,
        description="事件烈度参数：0.0=极低，1.0=极高"
    )
    event_type: str = Field(
        ..., description="事件类型（如：产品质量危机、校园冲突、政策争议）"
    )
    event_entities: List[Entity] = Field(
        ..., min_length=1, description="事件实体列表（直接参与事件）"
    )
    opinion_spreaders: List[OpinionSpreader] = Field(
        ..., description="意见传播实体列表（评论事件）"
    )
    relations: List[Relation] = Field(..., description="实体关系列表")

    @field_validator('event_temperature', 'event_intensity')
    @classmethod
    def validate_ratios(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f'event_temperature/event_intensity 必须在 0.0-1.0 之间，当前为 {v}')
        return v

    @model_validator(mode='after')
    def validate_total_agents(self):
        """验证事件实体 + 意见传播实体总数不超过 15"""
        total = len(self.event_entities) + len(self.opinion_spreaders)
        if total > 15:
            raise ValueError(
                f"事件实体 + 意见传播实体总数 ({total}) 不得超过 15"
            )
        return self

    @model_validator(mode='after')
    def validate_opinion_spreader_entity_refs(self):
        """验证所有 opinion_spreader 的 related_event_entity 都在 event_entities 中"""
        entity_names = {e.name for e in self.event_entities}
        for spreader in self.opinion_spreaders:
            if spreader.related_event_entity not in entity_names:
                raise ValueError(
                    f"OpinionSpreader '{spreader.group_name}' 的 related_event_entity "
                    f"'{spreader.related_event_entity}' 不在 event_entities 中"
                )
        return self

    @model_validator(mode='after')
    def validate_extreme_stances(self):
        """验证至少有一个 stance_score < 3.0 和一个 > 7.0"""
        has_low = any(s.stance_score < 3.0 for s in self.opinion_spreaders)
        has_high = any(s.stance_score > 7.0 for s in self.opinion_spreaders)
        if not (has_low and has_high):
            raise ValueError(
                'opinion_spreaders 必须至少包含一个 stance_score < 3.0 和一个 > 7.0 的群体'
            )
        return self


# =============================================================================
# Phase 1: 动态人群生成（v1.1.4 保留但简化，Archetype 保留用于兼容）
# =============================================================================

class ConfirmationBiasLevel(str, Enum):
    """确认偏差强度"""
    NONE = "none"      # 无确认偏差
    WEAK = "weak"      # 弱确认偏差
    STRONG = "strong"  # 强确认偏差（铁杆粉丝/坚定反对者）


class Archetype(BaseModel):
    """
    人群原型 (Archetype)

    代表舆论场中的一类典型人群。

    注意：v1.1.4 中已被 OpinionSpreader 替代，保留用于向后兼容。
    """
    group_name: str = Field(..., description="群体名称，如'品牌死忠粉'、'理智成分党'")
    related_entity: str = Field(
        ..., description="关联的核心实体名称"
    )
    description: str = Field(..., max_length=100, description="50字以内的人设描述")
    stance_score: float = Field(..., ge=1.0, le=10.0, description="初始立场分。1=强烈支持，10=强烈批评")
    susceptibility: float = Field(..., ge=0.0, le=1.0, description="易感性。越高越容易被他人发言影响")
    confirmation_bias_level: Literal["none", "weak", "strong"] = Field(
        ..., description="确认偏差强度"
    )
    estimated_percentage: int = Field(..., ge=0, le=100, description="LLM 预估该群体占比")
    communication_style: str = Field(..., max_length=100, description="该群体的典型说话风格")

    @field_validator('stance_score')
    @classmethod
    def validate_stance_score(cls, v):
        if not 1.0 <= v <= 10.0:
            raise ValueError('stance_score must be between 1.0 and 10.0')
        return v

    @field_validator('susceptibility')
    @classmethod
    def validate_susceptibility(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('susceptibility must be between 0.0 and 1.0')
        return v

    @field_validator('estimated_percentage')
    @classmethod
    def validate_percentage(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('estimated_percentage must be between 0 and 100')
        return v


class Phase1Output(BaseModel):
    """
    Phase 1 输出结构（v1.1.4 保留用于兼容）

    注意：v1.1.4 主要使用 EntityExtractionOutput，此模型保留用于向后兼容。
    """
    event_summary: str = Field(..., max_length=500, description="事件一句话摘要")
    conflict_axes: List[str] = Field(..., min_length=1, description="冲突轴列表")
    archetypes: List[Archetype] = Field(..., description="人群原型列表")

    @field_validator('archetypes')
    @classmethod
    def validate_archetypes_percentage_sum(cls, v):
        """验证并自动校正所有 estimated_percentage 之和等于 100"""
        total = sum(a.estimated_percentage for a in v)
        if total != 100:
            delta = 100 - total
            if delta != 0:
                max_idx = max(range(len(v)), key=lambda i: v[i].estimated_percentage)
                v = list(v)
                v[max_idx] = v[max_idx].model_copy(
                    update={'estimated_percentage': v[max_idx].estimated_percentage + delta}
                )
        return v

    @field_validator('archetypes')
    @classmethod
    def validate_archetypes_extreme(cls, v):
        """验证至少有一个 stance_score < 3.0 和一个 > 7.0"""
        has_low = any(a.stance_score < 3.0 for a in v)
        has_high = any(a.stance_score > 7.0 for a in v)
        if not (has_low and has_high):
            raise ValueError('archetypes must contain at least one with stance_score < 3.0 and one > 7.0')
        return v


# =============================================================================
# Phase 2: 社交拓扑构建
# =============================================================================

class NodeRole(str, Enum):
    """节点角色"""
    CORE = "core"       # 大V/意见领袖（事件实体作为 Core）
    PERIPHERY = "periphery"  # 普通用户/粉丝（意见传播实体作为 Periphery）


class GraphNode(BaseModel):
    """
    图节点

    修改于：v1.1.4
    - archetype_index 使用特殊值：-1=事件实体，-2=意见传播实体
    - 新增 entity_category 字段区分节点类型
    """
    id: int = Field(..., description="节点唯一ID")
    group_name: str = Field(..., description="所属群体名称")
    archetype_index: int = Field(
        ...,
        description="在 archetypes 列表中的索引，-1=事件实体，-2=意见传播实体"
    )
    related_entity: str = Field(..., description="关联的实体名称")
    role: NodeRole = Field(..., description="节点角色：core 或 periphery")
    stance_score: float = Field(..., ge=1.0, le=10.0, description="当前立场分")
    susceptibility: float = Field(..., ge=0.0, le=1.0, description="易感性")
    confirmation_bias_level: Literal["none", "weak", "strong"] = Field(
        default="none", description="确认偏差强度"
    )
    entity_category: Literal["event_entity", "opinion_spreader"] = Field(
        ..., description="实体类别：event_entity 或 opinion_spreader"
    )


class EdgeType(str, Enum):
    """边类型"""
    FOLLOWS = "follows"    # 单向关注（群体内）
    FOLLOWS_CROSS_GROUP = "follows_cross_group"    # 跨圈层关注
    FOLLOWS_CORE_CROSS = "follows_core_cross"     # Core 节点间跨圈层关注


class GraphEdge(BaseModel):
    """图边"""
    source: int = Field(..., ge=0, description="源节点ID")
    target: int = Field(..., ge=0, description="目标节点ID")
    type: EdgeType = Field(default=EdgeType.FOLLOWS, description="边类型")


class Phase2Output(BaseModel):
    """
    Phase 2 输出结构

    社交网络拓扑的完整描述。
    """
    nodes: List[GraphNode] = Field(..., description="所有节点")
    edges: List[GraphEdge] = Field(..., description="所有边")


# =============================================================================
# Phase 3: 模拟推演
# =============================================================================

class AgentEntry(BaseModel):
    """单个 Agent 的发言条目"""
    agent_id: int = Field(..., description="Agent 唯一ID")
    group_name: str = Field(..., description="所属群体名称")
    saw_posts_from: List[int] = Field(..., description="本轮读取的发言者 ID 列表")
    previous_stance: float = Field(..., ge=1.0, le=10.0, description="上一轮立场分")
    current_stance: float = Field(..., ge=1.0, le=10.0, description="本轮立场分")
    stance_delta: float = Field(..., description="立场变化量，绝对值表示变化程度")
    comment: str = Field(..., max_length=200, description="发表的评论内容")
    reasoning: str = Field(..., max_length=100, description="立场理由")


class GlobalMetrics(BaseModel):
    """
    全局指标

    关键输出：x(t) 序列将用于后续 AD 快模块和 SEIR 慢模块。
    """
    mean_stance: float = Field(..., ge=1.0, le=10.0, description="全局平均立场分，即 x(t)")
    std_stance: float = Field(..., ge=0.0, description="立场标准差，衡量群体分裂程度")
    polarization_index: float = Field(..., ge=0.0, le=1.0, description="极化指数 = std/mean")


class TickLog(BaseModel):
    """每轮交互日志"""
    tick: int = Field(..., ge=0, description="轮次编号（0=事件实体发言）")
    entries: List[AgentEntry] = Field(..., description="所有 Agent 的发言条目")
    global_metrics: GlobalMetrics = Field(..., description="本轮全局指标")


# =============================================================================
# Phase 4: 报告生成
# =============================================================================

class EmotionTrajectory(BaseModel):
    """情绪演化轨迹条目"""
    tick: int
    mean_stance: float
    std_stance: float
    polarization_index: float
    key_event: str


class InflectionPoint(BaseModel):
    """拐点分析条目"""
    tick: int
    agent_id: int
    group_name: str
    pivotal_comment: str
    impact_description: str


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Phase4Output(BaseModel):
    """
    Phase 4 输出结构

    最终舆情洞察报告。
    """
    event_summary: str
    stakeholder_map: str
    emotion_trajectory: List[EmotionTrajectory]
    inflection_points: List[InflectionPoint]
    risk_level: RiskLevel
    risk_assessment: str
    x_t_sequence: List[float] = Field(..., description="x(t) 序列，用于后续 AD/SEIR 模块")
