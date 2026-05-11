"""
Deprecated legacy schema contracts.

Do not add new business logic here.
Replacement path: src.schemas.common / src.schemas.phase2 / src.schemas.phase3 / src.schemas.phase4.
Target removal: after v1.2.7 P/C/V Skeleton passes smoke and contract tests.
"""

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator

from .common import Entity, Relation


class EntityExtractionResult(BaseModel):
    """Phase 1 事实层输出。"""
    event_summary: str = Field(..., description="事件摘要")
    event_scale: float = Field(
        ..., ge=0.0, le=1.0, description="事件规模参数：0.0=个人事件，1.0=全社会事件"
    )
    event_controversy: float = Field(
        ..., ge=0.0, le=1.0, description="事件争议性：0.0=事实清晰，1.0=高度对立"
    )
    event_type: str = Field(..., description="事件类型")
    event_entities: List[Entity] = Field(
        ..., min_length=1, description="事件实体列表（直接参与事件）"
    )
    relations: List[Relation] = Field(default_factory=list, description="实体关系列表")


class GroupPlanItem(BaseModel):
    """Phase 1 结构层输出项。"""
    group_name: str = Field(..., description="群体名称")
    related_event_entity: str = Field(..., description="关联的事件实体名称")
    description: str = Field(..., max_length=100, description="骨架描述")
    I: float = Field(..., ge=1.0, le=10.0, description="立场强度")
    susceptibility: float = Field(..., ge=0.0, le=1.0, description="易感性")
    raw_weight: float = Field(..., gt=0.0, description="原始权重，用于后续归一化为百分比")
    entity_category: Literal["opinion_spreader"] = Field(
        default="opinion_spreader", description="固定为 opinion_spreader"
    )


class GroupPlanResult(BaseModel):
    """Phase 1 结构层输出。"""
    opinion_spreaders: List[GroupPlanItem] = Field(
        default_factory=list,
        description="意见传播者列表",
    )


class PersonaProfile(BaseModel):
    """Persona 表达层画像。"""
    persona_name: str = Field(..., description="群体典型代表名字")
    age_range: str = Field(..., description="年龄段")
    occupation: str = Field(..., description="职业或身份")
    personality: str = Field(..., description="性格特征")
    motivation: str = Field(..., description="发言核心动机")
    typical_phrases: List[str] = Field(..., min_length=2, max_length=3, description="口头禅")
    communication_style: str = Field(..., max_length=100, description="说话风格")


class PersonaEnrichedGroupItem(BaseModel):
    """合并 skeleton 与 persona 的中间结果。"""
    skeleton: GroupPlanItem
    persona: PersonaProfile


class PersonaEnrichedGroupPlan(BaseModel):
    """表达层增强后的群体计划。"""
    groups: List[PersonaEnrichedGroupItem] = Field(
        default_factory=list,
        description="合并 skeleton 与 persona 的群体列表",
    )


class Archetype(BaseModel):
    """人群原型，保留用于向后兼容。"""
    group_name: str = Field(..., description="群体名称，如'品牌死忠粉'、'理智成分党'")
    related_entity: str = Field(..., description="关联的核心实体名称")
    description: str = Field(..., max_length=100, description="50字以内的人设描述")
    stance_score: float = Field(..., ge=1.0, le=10.0, description="初始立场分。1.0-3.0=强烈批评，4.0-6.0=中立观望，7.0-10.0=强烈支持")
    susceptibility: float = Field(..., ge=0.0, le=1.0, description="易感性。越高越容易被他人发言影响")
    confirmation_bias_level: Literal["none", "weak", "strong"] = Field(..., description="确认偏差强度")
    estimated_percentage: int = Field(..., ge=0, le=100, description="LLM 预估该群体占比")
    communication_style: str = Field(..., max_length=100, description="该群体的典型说话风格")

    @field_validator("stance_score")
    @classmethod
    def validate_stance_score(cls, v):
        if not 1.0 <= v <= 10.0:
            raise ValueError("stance_score must be between 1.0 and 10.0")
        return v

    @field_validator("susceptibility")
    @classmethod
    def validate_susceptibility(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("susceptibility must be between 0.0 and 1.0")
        return v

    @field_validator("estimated_percentage")
    @classmethod
    def validate_percentage(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("estimated_percentage must be between 0 and 100")
        return v


class Phase1Output(BaseModel):
    """Phase 1 legacy output structure."""
    event_summary: str = Field(..., max_length=500, description="事件一句话摘要")
    conflict_axes: List[str] = Field(..., min_length=1, description="冲突轴列表")
    archetypes: List[Archetype] = Field(..., description="人群原型列表")

    @field_validator("archetypes")
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
                    update={"estimated_percentage": v[max_idx].estimated_percentage + delta}
                )
        return v

    @field_validator("archetypes")
    @classmethod
    def validate_archetypes_extreme(cls, v):
        """验证至少有一个 stance_score < 3.0 和一个 > 7.0"""
        has_low = any(a.stance_score < 3.0 for a in v)
        has_high = any(a.stance_score > 7.0 for a in v)
        if not (has_low and has_high):
            raise ValueError("archetypes must contain at least one with stance_score < 3.0 and one > 7.0")
        return v


class SimulationCard(BaseModel):
    """Phase 3 轻量模拟卡片。"""
    agent_id: int = Field(..., ge=0, description="Agent 唯一ID")
    group_name: str = Field(..., description="群体名称")
    related_entity: str = Field(..., description="关联实体")
    current_stance: float = Field(..., ge=1.0, le=10.0, description="当前立场分")
    susceptibility: float = Field(..., ge=0.0, le=1.0, description="易感性")
    short_personality: str = Field(..., description="压缩后的性格摘要")
    short_motivation: str = Field(..., description="压缩后的动机摘要")
    top_phrases: List[str] = Field(default_factory=list, description="保留的1-2条口头禅")
    activity_state: str = Field(default="active", description="为未来 state machine 预留的活动状态入口")


__all__ = [
    "EntityExtractionResult",
    "GroupPlanItem",
    "GroupPlanResult",
    "PersonaProfile",
    "PersonaEnrichedGroupItem",
    "PersonaEnrichedGroupPlan",
    "Archetype",
    "Phase1Output",
    "SimulationCard",
]
