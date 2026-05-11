"""Targeted Markdown grounding checks for v1.2.7 attempt-02."""

import ast
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.phase4 import report_agent
from src.phase4.report_agent import generate_fallback_report, save_markdown_report, save_report
from src.phase4.report_prompts import (
    FIVE_CHAPTER_HEADINGS,
    FORBIDDEN_REALITY_PHRASES,
    INTERNAL_CODE_OWNED_LABELS,
    NON_WHITELISTED_RISK_TYPE_EXAMPLES,
    POLICY_BOUNDARY_FORBIDDEN_PHRASES,
    RAW_METRIC_FIELD_NAMES,
    SIMULATION_DISCLAIMER,
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
    RISK_TYPE_LABELS,
    TickLog,
)
from src.whitebox.report_completeness import FINAL_SECTION_HEADINGS, REQUIRED_SECTION_GROUPS


def _extraction(summary="市监局介入的消费争议事件", entity_name="市监局") -> EntityExtractionOutput:
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
                original_statement="我们会核查处理，并按节点公开进展。",
            )
        ],
        opinion_spreaders=[
            OpinionSpreader(
                group_name="关注事实链群体",
                related_event_entity=entity_name,
                description="关注事实链是否完整",
                I=7.0,
                P=1,
                susceptibility=0.3,
                estimated_percentage=40,
                communication_style="理性追问",
                persona_name="小林",
                age_range="25-34",
                occupation="市民",
                personality="冷静",
                motivation="关注事实",
                typical_phrases=["先看证据", "节点要清楚"],
            ),
            OpinionSpreader(
                group_name="程序质疑群体",
                related_event_entity=entity_name,
                description="质疑回应节奏和程序透明度",
                I=3.0,
                P=-1,
                susceptibility=0.6,
                estimated_percentage=60,
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
            Relation(source=entity_name, target="程序质疑群体", type="舆论关联"),
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


def _tick(tick: int, polarization: float) -> TickLog:
    return TickLog(
        tick=tick,
        entries=[_entry(1, "程序质疑群体", 5.0, 4.0)],
        global_metrics=GlobalMetrics(
            mean_stance=4.8,
            std_stance=1.2,
            polarization_index=polarization,
        ),
    )


def _phase2_output(entity_name="市监局") -> Phase2Output:
    return Phase2Output(
        nodes=[
            GraphNode(
                id=1,
                group_name="程序质疑群体",
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


def _markdown(tmp_path: Path) -> str:
    extraction = _extraction()
    output = generate_fallback_report(
        extraction,
        [_tick(0, 0.2), _tick(1, 0.55)],
        [5.0, 4.8],
        phase2_output=_phase2_output(),
    )
    report_agent._llm_generated_markdown = ""
    md_path = tmp_path / "run_001" / "final_report.md"
    save_markdown_report(output, extraction, md_path)
    return md_path.read_text(encoding="utf-8")


def _output():
    extraction = _extraction()
    output = generate_fallback_report(
        extraction,
        [_tick(0, 0.2), _tick(1, 0.55)],
        [5.0, 4.8],
        phase2_output=_phase2_output(),
    )
    return extraction, output


def _risk_section(markdown: str) -> str:
    return markdown.split("## 三、风险研判", 1)[1].split("## 四、对策建议", 1)[0]


def test_markdown_contains_five_chapter_template_and_simulation_disclaimer(tmp_path):
    markdown = _markdown(tmp_path)

    for heading in FIVE_CHAPTER_HEADINGS:
        assert f"## {heading}" in markdown
    assert "## 核心结论" not in markdown
    assert SIMULATION_DISCLAIMER in markdown


def test_risk_section_is_structured(tmp_path):
    markdown = _markdown(tmp_path)

    risk_section = _risk_section(markdown)
    assert "风险等级：" in risk_section
    assert "主要风险类型：" in risk_section
    assert "风险解释：" in risk_section
    assert "监管责任质疑风险" in risk_section


def test_forbidden_phrases_and_raw_metric_fields_are_absent(tmp_path):
    markdown = _markdown(tmp_path)

    forbidden = list(FORBIDDEN_REALITY_PHRASES) + [
        "event_scale",
        "event_controversy",
        "polarization_index",
        "stance_delta",
        "risk_score",
    ]
    for phrase in forbidden:
        assert phrase not in markdown


def test_policy_boundary_phrases_are_absent(tmp_path):
    markdown = _markdown(tmp_path)

    for phrase in POLICY_BOUNDARY_FORBIDDEN_PHRASES:
        assert phrase not in markdown
    assert "替政府部门作行政决策" not in markdown
    assert "责任定性" not in markdown


def test_whitebox_section_constants_align_to_five_chapter_template():
    required = [group[0] for group in REQUIRED_SECTION_GROUPS]

    assert required == ["舆情概要", "演化分析", "风险研判", "对策建议", "附录"]
    assert "## 五、附录" in FINAL_SECTION_HEADINGS
    assert "### 五、附录" in FINAL_SECTION_HEADINGS
    assert all("综合建议" not in heading for heading in FINAL_SECTION_HEADINGS)
    assert all("应对建议" not in heading for heading in FINAL_SECTION_HEADINGS)


def test_report_prompts_module_is_static_only():
    prompt_path = PROJECT_ROOT / "src" / "phase4" / "report_prompts.py"
    tree = ast.parse(prompt_path.read_text(encoding="utf-8"))
    forbidden_nodes = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.Import,
        ast.ImportFrom,
        ast.Call,
    )

    assert not [
        node for node in ast.walk(tree)
        if isinstance(node, forbidden_nodes)
    ]


def test_generated_at_consistent_in_json_fallback_and_llm_paths(tmp_path):
    extraction, output = _output()

    json_path = tmp_path / "run_002" / "final_report.json"
    fallback_path = tmp_path / "run_002" / "fallback.md"
    llm_path = tmp_path / "run_002" / "llm.md"

    save_report(output, json_path)
    report_agent._llm_generated_markdown = ""
    save_markdown_report(output, extraction, fallback_path)
    report_agent._llm_generated_markdown = "# LLM 报告\n\n" + ("模拟内容" * 80)
    save_markdown_report(output, extraction, llm_path)
    report_agent._llm_generated_markdown = ""

    data = json.loads(json_path.read_text(encoding="utf-8"))
    generated_at = data["report_meta"]["generated_at"]
    assert f"生成时间：{generated_at}" in fallback_path.read_text(encoding="utf-8")
    assert f"生成时间：{generated_at}" in llm_path.read_text(encoding="utf-8")


def test_saved_markdown_header_and_body_risk_level_are_code_owned(tmp_path):
    extraction, output = _output()
    path = tmp_path / "run_003" / "final_report.md"

    report_agent._llm_generated_markdown = (
        "# LLM 报告\n\n"
        "## 三、风险研判\n\n"
        "风险等级：中等偏高\n\n"
        "主要风险类型：\n"
        "1. 品牌声誉风险\n"
        "2. 舆论极化风险\n\n"
        "风险解释：这是 LLM 自行生成的风险段。\n\n"
        "## 四、对策建议\n\n"
        "补齐事实链。\n"
    )
    save_markdown_report(output, extraction, path)
    report_agent._llm_generated_markdown = ""

    markdown = path.read_text(encoding="utf-8")
    risk_section = _risk_section(markdown)
    assert f"风险等级：{output.risk_level_label}" in markdown.splitlines()[:8]
    assert f"风险等级：{output.risk_level_label}" in risk_section
    assert "中等偏高" not in risk_section


def test_fallback_markdown_header_and_body_risk_level_are_code_owned(tmp_path):
    extraction, output = _output()
    path = tmp_path / "run_003_fallback" / "final_report.md"

    report_agent._llm_generated_markdown = ""
    save_markdown_report(output, extraction, path)

    markdown = path.read_text(encoding="utf-8")
    risk_section = _risk_section(markdown)
    assert f"风险等级：{output.risk_level_label}" in markdown.splitlines()[:8]
    assert f"风险等级：{output.risk_level_label}" in risk_section


def test_saved_markdown_risk_types_are_code_owned(tmp_path):
    extraction, output = _output()
    path = tmp_path / "run_004" / "final_report.md"

    report_agent._llm_generated_markdown = (
        "# LLM 报告\n\n"
        "## 三、风险研判\n\n"
        "风险等级：中等偏高\n\n"
        "主要风险类型：\n"
        "1. 品牌声誉风险\n"
        "2. 舆论极化风险\n"
        "3. 衍生争议风险\n\n"
        "风险解释：品牌声誉、舆论分化和衍生讨论可能存在，但不应作为标签。\n\n"
        "## 四、对策建议\n\n"
        "补齐事实链。\n"
    )
    save_markdown_report(output, extraction, path)
    report_agent._llm_generated_markdown = ""

    risk_section = _risk_section(path.read_text(encoding="utf-8"))
    risk_type_block = risk_section.split("主要风险类型：", 1)[1].split("风险解释：", 1)[0]
    for risk_type in output.risk_type_labels:
        assert risk_type in risk_type_block
        assert risk_type in RISK_TYPE_LABELS.values()
    for risk_type in NON_WHITELISTED_RISK_TYPE_EXAMPLES:
        assert risk_type not in risk_type_block


def test_llm_saved_markdown_hides_internal_labels_and_raw_metric_fields(tmp_path):
    extraction, output = _output()
    path = tmp_path / "run_005" / "final_report.md"

    report_agent._llm_generated_markdown = (
        "# LLM 报告\n\n"
        "## 二、演化分析\n\n"
        "【CODE_OWNED_AGENT_STANCE_MATRIX】\n"
        "event_scale、event_controversy、polarization_index、stance_delta、risk_score。\n"
        "【CODE_OWNED_INFLECTION_POINTS】\n\n"
        "## 三、风险研判\n\n"
        "风险等级：中等偏高\n\n"
        "主要风险类型：\n1. 品牌声誉风险\n\n"
        "风险解释：模拟讨论可能影响品牌声誉。\n\n"
        "## 四、对策建议\n\n"
        "补齐事实链。\n"
    )
    save_markdown_report(output, extraction, path)
    report_agent._llm_generated_markdown = ""

    markdown = path.read_text(encoding="utf-8")
    for label in INTERNAL_CODE_OWNED_LABELS:
        assert label not in markdown
    for field_name in RAW_METRIC_FIELD_NAMES:
        assert field_name not in markdown
