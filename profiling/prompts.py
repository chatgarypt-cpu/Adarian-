"""Shared prompts and prompt builders for v1.1.19 profiling."""

from __future__ import annotations

from src.phase1_entity_extraction import (
    GENERATOR_SYSTEM_PROMPT,
    GENERATOR_USER_PROMPT,
    VALIDATOR_SYSTEM_PROMPT,
    VALIDATOR_USER_PROMPT,
)


SIMPLE_PROMPT_SYSTEM = """你是一个严格遵守格式要求的助手。只输出 JSON，不要解释。"""

SIMPLE_PROMPT_USER = """请输出 JSON：
{
  "summary": "50字以内",
  "risk_level": "low/medium/high"
}

事件：
某品牌因客服回应不当引发争议，网友出现批评与辩护两种声音。
"""


def build_generator_prompts(case: dict, error_feedback: str) -> tuple[str, str]:
    """Build generator prompts for a fixed profiling case."""
    system = GENERATOR_SYSTEM_PROMPT.format(
        event_scale=case["event_scale"],
        event_controversy=case["event_controversy"],
        event_type=case["event_type"],
        event_summary=case["event_summary"],
    )
    user = GENERATOR_USER_PROMPT.format(
        seed_text=case["seed_text"],
        event_scale=case["event_scale"],
        event_controversy=case["event_controversy"],
        event_type=case["event_type"],
        event_summary=case["event_summary"],
        error_feedback=error_feedback,
    )
    return system, user


def build_validator_prompts(seed_text: str, json_content: dict) -> tuple[str, str]:
    """Build validator prompts for a profiling sample."""
    user = VALIDATOR_USER_PROMPT.format(
        seed_text=seed_text,
        json_content=__import__("json").dumps(json_content, ensure_ascii=False),
    )
    return VALIDATOR_SYSTEM_PROMPT, user

