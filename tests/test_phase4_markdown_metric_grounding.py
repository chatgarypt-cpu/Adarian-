"""Targeted checks for Phase 4 Markdown metric grounding."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.phase4.report_agent import (
    _build_code_owned_agent_stance_matrix,
    _format_code_owned_inflection_points,
)
from src.schemas import AgentEntry, GlobalMetrics, TickLog


def _entry(agent_id: int, group_name: str, previous: float, current: float) -> AgentEntry:
    return AgentEntry(
        agent_id=agent_id,
        group_name=group_name,
        saw_posts_from=[],
        previous_stance=previous,
        current_stance=current,
        stance_delta=current - previous,
        susceptibility=0.5,
        change_reason="within_effective_delta",
        comment="test",
        reasoning="test",
    )


def _tick(tick: int, entries: list[AgentEntry]) -> TickLog:
    return TickLog(
        tick=tick,
        entries=entries,
        global_metrics=GlobalMetrics(
            mean_stance=5.0,
            std_stance=1.0,
            polarization_index=0.2,
        ),
    )


def test_code_owned_stance_matrix_uses_tick1_to_final_tick():
    tick_logs = [
        _tick(0, [_entry(0, "事件实体", 5.0, 5.0)]),
        _tick(1, [_entry(8, "跟风吐槽网友", 7.5, 7.0)]),
        _tick(5, [_entry(8, "跟风吐槽网友", 5.0, 4.5)]),
    ]

    matrix = _build_code_owned_agent_stance_matrix(tick_logs)

    assert matrix == [
        {
            "agent_id": 8,
            "group_name": "跟风吐槽网友",
            "start_tick": 1,
            "end_tick": 5,
            "initial_stance": 7.0,
            "final_stance": 4.5,
            "delta": -2.5,
        }
    ]


def test_empty_code_owned_inflection_block_forbids_markdown_claims():
    lines = _format_code_owned_inflection_points([])
    text = "\n".join(lines)

    assert "本轮模拟未发现显著拐点" in text
    assert "不得声称存在拐点" in text
