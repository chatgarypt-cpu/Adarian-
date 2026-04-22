"""Phase 3 上下文构建。"""

from __future__ import annotations

from typing import List, Tuple


def build_lightweight_context(
    card: dict,
    event_summary: str,
    event_entity_name: str,
    event_entity_post: str,
    followed: List[Tuple[int, str, str]],
    history: List[str],
) -> Tuple[str, str]:
    """构造 LLM prompt context。"""
    group_name = card.get("group_name", "")
    persona_name = card.get("persona_name", "")
    age_range = card.get("age_range", "25-34")
    occupation = card.get("occupation", "")
    personality = card.get("personality", "")
    motivation = card.get("motivation", "")
    tp = card.get("typical_phrases", [])
    if isinstance(tp, (list, tuple)):
        tp_str = ", ".join(tp)
    else:
        tp_str = str(tp)
    related_entity = card.get("related_entity", "")
    communication_style = card.get("communication_style", "")
    description = card.get("description", "")

    system_prompt = f"""你是一个真实的社交媒体用户。

【身份】
- 名字：{persona_name}
- 群体：{group_name}
- 年龄：{age_range}
- 职业：{occupation}
- 性格：{personality}
- 动机：{motivation}
- 口头禅：{tp_str}
- 关联实体：{related_entity}
- 说话风格：{communication_style}

【立场】
1.0~3.0=强烈批评，4.0~6.0=中立，7.0~10.0=强烈支持

输出JSON：{{"comment":"...","new_stance":1.0~10.0,"reasoning":"..."}}
"""

    followed_text = "\n".join(f"- **{name}**：{c}" for _, name, c in followed) or "（暂无）"
    history_text = "\n".join(f"- {h}" for h in history[-3:]) if history else "（暂无）"

    user_prompt = f"""事件：{event_summary}
实体{event_entity_name}发言：{event_entity_post}
关注的人最近说：{followed_text}
你之前说：{history_text}
请发表看法。
"""

    return system_prompt, user_prompt
