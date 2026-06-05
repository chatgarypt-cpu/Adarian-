import statistics
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.phase4 import report_agent
from src.phase4.report_agent import (
    _build_code_owned_report_contract_block,
    generate_fallback_report,
    parse_llm_report_response,
    save_markdown_report,
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


def _valid_llm_markdown(sentinel: str) -> str:
    return f"""# 测试报告

## 一、舆情概要

{sentinel} 舆情概要内容足够长，用于验证显式 markdown 参数优先于旧全局缓存。

## 二、演化分析

演化分析内容足够长，包含模拟立场变化描述。

## 三、风险研判

风险等级：高风险

主要风险类型：
1. 信息不透明风险

风险解释：dataset risk basis

## 四、对策建议

治理动作：及时回应。

## 五、附录

模拟说明与口径说明。
"""


def test_new_path_explicit_markdown_is_saved(tmp_path):
    extraction = _extraction()
    output = generate_fallback_report(
        extraction,
        _tick_logs(),
        [5.0, 4.7],
        phase2_output=_phase2_output(),
    )
    report_agent._llm_generated_markdown = _valid_llm_markdown("LEGACY_MARKDOWN_SENTINEL")

    path = tmp_path / "run_explicit" / "final_report.md"
    save_markdown_report(
        output,
        extraction,
        path,
        markdown=_valid_llm_markdown("EXPLICIT_MARKDOWN_SENTINEL"),
    )
    markdown = path.read_text(encoding="utf-8")
    report_agent._llm_generated_markdown = ""

    assert "EXPLICIT_MARKDOWN_SENTINEL" in markdown
    assert "LEGACY_MARKDOWN_SENTINEL" not in markdown


def test_old_path_without_explicit_markdown_uses_legacy_global(tmp_path):
    extraction = _extraction()
    output = generate_fallback_report(
        extraction,
        _tick_logs(),
        [5.0, 4.7],
        phase2_output=_phase2_output(),
    )
    report_agent._llm_generated_markdown = _valid_llm_markdown("LEGACY_MARKDOWN_SENTINEL")

    path = tmp_path / "run_legacy" / "final_report.md"
    save_markdown_report(output, extraction, path)
    markdown = path.read_text(encoding="utf-8")
    report_agent._llm_generated_markdown = ""

    assert "LEGACY_MARKDOWN_SENTINEL" in markdown


def test_parse_llm_response_uses_dataset_risk_verdict(monkeypatch):
    def fail_old_risk(*args, **kwargs):
        raise AssertionError("old assess_risk should not be called when dataset exists")

    monkeypatch.setattr(report_agent, "assess_risk", fail_old_risk)
    output = parse_llm_report_response(
        "short",
        _extraction(),
        _tick_logs(),
        [5.0, 4.7],
        phase2_output=_phase2_output(),
        simulation_dataset=_dataset(),
    )

    assert output.risk_level == RiskLevel.HIGH
    assert output.risk_assessment == "dataset risk basis"
    assert output.audience_mode == AudienceMode.REGULATOR_FACING
    assert output.primary_risk_types == ["information_opacity_risk"]


def test_parse_llm_response_uses_dataset_inflection_points(monkeypatch):
    def fail_old_inflection(*args, **kwargs):
        raise AssertionError("old identify_inflection_points should not be called when dataset exists")

    monkeypatch.setattr(report_agent, "identify_inflection_points", fail_old_inflection)
    output = parse_llm_report_response(
        "short",
        _extraction(),
        _tick_logs(),
        [5.0, 4.7],
        phase2_output=_phase2_output(),
        simulation_dataset=_dataset(),
    )

    assert len(output.inflection_points) == 1
    assert output.inflection_points[0].impact_description == "dataset inflection preserved"
    assert len(output.emotion_trajectory) == 2
    assert output.emotion_trajectory[1].key_event == "dataset tick 1"


def test_contract_block_uses_dataset_values(monkeypatch):
    def fail_old_risk(*args, **kwargs):
        raise AssertionError("old assess_risk should not be called when dataset exists")

    monkeypatch.setattr(report_agent, "assess_risk", fail_old_risk)
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


def test_old_path_without_dataset_keeps_legacy_behavior(monkeypatch):
    called = {"risk": False}

    def legacy_risk(*args, **kwargs):
        called["risk"] = True
        return RiskLevel.LOW, "legacy risk basis"

    monkeypatch.setattr(report_agent, "assess_risk", legacy_risk)
    block = _build_code_owned_report_contract_block(
        _extraction(),
        _tick_logs(),
        [5.0, 4.7],
    )

    assert called["risk"] is True
    assert "risk_level_label: 低风险" in block
    assert "risk_assessment: legacy risk basis" in block
