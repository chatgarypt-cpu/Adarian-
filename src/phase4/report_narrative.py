"""LLM narrative generation and prompt context assembly for Phase 4."""

from typing import Callable, List, Tuple

from rich.console import Console

from src.llm_client import get_llm_client
from src.schemas import EntityExtractionOutput, InflectionPoint, Phase2Output, Phase4Output, TickLog
from .report_prompts import REPORT_SYSTEM_PROMPT, REPORT_USER_PROMPT_SUFFIX


console = Console()


def build_full_report_context(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
    *,
    format_agent_stance_matrix: Callable[[List[TickLog]], List[str]],
    identify_inflection_points: Callable[[List[TickLog], Phase2Output], List[InflectionPoint]],
    format_inflection_points: Callable[[List[InflectionPoint]], List[str]],
) -> str:
    """Build the report context string without changing prompt semantics."""
    lines = []

    # 1. 事件概要
    lines.append("【事件概要】")
    lines.append(f"事件摘要：{extraction_output.event_summary}")
    lines.append(f"事件类型：{extraction_output.event_type}")

    # 2. 实体图谱
    lines.append("\n【实体图谱】")
    lines.append(f"事件实体（直接参与者）：{len(extraction_output.event_entities)} 个")
    for entity in extraction_output.event_entities:
        lines.append(f"  - {entity.name}（{entity.type}）: {entity.role} | can_speak={entity.can_speak}")
        if entity.original_statement:
            lines.append(f"    原始发言：{entity.original_statement[:50]}...")

    lines.append(f"\n意见传播者（评论者）：{len(extraction_output.opinion_spreaders)} 个")
    for spreader in extraction_output.opinion_spreaders:
        lines.append(f"  - {spreader.group_name}")
        lines.append(f"    关联实体：{spreader.related_event_entity}，立场：{spreader.stance_score}，偏差：{spreader.confirmation_bias_level}，占比：{spreader.estimated_percentage}%")

    # 3. 轮次 0 发言
    lines.append("\n【轮次 0 事件实体发言】")
    tick_0_log = tick_logs[0] if tick_logs else None
    if tick_0_log:
        for entry in tick_0_log.entries:
            if entry.comment:
                lines.append(f"  [{entry.group_name}]: {entry.comment[:80]}...")

    # 4. 模拟立场演化数据
    lines.append("\n【模拟立场演化数据】")
    lines.append("轮次 | 模拟立场均值 | 标准差 | 模拟极化指数 | 关键变化")
    lines.append("-" * 70)
    prev_pol = None
    for log in tick_logs:
        if not log.entries:
            continue
        max_entry = max(log.entries, key=lambda e: abs(e.stance_delta))
        pol = log.global_metrics.polarization_index
        pol_change = ""
        if prev_pol is not None:
            pol_change = f"({pol - prev_pol:+.2f})"
        lines.append(f"{log.tick:4d} | {log.global_metrics.mean_stance:5.2f} | {log.global_metrics.std_stance:5.2f} | {pol:5.2f} {pol_change:8s} | #{max_entry.agent_id} {max_entry.group_name[:10]}: {max_entry.stance_delta:+.1f}")
        prev_pol = pol

    # 5. 模拟极化演化轨迹
    lines.append("\n【模拟极化演化轨迹】")
    pol_sequence = [f"{log.global_metrics.polarization_index:.2f}" for log in tick_logs if log.entries]
    lines.append(" → ".join(pol_sequence))
    if len(pol_sequence) >= 2:
        first_pol = float(pol_sequence[0])
        last_pol = float(pol_sequence[-1])
        change_pct = (last_pol - first_pol) / first_pol * 100 if first_pol > 0 else 0
        direction = "下降" if change_pct < 0 else "上升"
        lines.append(f"模拟极化指数从 {pol_sequence[0]} 变化到 {pol_sequence[-1]}，{direction} {abs(change_pct):.0f}%")

    # 6. code-owned grounding blocks
    lines.append("\n【CODE_OWNED_AGENT_STANCE_MATRIX】")
    lines.extend(format_agent_stance_matrix(tick_logs))

    lines.append("\n【CODE_OWNED_INFLECTION_POINTS】")
    inflection_points = identify_inflection_points(tick_logs, phase2_output) if phase2_output else []
    lines.extend(format_inflection_points(inflection_points))

    # 7. 模拟立场均值序列
    lines.append(f"\n【模拟立场均值序列】：{' → '.join([f'{x:.2f}' for x in x_t_sequence])}")

    return "\n".join(lines)


def build_report_user_prompt(code_owned_contract_block: str, report_context: str) -> str:
    return f"""请根据以下数据生成舆情风险研判报告：

{code_owned_contract_block}

{report_context}

{REPORT_USER_PROMPT_SUFFIX}"""


def generate_report_with_llm_narrative(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output,
    *,
    build_report_context: Callable[..., str],
    build_code_owned_contract_block: Callable[[EntityExtractionOutput, List[TickLog], List[float]], str],
    parse_llm_report_response: Callable[..., Phase4Output],
    get_llm_client_func: Callable[[], object] = get_llm_client,
) -> Tuple[Phase4Output, str]:
    """Run the LLM narrative path and return both parsed output and raw Markdown."""
    llm = get_llm_client_func()

    report_context = build_report_context(
        extraction_output,
        tick_logs,
        x_t_sequence,
        phase2_output=phase2_output,
    )
    code_owned_contract_block = build_code_owned_contract_block(
        extraction_output,
        tick_logs,
        x_t_sequence,
    )
    user_prompt = build_report_user_prompt(code_owned_contract_block, report_context)

    console.print("[cyan]正在调用 LLM 生成报告...[/cyan]")

    response = llm.generate(
        system=REPORT_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,
    )

    phase4_output = parse_llm_report_response(
        response,
        extraction_output,
        tick_logs,
        x_t_sequence,
        phase2_output=phase2_output,
    )
    return phase4_output, response
