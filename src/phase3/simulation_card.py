"""Phase 3 模拟卡片。"""

from __future__ import annotations


def build_simulation_card(agent, current_stance: float) -> dict:
    """从 agent 构建轻量上下文字典。"""
    return {
        "group_name": getattr(agent, "group_name", ""),
        "persona_name": getattr(agent, "persona_name", getattr(agent, "group_name", "")),
        "age_range": getattr(agent, "age_range", "25-34"),
        "occupation": getattr(agent, "occupation", "网民"),
        "personality": getattr(agent, "personality", "理性"),
        "motivation": getattr(agent, "motivation", "表达观点"),
        "typical_phrases": getattr(agent, "typical_phrases", ["说句实话", "我觉得"]),
        "related_entity": getattr(agent, "related_entity", getattr(agent, "group_name", "")),
        "communication_style": getattr(agent, "communication_style", "客观陈述"),
        "description": getattr(agent, "description", ""),
        "current_stance": current_stance,
        "confirmation_bias_level": getattr(agent, "confirmation_bias_level", "weak"),
    }
