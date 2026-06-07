"""Targeted checks for v1.2.8.1.1 inflection point output guards.

v1.3.1: identify_inflection_points and the legacy _replace_* helpers
are archived. This test drives the legacy archive to keep the
guard semantics validated.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.phase4 import report_normalizer
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
from src.phase4.report_normalizer import (
    _replace_reality_claims_about_inflection,
    _replace_report_metric_terms,
)
from legacy.phase4.legacy_analytics import identify_inflection_points
from legacy.phase4 import legacy_generation
from legacy.phase4.legacy_generation import (
    generate_fallback_report,
    save_markdown_report as legacy_save_markdown_report,
)


def _entry(agent_id: int, previous: float, current: float, group_name: str = "质疑群体") -> AgentEntry:
    return AgentEntry(
        agent_id=agent_id,
        group_name=group_name,
        saw_posts_from=[],
        previous_stance=previous,
        current_stance=current,
        stance_delta=current - previous,
        susceptibility=0.5,
        change_reason="within_effective_delta",
        comment="需要更清楚的事实说明。",
        reasoning="测试样本",
    )


def _tick(tick: int, polarization: float, entries: list[AgentEntry] | None = None) -> TickLog:
    return TickLog(
        tick=tick,
        entries=entries if entries is not None else [_entry(8, 5.0, 4.5)],
        global_metrics=GlobalMetrics(
            mean_stance=5.0,
            std_stance=1.0,
            polarization_index=polarization,
        ),
    )


def _phase2_output() -> Phase2Output:
    return Phase2Output(
        nodes=[
            GraphNode(
                id=8,
                group_name="质疑群体",
                archetype_index=-1,
                related_entity="某主体",
                role=NodeRole.PERIPHERY,
                stance_score=4.0,
                susceptibility=0.5,
                entity_category="opinion_spreader",
            )
        ],
        edges=[GraphEdge(source=8, target=8)],
    )


def _extraction() -> EntityExtractionOutput:
    return EntityExtractionOutput(
        event_summary="普通公共争议事件",
        event_scale=0.3,
        event_controversy=0.4,
        event_type="公共事件",
        event_entities=[
            Entity(
                name="某主体",
                type="organization",
                role="涉事主体",
                can_speak=True,
                original_statement="将补充说明。",
            )
        ],
        opinion_spreaders=[
            OpinionSpreader(
                group_name="观望群体",
                related_event_entity="某主体",
                description="等待事实",
                I=5.5,
                P=1,
                susceptibility=0.3,
                estimated_percentage=55,
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
                related_event_entity="某主体",
                description="质疑回应",
                I=3.5,
                P=-1,
                susceptibility=0.6,
                estimated_percentage=45,
                communication_style="直接追问",
                persona_name="老周",
                age_range="35-45",
                occupation="消费者",
                personality="较真",
                motivation="要求透明",
                typical_phrases=["需要公开", "回应要及时"],
            ),
        ],
        relations=[Relation(source="某主体", target="质疑群体", type="舆论关联")],
    )


def test_identify_inflection_points_positive_polarization_delta():
    tick_logs = [
        _tick(0, 0.20, [_entry(8, 5.0, 5.0)]),
        _tick(1, 0.35, [_entry(8, 5.0, 4.2)]),
    ]

    points = identify_inflection_points(tick_logs, _phase2_output())

    assert points
    assert points[0].tick == 1
    assert "模拟极化指数变化" in points[0].impact_description
    assert "现实舆情拐点" not in points[0].impact_description


def test_reality_inflection_claims_are_rewritten_to_simulation_boundary():
    markdown = (
        "现实舆情已经出现拐点。\n"
        "全网舆情发生转折。\n"
        "公众态度已经改变。"
    )

    normalized = _replace_reality_claims_about_inflection(markdown)

    for phrase in ("现实舆情已经出现拐点", "全网舆情发生转折", "公众态度已经改变"):
        assert phrase not in normalized
    assert "模拟关键变化点" in normalized
    assert "不等同于现实舆情传播中的真实转折" in normalized


def test_metric_term_replacement_does_not_duplicate_simulation_prefix():
    markdown = (
        "## 一、舆情概要\n\n"
        "模拟极化指数与极化指数均被提及。"
        "模拟关键变化点与拐点均被提及。"
        "模拟立场均值与情绪均值均被提及。"
    )

    normalized = _replace_report_metric_terms(markdown)

    assert "模拟模拟极化指数" not in normalized
    assert "模拟模拟关键变化点" not in normalized
    assert "模拟模拟立场均值" not in normalized
    assert "模拟极化指数" in normalized
    assert "模拟关键变化点" in normalized
    assert "模拟立场均值" in normalized


def test_empty_code_owned_inflections_do_not_allow_reality_claims(tmp_path):
    extraction = _extraction()
    output = generate_fallback_report(
        extraction,
        [_tick(0, 0.20), _tick(1, 0.25)],
        [5.0, 5.0],
        phase2_output=_phase2_output(),
    )
    assert output.inflection_points == []

    legacy_generation._llm_generated_markdown = (
        "# LLM 报告\n\n"
        "## 一、舆情概要\n\n第3轮出现现实舆情拐点。\n\n"
        "## 二、演化分析\n\n第2轮公众态度已经改变。\n\n"
        "## 三、风险研判\n\n风险等级：低风险\n\n"
        "## 四、对策建议\n\n内容。\n\n"
        "## 五、附录\n\n内容。"
    )

    path = tmp_path / "run_001" / "final_report.md"
    legacy_save_markdown_report(output, extraction, path)
    legacy_generation._llm_generated_markdown = ""

    markdown = path.read_text(encoding="utf-8")
    assert output.inflection_points == []
    assert "第3轮出现现实舆情拐点" not in markdown
    assert "第2轮公众态度已经改变" not in markdown
    assert "现实舆情已经出现拐点" not in markdown
    assert "模拟关键变化点" in markdown


def test_non_empty_code_owned_inflections_do_not_allow_extra_reality_node(tmp_path):
    extraction = _extraction()
    output = generate_fallback_report(
        extraction,
        [_tick(0, 0.20), _tick(1, 0.35)],
        [5.0, 5.0],
        phase2_output=_phase2_output(),
    )
    assert output.inflection_points

    legacy_generation._llm_generated_markdown = (
        "# LLM 报告\n\n"
        "## 一、舆情概要\n\n内容。\n\n"
        "## 二、演化分析\n\n第3轮现实舆情已经出现拐点。\n\n"
        "## 三、风险研判\n\n风险等级：中风险\n\n"
        "## 四、对策建议\n\n内容。\n\n"
        "## 五、附录\n\n内容。"
    )

    path = tmp_path / "run_002" / "final_report.md"
    legacy_save_markdown_report(output, extraction, path)
    legacy_generation._llm_generated_markdown = ""

    markdown = path.read_text(encoding="utf-8")
    assert "第3轮现实舆情已经出现拐点" not in markdown
    assert "现实舆情已经出现拐点" not in markdown
    assert "不等同于现实舆情传播中的真实转折" in markdown
