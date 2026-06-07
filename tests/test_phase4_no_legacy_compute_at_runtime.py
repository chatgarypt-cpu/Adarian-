"""v1.3.1: At runtime, the clean Phase4 product path must not call any legacy
compute function. We assert by monkey-patching legacy symbols to raise and
verifying that the public clean API still works end-to-end.
"""

import pytest


def _extraction():
    from src.schemas import EntityExtractionOutput, Entity, OpinionSpreader, Relation
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


def test_consumer_namespace_does_not_hold_legacy_compute():
    """Clean report_agent module must not bind legacy compute names."""
    from src.phase4 import report_agent
    for name in (
        "assess_risk",
        "identify_inflection_points",
        "determine_audience_mode",
        "select_primary_risk_types",
        "_max_negative_shift_from_stance_matrix",
        "_sensitive_prior_risk_types",
    ):
        assert not hasattr(report_agent, name), (
            f"report_agent unexpectedly binds legacy compute: {name}"
        )


def test_clean_contract_block_does_not_call_legacy_assess_risk(monkeypatch):
    """When simulation_dataset is supplied, contract block must not call legacy analytics."""
    from src.phase4.report_agent import _build_code_owned_report_contract_block
    import legacy.phase4.legacy_analytics as legacy_analytics

    extraction = _extraction()
    tick_logs = []
    dataset = {
        "run_info": {"audience_mode": "generic_government"},
        "simulation_result": {
            "risk_verdict": {
                "level": "low",
                "label": "低风险",
                "basis_text": "dataset basis",
                "signals": {},
            },
            "risk_type_classification": {
                "primary_types": ["negative_narrative_risk"],
                "type_labels": ["负面叙事聚合风险"],
            },
        },
    }

    def fail(*args, **kwargs):
        raise AssertionError("legacy assess_risk must not be called when dataset exists")

    monkeypatch.setattr(legacy_analytics, "assess_risk", fail)
    monkeypatch.setattr(legacy_analytics, "identify_inflection_points", fail)

    block = _build_code_owned_report_contract_block(
        extraction, tick_logs, [5.0, 4.8], simulation_dataset=dataset,
    )
    assert "低风险" in block
    assert "负面叙事聚合风险" in block


def test_clean_parse_does_not_call_legacy_compute(monkeypatch):
    from src.phase4.report_agent import parse_llm_report_response
    import legacy.phase4.legacy_analytics as legacy_analytics

    extraction = _extraction()
    dataset = {
        "run_info": {"audience_mode": "generic_government"},
        "simulation_result": {
            "risk_verdict": {
                "level": "low",
                "label": "低风险",
                "basis_text": "dataset basis",
                "signals": {},
            },
            "risk_type_classification": {
                "primary_types": ["negative_narrative_risk"],
                "type_labels": ["负面叙事聚合风险"],
            },
            "inflection_points": [],
            "emotion_trajectory": [],
            "agent_stance_matrix": [],
        },
    }

    def fail(*args, **kwargs):
        raise AssertionError("legacy compute must not be called from clean parse path")

    monkeypatch.setattr(legacy_analytics, "assess_risk", fail)
    monkeypatch.setattr(legacy_analytics, "identify_inflection_points", fail)

    out = parse_llm_report_response(
        "irrelevant response text",
        extraction,
        [],
        [5.0, 4.8],
        simulation_dataset=dataset,
    )
    from src.schemas.phase4 import RiskLevel
    assert out.risk_level == RiskLevel.LOW
    assert out.risk_assessment == "dataset basis"
