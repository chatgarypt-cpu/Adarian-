"""Targeted Phase 4 report product contract checks for v1.2.8 attempt-01."""

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.phase4 import report_agent
from src.phase4.report_agent import (
    _build_code_owned_report_contract_block,
    _ensure_metadata_header,
    _normalize_saved_markdown,
    _normalized_report_title,
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


def _section(markdown: str, start: str, end: str) -> str:
    return markdown.split(start, 1)[1].split(end, 1)[0]


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

    assert with_header.startswith(f"# {_normalized_report_title(output.report_meta.event_name)}")
    assert f"生成时间：{output.report_meta.generated_at}" in with_header
    assert "报告类型：模拟推演型舆情风险研判报告" in with_header
    assert "# LLM 自生成报告" in with_header


def test_report_title_hygiene_removes_marketing_connector_duplication():
    assert _normalized_report_title("OPPO母亲节营销海报引发价值观争议") == "OPPO母亲节营销争议舆情风险研判报告"
    assert _normalized_report_title("OPPO母亲节文案营销争议引发讨论") == "OPPO母亲节营销争议舆情风险研判报告"
    assert "营营销" not in _normalized_report_title("OPPO母亲节营销争议")
    assert "文营销" not in _normalized_report_title("OPPO母亲节文案营销争议")


def test_llm_user_prompt_injects_code_owned_report_contract(monkeypatch):
    extraction = _extraction(summary="OPPO母亲节营销海报引发价值观争议", entity_name="OPPO")
    tick_logs = [_tick(0, 0.2), _tick(1, 0.58)]
    captured = {}

    class FakeLLM:
        def generate(self, system, user, response_model=None):
            captured["system"] = system
            captured["user"] = user
            return (
                "# 模拟报告\n\n"
                "## 一、舆情概要\n\n内容足够长。\n\n"
                "## 二、演化分析\n\n第一阶段：争议触发期。\n\n"
                "## 三、风险研判\n\n风险等级：中风险\n\n主要风险类型：\n1. 群体对立风险\n\n风险解释：模拟内容。\n\n"
                "## 四、对策建议\n\n治理动作：关注。\n\n"
                "## 五、附录\n\n模拟说明。"
            )

    monkeypatch.setattr(report_agent, "get_llm_client", lambda: FakeLLM())
    report_agent.generate_report_with_llm(
        extraction,
        tick_logs,
        [5.0, 5.2],
        phase2_output=_phase2_output("OPPO"),
    )
    report_agent._llm_generated_markdown = ""

    expected_block = _build_code_owned_report_contract_block(extraction, tick_logs, [5.0, 5.2])
    assert expected_block in captured["user"]
    assert "【CODE_OWNED_REPORT_CONTRACT】" in captured["user"]
    assert "risk_level_label:" in captured["user"]
    assert "risk_type_labels:" in captured["user"]
    assert "audience_mode:" in captured["user"]
    assert "primary_risk_types:" in captured["user"]


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


def test_fallback_markdown_has_v128_government_facing_narrative(tmp_path):
    extraction = _extraction(
        summary="OPPO母亲节营销海报引发价值观争议和平台讨论",
        entity_name="OPPO",
    )
    output = generate_fallback_report(
        extraction,
        [_tick(0, 0.2), _tick(1, 0.58), _tick(2, 0.62)],
        [5.0, 4.6, 4.4],
        phase2_output=_phase2_output("OPPO"),
    )

    path = tmp_path / "run_007" / "final_report.md"
    report_agent._llm_generated_markdown = ""
    save_markdown_report(output, extraction, path)

    markdown = path.read_text(encoding="utf-8")
    title = markdown.splitlines()[0].removeprefix("# ")
    evolution_section = _section(markdown, "## 二、演化分析", "## 三、风险研判")
    risk_section = _section(markdown, "## 三、风险研判", "## 四、对策建议")
    recommendation_section = _section(markdown, "## 四、对策建议", "## 五、附录")

    assert title.endswith("舆情风险研判报告")
    assert len(title) <= 25
    assert "OPPO" in title
    assert "营营销" not in title
    assert title == "OPPO母亲节营销争议舆情风险研判报告"
    for subheading in (
        "### （一）主体与发声结构分析",
        "### （二）关键群体变化分析",
        "### （三）阶段演化分析",
        "### （四）关键洞察",
    ):
        assert subheading in evolution_section
    assert "第一阶段" in evolution_section
    assert "第二阶段" in evolution_section
    assert "关键洞察" in evolution_section
    assert "Tick 1" not in evolution_section
    assert "Tick 2" not in evolution_section
    assert "Tick 3" not in evolution_section
    for subheading in (
        "### （一）矛盾焦点分析",
        "### （二）结构性风险点一",
        "### （三）结构性风险点二",
        "### （四）结构性风险点三",
        "### （五）短中期态势判断",
    ):
        assert subheading in risk_section
    assert "结构性风险点一" in risk_section
    assert "结构性风险点二" in risk_section
    assert "结构性风险点三" in risk_section
    assert "矛盾焦点分析" in risk_section
    assert "品牌声誉风险" not in risk_section
    assert "舆论极化风险" not in risk_section
    assert "衍生争议风险" not in risk_section
    assert recommendation_section.count("治理动作：") >= 5
    assert recommendation_section.count("触发条件：") >= 5
    assert recommendation_section.count("介入边界：") >= 5
    assert recommendation_section.count("预期效果：") >= 5
    assert any(
        word in recommendation_section
        for word in ("关注", "研判", "跟踪", "协调", "督促", "预置", "提示", "监测", "引导", "避免过度介入")
    )
    for forbidden in ("建议OPPO", "建议品牌方", "建议品牌", "建议企业", "建议涉事企业", "贵司", "贵校", "危机公关", "品牌修复", "舆情洗白"):
        assert forbidden not in markdown


def test_empty_inflection_and_quote_raw_metric_guards_in_saved_markdown(tmp_path):
    extraction = _extraction()
    output = generate_fallback_report(
        extraction,
        [_tick(0, 0.2)],
        [4.8],
        phase2_output=_phase2_output(),
    )

    path = tmp_path / "run_008" / "final_report.md"
    save_markdown_report(output, extraction, path)

    markdown = path.read_text(encoding="utf-8")
    assert "本轮模拟未发现显著拐点" in markdown
    assert "待评估" not in markdown
    for field_name in ("event_scale", "event_controversy", "polarization_index", "stance_delta", "risk_score"):
        assert field_name not in markdown
    for quote_pattern in ("有网民表示：", "据网友反映：", "一位市民说：", "部分网友称：", "有评论指出："):
        assert quote_pattern not in markdown


def test_h1_hygiene_removes_body_h1_without_dropping_five_chapters():
    output = generate_fallback_report(
        _extraction(summary="OPPO母亲节营销海报引发价值观争议", entity_name="OPPO"),
        [_tick(0), _tick(1)],
        [5.0, 5.2],
        phase2_output=_phase2_output("OPPO"),
    )
    markdown = (
        "# 旧标题\n\n"
        "报告类型：模拟推演型舆情风险研判报告\n"
        f"生成时间：{output.report_meta.generated_at}\n\n"
        "# Body H1 Should Be Removed\n\n"
        "## 一、舆情概要\n\n内容\n\n"
        "## 二、演化分析\n\n内容\n\n"
        "## 三、风险研判\n\n内容\n\n"
        "## 四、对策建议\n\n内容\n\n"
        "## 五、附录\n\n内容\n"
    )

    normalized = _normalize_saved_markdown(markdown, output)

    assert len([line for line in normalized.splitlines() if line.startswith("# ")]) == 1
    assert "Body H1 Should Be Removed" not in normalized
    for heading in ("## 一、舆情概要", "## 二、演化分析", "## 三、风险研判", "## 四、对策建议", "## 五、附录"):
        assert heading in normalized
