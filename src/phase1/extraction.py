"""
Phase 1: 实体提取与分类模块（Analyzer/Generator/Validator 协作架构）
---
通过 Analyzer/Generator/Validator 三阶段协作，实现实体分类（事件实体 vs 意见传播实体），
并通过迭代校验确保输出质量。

架构流程：
1. Analyzer：分析种子材料 → event_scale + event_controversy
2. Generator：提取事件实体 + 生成意见传播者
3. Validator：格式校验（失败则 Generator 重试）

为什么需要这个模块（Why）：
- v1.1.4 版本区分两种实体类型：事件实体（直接参与）和意见传播实体（评论事件）
- 事件实体作为第一批发言者，参与社交网络的核心传播
- 意见传播实体基于规模/争议性生成，必须关注事件实体才能发言

新增于：v1.1.4
修改于：v1.1.10（LLM1/2/3 → Analyzer/Generator/Validator）
"""

# v1.2.5.1 源码事实：Phase 1 package entrypoint is src.phase1.
# 后续如进入 R1 Parser / Compiler / Validator Skeleton，必须以 v1.2.3 contract 为准。

import json
import ast
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console

import config
from src.llm_client import get_llm_client
from src.schemas import EntityExtractionOutput, Entity, OpinionSpreader, Relation

console = Console()


def _normalize_unescaped_quotes_inside_string_values(candidate: str) -> str:
    """LLM JSON 容错层：处理字符串 value 内部未转义引号。

    背景（Why）：
    LLM 可能返回 JSON 字符串 value 内部包含未转义英文双引号，如：
    {"event_summary": "深圳公交站引发"裸检"争议"}

    这不是 Unicode/UTF-8 冲突，而是 JSON 语法问题：
    - 外层 JSON 字符串用英文双引号包裹
    - value 内部又出现未转义英文双引号
    - json.loads 会把内部引号误判为字符串结束边界

    处理方式（状态机扫描）：
    - 使用字符级状态机遍历 JSON 文本
    - 区分 key 字符串（冒号前）和 value 字符串（冒号后）
    - 只处理 value 字符串内部的未转义引号
    - 不改变 JSON key 与结构边界
    - 使用启发式判断：value 内部引号后若非 , }] 则替换为单引号

    Args:
        candidate: 待解析的 JSON 字符串

    Returns:
        处理后的 JSON 字符串，value 内部未转义引号已替换为单引号

    新增于：v1.2.0（test7_1 白盒测试收口修复）
    """
    result = []
    i = 0
    n = len(candidate)

    # 状态机变量
    in_string = False          # 当前是否在 JSON 字符串内
    escape = False             # 上一个字符是否是反斜杠
    after_colon = False        # 当前是否在冒号后的 value 区域

    while i < n:
        ch = candidate[i]

        # 处理转义字符
        if escape:
            result.append(ch)
            escape = False
            i += 1
            continue

        if ch == '\\':
            result.append(ch)
            escape = True
            i += 1
            continue

        # 处理双引号（字符串边界或内部引号）
        if ch == '"':
            if not in_string:
                # 进入字符串
                in_string = True
                string_start_pos = i
                result.append(ch)
                # 检查是否在冒号后的 value 区域
                # 回溯找最近的冒号
                j = i - 1
                while j >= 0 and candidate[j] in ' \t\n\r':
                    j -= 1
                if j >= 0 and candidate[j] == ':':
                    after_colon = True
                else:
                    after_colon = False
            else:
                # 在字符串内遇到双引号
                # 判断这是字符串结束还是内部引号
                # 启发式：向后查看下一个有效字符
                j = i + 1
                while j < n and candidate[j] in ' \t\n\r':
                    j += 1

                if j < n and candidate[j] in ',}]':
                    # 这是 value 字符串结束边界
                    in_string = False
                    after_colon = False
                    result.append(ch)
                elif after_colon:
                    # 这是 value 内部未转义引号，替换为单引号
                    result.append("'")
                else:
                    # 这是 key 字符串结束（不应该有内部引号）
                    # 保守处理：保留原字符
                    in_string = False
                    result.append(ch)
            i += 1
            continue

        # 其他字符
        if ch == ':':
            result.append(ch)
            # 冒号后的空白跳过后，下一个字符串是 value
            # 但状态机会在下一个 " 进入时设置 after_colon
        elif ch == ',':
            result.append(ch)
            after_colon = False  # 新 key-value 开始
        elif ch in '{}[]':
            result.append(ch)
            if ch in '{}':
                after_colon = False  # 新对象/数组开始
        else:
            result.append(ch)

        i += 1

    return ''.join(result)


def _normalize_inner_cjk_quotes(candidate: str) -> str:
    """LLM JSON 兼容层：处理字符串值内部的中文弯引号。

    背景（Why）：
    LLM 可能返回包含中文弯引号的 JSON 字符串值，如：
    {"event_summary": "深圳公交站引发"裸检"争议"}

    中文弯引号 " (U+201C) 和 " (U+201D) 在 JSON 字符串值内部是合法字符，
    json.loads 可以正确解析。但如果 JSON 因其他原因失败后，
    fallback 到 ast.literal_eval 时，Python 解析器可能会误判。

    处理方式：
    - 将中文双引号 ""（U+201C/U+201D）替换为普通单引号 '（U+0027）
    - 将中文单引号 ''（U+2018/U+2019）替换为普通单引号 '（U+0027）
    - 不改变 JSON key 和结构边界（使用英文双引号 U+0022）

    Args:
        candidate: 待解析的 JSON 字符串

    Returns:
        处理后的 JSON 字符串，中文弯引号已替换为单引号

    新增于：v1.2.0（test7_1 白盒测试收口修复）
    """
    # 中文双引号：""（U+201C/U+201D）
    LEFT_CJK_DOUBLE_QUOTE = "“"  # "
    RIGHT_CJK_DOUBLE_QUOTE = "”"  # "
    LEFT_CJK_SINGLE_QUOTE = "‘"  # '
    RIGHT_CJK_SINGLE_QUOTE = "’"  # '
    ORDINARY_SINGLE_QUOTE = "'"  # U+0027

    result = candidate.replace(LEFT_CJK_DOUBLE_QUOTE, ORDINARY_SINGLE_QUOTE)
    result = result.replace(RIGHT_CJK_DOUBLE_QUOTE, ORDINARY_SINGLE_QUOTE)
    result = result.replace(LEFT_CJK_SINGLE_QUOTE, ORDINARY_SINGLE_QUOTE)
    result = result.replace(RIGHT_CJK_SINGLE_QUOTE, ORDINARY_SINGLE_QUOTE)
    return result


def _parse_json_candidate(candidate: str) -> Any:
    # 优先路径：直接 json.loads（合法 JSON 不允许被预处理污染）
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # normalization 层：处理常见 LLM 输出问题（保留原始行为）
    normalized = candidate.replace("{{", "{").replace("}}", "}")
    normalized = re.sub(r",(\s*[}\]])", r"\1", normalized)
    normalized = re.sub(r"\bNone\b", "null", normalized)
    normalized = re.sub(r"\bTrue\b", "true", normalized)
    normalized = re.sub(r"\bFalse\b", "false", normalized)

    # 第二次 json.loads 尝试（保留原始行为）
    try:
        return json.loads(normalized)
    except json.JSONDecodeError:
        pass

    # v1.2.0 新增：value 内部未转义引号容错层（状态机扫描）
    # 仅在 json.loads 失败后调用，不影响主路径
    normalized_fixed = _normalize_unescaped_quotes_inside_string_values(normalized)
    try:
        return json.loads(normalized_fixed)
    except json.JSONDecodeError:
        pass

    # v1.2.0 新增：中文弯引号兼容层
    normalized_cjk = _normalize_inner_cjk_quotes(normalized_fixed)
    try:
        return json.loads(normalized_cjk)
    except json.JSONDecodeError:
        pass

    # 末级 fallback：ast.literal_eval（保留原始行为，不强化为主路径）
    python_literal = re.sub(r"\btrue\b", "True", normalized_cjk)
    python_literal = re.sub(r"\bfalse\b", "False", python_literal)
    python_literal = re.sub(r"\bnull\b", "None", python_literal)
    return ast.literal_eval(python_literal)


def _parse_llm_json_payload(result: Any) -> Any:
    """尽量从 LLM 返回中提取顶层 JSON。"""
    if not isinstance(result, str):
        return result

    content = result.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return _parse_json_candidate(content)
    except (json.JSONDecodeError, ValueError, SyntaxError):
        pass

    object_start = content.find("{")
    object_end = content.rfind("}")
    if object_start != -1 and object_end != -1 and object_end > object_start:
        return _parse_json_candidate(content[object_start:object_end + 1])

    list_start = content.find("[")
    list_end = content.rfind("]")
    if list_start != -1 and list_end != -1 and list_end > list_start:
        return _parse_json_candidate(content[list_start:list_end + 1])

    raise json.JSONDecodeError("No JSON object found", content, 0)


def _coerce_top_level_object(payload: Any, source: str) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return payload

    if isinstance(payload, list):
        if len(payload) == 1 and isinstance(payload[0], dict):
            return payload[0]
        for item in payload:
            if isinstance(item, dict) and (
                "event_entities" in item or "opinion_spreaders" in item or "relations" in item or "pass" in item
            ):
                return item

    raise ValueError(f"{source} 返回顶层必须是 JSON object，当前为 {type(payload).__name__}")

from .prompts import (
    ANALYZER_SYSTEM_PROMPT,
    ANALYZER_USER_PROMPT,
    GENERATOR_SYSTEM_PROMPT,
    GENERATOR_USER_PROMPT,
    SPREADER_SYSTEM_PROMPT,
    SPREADER_USER_PROMPT,
)

# =============================================================================
# Analyzer: 设置参数
# =============================================================================

def analyzer_set_parameters(seed_text: str) -> Dict[str, Any]:
    """
    Analyzer: 分析种子材料，设置 event_scale 和 event_controversy

    Args:
        seed_text: 种子文本内容

    Returns:
        包含 event_scale、event_controversy、event_summary、event_type 的字典
    """
    llm = get_llm_client()

    user_prompt = ANALYZER_USER_PROMPT.format(seed_text=seed_text)

    console.print("[bold cyan]Analyzer:[/bold cyan] 正在分析事件参数...")

    result = llm.generate(
        system=ANALYZER_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,  # Analyzer 返回自由 JSON
    )

    try:
        params = _coerce_top_level_object(_parse_llm_json_payload(result), "Analyzer")
    except (json.JSONDecodeError, ValueError) as e:
        console.print(f"  [yellow]⚠[/yellow] Analyzer 返回格式错误: {e}")
        raise

    console.print(f"  [green]✓[/green] 事件规模: {params.get('event_scale', 'N/A')}")
    console.print(f"  [green]✓[/green] 事件争议性: {params.get('event_controversy', 'N/A')}")

    return params


# =============================================================================
# Generator: 生成实体
# =============================================================================

def generator_create_event_entities(
    seed_text: str,
    event_scale: float,
    event_controversy: float,
    event_type: str,
    event_summary: str,
    error_feedback: str = ""
) -> Dict[str, Any]:
    """
    Generator: 提取事件实体 + 规划传播者框架

    只负责：
    - 提取 event_entities
    - 规划 opinion_spreaders 框架（确定数量和分布，不含完整人设）
    - 提取 relations

    Args:
        seed_text: 种子文本内容
        event_scale: 事件规模
        event_controversy: 事件争议性
        event_type: 事件类型
        event_summary: 事件摘要
        error_feedback: 上一轮的错误反馈（用于重试）

    Returns:
        包含 event_entities, spreader_plan（stubs）, relations 的字典
    """
    from src.llm_client import LLMClient
    llm = LLMClient(temperature=0.7, task_type="phase1_extraction")

    user_prompt = GENERATOR_USER_PROMPT.format(
        seed_text=seed_text,
        event_scale=event_scale,
        event_controversy=event_controversy,
        event_type=event_type,
        event_summary=event_summary,
        error_feedback=error_feedback,
    )

    console.print("[bold cyan]Generator:[/bold cyan] 正在提取事件实体与规划传播者框架...")

    result = llm.generate(
        system=GENERATOR_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,
    )

    try:
        entities_data = _coerce_top_level_object(_parse_llm_json_payload(result), "Generator")
    except (json.JSONDecodeError, ValueError, SyntaxError, TypeError) as e:
        raise ValueError(f"Generator 返回内容无法解析为 JSON: {e}\n原始内容: {result[:200] if result else '空'}")

    event_count = len(entities_data.get("event_entities", []))
    spreader_count = len(entities_data.get("opinion_spreaders", []))
    console.print(f"  [green]✓[/green] 事件实体: {event_count}, 规划传播者: {spreader_count}")

    # 后处理
    entities_data = _post_process_entities(entities_data, seed_text)
    return entities_data


def generator_create_spreader(
    group_name: str,
    related_event_entity: str,
    description: str,
    I: float,
    P: int,
    estimated_percentage: int,
    idx: int,
    total_N: int,
    event_summary: str,
    event_type: str,
    event_entities_text: str,
) -> Dict[str, Any]:
    """
    单个传播者完整人设生成（可并发调用）。

    Args:
        每个参数对应一个传播者的属性

    Returns:
        Dict with full persona fields: susceptibility, communication_style,
        persona_name, age_range, occupation, personality, motivation, typical_phrases
    """
    from src.llm_client import LLMClient

    camp = "支持" if P == +1 else "反对"
    camp_detail = "维护品牌/支持立场" if P == +1 else "批评/表达不满"

    llm = LLMClient(temperature=0.7, task_type="phase1_extraction")
    system_prompt = SPREADER_SYSTEM_PROMPT.format(
        group_name=group_name,
        camp=camp,
        camp_detail=camp_detail,
        related_event_entity=related_event_entity,
        estimated_percentage=estimated_percentage,
        I=I,
        P=P,
        description=description,
        event_summary=event_summary,
        event_type=event_type,
        event_entities_text=event_entities_text,
        total_N=total_N,
        idx=idx + 1,
    )
    user_prompt = SPREADER_USER_PROMPT.format(
        group_name=group_name,
        related_event_entity=related_event_entity,
        total_N=total_N,
        idx=idx + 1,
        camp=camp,
        camp_detail=camp_detail,
        I=I,
    )

    console.print(f"  [cyan]Spreader {idx+1}/{total_N}:[/cyan] {group_name}...")
    result = llm.generate(
        system=system_prompt,
        user=user_prompt,
        response_model=None,
    )

    try:
        detail = _coerce_top_level_object(_parse_llm_json_payload(result), f"Spreader {group_name}")
    except (json.JSONDecodeError, ValueError, SyntaxError, TypeError) as e:
        raise ValueError(f"Spreader '{group_name}' 人设生成失败: {e}\n原始内容: {result[:200] if result else '空'}")

    # Merge stub + detail into full OpinionSpreader
    spreader = {
        "group_name": group_name,
        "related_event_entity": related_event_entity,
        "description": description,
        "I": I,
        "P": P,
        "estimated_percentage": estimated_percentage,
        "entity_category": "opinion_spreader",
        "susceptibility": detail.get("susceptibility"),
        "communication_style": detail.get("communication_style"),
        "persona_name": detail.get("persona_name"),
        "age_range": detail.get("age_range"),
        "occupation": detail.get("occupation"),
        "personality": detail.get("personality"),
        "motivation": detail.get("motivation"),
        "typical_phrases": detail.get("typical_phrases"),
    }
    console.print(f"    [green]✓[/green] 人设完成: {spreader.get('persona_name', '?')} ({spreader.get('occupation', '?')})")
    return spreader


def generator_create_spreaders_concurrent(
    spreaders_plan: List[Dict[str, Any]],
    event_summary: str,
    event_type: str,
    event_entities: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    并发生成所有传播者的完整人设（带二分并发降级）。

    策略：
    1. 以 config.PHASE1_MAX_CONCURRENT_SPREADERS 为上限全量并发
    2. 若单个失败 → LLMClient 内部重试兜底
    3. 若批量失败（模型限流）→ 并发数砍半重新提交，直到 1

    Args:
        spreaders_plan: Generator 规划出的传播者框架列表
        event_summary: 事件摘要
        event_type: 事件类型
        event_entities: 事件实体列表

    Returns:
        完整 OpinionSpreader dict 列表
    """
    import config
    event_entities_text = "\n".join(
        f"- {e.get('name', '?')}（{e.get('type', '?')}）: {e.get('role', '?')}"
        for e in event_entities
    )
    total_N = len(spreaders_plan)

    if total_N == 0:
        return []

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _submit_batch(pending_indices: List[int], max_workers: int) -> List[Optional[Dict[str, Any]]]:
        """提交一批传播者生成任务，返回结果列表。"""
        batch_results: List[Optional[Dict[str, Any]]] = [None] * total_N
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {}
            for idx in pending_indices:
                stub = spreaders_plan[idx]
                future = pool.submit(
                    generator_create_spreader,
                    group_name=stub.get("group_name", f"群体{idx}"),
                    related_event_entity=stub.get("related_event_entity", ""),
                    description=stub.get("description", ""),
                    I=stub.get("I", 5.0),
                    P=stub.get("P", +1),
                    estimated_percentage=stub.get("estimated_percentage", 0),
                    idx=idx,
                    total_N=total_N,
                    event_summary=event_summary,
                    event_type=event_type,
                    event_entities_text=event_entities_text,
                )
                future_map[future] = idx

            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    batch_results[idx] = future.result()
                except Exception as e:
                    console.print(f"  [yellow]警告：[/yellow] 第 {idx+1} 个传播者生成失败: {e}")
                    batch_results[idx] = None  # mark for retry
        return batch_results

    def _make_fallback(idx: int) -> Dict[str, Any]:
        stub = spreaders_plan[idx]
        return {
            "group_name": stub.get("group_name", f"群体{idx}"),
            "related_event_entity": stub.get("related_event_entity", ""),
            "description": stub.get("description", ""),
            "I": stub.get("I", 5.0),
            "P": stub.get("P", +1),
            "estimated_percentage": stub.get("estimated_percentage", 0),
            "entity_category": "opinion_spreader",
            "susceptibility": 0.5,
            "communication_style": "常规表达",
            "persona_name": "用户",
            "age_range": "25-45",
            "occupation": "普通公众",
            "personality": "理性中立",
            "motivation": "表达观点",
            "typical_phrases": ["我觉得吧", "说实话"],
        }

    results: List[Optional[Dict[str, Any]]] = [None] * total_N
    pending = list(range(total_N))
    cap = config.PHASE1_MAX_CONCURRENT_SPREADERS
    max_workers = max(1, min(total_N, cap)) if cap > 0 else total_N

    while pending:
        batch = _submit_batch(pending, max_workers)
        still_failed = []

        for idx in pending:
            if batch[idx] is not None:
                results[idx] = batch[idx]
            else:
                still_failed.append(idx)

        if not still_failed:
            break

        if max_workers > 1:
            max_workers = max(1, max_workers // 2)
            console.print(f"  [yellow]二分降级: 并发数 {max_workers * 2} → {max_workers}，重试 {len(still_failed)} 个[/yellow]")
            pending = still_failed
        else:
            # 已经到 1 了，给 fallback
            console.print(f"  [yellow]单线程仍失败，使用 fallback 人设: {len(still_failed)} 个[/yellow]")
            for idx in still_failed:
                results[idx] = _make_fallback(idx)
            break

    return results


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

    return entities_data


# =============================================================================
# 主函数：带迭代校验的实体提取
# =============================================================================

MAX_RETRIES = 3

def extract_entities_with_validation(seed_text: str) -> EntityExtractionOutput:
    """
    Phase 1 Orchestrator: Analyzer → Entity Generator → Concurrent Spreader Generator → Validator

    Args:
        seed_text: 种子文本内容

    Returns:
        EntityExtractionOutput: 包含 event_entities, opinion_spreaders 等
    """
    params = analyzer_set_parameters(seed_text)
    last_validation: Optional[Dict[str, Any]] = None
    error_feedback = ""

    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            console.print(f"[yellow]重试第 {attempt + 1}/{MAX_RETRIES} 轮...[/yellow]")

        try:
            # Step 1: 提取事件实体 + 规划传播者框架
            entities_data = generator_create_event_entities(
                seed_text=seed_text,
                event_scale=params["event_scale"],
                event_controversy=params["event_controversy"],
                event_type=params["event_type"],
                event_summary=params["event_summary"],
                error_feedback=error_feedback,
            )
        except ValueError as e:
            last_validation = {
                "pass": False,
                "message": "Generator 输出解析失败",
                "errors": [str(e)],
            }
            error_feedback = (
                "上一轮输出未能解析为合法 JSON。"
                "请严格输出单个 JSON object，不要附带解释、不要使用双大括号模板。"
                f"\n- {e}"
            )
            continue

        # Step 2: 并发生成每个传播者的完整人设
        try:
            spreader_plan = entities_data.get("opinion_spreaders", [])
            event_entities = entities_data.get("event_entities", [])
            spreaders = generator_create_spreaders_concurrent(
                spreaders_plan=spreader_plan,
                event_summary=params["event_summary"],
                event_type=params["event_type"],
                event_entities=event_entities,
            )
            entities_data["opinion_spreaders"] = spreaders
        except ValueError as e:
            last_validation = {
                "pass": False,
                "message": "传播者人设生成失败",
                "errors": [str(e)],
            }
            error_feedback = (
                f"传播者人设生成失败: {e}"
            )
            continue

        # Step 3: 校验（确定性 Pydantic 校验，替代 LLM Validator）
        from pydantic import ValidationError
        merged_output = {
            "event_summary": params["event_summary"],
            "event_scale": params["event_scale"],
            "event_controversy": params["event_controversy"],
            "event_type": params["event_type"],
            "event_entities": entities_data.get("event_entities", []),
            "opinion_spreaders": entities_data.get("opinion_spreaders", []),
            "relations": entities_data.get("relations", []),
        }
        try:
            return EntityExtractionOutput(**merged_output)
        except ValidationError as e:
            errors_str = "; ".join(
                f"{err['loc']}: {err['msg']}" for err in e.errors()
            )
            console.print(f"  [yellow]⚠[/yellow] Pydantic 校验失败: {e.errors()[0].get('msg', str(e))}")
            last_validation = {
                "pass": False,
                "message": "Pydantic 校验失败",
                "errors": [errors_str],
            }
            error_feedback = errors_str
            continue

    raise ValueError(
        "Phase 1 校验失败，超过最大重试次数。"
        f" 最后一次校验结果: {last_validation}"
    )


# =============================================================================
# 兼容函数
# =============================================================================

def extract_entities(seed_text: str) -> EntityExtractionOutput:
    """
    兼容函数：直接调用 orchestrator 入口

    Args:
        seed_text: 种子文本内容

    Returns:
        EntityExtractionOutput
    """
    return extract_entities_with_validation(seed_text)


def extract_entities_from_file(seed_file: str) -> EntityExtractionOutput:
    """
    从种子文件提取实体

    Args:
        seed_file: 种子文件路径

    Returns:
        EntityExtractionOutput 对象
    """
    seed_text = Path(seed_file).read_text(encoding="utf-8")
    return extract_entities_with_validation(seed_text)


def save_entities_output(
    entities_output: EntityExtractionOutput,
    output_path: Optional[str] = None
) -> str:
    """
    保存实体提取结果到 JSON 文件

    Args:
        entities_output: 实体提取结果
        output_path: 输出路径

    Returns:
        保存的文件路径
    """
    if output_path is None:
        output_path = config.ENTITIES_OUTPUT_PATH
    else:
        output_path = Path(output_path)

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(entities_output.model_dump(), f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/green] 实体提取结果已保存至: {output_path}")

    return str(output_path)


# =============================================================================
# 主入口（可独立运行）
# =============================================================================

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 检查是否提供了种子文件路径
    if len(sys.argv) < 2:
        seed_file = Path(__file__).parent.parent / "seeds" / "example_event.txt"
        if not seed_file.exists():
            console.print("[bold red]错误：[/bold red] 未提供种子文件路径，且默认文件不存在")
            console.print(f"请将种子文本文件放入: seeds/")
            sys.exit(1)
    else:
        seed_file = Path(sys.argv[1])

    console.print(f"[bold]读取种子文本：[/bold] {seed_file}")

    # 提取实体
    entities_output = extract_entities_from_file(str(seed_file))

    # 保存结果
    output_path = save_entities_output(entities_output)

    # 打印摘要
    console.print("\n[bold]事件实体：[/bold]")
    for entity in entities_output.event_entities:
        console.print(f"  - {entity.name} ({entity.type}): {entity.role}")

    console.print(f"\n[bold]意见传播者：[/bold]")
    for spreader in entities_output.opinion_spreaders:
        console.print(f"  - {spreader.group_name} (关联: {spreader.related_event_entity})")
        console.print(f"    I={spreader.I}, P={spreader.P}, susceptibility={spreader.susceptibility}")

    console.print(f"\n[bold]关系：[/bold]")
    for relation in entities_output.relations:
        console.print(f"  - {relation.source} --[{relation.type}]--> {relation.target}")
