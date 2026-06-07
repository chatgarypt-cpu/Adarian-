"""Phase 1 Compiler — post-processing and normalization (zero LLM)."""

from typing import Any, Dict

from .reporter import Phase1Reporter
from .utils import console


def _post_process_entities(
    entities_data: Dict[str, Any],
    seed_text: str
) -> Dict[str, Any]:
    """
    后处理：自动修正 Generator 生成的实体数据中的常见错误

    Args:
        entities_data: Generator 生成的原始数据
        seed_text: 种子文本（用于检查已故关键词）

    Returns:
        修正后的数据
    """
    import re

    # 0. 自动补充缺失的 entity_category 字段
    for entity in entities_data.get("event_entities", []):
        if "entity_category" not in entity:
            entity["entity_category"] = "event_entity"
            console.print(f"  [yellow]⚠[/yellow] 自动补充：{entity.get('name', '未知')} 的 entity_category")

    for spreader in entities_data.get("opinion_spreaders", []):
        if "entity_category" not in spreader:
            spreader["entity_category"] = "opinion_spreader"
            console.print(f"  [yellow]⚠[/yellow] 自动补充：{spreader.get('group_name', '未知')} 的 entity_category")

    # 1. 自动修正 can_speak（检查种子材料中是否有已故关键词）
    death_keywords = ["已故", "去世", "死亡", "离世", "身亡", "逝世", "轻生", "跳江", "跳楼", "自杀", "遇难"]
    seed_lower = seed_text.lower()

    for entity in entities_data.get("event_entities", []):
        entity_name = entity.get("name", "")
        entity_type = entity.get("type", "")
        # 检查实体名称或角色是否包含死亡关键词
        if any(kw in entity_name or kw in entity.get("role", "") for kw in death_keywords):
            if entity.get("can_speak", True):
                console.print(f"  [yellow]⚠[/yellow] 自动修正：{entity_name} 已故，can_speak 设为 false")
                entity["can_speak"] = False
        # 如果实体是个体且名字不在名称/角色中包含死亡关键词
        # 检查种子文本中该实体是否被描述为死亡主体（而非仅出现在死亡上下文中）
        elif entity_type == "individual" and entity.get("can_speak", True):
            # 检查种子文本中是否有"[实体]死亡/去世/..."的模式
            # 即：实体名称 + 死亡动词（0-10字间隔内），或者"已故的[实体]"
            name_escaped = re.escape(entity_name)
            # 模式1：实体名后紧跟死亡动词（0-10字间隔）
            pattern1 = f"{name_escaped}[.　]{{0,10}}(已故|去世|死亡|离世|身亡|逝世|轻生)"
            # 模式2：实体名前有死亡形容词修饰
            pattern2 = f"(已故|去世|死亡|离世|身亡|逝世|轻生)的{entity_name}"
            if re.search(pattern1, seed_text) or re.search(pattern2, seed_text):
                console.print(f"  [yellow]⚠[/yellow] 自动修正：{entity_name} 在种子材料中被描述为已故，can_speak 设为 false")
                entity["can_speak"] = False

    # 2. 自动修正 original_statement（如果 can_speak=false，original_statement 应为 null）
    for entity in entities_data.get("event_entities", []):
        if not entity.get("can_speak", True) and entity.get("original_statement"):
            # 如果实体不可发言，original_statement 应该为 null
            if entity["original_statement"] and len(entity["original_statement"]) > 0:
                console.print(f"  [yellow]⚠[/yellow] 自动修正：{entity.get('name')} 不可发言，original_statement 设为 null")
                entity["original_statement"] = None

    # 3. 归一化 opinion_spreaders 的 estimated_percentage 之和到 100
    spreaders = entities_data.get("opinion_spreaders", [])
    if spreaders:
        raw_sum = sum(s.get("estimated_percentage", 0) for s in spreaders)
        if raw_sum != 100 and raw_sum > 0:
            scale = 100.0 / raw_sum
            new_vals = [max(1, round(s.get("estimated_percentage", 0) * scale)) for s in spreaders]
            diff = 100 - sum(new_vals)
            if diff != 0:
                new_vals[0] += diff
            for s, v in zip(spreaders, new_vals):
                s["estimated_percentage"] = v
            new_sum = sum(s["estimated_percentage"] for s in spreaders)
            if new_sum != raw_sum:
                console.print(f"  [cyan] 归一化: estimated_percentage {raw_sum} -> {new_sum}")
                rep = Phase1Reporter.get_current()
                if rep:
                    rep.record_compiler_normalization("estimated_percentage", raw_sum, new_sum)

    return entities_data

