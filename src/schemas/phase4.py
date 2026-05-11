"""Phase 4 schema contracts."""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


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
    """Phase 4 输出结构。"""
    event_summary: str
    stakeholder_map: str
    emotion_trajectory: List[EmotionTrajectory]
    inflection_points: List[InflectionPoint]
    risk_level: RiskLevel
    risk_assessment: str
    x_t_sequence: List[float] = Field(..., description="x(t) 序列，用于后续 AD/SEIR 模块")


__all__ = [
    "EmotionTrajectory",
    "InflectionPoint",
    "RiskLevel",
    "Phase4Output",
]
