"""Active risk schema contracts — migrated from schemas/phase4.py (v1.5.2.3)."""

from enum import Enum
from typing import Dict

# ── Risk level labels ──────────────────────────────

RISK_LEVEL_LABELS: Dict[str, str] = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "critical": "重大风险",
}

# ── Risk level enum ────────────────────────────────

class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Audience mode enum ─────────────────────────────

class AudienceMode(str, Enum):
    """报告阅读主体模式。"""
    GENERIC_GOVERNMENT = "generic_government"
    LAW_ENFORCEMENT_FACING = "law_enforcement_facing"
    REGULATOR_FACING = "regulator_facing"
    PUBLIC_MANAGEMENT_FACING = "public_management_facing"


# ── 一级风险域 ─────────────────────────────────────

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

# ── 二级风险类型中文标签 ────────────────────────────

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

# ── Public exports ──────────────────────────────────

__all__ = [
    "RiskLevel",
    "AudienceMode",
    "RiskDomain",
    "DOMAIN_LABELS",
    "TYPE_TO_DOMAIN_MAP",
    "RISK_TYPE_LABELS",
    "RISK_LEVEL_LABELS",
]
