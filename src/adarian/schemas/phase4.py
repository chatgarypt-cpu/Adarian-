"""Phase 4 schema contracts."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


REPORT_TYPE = "模拟推演型舆情风险研判报告"

RISK_LEVEL_LABELS = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "critical": "重大风险",
}

# ── 一级风险域 ──────────────────────────────────

class RiskDomain(str, Enum):
    """一级风险域（稳定索引层，code-owned 映射，不由 Agent 输出）。"""
    GOVERNANCE_TRUST = "governance_trust"
    PUBLIC_SAFETY_LIVELIHOOD = "public_safety_livelihood"
    COMMUNICATION_EVOLUTION = "communication_evolution"
    INFORMATION_SECURITY_IDEOLOGY = "information_security_ideology"
    GOVERNANCE_PRESSURE = "governance_pressure"
    ECONOMIC_FINANCIAL = "economic_financial"

DOMAIN_LABELS: Dict[str, str] = {
    "governance_trust": "治理信任类",
    "public_safety_livelihood": "公共安全与民生类",
    "communication_evolution": "传播演化类",
    "information_security_ideology": "信息安全与意识形态类",
    "governance_pressure": "治理执行压力类",
    "economic_financial": "经济金融类",
}

# ── 二级类型 → 一级域映射（Agent 输出二级类型后，code 映射域）──

TYPE_TO_DOMAIN_MAP: Dict[str, str] = {
    # 治理信任类
    "regulatory_trust_risk": "governance_trust",
    "law_enforcement_credibility_risk": "governance_trust",
    "transparency_risk": "governance_trust",
    "accountability_escalation_risk": "governance_trust",
    "policy_interpretation_pressure_risk": "governance_trust",
    # 公共安全与民生类
    "food_product_safety_risk": "public_safety_livelihood",
    "campus_minor_protection_risk": "public_safety_livelihood",
    "public_safety_concern_risk": "public_safety_livelihood",
    "livelihood_vulnerable_protection_risk": "public_safety_livelihood",
    "public_health_event_risk": "public_safety_livelihood",
    "environmental_ecological_risk": "public_safety_livelihood",
    # 传播演化类
    "negative_narrative_aggregation_risk": "communication_evolution",
    "group_polarization_fragmentation_risk": "communication_evolution",
    "secondary_spread_issue_overflow_risk": "communication_evolution",
    "rumor_fact_confusion_risk": "communication_evolution",
    # 信息安全与意识形态类
    "ai_deepfake_abuse_risk": "information_security_ideology",
    "data_network_security_risk": "information_security_ideology",
    "ideology_foreign_narrative_risk": "information_security_ideology",
    "tech_ethics_ai_governance_risk": "information_security_ideology",
    # 治理执行压力类
    "public_service_response_pressure_risk": "governance_pressure",
    "grassroots_governance_pressure_risk": "governance_pressure",
    "cross_dept_coordination_boundary_risk": "governance_pressure",
    "platform_governance_consumer_overflow_risk": "governance_pressure",
    # 经济金融类
    "financial_market_instability_risk": "economic_financial",
    "local_debt_fiscal_risk": "economic_financial",
    "employment_labor_dispute_risk": "economic_financial",
    "housing_estate_risk": "economic_financial",
    "financial_fraud_illegal_fundraising_risk": "economic_financial",
}

# ── 二级风险类型中文标签（保留旧类型兼容，Agent 输出使用新 28 类）──

RISK_TYPE_LABELS: Dict[str, str] = {
    # 旧类型（兼容已有 dataset）
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
    # 治理信任类
    "regulatory_trust_risk": "监管信任风险",
    "law_enforcement_credibility_risk": "执法公信风险",
    "transparency_risk": "处置透明度风险",
    "accountability_escalation_risk": "舆论问责升级风险",
    "policy_interpretation_pressure_risk": "政策解释压力风险",
    # 公共安全与民生类
    "food_product_safety_risk": "食品与产品安全治理风险",
    "campus_minor_protection_risk": "校园与未成年人保护风险",
    "public_safety_concern_risk": "公共安全感风险",
    "livelihood_vulnerable_protection_risk": "民生保障与弱势群体保护风险",
    "public_health_event_risk": "公共卫生事件风险",
    "environmental_ecological_risk": "环境与生态安全风险",
    # 传播演化类
    "negative_narrative_aggregation_risk": "负向叙事聚合风险",
    "group_polarization_fragmentation_risk": "群体极化与舆论撕裂风险",
    "secondary_spread_issue_overflow_risk": "次生传播与议题外溢风险",
    "rumor_fact_confusion_risk": "谣言与事实混淆风险",
    # 信息安全与意识形态类
    "ai_deepfake_abuse_risk": "AI/深度伪造滥用风险",
    "data_network_security_risk": "数据与网络安全关注风险",
    "ideology_foreign_narrative_risk": "意识形态、价值观与涉外叙事风险",
    "tech_ethics_ai_governance_risk": "科技伦理与AI治理风险",
    # 治理执行压力类
    "public_service_response_pressure_risk": "公共服务回应压力风险",
    "grassroots_governance_pressure_risk": "基层治理承压风险",
    "cross_dept_coordination_boundary_risk": "跨部门协同与责任边界风险",
    "platform_governance_consumer_overflow_risk": "平台治理与消费争议外溢风险",
    # 经济金融类
    "financial_market_instability_risk": "金融市场波动风险",
    "local_debt_fiscal_risk": "地方债务与财政风险",
    "employment_labor_dispute_risk": "就业与劳动权益风险",
    "housing_estate_risk": "房地产与资产价格风险",
    "financial_fraud_illegal_fundraising_risk": "金融诈骗与非法集资风险",
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
    agent_stance_matrix: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Agent 立场矩阵（从 simulation_dataset 透传）",
    )
    primary_domain: Optional[str] = Field(
        default=None,
        description="一级风险域 id（code 从 #1 primary_risk_types 映射）",
    )
    primary_domain_label: Optional[str] = Field(
        default=None,
        description="一级风险域中文标签",
    )

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

    @field_validator("primary_domain")
    @classmethod
    def validate_primary_domain(cls, v):
        if v is not None and v not in DOMAIN_LABELS:
            raise ValueError(f"primary_domain must be one of {list(DOMAIN_LABELS.keys())}")
        return v

    @model_validator(mode="after")
    def validate_risk_contract(self):
        expected_risk_label = RISK_LEVEL_LABELS[self.risk_level.value]
        if self.risk_level_label != expected_risk_label:
            raise ValueError("risk_level_label must match risk_level")

        expected_type_labels = [RISK_TYPE_LABELS[risk_type] for risk_type in self.primary_risk_types]
        if self.risk_type_labels != expected_type_labels:
            raise ValueError("risk_type_labels must match primary_risk_types")

        if self.primary_domain is not None and self.primary_risk_types:
            expected_domain = TYPE_TO_DOMAIN_MAP.get(self.primary_risk_types[0])
            if expected_domain and self.primary_domain != expected_domain:
                raise ValueError(
                    f"primary_domain ({self.primary_domain}) does not match "
                    f"TYPE_TO_DOMAIN_MAP for {self.primary_risk_types[0]} ({expected_domain})"
                )

        return self


__all__ = [
    "RiskDomain",
    "DOMAIN_LABELS",
    "TYPE_TO_DOMAIN_MAP",
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
