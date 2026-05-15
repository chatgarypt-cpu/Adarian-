"""Targeted Markdown grounding checks for v1.2.8 attempt-01."""

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
    ENTERPRISE_PR_FORBIDDEN_PHRASES,
    DATA_TO_JUDGMENT_RULES,
    ELABORATION_CHAIN_RULES,
    EVOLUTION_STAGE_NARRATIVE_RULES,
    EVOLUTION_SECTION_EXPANSION_RULES,
    FIVE_CHAPTER_HEADINGS,
    FORBIDDEN_REALITY_PHRASES,
    GOVERNANCE_RECOMMENDATION_DEPTH_RULES,
    GOVERNANCE_RECOMMENDATION_RULES,
    GOVERNMENT_ACTOR_PRESSURE_RULES,
    GOVERNMENT_FACING_PERSPECTIVE_RULES,
    H1_HYGIENE_RULES,
    INTERNAL_CODE_OWNED_LABELS,
    KEY_INSIGHT_RULES,
    MAIN_BODY_LENGTH_BUDGET_RULES,
    METRIC_BUSINESS_LABEL_MAP,
    METRIC_BUSINESS_LABEL_RULES,
    METRIC_EXPLANATION_PREFILL,
    NON_WHITELISTED_RISK_TYPE_EXAMPLES,
    POLICY_BOUNDARY_FORBIDDEN_PHRASES,
    QUOTE_FABRICATION_PATTERNS,
    QUOTE_FABRICATION_RULES,
    RAW_METRIC_FIELD_NAMES,
    REPORT_RULE_PRIORITY,
    REPORT_SUMMARY_NARRATIVE_RULES,
    REPORT_SYSTEM_PROMPT,
    REPORT_TITLE_RULES,
    RISK_CONFLICT_ANALYSIS_RULES,
    RISK_ANALYSIS_EXPANSION_RULES,
    SECTION_LEVEL_FEWSHOT_EVOLUTION,
    SECTION_LEVEL_FEWSHOT_RISK_ANALYSIS,
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


def _assert_five_chapters(markdown: str):
    for heading in FIVE_CHAPTER_HEADINGS:
        assert f"## {heading}" in markdown


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


def test_v128_prompt_assets_exist_and_metric_label_map_is_complete():
    required_assets = [
        REPORT_RULE_PRIORITY,
        GOVERNMENT_FACING_PERSPECTIVE_RULES,
        GOVERNMENT_ACTOR_PRESSURE_RULES,
        REPORT_TITLE_RULES,
        REPORT_SUMMARY_NARRATIVE_RULES,
        EVOLUTION_STAGE_NARRATIVE_RULES,
        RISK_ANALYSIS_EXPANSION_RULES,
        GOVERNANCE_RECOMMENDATION_RULES,
        METRIC_BUSINESS_LABEL_RULES,
        MAIN_BODY_LENGTH_BUDGET_RULES,
        METRIC_EXPLANATION_PREFILL,
        DATA_TO_JUDGMENT_RULES,
        ELABORATION_CHAIN_RULES,
        EVOLUTION_SECTION_EXPANSION_RULES,
        KEY_INSIGHT_RULES,
        RISK_CONFLICT_ANALYSIS_RULES,
        GOVERNANCE_RECOMMENDATION_DEPTH_RULES,
        H1_HYGIENE_RULES,
        QUOTE_FABRICATION_RULES,
        SECTION_LEVEL_FEWSHOT_EVOLUTION,
        SECTION_LEVEL_FEWSHOT_RISK_ANALYSIS,
    ]

    assert all(asset for asset in required_assets)
    assert METRIC_BUSINESS_LABEL_MAP["event_scale"]["0.0-0.3"] == "区域性热点事件"
    assert METRIC_BUSINESS_LABEL_MAP["event_scale"]["0.3-0.7"] == "全国性舆情事件"
    assert METRIC_BUSINESS_LABEL_MAP["event_scale"]["0.7-1.0"] == "全国重大舆情事件"
    assert METRIC_BUSINESS_LABEL_MAP["event_controversy"]["0.3-0.7"] == "中等争议"
    assert METRIC_BUSINESS_LABEL_MAP["polarization_index"]["0.7-1.0"] == "高冲突 / 高分化"
    assert METRIC_BUSINESS_LABEL_MAP["stance_delta"]["0.2-0.5"] == "显著立场迁移"


def test_patch02_prompt_rules_are_in_system_prompt():
    required_fragments = [
        "【主体正文篇幅预算】",
        "3500-4500 中文字",
        "【数据转判断规则】",
        "数据只能作为判断依据",
        "【展开链规则】",
        "判断 → 依据 → 机制 → 治理含义 → 观察信号",
        "【关键洞察规则】",
        "【矛盾焦点与风险展开规则】",
        "【对策建议四要素规则】",
        "【H1 标题卫生规则】",
    ]

    for fragment in required_fragments:
        assert fragment in REPORT_SYSTEM_PROMPT


def test_report_prompt_priority_places_t0_t1_before_quality_rules():
    for tier in ("T0", "T1", "T2", "T3"):
        assert tier in REPORT_RULE_PRIORITY

    priority_index = REPORT_SYSTEM_PROMPT.index("【规则优先级】")
    disclaimer_index = REPORT_SYSTEM_PROMPT.index(SIMULATION_DISCLAIMER)
    title_index = REPORT_SYSTEM_PROMPT.index("【标题规则】")
    fewshot_index = REPORT_SYSTEM_PROMPT.index("【演化分析参考写法")

    assert priority_index < disclaimer_index < title_index < fewshot_index
    assert REPORT_SYSTEM_PROMPT.index("T0") < REPORT_SYSTEM_PROMPT.index("T2")
    assert REPORT_SYSTEM_PROMPT.index("T1") < REPORT_SYSTEM_PROMPT.index("T3")


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
        "【CODE_OWNED_REPORT_CONTRACT】\n"
        "risk_level_label: 高风险\n"
        "risk_type_labels: 品牌声誉风险\n\n"
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
    assert "risk_level_label:" not in markdown
    assert "risk_type_labels:" not in markdown
    for field_name in RAW_METRIC_FIELD_NAMES:
        assert field_name not in markdown


def test_saved_markdown_removes_enterprise_pr_phrases_and_fabricated_quotes(tmp_path):
    extraction, output = _output()
    path = tmp_path / "run_006" / "final_report.md"

    report_agent._llm_generated_markdown = (
        "# OPPO品牌在母亲节发布争议海报引发多方讨论舆情风险研判报告\n\n"
        "报告类型：模拟推演型舆情风险研判报告\n"
        f"生成时间：{output.report_meta.generated_at}\n\n"
        "## 一、舆情概要\n\n"
        "有网民表示：这是需要危机公关的事件，贵司应重视。\n\n"
        "## 二、演化分析\n\n"
        "待评估。\n\n"
        "## 三、风险研判\n\n"
        "风险等级：中等偏高\n\n"
        "主要风险类型：\n1. 品牌声誉风险\n\n"
        "风险解释：品牌修复压力较高。\n\n"
        "## 四、对策建议\n\n"
        "建议OPPO说明情况。建议品牌方开展舆情洗白。建议企业做好形象修复。贵校也应参考。\n\n"
        "## 五、附录\n\n"
        "event_scale risk_score\n"
    )
    save_markdown_report(output, extraction, path)
    report_agent._llm_generated_markdown = ""

    markdown = path.read_text(encoding="utf-8")
    for phrase in ENTERPRISE_PR_FORBIDDEN_PHRASES:
        assert phrase not in markdown
    for pattern in QUOTE_FABRICATION_PATTERNS:
        assert pattern not in markdown
    for field_name in RAW_METRIC_FIELD_NAMES:
        assert field_name not in markdown
    assert "待评估" not in markdown
    assert "本轮模拟未发现显著模拟关键变化点" in markdown
    assert "结构性风险点一" in markdown
    assert "结构性风险点二" in markdown


def test_incomplete_llm_markdown_rebuilds_to_five_chapter_fallback(tmp_path):
    extraction, output = _output()
    path = tmp_path / "run_007" / "final_report.md"

    report_agent._llm_generated_markdown = (
        "# 残缺 LLM 报告\n\n"
        "## 三、风险研判\n\n"
        "风险等级：中等偏高\n\n"
        "主要风险类型：\n1. 品牌声誉风险\n\n"
        "风险解释：event_scale、event_controversy、polarization_index、stance_delta、risk_score。"
        "建议OPPO开展危机公关。有网民表示：待评估。\n\n"
    )
    save_markdown_report(output, extraction, path)
    report_agent._llm_generated_markdown = ""

    markdown = path.read_text(encoding="utf-8")
    _assert_five_chapters(markdown)
    assert "中等偏高" not in _risk_section(markdown)
    assert f"风险等级：{output.risk_level_label}" in _risk_section(markdown)
    for risk_type in output.risk_type_labels:
        assert risk_type in _risk_section(markdown)
    for phrase in list(RAW_METRIC_FIELD_NAMES) + ["建议OPPO", "建议品牌方", "建议品牌", "建议企业", "有网民表示：", "据网友反映：", "待评估"]:
        assert phrase not in markdown


def test_question_style_llm_markdown_rebuilds_to_five_chapter_fallback(tmp_path):
    extraction, output = _output()
    path = tmp_path / "run_008" / "final_report.md"

    report_agent._llm_generated_markdown = (
        "我注意到输入数据中缺少 risk_level_label 和 risk_type_labels 这两个关键字段。"
        "请补充 risk_level_label / risk_type_labels 后再生成报告。"
        "当前不能自行发明风险等级和主要风险类型，因此无法输出完整报告。"
    )
    save_markdown_report(output, extraction, path)
    report_agent._llm_generated_markdown = ""

    markdown = path.read_text(encoding="utf-8")
    _assert_five_chapters(markdown)
    assert "请补充 risk_level_label" not in markdown
    assert "无法输出完整报告" not in markdown
    assert f"风险等级：{output.risk_level_label}" in markdown
    for risk_type in output.risk_type_labels:
        assert risk_type in markdown


def test_complete_five_chapter_llm_markdown_is_not_unconditionally_replaced(tmp_path):
    extraction, output = _output()
    path = tmp_path / "run_009" / "final_report.md"

    report_agent._llm_generated_markdown = (
        "# LLM 完整报告\n\n"
        "## 一、舆情概要\n\n"
        "LLM_UNIQUE_SUMMARY_MARKER\n\n"
        "## 二、演化分析\n\n"
        "第一阶段：争议触发期。\n\n第二阶段：群体分化期。\n\n"
        "## 三、风险研判\n\n"
        f"风险等级：{output.risk_level_label}\n\n"
        "主要风险类型：\n"
        + "\n".join(f"{index}. {label}" for index, label in enumerate(output.risk_type_labels, start=1))
        + "\n\n风险解释：LLM 风险解释。\n\n"
        "## 四、对策建议\n\n"
        "LLM_UNIQUE_RECOMMENDATION_MARKER\n\n"
        "## 五、附录\n\n"
        "LLM_UNIQUE_APPENDIX_MARKER\n"
    )
    save_markdown_report(output, extraction, path)
    report_agent._llm_generated_markdown = ""

    markdown = path.read_text(encoding="utf-8")
    _assert_five_chapters(markdown)
    assert "LLM_UNIQUE_SUMMARY_MARKER" in markdown
    assert "LLM_UNIQUE_RECOMMENDATION_MARKER" in markdown
    assert "LLM_UNIQUE_APPENDIX_MARKER" in markdown
