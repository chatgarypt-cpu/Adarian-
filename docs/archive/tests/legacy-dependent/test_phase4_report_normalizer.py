"""Targeted checks for the extracted Phase 4 Markdown normalizer."""

from src.phase4 import report_agent
from src.phase4.report_normalizer import (
    _code_owned_risk_section,
    _normalize_saved_markdown,
    _replace_reality_claims_about_inflection,
    _replace_report_metric_terms,
)
from src.phase4.report_prompts import METRIC_EXPLANATION_PREFILL
from src.schemas import AudienceMode, Phase4Output, ReportMeta, RiskLevel


def _phase4_output() -> Phase4Output:
    return Phase4Output(
        report_meta=ReportMeta(
            generated_at="2026年05月15日 18:00",
            timezone="CST",
            event_name="OPPO母亲节营销海报引发价值观争议",
            total_ticks=2,
            simulation_run_id="run_001",
        ),
        event_summary="OPPO母亲节营销海报引发价值观争议",
        stakeholder_map="事件实体: OPPO | 传播者: 消费者",
        emotion_trajectory=[],
        inflection_points=[],
        risk_level=RiskLevel.MEDIUM,
        risk_level_label="中风险",
        audience_mode=AudienceMode.GENERIC_GOVERNMENT,
        primary_risk_types=["negative_narrative_risk"],
        risk_type_labels=["负面叙事聚合风险"],
        risk_assessment="中等风险",
        x_t_sequence=[5.0, 4.6],
    )


def test_report_agent_does_not_reexport_unused_normalizer_helpers():
    """v1.3.1: src.phase4.report_agent is a pure consumer; metric-term / reality
    replacements live in src.phase4.report_normalizer and must NOT be re-exported
    by report_agent (they are only used by the legacy fallback path).
    _normalize_saved_markdown stays as a thin re-export because the clean
    save_markdown_report runs it on the explicit markdown argument.
    """
    for name in (
        "_replace_report_metric_terms",
        "_replace_reality_claims_about_inflection",
    ):
        assert not hasattr(report_agent, name), f"report_agent should not re-export {name}"


def test_extracted_metric_term_replacement_does_not_duplicate_prefixes():
    markdown = (
        "## 一、舆情概要\n\n"
        "模拟极化指数、极化指数、模拟关键变化点、拐点、模拟立场均值、情绪均值。"
    )

    normalized = _replace_report_metric_terms(markdown)

    assert "模拟模拟极化指数" not in normalized
    assert "模拟模拟关键变化点" not in normalized
    assert "模拟模拟立场均值" not in normalized
    assert normalized.count("模拟极化指数") == 2
    assert "模拟关键变化点" in normalized
    assert "模拟立场均值" in normalized


def test_normalizer_strips_prompt_instruction_leakage_without_removing_report_boundary():
    markdown = (
        "# 临时标题\n\n"
        "## 一、舆情概要\n\n"
        "【CODE_OWNED_REPORT_CONTRACT】\n"
        "risk_level_label: 高风险\n"
        "以上字段为代码侧结果，Markdown 必须逐字使用 risk_level_label 与 risk_type_labels，不得询问用户补充，不得自行改写。\n\n"
        "以下表格是 Markdown 报告中模拟关键变化点的唯一来源；不得新增其他模拟关键变化点。\n"
        "## 二、演化分析\n\n内容\n\n"
        "## 三、风险研判\n\nLLM 风险。\n\n"
        "## 四、对策建议\n\n内容\n\n"
        "## 五、附录\n\n"
        "- 风险等级和主要风险类型来自代码侧结果，正文只做解释性表达。"
    )

    normalized = _normalize_saved_markdown(markdown, _phase4_output())

    assert "CODE_OWNED_REPORT_CONTRACT" not in normalized
    assert "Markdown 必须" not in normalized
    assert "唯一来源" not in normalized
    assert "不得新增其他模拟关键变化点" not in normalized
    assert "风险等级和主要风险类型来自代码侧结果" in normalized


def test_normalizer_replaces_risk_section_and_keeps_metric_prefill_once():
    markdown = (
        "## 一、舆情概要\n\n内容\n\n"
        "## 二、演化分析\n\n内容\n\n"
        "## 三、风险研判\n\n风险等级：低风险\n\n"
        "## 四、对策建议\n\n内容\n\n"
        "## 五、附录\n\n### 指标说明\n\nLLM 自写指标。"
    )

    normalized = _normalize_saved_markdown(markdown, _phase4_output())

    assert _code_owned_risk_section(_phase4_output()) in normalized
    assert "风险等级：低风险" not in normalized
    assert normalized.count(METRIC_EXPLANATION_PREFILL) == 1
