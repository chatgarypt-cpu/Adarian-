"""Targeted tests for Phase 3 RiskAnalyzer — decoupled risk assessment layer."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_src = str(PROJECT_ROOT / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from adarian.analysis.risk_analyzer import RiskAnalyzer
from adarian.schemas import (
    AgentEntry,
    Entity,
    EntityExtractionOutput,
    GlobalMetrics,
    OpinionSpreader,
    Relation,
    TickLog,
)
from adarian.schemas.risk import RiskLevel


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _extraction(
    summary: str = "普通消费争议事件",
    entity_name: str = "某主体",
    *,
    event_scale: float = 0.2,
    event_controversy: float = 0.2,
) -> EntityExtractionOutput:
    return EntityExtractionOutput(
        event_summary=summary,
        event_scale=event_scale,
        event_controversy=event_controversy,
        event_type="公共事件",
        event_entities=[
            Entity(
                name=entity_name,
                type="organization",
                role="涉事主体",
                can_speak=True,
                original_statement="将继续说明情况。",
            )
        ],
        opinion_spreaders=[
            OpinionSpreader(
                group_name="观望群体",
                related_event_entity=entity_name,
                description="等待进一步事实",
                I=5.5,
                P=1,
                susceptibility=0.3,
                estimated_percentage=60,
                communication_style="克制表达",
                persona_name="小林",
                age_range="25-34",
                occupation="市民",
                personality="冷静",
                motivation="关注事实",
                typical_phrases=["继续观察", "先看说明"],
            ),
            OpinionSpreader(
                group_name="质疑群体",
                related_event_entity=entity_name,
                description="质疑处置透明度",
                I=3.5,
                P=-1,
                susceptibility=0.5,
                estimated_percentage=40,
                communication_style="直接追问",
                persona_name="老周",
                age_range="35-45",
                occupation="消费者",
                personality="较真",
                motivation="要求透明",
                typical_phrases=["需要公开", "回应要及时"],
            ),
        ],
        relations=[Relation(source=entity_name, target="观望群体", type="舆论关联")],
    )


def _entry(
    agent_id: int, previous: float, current: float, group_name: str = "观望群体",
) -> AgentEntry:
    return AgentEntry(
        agent_id=agent_id,
        group_name=group_name,
        saw_posts_from=[],
        previous_stance=previous,
        current_stance=current,
        stance_delta=current - previous,
        susceptibility=0.5,
        change_reason="within_effective_delta",
        comment="继续观察事实说明。",
        reasoning="测试样本",
    )


def _tick(
    tick: int, polarization: float = 0.1, entries: list[AgentEntry] | None = None,
) -> TickLog:
    return TickLog(
        tick=tick,
        entries=entries if entries is not None else [_entry(1, 5.0, 5.0)],
        global_metrics=GlobalMetrics(
            mean_stance=5.0,
            std_stance=1.0,
            polarization_index=polarization,
        ),
    )


# ---------------------------------------------------------------------------
# Tests — assess_risk
# ---------------------------------------------------------------------------


def test_assess_risk_normal_input():
    """Standard two-tick input returns a valid (RiskLevel, str) tuple."""
    analyzer = RiskAnalyzer()
    ticks = [_tick(0, 0.1), _tick(1, 0.1)]

    risk_level, assessment = analyzer.assess_risk([5.0, 5.0], ticks)

    assert isinstance(risk_level, RiskLevel)
    assert isinstance(assessment, str)
    assert len(assessment) > 0


def test_assess_risk_empty_input():
    """Empty x_t_sequence returns LOW with the data-insufficient message."""
    analyzer = RiskAnalyzer()

    risk_level, assessment = analyzer.assess_risk([], [])

    assert risk_level == RiskLevel.LOW
    assert assessment == "数据不足，无法评估"


def test_assess_risk_boundary_polarization():
    """Polarization exactly at 0.30 triggers MEDIUM risk."""
    analyzer = RiskAnalyzer()
    ticks = [_tick(0, 0.1), _tick(1, 0.30)]

    risk_level, _ = analyzer.assess_risk([5.2, 5.2], ticks)

    assert risk_level == RiskLevel.MEDIUM


# ---------------------------------------------------------------------------
# Tests — determine_audience_mode
# ---------------------------------------------------------------------------


def test_determine_audience_mode_law_enforcement():
    """Extraction with law-enforcement keyword returns law_enforcement_facing."""
    analyzer = RiskAnalyzer()
    extraction = _extraction("公安处置程序争议", "公安")

    mode = analyzer.determine_audience_mode(extraction)

    assert mode == "law_enforcement_facing"


def test_determine_audience_mode_generic():
    """Extraction without special keywords returns generic_government."""
    analyzer = RiskAnalyzer()
    extraction = _extraction()

    mode = analyzer.determine_audience_mode(extraction)

    assert mode == "generic_government"


# ---------------------------------------------------------------------------
# Tests — _compute_sensitive_context_hit
# ---------------------------------------------------------------------------


def test_sensitive_context_hit_non_generic_audience():
    """Non-generic audience mode (law-enforcement) triggers sensitive context."""
    analyzer = RiskAnalyzer()
    extraction = _extraction("公安处置程序争议", "公安")

    hit = analyzer._compute_sensitive_context_hit(extraction, [])

    assert hit is True


def test_sensitive_context_hit_generic_no_hit():
    """Generic audience + low polarization → no hit."""
    analyzer = RiskAnalyzer()
    extraction = _extraction()
    ticks = [_tick(0, 0.1), _tick(1, 0.3)]

    hit = analyzer._compute_sensitive_context_hit(extraction, ticks)

    assert hit is False


def test_sensitive_context_hit_high_polarization():
    """Generic audience but pol >= 0.50 → hit."""
    analyzer = RiskAnalyzer()
    extraction = _extraction()
    ticks = [_tick(0, 0.1), _tick(1, 0.5)]

    hit = analyzer._compute_sensitive_context_hit(extraction, ticks)

    assert hit is True


# ---------------------------------------------------------------------------
# Tests — compute_signals
# ---------------------------------------------------------------------------


def test_compute_signals_returns_expected_keys():
    """compute_signals returns all expected signal keys."""
    analyzer = RiskAnalyzer()
    extraction = _extraction()
    ticks = [_tick(0, 0.1), _tick(1, 0.3)]

    signals = analyzer.compute_signals(
        [5.0, 4.8], ticks, extraction_output=extraction,
    )

    expected_keys = {
        "negative_trend",
        "final_polarization",
        "max_negative_shift",
        "event_prior_floor",
        "sensitive_context_hit",
        "start_x",
        "final_x",
        "negative_pressure",
        "event_scale",
        "event_controversy",
        "high_sensitive_prior",
    }

    assert expected_keys == set(signals.keys())
