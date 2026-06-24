"""Phase 1 Analyzer — seed material analysis."""

import json
from typing import Any, Dict

from adarian.llm_client import get_llm_client

from .utils import (
    _coerce_top_level_object,
    _parse_llm_json_payload,
    console,
)
from .prompts import ANALYZER_SYSTEM_PROMPT, ANALYZER_USER_PROMPT


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