"""Phase 2 schema contracts."""

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class NodeRole(str, Enum):
    """节点角色"""
    CORE = "core"
    PERIPHERY = "periphery"


class GraphNode(BaseModel):
    """图节点。"""
    id: int = Field(..., description="节点唯一ID")
    group_name: str = Field(..., description="所属群体名称")
    archetype_index: int = Field(
        ..., description="在 archetypes 列表中的索引，-1=事件实体，-2=意见传播实体"
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
    persona_name: Optional[str] = Field(default=None, description="群体典型代表的名字")
    age_range: Optional[str] = Field(default=None, description="年龄段")
    occupation: Optional[str] = Field(default=None, description="职业或身份")
    personality: Optional[str] = Field(default=None, description="性格特征")
    motivation: Optional[str] = Field(default=None, description="发言的核心动机")
    typical_phrases: Optional[List[str]] = Field(default=None, description="口头禅列表")


class EdgeType(str, Enum):
    """边类型"""
    FOLLOWS = "follows"
    FOLLOWS_CROSS_GROUP = "follows_cross_group"
    FOLLOWS_CORE_CROSS = "follows_core_cross"


class GraphEdge(BaseModel):
    """图边"""
    source: int = Field(..., ge=0, description="源节点ID")
    target: int = Field(..., ge=0, description="目标节点ID")
    type: EdgeType = Field(default=EdgeType.FOLLOWS, description="边类型")


class Phase2Output(BaseModel):
    """Phase 2 输出结构。"""
    nodes: List[GraphNode] = Field(..., description="所有节点")
    edges: List[GraphEdge] = Field(..., description="所有边")


__all__ = [
    "NodeRole",
    "GraphNode",
    "EdgeType",
    "GraphEdge",
    "Phase2Output",
]
