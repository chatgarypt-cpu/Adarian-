"""Phase 3 自适应发言调度。"""

from __future__ import annotations

import math
import random
from typing import Dict, List

from adarian.schemas import GraphNode, SpeakerSelectionResult


def _target_ratio(spreader_count: int, tick: int) -> float:
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
    spreader_count: int,
    computed_num_speakers: int,
    selected_count: int,
) -> tuple[bool, str]:
    is_full_selection = spreader_count > 0 and selected_count == spreader_count
    if not is_full_selection:
        return False, "not_full_selection"
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
    """选择本轮发言的 spreader。"""
    spreader_count = len(spreader_nodes)
    ratio = _target_ratio(spreader_count, tick)
    min_speakers = max(4, math.ceil(spreader_count * 0.5))
    num_speakers = min(spreader_count, max(min_speakers, math.ceil(spreader_count * ratio)))

    scored = []
    for node in spreader_nodes:
        score = (
            0.5 * activity_levels.get(node.id, 0.0)
            + 0.3 * exposure_levels.get(node.id, 0.0)
            + 0.2 * novelty_scores.get(node.id, 0.0)
            + random.uniform(0.0, 0.15)
        )
        scored.append((node.id, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    selector_scores = {agent_id: round(score, 4) for agent_id, score in scored}
    selector_ranks = {agent_id: rank for rank, (agent_id, _) in enumerate(scored, start=1)}
    selected = [agent_id for agent_id, _ in scored[:num_speakers]]
    silent = [node.id for node in spreader_nodes if node.id not in set(selected)]
    actual_selected_count = len(selected)
    is_full_selection, full_selection_reason = _classify_full_selection(
        spreader_count=spreader_count,
        computed_num_speakers=num_speakers,
        selected_count=actual_selected_count,
    )

    if not is_full_selection and actual_selected_count != num_speakers:
        raise AssertionError(
            "Speaker selection count mismatch on non-full-selection path: "
            f"expected_selected_count={num_speakers}, actual_selected_count={actual_selected_count}"
        )
    if full_selection_reason == "unexpected_full_selection":
        raise AssertionError("Unexpected full selection detected in speaker scheduler")

    return SpeakerSelectionResult(
        selected_speakers=selected,
        silent_agents=silent,
        selector_scores=selector_scores,
        selector_ranks=selector_ranks,
        ratio=ratio,
        spreader_count=spreader_count,
        computed_num_speakers=num_speakers,
        expected_selected_count=num_speakers,
        actual_selected_count=actual_selected_count,
        is_full_selection=is_full_selection,
        full_selection_reason=full_selection_reason,
        validation_basis="selected_speakers",
    )
