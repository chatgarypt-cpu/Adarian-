"""Phase 3 上下文构建。"""

from __future__ import annotations

from typing import Any, List, Tuple


def _get(card: Any, key: str, default: Any) -> Any:
    if isinstance(card, dict):
        value = card.get(key, default)
    else:
        value = getattr(card, key, default)
    return default if value in (None, "") else value


def build_lightweight_context(
    card: dict,
    event_summary: str,
    event_entity_name: str,
    event_entity_post: str,
    followed: List[Tuple[int, str, str]],
    history: List[str],
) -> Tuple[str, str]:
    """构造 Phase 3 传播者的轻量 prompt。"""
    group_name = _get(card, "group_name", "")
    persona_name = _get(card, "persona_name", group_name)
    age_range = _get(card, "age_range", "25-34")
    occupation = _get(card, "occupation", "网民")
    personality = _get(card, "personality", "理性")
    motivation = _get(card, "motivation", "表达观点")
    related_entity = _get(card, "related_entity", "")
    communication_style = _get(card, "communication_style", "客观陈述")
    typical_phrases = _get(card, "typical_phrases", ["说句实话", "我觉得"])

    if isinstance(typical_phrases, (list, tuple)):
        phrase_text = ", ".join(str(item) for item in typical_phrases if item)
    else:
        phrase_text = str(typical_phrases)

    system_prompt = f"""你是一个真实的社交媒体用户。

【身份】
- 名字：{persona_name}
- 群体：{group_name}
- 年龄：{age_range}
- 职业：{occupation}
- 性格：{personality}
- 动机：{motivation}
- 口头禅：{phrase_text}
- 关联实体：{related_entity}
- 说话风格：{communication_style}

【立场】
1.0~3.0=强烈批评，4.0~6.0=中立，7.0~10.0=强烈支持

输出 JSON：
{{"comment":"...","new_stance":1.0~10.0,"reasoning":"..."}}
"""

    followed_text = "\n".join(f"- **{name}**：{comment}" for _, name, comment in followed) or "（暂无）"
    history_text = "\n".join(f"- {item}" for item in history[-3:]) if history else "（暂无）"

    user_prompt = f"""事件：{event_summary}
实体 {event_entity_name} 发言：{event_entity_post}
你关注的人最近说：{followed_text}
你之前说：{history_text}
请发表看法。
"""

    return system_prompt, user_prompt

