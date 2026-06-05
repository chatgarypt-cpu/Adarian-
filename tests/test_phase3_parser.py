"""Tests for SimulationDatasetParser — Phase 3 dataset output contract."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase3.parser import SimulationDatasetParser
from src.schemas import (
    AgentEntry,
    Entity,
    EntityExtractionOutput,
    GlobalMetrics,
    GraphEdge,
    GraphNode,
    NodeRole,
    OpinionSpreader,
    Phase2Output,
    Relation,
    TickLog,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _extraction():
    return EntityExtractionOutput(
        event_summary="测试事件",
        event_scale=0.3,
        event_controversy=0.3,
        event_type="公共事件",
        event_entities=[
            Entity(
                name="主体A",
                type="organization",
                role="涉事主体",
                can_speak=True,
            )
        ],
        opinion_spreaders=[
            OpinionSpreader(
                group_name="群体1",
                related_event_entity="主体A",
                description="描述",
                I=5.0,
                P=1,
                susceptibility=0.3,
                estimated_percentage=50,
                communication_style="克制",
                persona_name="张三",
                age_range="25-34",
                occupation="市民",
                personality="冷静",
                motivation="关注",
                typical_phrases=["继续观察", "先看说明"],
            ),
            OpinionSpreader(
                group_name="群体2",
                related_event_entity="主体A",
                description="描述",
                I=3.0,
                P=-1,
                susceptibility=0.5,
                estimated_percentage=50,
                communication_style="直接",
                persona_name="李四",
                age_range="35-45",
                occupation="消费者",
                personality="较真",
                motivation="质疑",
                typical_phrases=["需要公开", "回应要及时"],
            ),
        ],
        relations=[Relation(source="主体A", target="群体1", type="舆论关联")],
    )


def _phase2():
    return Phase2Output(
        nodes=[
            GraphNode(
                id=1,
                group_name="群体1",
                archetype_index=0,
                related_entity="主体A",
                role=NodeRole.PERIPHERY,
                stance_score=5.0,
                susceptibility=0.3,
                entity_category="opinion_spreader",
            )
        ],
        edges=[GraphEdge(source=1, target=1)],
    )


def _entry(agent_id, previous, current, group_name="群体1"):
    return AgentEntry(
        agent_id=agent_id,
        group_name=group_name,
        saw_posts_from=[],
        previous_stance=previous,
        current_stance=current,
        stance_delta=current - previous,
        susceptibility=0.3,
        change_reason="within_effective_delta",
        comment="测试评论。",
        reasoning="测试",
    )


def _tick(tick, entries=None):
    return TickLog(
        tick=tick,
        entries=entries or [_entry(1, 5.0, 5.0)],
        global_metrics=GlobalMetrics(
            mean_stance=5.0, std_stance=1.0, polarization_index=0.1
        ),
    )


def _x_t(ticks):
    """Compute x_t_sequence from tick_logs."""
    return [t.global_metrics.mean_stance for t in ticks]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_parse_returns_correct_structure():
    """parse() must return a dict with all top-level contract keys."""
    ticks = [_tick(0), _tick(1), _tick(2)]
    parser = SimulationDatasetParser()
    result = parser.parse(_extraction(), _phase2(), ticks, _x_t(ticks))

    assert isinstance(result, dict)

    expected_keys = {
        "_schema_version",
        "_generated_by",
        "run_info",
        "simulation_result",
        "source_artifact_refs",
        "known_limitations",
    }
    missing = expected_keys - result.keys()
    assert not missing, f"Missing top-level keys: {missing}"


def test_parse_simulation_result_fields():
    """simulation_result must contain all required sub-keys."""
    ticks = [_tick(0), _tick(1), _tick(2)]
    parser = SimulationDatasetParser()
    result = parser.parse(_extraction(), _phase2(), ticks, _x_t(ticks))
    sim = result["simulation_result"]

    expected_keys = {
        "x_t_sequence",
        "final_x",
        "final_polarization_index",
        "emotion_trajectory",
        "inflection_points",
        "risk_verdict",
        "risk_type_classification",
        "agent_stance_matrix",
    }
    missing = expected_keys - sim.keys()
    assert not missing, f"Missing simulation_result keys: {missing}"

    assert isinstance(sim["x_t_sequence"], list)
    assert len(sim["x_t_sequence"]) == 3
    assert sim["final_x"] == sim["x_t_sequence"][-1]


def test_parse_risk_verdict_structure():
    """risk_verdict must have level, label, basis_text, signals."""
    ticks = [_tick(0), _tick(1)]
    parser = SimulationDatasetParser()
    result = parser.parse(_extraction(), _phase2(), ticks, _x_t(ticks))
    verdict = result["simulation_result"]["risk_verdict"]

    assert isinstance(verdict, dict)
    for key in ("level", "label", "basis_text", "signals"):
        assert key in verdict, f"risk_verdict missing key: {key}"

    # signals is a dict (not list)
    assert isinstance(verdict["signals"], dict)


def test_save_dataset(tmp_path):
    """save_dataset() writes a valid JSON file."""
    ticks = [_tick(0), _tick(1)]
    parser = SimulationDatasetParser()
    dataset = parser.parse(_extraction(), _phase2(), ticks, _x_t(ticks))

    out_path = tmp_path / "dataset.json"
    parser.save_dataset(dataset, str(out_path))

    assert out_path.exists(), "save_dataset did not create the output file"

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "_schema_version" in data
    assert "simulation_result" in data


def test_parse_empty_tick_logs():
    """Parser must degrade gracefully when tick_logs is empty."""
    parser = SimulationDatasetParser()
    result = parser.parse(_extraction(), _phase2(), [], [])

    assert isinstance(result, dict)
    sim = result["simulation_result"]

    assert sim["x_t_sequence"] == []
    assert "final_x" in sim
    assert "risk_verdict" in sim
