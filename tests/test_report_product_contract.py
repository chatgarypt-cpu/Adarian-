"""Targeted Phase 4 report product contract checks for v1.2.7 attempt-01."""

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.phase4 import report_agent
from src.phase4.report_agent import (
    _ensure_metadata_header,
    determine_audience_mode,
    generate_fallback_report,
    save_markdown_report,
    save_report,
)
from src.schemas import (
    AgentEntry,
    AudienceMode,
    Entity,
    EntityExtractionOutput,
    GlobalMetrics,
    GraphEdge,
    GraphNode,
    NodeRole,
    OpinionSpreader,
    Phase2Output,
    RISK_TYPE_LABELS,
    Relation,
    TickLog,
)
from src.schemas.phase4 import REPORT_TYPE, RiskLevel


def _extraction(summary="普通消费争议事件", entity_name="某品牌") -> EntityExtractionOutput:
    return EntityExtractionOutput(
        event_summary=summary,
        event_scale=0.6,
        event_controversy=0.7,
        event_type="公共事件",
        event_entities=[
            Entity(
                name=entity_name,
                type="organization",
                role="涉事主体",
                can_speak=True,
                original_statement="我们会核查处理。",
            )
        ],
        opinion_spreaders=[
            OpinionSpreader(
                group_name="支持方",
                related_event_entity=entity_name,
                description="等待更多事实",
                I=7.5,
                P=1,
                susceptibility=0.3,
                estimated_percentage=45,
                communication_style="克制表达",
                persona_name="小林",
                age_range="25-34",
                occupation="市民",
                personality="冷静",
                motivation="关注事实",
                typical_phrases=["先看证据", "别急着下结论"],
            ),
            OpinionSpreader(
                group_name="质疑方",
                related_event_entity=entity_name,
                description="质疑处置透明度",
                I=3.0,
                P=-1,
                susceptibility=0.6,
                estimated_percentage=55,
                communication_style="直接追问",
                persona_name="老周",
                age_range="35-45",
                occupation="消费者",
                personality="较真",
                motivation="要求透明",
                typical_phrases=["流程要公开", "回应太慢了"],
            ),
        ],
        relations=[
            Relation(source=entity_name, target="质疑方", type="舆论关联"),
        ],
    )


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
        comment="流程要公开，回应不能拖。",
        reasoning="程序透明度不足",
    )


def _tick(tick: int, polarization: float = 0.55) -> TickLog:
    entries = [_entry(1, "质疑方", 5.0, 4.0)]
    return TickLog(
        tick=tick,
        entries=entries,
        global_metrics=GlobalMetrics(
            mean_stance=4.8,
            std_stance=1.2,
            polarization_index=polarization,
        ),
    )


def _phase2_output(entity_name="某品牌") -> Phase2Output:
    return Phase2Output(
        nodes=[
            GraphNode(
                id=1,
                group_name="质疑方",
                archetype_index=-2,
                related_entity=entity_name,
                role=NodeRole.PERIPHERY,
                stance_score=4.0,
                susceptibility=0.5,
                entity_category="opinion_spreader",
            )
        ],
        edges=[GraphEdge(source=1, target=1)],
    )


def test_report_meta_json_and_markdown_generated_at_are_consistent(tmp_path):
    extraction = _extraction(summary="市监局介入的消费争议事件", entity_name="市监局")
    tick_logs = [_tick(0, 0.2), _tick(1, 0.55)]
    output = generate_fallback_report(
        extraction,
        tick_logs,
        [5.0, 4.8],
        phase2_output=_phase2_output("市监局"),
    )

    json_path = tmp_path / "run_001" / "final_report.json"
    md_path = tmp_path / "run_001" / "final_report.md"
    save_report(output, json_path)
    save_markdown_report(output, extraction, md_path)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    generated_at = data["report_meta"]["generated_at"]
    assert generated_at
    assert "{{" not in generated_at
    assert data["report_meta"]["report_type"] == REPORT_TYPE
    assert data["report_meta"]["simulation_run_id"] == "run_001"
    assert generated_at in markdown.splitlines()[:8][3]
    assert f"生成时间：{generated_at}" in markdown
    assert "报告类型：模拟推演型舆情风险研判报告" in markdown
    assert "模拟轮次：2轮" in markdown


def test_audience_mode_keyword_rules_and_default():
    assert determine_audience_mode(_extraction("公安处置现场争议", "公安")) == AudienceMode.LAW_ENFORCEMENT_FACING
    assert determine_audience_mode(_extraction("市监局介入消费争议", "市监局")) == AudienceMode.REGULATOR_FACING
    assert determine_audience_mode(_extraction("市场监督管理局回应投诉", "市场监督管理局")) == AudienceMode.REGULATOR_FACING
    assert determine_audience_mode(_extraction()) == AudienceMode.GENERIC_GOVERNMENT


def test_risk_level_label_and_risk_types_are_whitelisted():
    extraction = _extraction(summary="公安回应程序争议与信息公开问题", entity_name="公安")
    output = generate_fallback_report(
        extraction,
        [_tick(0), _tick(1)],
        [5.5, 6.0],
        phase2_output=_phase2_output("公安"),
    )

    assert output.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.LOW}
    assert output.risk_level_label in {"低风险", "中风险", "高风险", "重大风险"}
    assert output.risk_type_labels == [RISK_TYPE_LABELS[item] for item in output.primary_risk_types]
    assert output.primary_risk_types
    assert all(item in RISK_TYPE_LABELS for item in output.primary_risk_types)


def test_llm_markdown_path_gets_code_owned_metadata_header():
    extraction = _extraction()
    output = generate_fallback_report(
        extraction,
        [_tick(0)],
        [4.8],
        phase2_output=_phase2_output(),
    )
    llm_markdown = "# LLM 自生成报告\n\n正文内容足够长。" * 10

    with_header = _ensure_metadata_header(llm_markdown, output)

    assert with_header.startswith(f"# {output.report_meta.event_name}舆情风险研判报告")
    assert f"生成时间：{output.report_meta.generated_at}" in with_header
    assert "报告类型：模拟推演型舆情风险研判报告" in with_header
    assert "# LLM 自生成报告" in with_header


def test_save_markdown_llm_path_and_fallback_path_share_metadata(tmp_path):
    extraction = _extraction()
    output = generate_fallback_report(
        extraction,
        [_tick(0)],
        [4.8],
        phase2_output=_phase2_output(),
    )

    fallback_path = tmp_path / "run_002" / "fallback.md"
    report_agent._llm_generated_markdown = ""
    save_markdown_report(output, extraction, fallback_path)
    fallback_markdown = fallback_path.read_text(encoding="utf-8")

    llm_path = tmp_path / "run_002" / "llm.md"
    report_agent._llm_generated_markdown = "# LLM 报告\n\n" + ("内容" * 80)
    save_markdown_report(output, extraction, llm_path)
    llm_markdown = llm_path.read_text(encoding="utf-8")
    report_agent._llm_generated_markdown = ""

    assert f"生成时间：{output.report_meta.generated_at}" in fallback_markdown
    assert f"生成时间：{output.report_meta.generated_at}" in llm_markdown
    assert "报告类型：模拟推演型舆情风险研判报告" in fallback_markdown
    assert "报告类型：模拟推演型舆情风险研判报告" in llm_markdown
