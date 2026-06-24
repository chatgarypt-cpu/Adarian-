import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
_src = str(PROJECT_ROOT / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from adarian.analysis.inflection_detector import InflectionDetector
from adarian.schemas import (
    AgentEntry, GlobalMetrics, GraphEdge, GraphNode, NodeRole,
    Phase2Output, TickLog,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _entry(agent_id, previous, current, group_name="观望群体"):
    return AgentEntry(
        agent_id=agent_id, group_name=group_name, saw_posts_from=[],
        previous_stance=previous, current_stance=current,
        stance_delta=current - previous,
        susceptibility=0.5, change_reason="within_effective_delta",
        comment="测试评论内容。", reasoning="测试",
    )


def _tick(tick, polarization, entries=None):
    return TickLog(
        tick=tick,
        entries=entries if entries is not None else [_entry(1, 5.0, 5.0)],
        global_metrics=GlobalMetrics(
            mean_stance=5.0, std_stance=1.0,
            polarization_index=polarization,
        ),
    )


def _phase2():
    return Phase2Output(
        nodes=[
            GraphNode(
                id=1, group_name="观望群体", archetype_index=0,
                related_entity="某主体", role=NodeRole.PERIPHERY,
                stance_score=5.0, susceptibility=0.5,
                entity_category="opinion_spreader",
            ),
        ],
        edges=[GraphEdge(source=1, target=1)],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInflectionDetector:

    def setup_method(self):
        self.detector = InflectionDetector()

    # 1. Normal inflection — pol_delta > 0.1
    def test_detect_normal_inflection(self):
        """Two ticks with a polarization jump > threshold should yield one inflection."""
        phase2 = _phase2()
        tick_logs = [
            _tick(0, 0.10),
            _tick(1, 0.30, entries=[_entry(1, 5.0, 7.0)]),
        ]

        result = self.detector.detect(tick_logs, phase2)

        assert len(result) == 1
        point = result[0]
        assert point["tick"] == 1
        assert point["agent_id"] == 1
        assert point["group_name"] == "观望群体"
        assert point["pol_delta"] == pytest.approx(0.20)
        assert point["stance_delta"] == pytest.approx(2.0)
        assert "pivotal_comment" in point
        assert "impact_description" in point

    # 2. Empty tick logs
    def test_detect_empty_tick_logs(self):
        """An empty tick_logs list should return an empty result."""
        phase2 = _phase2()
        result = self.detector.detect([], phase2)
        assert result == []

    # 3. No significant change — pol_delta < threshold
    def test_detect_no_significant_change(self):
        """Ticks with polarization changes below threshold yield no inflections."""
        phase2 = _phase2()
        tick_logs = [
            _tick(0, 0.50),
            _tick(1, 0.55),   # delta = 0.05 < 0.1
            _tick(2, 0.58),   # delta = 0.03 < 0.1
        ]

        result = self.detector.detect(tick_logs, phase2)
        assert result == []

    # 4. group_name comes from Phase2Output node_map
    def test_detect_uses_phase2_for_group_name(self):
        """The group_name in the result should be sourced from Phase2Output nodes, not the entry."""
        phase2 = Phase2Output(
            nodes=[
                GraphNode(
                    id=1, group_name="核心支持者", archetype_index=0,
                    related_entity="某主体", role=NodeRole.CORE,
                    stance_score=8.0, susceptibility=0.3,
                    entity_category="opinion_spreader",
                ),
            ],
            edges=[GraphEdge(source=1, target=1)],
        )
        # Entry says "观望群体" but node_map says "核心支持者"
        tick_logs = [
            _tick(0, 0.10, entries=[_entry(1, 5.0, 5.0, group_name="观望群体")]),
            _tick(1, 0.30, entries=[_entry(1, 5.0, 7.0, group_name="观望群体")]),
        ]

        result = self.detector.detect(tick_logs, phase2)

        assert len(result) == 1
        assert result[0]["group_name"] == "核心支持者"

    # 5. max_points is respected
    def test_detect_max_points_limit(self):
        """When more inflection-worthy ticks exist than max_points, only max_points are returned."""
        phase2 = _phase2()

        # Build 7 ticks where each consecutive pair has pol_delta > 0.1
        # polarization_index is clamped to [0.0, 1.0]
        pol_values = [0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95]
        tick_logs = []
        for i, pol in enumerate(pol_values):
            tick_logs.append(
                _tick(i, pol, entries=[_entry(1, 5.0, 5.0 + i * 0.3)])
            )

        # All 6 transitions exceed 0.1 threshold
        result = self.detector.detect(tick_logs, phase2, max_points=3)
        assert len(result) == 3

        # Verify increasing tick order is preserved
        assert result[0]["tick"] < result[1]["tick"] < result[2]["tick"]

    # 6. Single tick returns empty
    def test_detect_single_tick_returns_empty(self):
        """A single tick (no prior tick to compare) should return empty."""
        phase2 = _phase2()
        tick_logs = [_tick(0, 0.50)]
        result = self.detector.detect(tick_logs, phase2)
        assert result == []

    # 7. Agent not in node_map gets fallback group_name
    def test_detect_unknown_agent_fallback(self):
        """When the max-delta agent is not in the node_map, group_name should be '未知'."""
        phase2 = Phase2Output(
            nodes=[],  # empty node map
            edges=[],
        )
        tick_logs = [
            _tick(0, 0.10, entries=[_entry(1, 5.0, 5.0)]),
            _tick(1, 0.30, entries=[_entry(1, 5.0, 7.0)]),
        ]

        result = self.detector.detect(tick_logs, phase2)

        assert len(result) == 1
        assert result[0]["group_name"] == "未知"
