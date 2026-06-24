"""Phase 1 shared utilities — JSON parsing and normalization."""

import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

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
    # 中文全角逗号 → 英文逗号（minimax 等模型可能输出中文标点）
    normalized = normalized.replace("，", ",")

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
