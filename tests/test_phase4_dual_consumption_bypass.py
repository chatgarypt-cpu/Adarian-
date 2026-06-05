"""
Phase 4 dual-consumption bypass tests.

Verifies that the new Phase 3 code-owned path produces identical results to
the old Phase 4 path for every deterministic computation:
  - risk level assessment
  - inflection point detection
  - audience mode classification
  - risk type classification
  - full pipeline output
  - stance matrix max-negative-shift
"""

import statistics
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase3.parser import SimulationDatasetParser
from src.phase3.risk_analyzer import RiskAnalyzer
from src.phase3.inflection_detector import InflectionDetector
from src.phase3.stance_analyzer import StanceAnalyzer
from src.phase4.report_agent import (
    assess_risk as old_assess_risk,
    identify_inflection_points as old_identify_inflection_points,
    determine_audience_mode as old_determine_audience_mode,
    select_primary_risk_types as old_select_primary_risk_types,
    run_old_path,
    run_new_path,
)
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
from src.schemas.phase4 import RiskLevel, AudienceMode, RISK_LEVEL_LABELS


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _extraction(*, event_scale=0.3, event_controversy=0.3):
    return EntityExtractionOutput(
        event_summary="测试事件",
        event_scale=event_scale,
        event_controversy=event_controversy,
        event_type="公共事件",
        event_entities=[
            Entity(
                name="主体A",
                type="organization",
                role="涉事主体",
                can_speak=True,
                original_statement="声明内容。",
            ),
        ],
        opinion_spreaders=[
            OpinionSpreader(
                group_name="群体1",
                related_event_entity="主体A",
                description="描述",
                I=5.5,
                P=1,
                susceptibility=0.3,
                estimated_percentage=60,
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
                I=3.5,
                P=-1,
                susceptibility=0.5,
                estimated_percentage=40,
                communication_style="直接",
                persona_name="李四",
                age_range="35-45",
                occupation="消费者",
                personality="较真",
                motivation="质疑",
                typical_phrases=["需要公开", "回应要及时"],
            ),
        ],
        relations=[
            Relation(source="主体A", target="群体1", type="舆论关联"),
        ],
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
            ),
            GraphNode(
                id=2,
                group_name="群体2",
                archetype_index=0,
                related_entity="主体A",
                role=NodeRole.PERIPHERY,
                stance_score=3.0,
                susceptibility=0.5,
                entity_category="opinion_spreader",
            ),
        ],
        edges=[GraphEdge(source=1, target=2)],
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
        comment="测试评论内容。",
        reasoning="测试推理",
    )


def _tick(tick, entries):
    if not entries:
        mean_s = 5.0
        pol = 0.1
    else:
        stances = [e.current_stance for e in entries]
        mean_s = sum(stances) / len(stances)
        pol = statistics.stdev(stances) / mean_s if mean_s > 0 else 0.0
    return TickLog(
        tick=tick,
        entries=entries,
        global_metrics=GlobalMetrics(
            mean_stance=mean_s,
            std_stance=statistics.stdev(stances) if len(stances) > 1 else 0.0,
            polarization_index=pol,
        ),
    )


def _make_ticks():
    return [
        _tick(0, [
            _entry(1, 5.0, 5.0, "群体1"),
            _entry(2, 3.0, 3.0, "群体2"),
        ]),
        _tick(1, [
            _entry(1, 5.0, 4.8, "群体1"),
            _entry(2, 3.0, 2.5, "群体2"),
        ]),
        _tick(2, [
            _entry(1, 4.8, 4.5, "群体1"),
            _entry(2, 2.5, 2.0, "群体2"),
        ]),
    ]


# ---------------------------------------------------------------------------
# 1. Risk level bypass
# ---------------------------------------------------------------------------


def test_risk_level_bypass():
    """Old and new risk level assessment must be identical."""
    ext = _extraction()
    ticks = _make_ticks()
    x_t = [tick.global_metrics.mean_stance for tick in ticks]

    old_risk_level, old_assessment = old_assess_risk(
        x_t, ticks, extraction_output=ext,
    )
    new_risk_level, new_assessment = RiskAnalyzer().assess_risk(
        x_t, ticks, extraction_output=ext,
    )

    assert old_risk_level == new_risk_level, (
        f"Risk level mismatch: old={old_risk_level}, new={new_risk_level}"
    )
    assert old_risk_level.value in RISK_LEVEL_LABELS


# ---------------------------------------------------------------------------
# 2. Inflection count bypass
# ---------------------------------------------------------------------------


def test_inflection_count_bypass():
    """Old and new inflection point detection must agree on count and fields."""
    ext = _extraction()
    p2 = _phase2()
    ticks = _make_ticks()

    old_points = old_identify_inflection_points(ticks, p2)
    new_result = InflectionDetector().detect(ticks, p2)

    # Accept either a bare list or an object with a .points attribute
    new_points = new_result.points if hasattr(new_result, "points") else new_result

    assert len(old_points) == len(new_points), (
        f"Inflection count mismatch: old={len(old_points)}, new={len(new_points)}"
    )
    for old_p, new_p in zip(old_points, new_points):
        assert old_p.tick == new_p.tick
        assert old_p.agent_id == new_p.agent_id
        assert old_p.group_name == new_p.group_name
        assert old_p.pivotal_comment == new_p.pivotal_comment
        assert old_p.impact_description == new_p.impact_description


# ---------------------------------------------------------------------------
# 3. Audience mode bypass
# ---------------------------------------------------------------------------


def test_audience_mode_bypass():
    """Old and new audience mode classification must be identical."""
    ext = _extraction()

    old_mode = old_determine_audience_mode(ext)
    new_mode = RiskAnalyzer().determine_audience_mode(ext)

    assert old_mode == new_mode, (
        f"Audience mode mismatch: old={old_mode}, new={new_mode}"
    )


# ---------------------------------------------------------------------------
# 4. Risk type classification bypass
# ---------------------------------------------------------------------------


def test_risk_type_classification_bypass():
    """Old and new risk type classification must be identical."""
    ext = _extraction()
    ticks = _make_ticks()

    # Old path
    old_audience = old_determine_audience_mode(ext)
    old_types = old_select_primary_risk_types(old_audience, "", ticks)

    # New path
    new_audience = RiskAnalyzer().determine_audience_mode(ext)
    new_types = RiskAnalyzer().classify_risk_types(new_audience, "", ticks)

    assert old_types == new_types, (
        f"Risk type mismatch: old={old_types}, new={new_types}"
    )


# ---------------------------------------------------------------------------
# 5. Full pipeline bypass (CRITICAL)
# ---------------------------------------------------------------------------


def test_full_pipeline_bypass():
    """Full old-path vs new-path pipeline must produce identical outputs."""
    ext = _extraction()
    p2 = _phase2()
    ticks = _make_ticks()
    x_t = [tick.global_metrics.mean_stance for tick in ticks]

    # Build simulation dataset for new path
    dataset = SimulationDatasetParser().parse(ext, p2, ticks, x_t)

    old_output = run_old_path(ext, ticks, x_t, p2)
    new_output = run_new_path(dataset, ext, ticks, x_t)

    # --- risk level ---
    assert old_output.risk_level == new_output.risk_level, (
        f"Pipeline risk_level mismatch: old={old_output.risk_level}, "
        f"new={new_output.risk_level}"
    )
    assert old_output.risk_level_label == new_output.risk_level_label, (
        f"Pipeline risk_level_label mismatch: old={old_output.risk_level_label}, "
        f"new={new_output.risk_level_label}"
    )

    # --- risk types ---
    assert old_output.primary_risk_types == new_output.primary_risk_types, (
        f"Pipeline primary_risk_types mismatch: old={old_output.primary_risk_types}, "
        f"new={new_output.primary_risk_types}"
    )
    assert old_output.risk_type_labels == new_output.risk_type_labels, (
        f"Pipeline risk_type_labels mismatch: old={old_output.risk_type_labels}, "
        f"new={new_output.risk_type_labels}"
    )

    # --- inflection points ---
    assert len(old_output.inflection_points) == len(new_output.inflection_points), (
        f"Pipeline inflection count mismatch: "
        f"old={len(old_output.inflection_points)}, "
        f"new={len(new_output.inflection_points)}"
    )
    for old_p, new_p in zip(old_output.inflection_points, new_output.inflection_points):
        assert old_p.tick == new_p.tick
        assert old_p.agent_id == new_p.agent_id
        assert old_p.group_name == new_p.group_name
        assert old_p.pivotal_comment == new_p.pivotal_comment
        assert old_p.impact_description == new_p.impact_description

    # --- x_t_sequence (tolerance 1e-6) ---
    assert len(old_output.x_t_sequence) == len(new_output.x_t_sequence)
    for old_val, new_val in zip(old_output.x_t_sequence, new_output.x_t_sequence):
        assert abs(old_val - new_val) < 1e-6, (
            f"x_t_sequence value mismatch: old={old_val}, new={new_val}"
        )


# ---------------------------------------------------------------------------
# 6. Stance matrix max-negative-shift bypass
# ---------------------------------------------------------------------------


def test_stance_matrix_max_negative_shift_bypass():
    """Old and new max-negative-shift calculation must agree."""
    from src.phase4.report_agent import (
        _max_negative_shift_from_stance_matrix as old_max_shift,
    )

    ticks = _make_ticks()

    old_val = old_max_shift(ticks)
    new_val = StanceAnalyzer().max_negative_shift(ticks)

    assert old_val == new_val, (
        f"Max negative shift mismatch: old={old_val}, new={new_val}"
    )
