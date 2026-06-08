"""
Phase 4: 宏观洞察生成器
---
根据 Phase 3 的模拟结果，生成舆情演化洞察报告。

本模块是 simulation_dataset 的纯消费者（v1.3.1）：
- 只暴露 5 个 consumer symbols
- 所有 risk/inflection/stance/audience 决策都从 simulation_dataset 读取
- 不再自行重算、不再走 LLM fallback、不再走 generate_markdown_report
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List

from rich.console import Console

import config
from src.schemas import (
    EntityExtractionOutput,
    Phase4Output,
    EmotionTrajectory,
    InflectionPoint,
    ReportMeta,
    RiskLevel,
    REPORT_TYPE,
    RISK_LEVEL_LABELS,
    RISK_TYPE_LABELS,
)
from .report_normalizer import (
    _has_required_five_chapter_sections,
    _normalize_saved_markdown,
)

console = Console()


def _generate_report_timestamp(now: datetime = None) -> str:
    """Generate code-owned report timestamp."""
    current = now or datetime.now().astimezone()
    return current.strftime("%Y年%m月%d日 %H:%M")


def _current_timezone_label(now: datetime = None) -> str:
    current = now or datetime.now().astimezone()
    if current.tzinfo is None:
        return "local"
    return current.tzname() or str(current.utcoffset()) or "local"


def _infer_simulation_run_id(output_path: Path = None) -> str:
    if output_path is None:
        return "unknown"
    parent_name = Path(output_path).parent.name
    return parent_name or "unknown"


def _risk_type_labels(primary_risk_types: List[str]) -> List[str]:
    return [RISK_TYPE_LABELS[risk_type] for risk_type in primary_risk_types]


def _risk_level_label_for(risk_level: RiskLevel) -> str:
    return RISK_LEVEL_LABELS[risk_level.value]


def build_report_meta(
    dataset: dict,
    output_path: Path = None,
    generated_at: str = None,
) -> ReportMeta:
    run_info = dataset.get("run_info", {})
    source = dataset.get("source_context", {})
    return ReportMeta(
        generated_at=generated_at or _generate_report_timestamp(),
        timezone=_current_timezone_label(),
        report_type=REPORT_TYPE,
        event_name=source.get("event_summary", ""),
        total_ticks=run_info.get("total_ticks", 0),
        simulation_run_id=_infer_simulation_run_id(output_path),
    )


def _align_report_meta_to_output_path(phase4_output: Phase4Output, output_path: Path = None) -> Phase4Output:
    run_id = _infer_simulation_run_id(output_path)
    if run_id != "unknown":
        phase4_output.report_meta.simulation_run_id = run_id
    return phase4_output


def _scale_description(value: float) -> str:
    if value >= 0.75:
        return "模拟影响范围较广，相关讨论可能跨越单一群体扩散。"
    if value >= 0.45:
        return "模拟影响范围处于中等水平，讨论可能集中在主要相关群体之间。"
    return "模拟影响范围相对有限，讨论更可能停留在直接相关群体内部。"


def _controversy_description(value: float) -> str:
    if value >= 0.75:
        return "争议强度较高，事实认知和处置程序容易成为持续追问点。"
    if value >= 0.45:
        return "争议强度中等，后续回应节奏会影响讨论是否继续升温。"
    return "争议强度相对可控，讨论更依赖后续信息补充。"


def _build_phase4_output_from_simulation_dataset(
    dataset: dict,
) -> Phase4Output:
    sim = dataset.get("simulation_result", {})
    source = dataset.get("source_context", {})

    risk_verdict = sim.get("risk_verdict", {})
    risk_level_str = risk_verdict.get("level", RiskLevel.LOW.value)
    risk_level = RiskLevel(risk_level_str)
    risk_assessment = risk_verdict.get("basis_text", "")

    inflection_points = [
        InflectionPoint(
            tick=point.get("tick", 0),
            agent_id=point.get("agent_id", 0),
            group_name=point.get("group_name", "未知"),
            pivotal_comment=point.get("pivotal_comment", point.get("comment", "")),
            impact_description=point.get(
                "impact_description",
                point.get("description", ""),
            ),
        )
        for point in sim.get("inflection_points", [])
    ]

    emotion_trajectory = [
        EmotionTrajectory(
            tick=item.get("tick", 0),
            mean_stance=item.get("mean_stance", 5.0),
            std_stance=item.get("std_stance", 0.0),
            polarization_index=item.get("polarization_index", 0.0),
            key_event=item.get("key_event", ""),
        )
        for item in sim.get("emotion_trajectory", [])
    ]

    risk_type_classification = sim.get("risk_type_classification", {})
    primary_risk_types = risk_type_classification.get("primary_types", []) or [
        "negative_narrative_risk"
    ]
    risk_type_labels = risk_type_classification.get("type_labels", []) or _risk_type_labels(
        primary_risk_types
    )

    from src.schemas import AudienceMode
    audience_mode_str = dataset.get("run_info", {}).get(
        "audience_mode",
        AudienceMode.GENERIC_GOVERNMENT.value,
    )
    audience_mode = AudienceMode(audience_mode_str)

    event_entities = source.get("event_entities", [])
    opinion_spreaders = source.get("opinion_spreaders", [])
    event_entities_str = ", ".join(e.get("name", "?") for e in event_entities)
    spreaders_str = ", ".join(s.get("group_name", "?") for s in opinion_spreaders)
    stakeholder_map = f"事件实体: {event_entities_str} | 传播者: {spreaders_str}"

    x_t_sequence = sim.get("x_t_sequence", [])

    return Phase4Output(
        report_meta=build_report_meta(dataset),
        event_summary=source.get("event_summary", ""),
        stakeholder_map=stakeholder_map,
        emotion_trajectory=emotion_trajectory,
        inflection_points=inflection_points,
        risk_level=risk_level,
        risk_level_label=_risk_level_label_for(risk_level),
        audience_mode=audience_mode,
        primary_risk_types=primary_risk_types,
        risk_type_labels=risk_type_labels,
        risk_assessment=risk_assessment,
        x_t_sequence=x_t_sequence,
        agent_stance_matrix=sim.get("agent_stance_matrix"),
    )


def parse_llm_report_response(
    response: str,
    simulation_dataset: dict,
) -> Phase4Output:
    """解析 LLM 报告响应（v1.3.1：纯消费 simulation_dataset）。

    不再走 fallback 路径；response 字段当前不被消费（保留入参兼容调用方）。
    """
    del response  # 兼容旧调用方；不再用于分支
    return _build_phase4_output_from_simulation_dataset(
        simulation_dataset,
    )


def _build_code_owned_report_contract_block(
    simulation_dataset: dict,
) -> str:
    """构建 code-owned report contract block（v1.3.1：纯消费 simulation_dataset）。"""
    sim = simulation_dataset.get("simulation_result", {})
    risk_verdict = sim.get("risk_verdict", {})
    risk_type_classification = sim.get("risk_type_classification", {})
    risk_level = RiskLevel(risk_verdict.get("level", RiskLevel.LOW.value))
    risk_assessment = risk_verdict.get("basis_text", "")
    from src.schemas import AudienceMode
    audience_mode = AudienceMode(
        simulation_dataset.get("run_info", {}).get(
            "audience_mode",
            AudienceMode.GENERIC_GOVERNMENT.value,
        )
    )
    primary_risk_types = risk_type_classification.get("primary_types", []) or [
        "negative_narrative_risk"
    ]
    risk_type_labels = risk_type_classification.get("type_labels", []) or _risk_type_labels(
        primary_risk_types
    )
    return "\n".join([
        "【CODE_OWNED_REPORT_CONTRACT】",
        f"risk_level_label: {_risk_level_label_for(risk_level)}",
        f"risk_type_labels: {'、'.join(risk_type_labels) if risk_type_labels else '负面叙事聚合风险'}",
        f"audience_mode: {audience_mode.value}",
        f"primary_risk_types: {', '.join(primary_risk_types) if primary_risk_types else 'negative_narrative_risk'}",
        f"risk_assessment: {risk_assessment}",
        "以上字段为代码侧结果，Markdown 必须逐字使用 risk_level_label 与 risk_type_labels，不得询问用户补充，不得自行改写。",
    ])


def save_report(phase4_output: Phase4Output, output_path: Path = None):
    """保存报告

    Args:
        phase4_output: Phase4 输出
        output_path: 输出路径，默认使用 config.FINAL_REPORT_PATH.with_suffix(".json")
    """
    output_path = output_path or config.FINAL_REPORT_PATH.with_suffix(".json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    phase4_output = _align_report_meta_to_output_path(phase4_output, output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(phase4_output.model_dump(), f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/green] JSON 报告已保存至: {output_path}")


def save_markdown_report(
    phase4_output: Phase4Output,
    output_path: Path = None,
    *,
    markdown: str,
):
    """保存 Markdown 格式报告（v1.3.1：必须显式传入 markdown）。

    Args:
        phase4_output: Phase4 输出
        extraction_output: 实体提取结果
        output_path: 输出路径，默认使用 config.FINAL_REPORT_PATH.with_suffix(".md")
        markdown: 已渲染的 Markdown 内容（必填，由调用方从 LLM 输出解析得到）
    """
    if markdown is None or len(markdown) < 100:
        raise ValueError("save_markdown_report requires explicit markdown content")

    md_path = output_path or config.FINAL_REPORT_PATH.with_suffix(".md")
    phase4_output = _align_report_meta_to_output_path(phase4_output, md_path)

    md_content = _normalize_saved_markdown(markdown, phase4_output)
    if not _has_required_five_chapter_sections(md_content):
        # 兜底：若 LLM 输出缺失五大章节，使用原 markdown 重新走一次 normalize 后保存
        md_content = _normalize_saved_markdown(markdown, phase4_output)

    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    console.print(f"[green]✓[/green] Markdown 报告已保存至: {md_path}")
