"""Tests for src.phase3.stance_analyzer.StanceAnalyzer."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.stance_analyzer import StanceAnalyzer
from src.schemas import AgentEntry, GlobalMetrics, TickLog


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _entry(agent_id, previous, current, group_name="观望群体"):
    return AgentEntry(
        agent_id=agent_id,
        group_name=group_name,
        saw_posts_from=[],
        previous_stance=previous,
        current_stance=current,
        stance_delta=current - previous,
        susceptibility=0.5,
        change_reason="within_effective_delta",
        comment="测试。",
        reasoning="测试",
    )


def _tick(tick, entries):
    return TickLog(
        tick=tick,
        entries=entries,
        global_metrics=GlobalMetrics(
            mean_stance=5.0, std_stance=1.0, polarization_index=0.1
        ),
    )


# ---------------------------------------------------------------------------
# build_stance_matrix tests
# ---------------------------------------------------------------------------

class TestBuildStanceMatrix:
    def test_build_stance_matrix_normal(self):
        """3 ticks: start_log=tick_logs[1], end_log=tick_logs[2]."""
        tick0 = _tick(0, [
            _entry(1, 5.0, 5.5, group_name="支持群体"),
            _entry(2, 6.0, 5.8, group_name="反对群体"),
        ])
        tick1 = _tick(1, [
            _entry(1, 5.5, 5.5, group_name="支持群体"),
            _entry(2, 5.8, 5.8, group_name="反对群体"),
        ])
        tick2 = _tick(2, [
            _entry(1, 5.5, 6.0, group_name="支持群体"),
            _entry(2, 5.8, 4.5, group_name="反对群体"),
        ])

        analyzer = StanceAnalyzer()
        matrix = analyzer.build_agent_stance_matrix([tick0, tick1, tick2])

        assert len(matrix) == 2

        row1 = next(r for r in matrix if r["agent_id"] == 1)
        assert row1["group_name"] == "支持群体"
        assert row1["initial_stance"] == 5.5  # tick_logs[1] current_stance
        assert row1["final_stance"] == 6.0    # tick_logs[2] current_stance

        row2 = next(r for r in matrix if r["agent_id"] == 2)
        assert row2["group_name"] == "反对群体"
        assert row2["initial_stance"] == 5.8  # tick_logs[1] current_stance
        assert row2["final_stance"] == 4.5    # tick_logs[2] current_stance

    def test_build_stance_matrix_empty(self):
        """Empty tick_logs -> returns []"""
        analyzer = StanceAnalyzer()
        matrix = analyzer.build_agent_stance_matrix([])
        assert matrix == []

    def test_build_stance_matrix_single_tick(self):
        """Only 1 tick -> uses tick[0] as both start and end."""
        tick0 = _tick(0, [
            _entry(3, 4.0, 4.0, group_name="中立群体"),
            _entry(4, 7.0, 7.0, group_name="坚定群体"),
        ])

        analyzer = StanceAnalyzer()
        matrix = analyzer.build_agent_stance_matrix([tick0])

        assert len(matrix) == 2

        row3 = next(r for r in matrix if r["agent_id"] == 3)
        assert row3["initial_stance"] == 4.0
        assert row3["final_stance"] == 4.0

        row4 = next(r for r in matrix if r["agent_id"] == 4)
        assert row4["initial_stance"] == 7.0
        assert row4["final_stance"] == 7.0


# ---------------------------------------------------------------------------
# max_negative_shift tests
# ---------------------------------------------------------------------------

class TestMaxNegativeShift:
    def test_max_negative_shift_with_decline(self):
        """3 ticks: start=tick1, end=tick2 with decline -> returns positive float."""
        tick0 = _tick(0, [_entry(1, 8.0, 7.0)])
        tick1 = _tick(1, [_entry(1, 7.0, 7.0)])
        tick2 = _tick(2, [_entry(1, 7.0, 5.0)])

        analyzer = StanceAnalyzer()
        result = analyzer.max_negative_shift([tick0, tick1, tick2])

        assert isinstance(result, float)
        assert result > 0.0

    def test_max_negative_shift_no_decline(self):
        """Entries with initial <= final -> returns 0.0."""
        tick0 = _tick(0, [_entry(1, 5.0, 6.0)])
        tick1 = _tick(1, [_entry(1, 6.0, 7.0)])

        analyzer = StanceAnalyzer()
        result = analyzer.max_negative_shift([tick0, tick1])

        assert result == 0.0

    def test_max_negative_shift_insufficient_data(self):
        """Empty tick_logs -> returns None."""
        analyzer = StanceAnalyzer()
        result = analyzer.max_negative_shift([])
        assert result is None
