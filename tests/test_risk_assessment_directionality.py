"""Targeted checks for v1.2.8.1 risk directionality and metric explanation."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.phase4 import report_agent
from src.phase4.report_agent import (
    _build_code_owned_report_contract_block,
    assess_risk,
    generate_fallback_report,
    save_markdown_report,
)
from src.phase4.report_prompts import METRIC_EXPLANATION_PREFILL, REPORT_USER_PROMPT_SUFFIX
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
    RISK_TYPE_LABELS,
    Relation,
    TickLog,
)
from src.schemas.phase4 import RiskLevel


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
            )
        ],
        relations=[Relation(source=entity_name, target="观望群体", type="舆论关联")],
    )


def _entry(agent_id: int, previous: float, current: float, group_name: str = "观望群体") -> AgentEntry:
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


def _tick(tick: int, polarization: float = 0.1, entries: list[AgentEntry] | None = None) -> TickLog:
    return TickLog(
        tick=tick,
        entries=entries if entries is not None else [_entry(1, 5.0, 5.0)],
        global_metrics=GlobalMetrics(
            mean_stance=5.0,
            std_stance=1.0,
            polarization_index=polarization,
        ),
    )


def _ticks_for_shift(initial: float, final: float, polarization: float = 0.1) -> list[TickLog]:
    return [
        _tick(0, polarization, [_entry(0, 5.0, 5.0, "事件实体")]),
        _tick(1, polarization, [_entry(8, initial, initial)]),
        _tick(2, polarization, [_entry(8, initial, final)]),
    ]


def _phase2_output(entity_name: str = "某主体") -> Phase2Output:
    return Phase2Output(
        nodes=[
            GraphNode(
                id=8,
                group_name="观望群体",
                archetype_index=0,
                related_entity=entity_name,
                role=NodeRole.PERIPHERY,
                stance_score=5.0,
                susceptibility=0.5,
                entity_category="opinion_spreader",
            )
        ],
        edges=[GraphEdge(source=8, target=8)],
    )


def test_low_final_stance_triggers_medium():
    risk_level, _ = assess_risk([5.0, 4.7], [_tick(0), _tick(1)])

    assert risk_level == RiskLevel.MEDIUM


def test_negative_trend_triggers_medium():
    risk_level, _ = assess_risk([5.5, 5.1], [_tick(0), _tick(1)])

    assert risk_level == RiskLevel.MEDIUM


def test_final_polarization_triggers_medium():
    risk_level, _ = assess_risk([5.2, 5.2], [_tick(0, 0.1), _tick(1, 0.30)])

    assert risk_level == RiskLevel.MEDIUM


def test_max_negative_shift_triggers_medium():
    risk_level, assessment = assess_risk(
        [5.2, 5.2, 5.2],
        _ticks_for_shift(6.0, 4.8),
    )

    assert risk_level == RiskLevel.MEDIUM
    assert "关键群体最大负向迁移=1.2" in assessment


def test_scale_and_controversy_provide_medium_floor():
    risk_level, assessment = assess_risk(
        [5.2, 5.2],
        [_tick(0), _tick(1)],
        extraction_output=_extraction(event_scale=0.7, event_controversy=0.7),
    )

    assert risk_level == RiskLevel.MEDIUM
    assert "高敏事件先验" in assessment


def test_single_light_signal_does_not_trigger_high_or_critical():
    risk_level, _ = assess_risk([5.2, 5.2], [_tick(0, 0.1), _tick(1, 0.46)])

    assert risk_level == RiskLevel.MEDIUM

    risk_level, _ = assess_risk([2.9, 2.9], [_tick(0, 0.1), _tick(1, 0.1)])

    assert risk_level != RiskLevel.CRITICAL


def test_oppo_brand_marketing_dispute_is_not_critical():
    extraction = _extraction(
        "OPPO母亲节营销海报引发价值观争议",
        "OPPO",
        event_scale=0.75,
        event_controversy=0.75,
    )

    risk_level, _ = assess_risk(
        [5.0, 4.8],
        [_tick(0, 0.1), _tick(1, 0.42)],
        extraction_output=extraction,
    )

    assert risk_level == RiskLevel.HIGH
    assert risk_level != RiskLevel.CRITICAL


def test_risk_type_labels_remain_code_owned():
    output = generate_fallback_report(
        _extraction("公安处置程序争议", "公安"),
        [_tick(0, 0.1), _tick(1, 0.35)],
        [5.2, 5.0],
        phase2_output=_phase2_output("公安"),
    )

    assert output.primary_risk_types
    assert output.risk_type_labels == [RISK_TYPE_LABELS[item] for item in output.primary_risk_types]


def test_llm_prompt_does_not_ask_llm_to_decide_risk_level():
    contract = _build_code_owned_report_contract_block(
        _extraction(),
        [_tick(0), _tick(1)],
        [5.2, 5.2],
    )

    assert "risk_level_label:" in contract
    assert "以上字段为代码侧结果" in contract
    assert "风险等级必须逐字使用 code-owned risk_level_label" in REPORT_USER_PROMPT_SUFFIX
    assert "自行判断风险等级" not in REPORT_USER_PROMPT_SUFFIX


def test_metric_explanation_prefill_is_code_owned_and_deduplicated(tmp_path):
    extraction = _extraction()
    output = generate_fallback_report(
        extraction,
        [_tick(0), _tick(1)],
        [5.2, 5.2],
        phase2_output=_phase2_output(),
    )
    report_agent._llm_generated_markdown = (
        "# LLM 报告\n\n"
        "## 一、舆情概要\n\n内容。\n\n"
        "## 二、演化分析\n\n内容。\n\n"
        "## 三、风险研判\n\n风险等级：低风险\n\n"
        "## 四、对策建议\n\n内容。\n\n"
        "## 五、附录\n\n"
        "### 模拟参数说明\n\n"
        "LLM 自由生成的指标解释。"
    )

    path = tmp_path / "run_001" / "final_report.md"
    save_markdown_report(output, extraction, path)
    report_agent._llm_generated_markdown = ""

    markdown = path.read_text(encoding="utf-8")
    assert METRIC_EXPLANATION_PREFILL in markdown
    assert markdown.count(METRIC_EXPLANATION_PREFILL) == 1
    assert "LLM 自由生成的指标解释" not in markdown


def test_saved_markdown_uses_metric_terminology(tmp_path):
    extraction = _extraction()
    output = generate_fallback_report(
        extraction,
        [_tick(0), _tick(1)],
        [5.2, 5.2],
        phase2_output=_phase2_output(),
    )
    report_agent._llm_generated_markdown = (
        "# LLM 报告\n\n"
        "## 一、舆情概要\n\nTick 1 情绪均值和极化指数出现拐点，x(t)下降。\n\n"
        "## 二、演化分析\n\n内容。\n\n"
        "## 三、风险研判\n\n风险等级：低风险\n\n"
        "## 四、对策建议\n\n内容。\n\n"
        "## 五、附录\n\n内容。"
    )

    path = tmp_path / "run_002" / "final_report.md"
    save_markdown_report(output, extraction, path)
    report_agent._llm_generated_markdown = ""

    markdown = path.read_text(encoding="utf-8")
    body = markdown.split("## 五、附录", 1)[0]
    assert "情绪均值" not in markdown
    assert "模拟立场均值" in body
    assert "模拟极化指数" in body
    assert "模拟关键变化点" in body
    assert "轮次 1" in body
