"""Phase 3 模拟卡片。"""

from __future__ import annotations


def _coalesce(value, default):
    return default if value in (None, "", []) else value


def build_simulation_card(agent, current_stance: float) -> dict:
    """从 GraphNode 构建轻量上下文字典。"""
    group_name = _coalesce(getattr(agent, "group_name", None), "")
    typical_phrases = _coalesce(getattr(agent, "typical_phrases", None), ["说句实话", "我觉得"])

    return {
        "group_name": group_name,
        "persona_name": _coalesce(getattr(agent, "persona_name", None), group_name),
        "age_range": _coalesce(getattr(agent, "age_range", None), "25-34"),
        "occupation": _coalesce(getattr(agent, "occupation", None), "网民"),
        "personality": _coalesce(getattr(agent, "personality", None), "理性"),
        "motivation": _coalesce(getattr(agent, "motivation", None), "表达观点"),
        "typical_phrases": typical_phrases,
        "related_entity": _coalesce(getattr(agent, "related_entity", None), group_name),
        "communication_style": "客观陈述",
        "description": "",
        "current_stance": current_stance,
        "confirmation_bias_level": _coalesce(
            getattr(agent, "confirmation_bias_level", None),
            "weak",
        ),
    }

