"""Phase 1 Generator — entity extraction + concurrent spreader generation."""

import json
import time
from typing import Any, Dict, List, Optional

from rich.console import Console

from .prompts import GENERATOR_SYSTEM_PROMPT, GENERATOR_USER_PROMPT
from .prompts import SPREADER_SYSTEM_PROMPT, SPREADER_USER_PROMPT
from .utils import _parse_llm_json_payload, _coerce_top_level_object, console


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
    t0 = time.perf_counter()
    result = llm.generate(
        system=system_prompt,
        user=user_prompt,
        response_model=None,
    )
    elapsed = time.perf_counter() - t0

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
    console.print(f"    [green]✓[/green] {spreader.get('persona_name', '?')} ({spreader.get('occupation', '?')}) [{elapsed:.1f}s]")
    from src.display import get_bar
    _bar = get_bar()
    if _bar and _bar.concurrency:
        _bar.concurrency.done(group_name, elapsed)
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

    console.print(f"  [cyan]→ 并 {max_workers}[/cyan] {total_N} 个传播者人设并发生成...")

    # 注册到状态栏
    from src.display import get_bar
    _bar = get_bar()
    if _bar:
        ct = _bar.set_concurrency()
        for stub in spreaders_plan:
            ct.add(stub.get("group_name", "?"))
    else:
        ct = None

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

    console.print(f"  [green]← 并[/green] {total_N}/{total_N} 全部返回")
    return results