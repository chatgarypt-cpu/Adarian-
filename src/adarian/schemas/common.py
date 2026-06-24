"""
Shared schema contracts used across Phase 1-4.
"""

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class EntityCategory(str, Enum):
    """实体类别"""
    EVENT_ENTITY = "event_entity"
    OPINION_SPREADER = "opinion_spreader"


class Entity(BaseModel):
    """事件实体（Event Entity）。"""
    name: str = Field(..., description="实体名称")
    type: Literal["individual", "organization", "group"] = Field(
        ..., description="实体类型：individual=个人, organization=组织机构, group=群体"
    )
    role: str = Field(..., description="在事件中的角色")
    entity_category: Literal["event_entity"] = Field(
        default="event_entity", description="固定为 event_entity"
    )
    can_speak: bool = Field(..., description="是否可以发言：true=可以，false=不可（如已故/匿名）")
    original_statement: Optional[str] = Field(
        default=None,
        description="从种子材料提取的原始发言（带引号的直接引语），无原始发言则为 None",
    )
    can_speak_reason: Optional[str] = Field(
        default=None,
        description="当 can_speak=false 时，说明不可发言的原因（如：已故、匿名、被禁言等）",
    )


class OpinionSpreader(BaseModel):
    """意见传播实体（Opinion Spreader）。"""
    group_name: str = Field(..., description="群体名称，如'花西子死忠粉'、'理性消费者'")
    related_event_entity: str = Field(
        ..., description="关联的事件实体名称（必须在 event_entities 中存在）"
    )
    description: str = Field(..., max_length=100, description="50字以内的人设描述")
    I: float = Field(
        ...,
        ge=1.0,
        le=10.0,
        description="立场强度(Intensity)：1.0-3.0=极易动摇，4.0-6.0=中等坚定，7.0-10.0=极度坚定",
    )
    P: int = Field(
        ...,
        description="立场方向(Position)：+1=支持/维护，-1=反对/批评",
    )
    susceptibility: float = Field(
        ..., ge=0.0, le=1.0, description="易感性。越高越容易被他人发言影响"
    )
    estimated_percentage: int = Field(
        ..., ge=0, le=100, description="该群体在意见传播者中的占比，所有群体之和=100"
    )
    communication_style: str = Field(
        ..., max_length=100, description="该群体的典型说话风格"
    )
    entity_category: Literal["opinion_spreader"] = Field(
        default="opinion_spreader", description="固定为 opinion_spreader"
    )
    persona_name: str = Field(..., description="群体典型代表的名字，如：小美、老张、陈老师")
    age_range: str = Field(..., description="年龄段，如：18-24、25-34、35-45、45-60")
    occupation: str = Field(..., description="职业或身份，如：大学生、美妆博主、全职妈妈、退休教师、程序员")
    personality: str = Field(..., description="性格特征，如：冲动易怒、冷静理性、感性共情、较真执拗、随大流")
    motivation: str = Field(..., description="发言的核心动机，如：维护消费者权益、追求性价比、支持国货、追求真相")
    typical_phrases: List[str] = Field(
        ...,
        description="2-3个口头禅或常用表达",
        min_length=2,
        max_length=3,
    )

    @field_validator("I")
    @classmethod
    def validate_I(cls, v):
        if not 1.0 <= v <= 10.0:
            raise ValueError("I must be between 1.0 and 10.0")
        return v

    @field_validator("P")
    @classmethod
    def validate_P(cls, v):
        if v not in (+1, -1):
            raise ValueError("P must be +1 or -1")
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

    @property
    def C(self) -> float:
        """C = P × (I/10)，系统固定推导"""
        return self.P * (self.I / 10)

    @property
    def stance_score(self) -> float:
        """兼容属性：将 I/P 映射回 1-10 分数"""
        if self.P == +1:
            return self.I
        return 11 - self.I

    @property
    def confirmation_bias_level(self) -> str:
        """兼容属性：从 I 推导 confirmation_bias_level"""
        if self.I >= 7:
            return "strong"
        if self.I >= 4:
            return "weak"
        return "none"


class Relation(BaseModel):
    """实体间关系。"""
    source: str = Field(..., description="关系起点实体名称")
    target: str = Field(..., description="关系终点实体名称")
    type: str = Field(..., description="关系类型（如：雇佣、监管、言论关联）")


class EntityExtractionOutput(BaseModel):
    """Phase 1 canonical output: entity extraction result."""
    event_summary: str = Field(..., description="事件摘要")
    event_scale: float = Field(
        ..., ge=0.0, le=1.0, description="事件规模参数：0.0=个人事件，1.0=全社会事件"
    )
    event_controversy: float = Field(
        ..., ge=0.0, le=1.0, description="事件争议性：0.0=事实清晰，1.0=高度对立"
    )
    event_type: str = Field(..., description="事件类型（如：产品质量危机、校园冲突、政策争议）")
    event_entities: List[Entity] = Field(
        ..., min_length=1, description="事件实体列表（直接参与事件）"
    )
    opinion_spreaders: List[OpinionSpreader] = Field(
        ..., description="意见传播实体列表（评论事件）"
    )
    relations: List[Relation] = Field(..., description="实体关系列表")

    @field_validator("event_scale", "event_controversy")
    @classmethod
    def validate_ratios(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"event_scale/event_controversy 必须在 0.0-1.0 之间，当前为 {v}")
        return v

    @model_validator(mode="after")
    def validate_total_agents(self):
        """验证事件实体 + 意见传播实体总数不超过 15"""
        total = len(self.event_entities) + len(self.opinion_spreaders)
        if total > 15:
            raise ValueError(f"事件实体 + 意见传播实体总数 ({total}) 不得超过 15")
        return self

    @model_validator(mode="after")
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

    @model_validator(mode="after")
    def validate_bipolar_P(self):
        """验证至少有一个 P=+1 和一个 P=-1（确保双向对立）"""
        has_support = any(s.P == +1 for s in self.opinion_spreaders)
        has_oppose = any(s.P == -1 for s in self.opinion_spreaders)
        if not (has_support and has_oppose):
            raise ValueError("opinion_spreaders 必须至少包含一个 P=+1（支持）和一个 P=-1（反对）的群体")
        return self

    @model_validator(mode="after")
    def validate_estimated_percentage_sum(self):
        """验证所有 opinion_spreader 的 estimated_percentage 之和 = 100"""
        total = sum(s.estimated_percentage for s in self.opinion_spreaders)
        if total != 100:
            raise ValueError(
                f"opinion_spreaders 的 estimated_percentage 之和为 {total}，必须等于 100"
            )
        return self


class ConfirmationBiasLevel(str, Enum):
    """确认偏差强度，保留为 public export。"""
    NONE = "none"
    WEAK = "weak"
    STRONG = "strong"


__all__ = [
    "EntityCategory",
    "Entity",
    "OpinionSpreader",
    "Relation",
    "EntityExtractionOutput",
    "ConfirmationBiasLevel",
]
