"""Phase 4 schema contracts."""

from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field, field_validator, model_validator


REPORT_TYPE = "模拟推演型舆情风险研判报告"

RISK_LEVEL_LABELS = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "critical": "重大风险",
}

RISK_TYPE_LABELS: Dict[str, str] = {
    "fact_dispute_risk": "事实争议风险",
    "procedure_dispute_risk": "程序争议风险",
    "regulatory_accountability_risk": "监管责任质疑风险",
    "law_enforcement_trust_risk": "执法公信力风险",
    "response_delay_risk": "回应滞后风险",
    "information_opacity_risk": "信息不透明风险",
    "negative_narrative_risk": "负面叙事聚合风险",
    "group_polarization_risk": "群体对立风险",
    "secondary_spread_risk": "次生传播风险",
    "overseas_amplification_risk": "境外放大风险",
    "rumor_spread_risk": "谣言扩散风险",
    "institution_image_risk": "机构形象风险",
    "local_governance_pressure_risk": "属地治理压力风险",
}


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


class AudienceMode(str, Enum):
    """报告阅读主体模式。"""
    GENERIC_GOVERNMENT = "generic_government"
    LAW_ENFORCEMENT_FACING = "law_enforcement_facing"
    REGULATOR_FACING = "regulator_facing"
    PUBLIC_MANAGEMENT_FACING = "public_management_facing"


class ReportMeta(BaseModel):
    """报告元信息。"""
    generated_at: str
    timezone: str
    report_type: str = REPORT_TYPE
    event_name: str
    total_ticks: int = Field(..., ge=0)
    simulation_run_id: str


class Phase4Output(BaseModel):
    """Phase 4 输出结构。"""
    report_meta: ReportMeta
    event_summary: str
    stakeholder_map: str
    emotion_trajectory: List[EmotionTrajectory]
    inflection_points: List[InflectionPoint]
    risk_level: RiskLevel
    risk_level_label: str
    audience_mode: AudienceMode = AudienceMode.GENERIC_GOVERNMENT
    primary_risk_types: List[str] = Field(default_factory=list)
    risk_type_labels: List[str] = Field(default_factory=list)
    risk_assessment: str
    x_t_sequence: List[float] = Field(..., description="x(t) 序列，用于后续 AD/SEIR 模块")

    @field_validator("risk_level_label")
    @classmethod
    def validate_risk_level_label(cls, v):
        if v not in RISK_LEVEL_LABELS.values():
            raise ValueError("risk_level_label must be one of the canonical Chinese risk labels")
        return v

    @field_validator("primary_risk_types")
    @classmethod
    def validate_primary_risk_types(cls, v):
        invalid = [risk_type for risk_type in v if risk_type not in RISK_TYPE_LABELS]
        if invalid:
            raise ValueError(f"primary_risk_types contains unknown risk types: {invalid}")
        return v

    @model_validator(mode="after")
    def validate_risk_contract(self):
        expected_risk_label = RISK_LEVEL_LABELS[self.risk_level.value]
        if self.risk_level_label != expected_risk_label:
            raise ValueError("risk_level_label must match risk_level")

        expected_type_labels = [RISK_TYPE_LABELS[risk_type] for risk_type in self.primary_risk_types]
        if self.risk_type_labels != expected_type_labels:
            raise ValueError("risk_type_labels must match primary_risk_types")
        return self


__all__ = [
    "EmotionTrajectory",
    "InflectionPoint",
    "RiskLevel",
    "AudienceMode",
    "ReportMeta",
    "REPORT_TYPE",
    "RISK_LEVEL_LABELS",
    "RISK_TYPE_LABELS",
    "Phase4Output",
]
