"""
repair_agent.py — LLM 定向修复层。

定位：Compiler（代码）和 Repair（代码）修不了的 Pydantic 校验错误，
       由 LLM 针对性地只修报错字段。最多重试 3 次。

在链路中的位置：
  Generator 输出 → Compiler(代码归一) → Pydantic 校验
    → 通过 ✓
    → 失败 ✗ → Repair(代码定向修) → 再校验
        → 通过 ✓
        → 失败 ✗ → Repair Agent(LLM定向修, 最多3次) → 再校验
            → 通过 ✓
            → 失败 ✗ → 全量 Generator 重试
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from src.llm_client import LLMClient
from src.schemas.common import EntityExtractionOutput


def _build_prompt(data: dict, errors: list[dict]) -> str:
    """构造定向修复 prompt。只展示报错字段，不展示全量数据。"""
    error_details = []
    for err in errors:
        loc = " -> ".join(str(p) for p in err.get("loc", []))
        msg = err.get("msg", "")
        error_details.append(f"  - {loc}: {msg}")

    # 抽取有问题的字段（按 error loc 的最小范围）
    relevant = {}
    for err in errors:
        loc = err.get("loc", [])
        if not loc:
            continue
        # 定位到 opinion_spreaders[N] 或 event_entities[N] 级别
        ptr = data
        valid = True
        for key in loc:
            if isinstance(ptr, dict) and key in ptr:
                ptr = ptr[key]
            elif isinstance(ptr, list) and isinstance(key, int) and 0 <= key < len(ptr):
                ptr = ptr[key]
            else:
                valid = False
                break
        if valid:
            relevant[repr(loc)] = ptr

    context_parts = ["以下是模拟数据中需要修复的部分：\n"]
    for loc_str, val in relevant.items():
        context_parts.append(f"字段路径: {loc_str}")
        context_parts.append(f"当前值: {json.dumps(val, ensure_ascii=False, indent=2)}")
        context_parts.append("")

    prompt = f"""你是一个 JSON 数据修复助手。你的任务是修复下方模拟数据中的格式错误。

## 校验错误
{chr(10).join(error_details)}

## 需要修复的数据
{chr(10).join(context_parts)}
## 要求
1. 只修报错的字段，不要改动其他字段
2. 严格遵循 JSON 语法（不要中文逗号、不要注释）
3. 保持字段值符合约束（typical_phrases 最多 3 条、estimated_percentage 在合理范围内等）
4. 只输出修复后的 JSON，不要任何解释
5. 如果无法修复，输出一个空 JSON 对象 {{}}

输出修复后的完整 JSON："""
    return prompt


def repair_with_agent(
    data: dict,
    validation_errors: list[dict],
    max_attempts: int = 3,
) -> Optional[dict]:
    """
    尝试用 LLM 定向修复 Pydantic 校验失败的数据。

    Args:
        data: 校验失败的数据 dict
        validation_errors: Pydantic ValidationError.errors() 列表
        max_attempts: 最大重试次数（默认 3）

    Returns:
        修复后的 dict（通过 Pydantic 校验），或 None（修复失败）
    """
    llm = LLMClient(
        temperature=0.3,
        task_type="phase1_extraction",
        max_tokens=4096,
    )
    current_data = data
    errors = validation_errors

    for attempt in range(1, max_attempts + 1):
        prompt = _build_prompt(current_data, errors)
        try:
            resp = llm.generate(
                system="你是一个 JSON 数据修复助手。严格按用户要求修复数据，只输出 JSON。",
                user=prompt,
            )
        except Exception as e:
            print(f"  [repair_agent] LLM 调用失败 (attempt {attempt}): {e}")
            continue

        # 提取 JSON
        content = resp.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            fixed = json.loads(content)
        except json.JSONDecodeError:
            print(f"  [repair_agent] JSON 解析失败 (attempt {attempt})")
            continue

        # 合并修复结果到原始数据（只覆盖 LLM 返回的字段）
        merged = _merge_fix(current_data, fixed)

        # Pydantic 校验
        try:
            validated = EntityExtractionOutput(**merged)
            print(f"  [repair_agent] ✓ 修复成功 (attempt {attempt})")
            return validated.model_dump()
        except Exception as e:
            # 提取新错误，下次重试用
            from pydantic import ValidationError
            if isinstance(e, ValidationError):
                errors = e.errors()
            else:
                errors = [{"loc": [], "msg": str(e)}]
            print(f"  [repair_agent] ✗ 修复后仍校验失败 (attempt {attempt}): {errors[0].get('msg', str(e))[:80]}")
            current_data = merged
            continue

    print(f"  [repair_agent] ✗ 修复失败（{max_attempts} 次均未通过）")
    return None


def _merge_fix(original: dict, fix: dict) -> dict:
    """将 LLM 返回的修复结果 merge 回原始数据。

    只覆盖 LLM 返回中存在的顶层字段（event_entities, opinion_spreaders 等），
    不改变 LLM 没提到的字段。
    """
    result = dict(original)
    for key in ("event_entities", "opinion_spreaders", "relations",
                 "event_summary", "event_scale", "event_controversy", "event_type"):
        if key in fix:
            result[key] = fix[key]
    return result
