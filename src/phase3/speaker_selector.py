"""Phase 3 自适应发言调度。"""

from __future__ import annotations

import math
import random
from typing import Dict, List

from src.schemas import GraphNode, SpeakerSelectionResult


def _target_ratio(spreader_count: int, tick: int) -> float:
    # v1.1.18.1: Tick 1 策略必须显式声明，不能依赖隐式默认
    if spreader_count <= 8:
        if tick == 1:
            return 0.75
        if tick == 2:
            return 0.85
        return 0.6

    if tick == 1:
        return 0.8
    if tick == 2:
        return 0.65
        return 0.5


def _classify_full_selection(
    tick: int,
    spreader_count: int,
    computed_num_speakers: int,
    selected_count: int,
) -> tuple[bool, str]:
    """分类当前 full selection 的语义。"""
    is_full_selection = spreader_count > 0 and selected_count == spreader_count
    if not is_full_selection:
        return False, "not_full_selection"

    explicit_full_selection = False
    if explicit_full_selection:
        return True, "explicit_full_selection"

    if computed_num_speakers >= spreader_count:
        return True, "constraint_forced_full_selection"

    return True, "unexpected_full_selection"


def select_speakers(
    tick: int,
    spreader_nodes: List[GraphNode],
    activity_levels: Dict[int, float],
    exposure_levels: Dict[int, float],
    novelty_scores: Dict[int, float],
) -> SpeakerSelectionResult:
    """根据自适应规则选择 speaker。"""
    spreader_count = len(spreader_nodes)
    ratio = _target_ratio(spreader_count, tick)
    min_speakers = max(4, math.ceil(spreader_count * 0.5))
    num_speakers = min(
        spreader_count,
        max(min_speakers, math.ceil(spreader_count * ratio)),
    )

    scored = []
    for node in spreader_nodes:
        score = (
            activity_levels.get(node.id, 0.0)
            + exposure_levels.get(node.id, 0.0)
            + novelty_scores.get(node.id, 0.0)
            + random.uniform(0.0, 0.15)
        )
        scored.append((node.id, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    selected = [agent_id for agent_id, _ in scored[:num_speakers]]
    silent = [node.id for node in spreader_nodes if node.id not in set(selected)]
    actual_selected_count = len(selected)
    is_full_selection, full_selection_reason = _classify_full_selection(
        tick=tick,
        spreader_count=spreader_count,
        computed_num_speakers=num_speakers,
        selected_count=actual_selected_count,
    )

    assert full_selection_reason != "unexpected_full_selection", (
        "Unexpected full selection detected. This may indicate scheduler fallback "
        "or selection logic error. Please check selection constraints and configuration."
    )
    if not is_full_selection:
        assert actual_selected_count == num_speakers, (
            "Speaker selection count mismatch on non-full-selection path: "
            f"expected_selected_count={num_speakers}, actual_selected_count={actual_selected_count}. "
            "This indicates the scored candidate list was shorter than computed_num_speakers "
            "or selection output was truncated unexpectedly."
        )

    return SpeakerSelectionResult(
        selected_speakers=selected,
        silent_agents=silent,
        ratio=ratio,
        spreader_count=spreader_count,
        computed_num_speakers=num_speakers,
        expected_selected_count=num_speakers,
        actual_selected_count=actual_selected_count,
        is_full_selection=is_full_selection,
        full_selection_reason=full_selection_reason,
        validation_basis="selected_speakers",
    )
