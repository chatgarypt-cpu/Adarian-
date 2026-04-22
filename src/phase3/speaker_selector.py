"""Phase 3 自适应发言调度。"""

from __future__ import annotations

import math
import random
from typing import Dict, List


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


def select_speakers(
    tick: int,
    spreader_nodes: list,
    activity_levels: Dict[int, float],
    exposure_levels: Dict[int, float],
    novelty_scores: Dict[int, float],
) -> dict:
    """选择本轮发言的 spreader。"""
    spreader_count = len(spreader_nodes)
    ratio = _target_ratio(spreader_count, tick)
    min_speakers = max(4, math.ceil(spreader_count * 0.5))
    num_speakers = min(spreader_count, max(min_speakers, math.ceil(spreader_count * ratio)))

    scored = [
        (node, 0.5 * activity_levels.get(node.id, 0) + 0.3 * exposure_levels.get(node.id, 0) + 0.2 * novelty_scores.get(node.id, 0))
        for node in spreader_nodes
    ]
    ranked = sorted(scored, key=lambda x: x[1], reverse=True)
    selected = [node for node, _ in ranked[:num_speakers]]
    random.shuffle(selected)

    return {
        "tick": tick,
        "spreader_count": spreader_count,
        "computed_num_speakers": num_speakers,
        "expected_selected_count": num_speakers,
        "actual_selected_count": len(selected),
        "selected_speakers": [n.id for n in selected],
        "is_full_selection": spreader_count > 0 and len(selected) == spreader_count,
        "full_selection_reason": "forced" if num_speakers >= spreader_count else "normal",
    }
