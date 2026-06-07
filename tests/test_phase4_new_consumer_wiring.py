"""v1.3.1 consumer-wiring checks (post Phase3 decoupling).

v1.3.1: src.phase4 no longer carries old compute functions. The legacy
assess_risk / identify_inflection_points / etc. live under
``legacy.phase4.legacy_analytics`` and ``legacy.phase4.legacy_generation``.
The new product main flow only consumes ``simulation_dataset``, so we
monkeypatch the legacy helpers in their legacy module to verify the
new path never reaches them.
"""

import statistics
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.phase4 import report_agent
from src.phase4.report_agent import (
    _build_code_owned_report_contract_block,
    parse_llm_report_response,
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
from src.schemas.phase4 import AudienceMode, RiskLevel

import legacy.phase4.legacy_analytics as legacy_analytics
import legacy.phase4.legacy_generation as legacy_generation


def _extraction() -> EntityExtractionOutput:
    return EntityExtractionOutput(
        event_summary="测试消费争议事件",
        event_scale=0.4,
        event_controversy=0.5,
        event_type="公共事件",
        event_entities=[
            Entity(
                name="某品牌",
                type="organization",
                role="涉事主体",
                can_speak=True,
                original_statement="我们会核查。",
            ),
        ],
        opinion_spreaders=[
            OpinionSpreader(
                group_name="支持方",
                related_event_entity="某品牌",
                description="等待核查结果",
                I=6.0,
                P=1,
                susceptibility=0.3,
                estimated_percentage=40,
                communication_style="克制表达",
                persona_name="小林",
                age_range="25-34",
                occupation="市民",
                personality="冷静",
                motivation="关注事实",
                typical_phrases=["先看证据", "等待回应"],
            ),
            OpinionSpreader(
                group_name="质疑方",
                related_event_entity="某品牌",
                description="关注流程透明度",
                I=3.0,
                P=-1,
                susceptibility=0.5,
                estimated_percentage=60,
                communication_style="直接追问",
                persona_name="老周",
                age_range="35-45",
                occupation="消费者",
                personality="较真",
                motivation="要求透明",
                typical_phrases=["回应要及时", "流程要公开"],
            ),
        ],
        relations=[Relation(source="某品牌", target="质疑方", type="舆论关联")],
    )


def _phase2_output() -> Phase2Output:
    return Phase2Output(
        nodes=[
            GraphNode(
                id=1,
                group_name="质疑方",
                archetype_index=-2,
                related_entity="某品牌",
                role=NodeRole.PERIPHERY,
                stance_score=4.0,
                susceptibility=0.5,
                entity_category="opinion_spreader",
            )
        ],
        edges=[GraphEdge(source=1, target=1)],
    )


def _entry(agent_id: int, previous: float, current: float) -> AgentEntry:
    return AgentEntry(
        agent_id=agent_id,
        group_name="质疑方",
        saw_posts_from=[],
        previous_stance=previous,
        current_stance=current,
        stance_delta=current - previous,
        susceptibility=0.5,
        change_reason="within_effective_delta",
        comment="流程要公开，回应不能拖。",
        reasoning="程序透明度不足",
    )


def _tick(tick: int, previous: float, current: float, polarization: float) -> TickLog:
    entries = [_entry(1, previous, current)]
    stances = [entry.current_stance for entry in entries]
    return TickLog(
        tick=tick,
        entries=entries,
        global_metrics=GlobalMetrics(
            mean_stance=sum(stances) / len(stances),
            std_stance=statistics.stdev(stances) if len(stances) > 1 else 0.0,
            polarization_index=polarization,
        ),
    )


def _tick_logs() -> list[TickLog]:
    return [_tick(0, 5.0, 5.0, 0.1), _tick(1, 5.0, 4.7, 0.2)]


def _dataset() -> dict:
    return {
        "run_info": {
            "audience_mode": AudienceMode.REGULATOR_FACING.value,
        },
        "simulation_result": {
            "emotion_trajectory": [
                {
                    "tick": 0,
                    "mean_stance": 5.0,
                    "std_stance": 0.0,
                    "polarization_index": 0.1,
                    "key_event": "dataset tick 0",
                },
                {
                    "tick": 1,
                    "mean_stance": 4.7,
                    "std_stance": 0.0,
                    "polarization_index": 0.2,
                    "key_event": "dataset tick 1",
                },
            ],
            "inflection_points": [
                {
                    "tick": 1,
                    "agent_id": 1,
                    "group_name": "质疑方",
                    "pivotal_comment": "需要解释流程。",
                    "impact_description": "dataset inflection preserved",
                }
            ],
            "risk_verdict": {
                "level": RiskLevel.HIGH.value,
                "label": "高风险",
                "basis_text": "dataset risk basis",
                "signals": {"max_negative_shift": 1.2},
            },
            "risk_type_classification": {
                "primary_types": ["information_opacity_risk"],
                "type_labels": ["信息不透明风险"],
            },
            "agent_stance_matrix": [],
        },
    }


def test_parse_llm_response_uses_dataset_risk_verdict(monkeypatch):
    """The new parse_llm_report_response must NOT call legacy assess_risk.

    v1.3.1: parse_llm_report_response lives in src.phase4.report_agent
    and is a pure consumer of simulation_dataset. We assert that even
    if legacy.phase4.legacy_analytics.assess_risk is rigged to raise,
    the parse path still succeeds by reading the dataset.
    """
    def fail_old_risk(*args, **kwargs):
        raise AssertionError("legacy assess_risk should not be called when dataset exists")

    monkeypatch.setattr(legacy_analytics, "assess_risk", fail_old_risk)
    output = parse_llm_report_response(
        "short",
        _extraction(),
        _tick_logs(),
        [5.0, 4.7],
        simulation_dataset=_dataset(),
    )

    assert output.risk_level == RiskLevel.HIGH
    assert output.risk_assessment == "dataset risk basis"
    assert output.audience_mode == AudienceMode.REGULATOR_FACING
    assert output.primary_risk_types == ["information_opacity_risk"]


def test_parse_llm_response_uses_dataset_inflection_points(monkeypatch):
    """The new parse_llm_report_response must NOT call legacy identify_inflection_points."""
    def fail_old_inflection(*args, **kwargs):
        raise AssertionError("legacy identify_inflection_points should not be called when dataset exists")

    monkeypatch.setattr(legacy_analytics, "identify_inflection_points", fail_old_inflection)
    output = parse_llm_report_response(
        "short",
        _extraction(),
        _tick_logs(),
        [5.0, 4.7],
        simulation_dataset=_dataset(),
    )

    assert len(output.inflection_points) == 1
    assert output.inflection_points[0].impact_description == "dataset inflection preserved"
    assert len(output.emotion_trajectory) == 2
    assert output.emotion_trajectory[1].key_event == "dataset tick 1"


def test_contract_block_uses_dataset_values(monkeypatch):
    """The new _build_code_owned_report_contract_block must NOT call legacy assess_risk."""
    def fail_old_risk(*args, **kwargs):
        raise AssertionError("legacy assess_risk should not be called when dataset exists")

    monkeypatch.setattr(legacy_analytics, "assess_risk", fail_old_risk)
    block = _build_code_owned_report_contract_block(
        _extraction(),
        _tick_logs(),
        [5.0, 4.7],
        simulation_dataset=_dataset(),
    )

    assert "risk_level_label: 高风险" in block
    assert "risk_type_labels: 信息不透明风险" in block
    assert "audience_mode: regulator_facing" in block
    assert "primary_risk_types: information_opacity_risk" in block
    assert "risk_assessment: dataset risk basis" in block
