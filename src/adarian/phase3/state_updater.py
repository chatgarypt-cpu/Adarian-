"""Phase 3 静默 agent 漂移更新。"""

from __future__ import annotations

from typing import List, Tuple

from adarian.schemas import SilentAgentUpdate


def update_silent_agent(
    agent_id: int,
    previous_stance: float,
    susceptibility: float,
    followed_comments: List[Tuple[int, str]],
) -> SilentAgentUpdate:
    """基于 exposure drift 更新本轮未发言的 agent。"""
    drift = 0.0
    if followed_comments:
        exposure_factor = min(len(followed_comments), 3) / 3
        drift = round(0.12 * susceptibility * exposure_factor, 2)

    current_stance = round(max(1.0, min(10.0, previous_stance + drift)), 2)

    return SilentAgentUpdate(
        agent_id=agent_id,
        previous_stance=previous_stance,
        current_stance=current_stance,
        stance_delta=round(current_stance - previous_stance, 2),
        saw_posts_from=[source_id for source_id, _ in followed_comments],
        change_reason="silent_exposure_drift" if drift else "silent_no_change",
        comment="（未发言）",
        reasoning="本轮未进入发言队列",
        activity_state="silent",
    )

