"""LLM narrative generation and prompt context assembly for Phase 4."""

from typing import Any, Callable, List, Optional, Tuple

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


def build_report_context_new(
    extraction_output, tick_logs, x_t_sequence, phase2_output, dataset,
) -> str:
    """Build the LLM report context using Phase3 parser data (v1.3.1 flow)."""
    sim = dataset["simulation_result"]
    rv = sim.get("risk_verdict", {})
    rt = sim.get("risk_type_classification", {})
    matrix = sim.get("agent_stance_matrix", [])
    inflection_points = sim.get("inflection_points", [])
    emotion_trajectory = sim.get("emotion_trajectory", [])

    lines = []

    # 1. 事件概要
    lines.append("【事件概要】")
    lines.append(f"事件摘要：{extraction_output.event_summary}")
    lines.append(f"事件类型：{extraction_output.event_type}")

    # 2. 实体图谱
    lines.append("\n【实体图谱】")
    lines.append(f"事件实体：{len(extraction_output.event_entities)} 个")
    for entity in extraction_output.event_entities:
        lines.append(f"  - {entity.name}（{entity.type}）: {entity.role} | can_speak={entity.can_speak}")
        if entity.original_statement:
            lines.append(f"    原始发言：{entity.original_statement[:50]}...")
    lines.append(f"\n意见传播者：{len(extraction_output.opinion_spreaders)} 个")
    for s in extraction_output.opinion_spreaders:
        lines.append(f"  - {s.group_name} | 关联实体：{s.related_event_entity}，立场：{s.stance_score}，占比：{s.estimated_percentage}%")

    # 3. 轮次 0 发言
    lines.append("\n【轮次 0 事件实体发言】")
    if tick_logs:
        for entry in tick_logs[0].entries:
            if entry.comment:
                lines.append(f"  [{entry.group_name}]: {entry.comment[:80]}...")

    # 4. 模拟立场演化（从 Phase3 parser 输出的 emotion_trajectory）
    lines.append("\n【模拟立场演化数据】")
    lines.append("轮次 | 模拟立场均值 | 标准差 | 模拟极化指数 | 关键变化")
    lines.append("-" * 70)
    prev_pol = None
    for et in emotion_trajectory:
        key_event = et.get("key_event", "")
        lines.append(f"| {et['tick']} | {et['mean_stance']:.2f} | {et['std_stance']:.2f} | {et['polarization_index']:.2f} | {key_event} |")
        prev_pol = et.get("polarization_index")

    # 5. 立场矩阵（从 Phase3 parser 输出）
    lines.append("\n【立场矩阵】")
    if not matrix:
        lines.append("无可用 opinion spreader 立场矩阵。")
    else:
        lines.append("以下表格是 Markdown 报告中最终立场变化的唯一数值来源；不得重算。")
        lines.append("| Agent | 群体 | 起始立场 | 结束立场 | Delta |")
        lines.append("|---|---:|---:|---:|---:|")
        for row in matrix:
            lines.append(f"| #{row['agent_id']} | {row['group_name']} | {row['initial_stance']:.2f} | {row['final_stance']:.2f} | {row.get('max_delta', row['final_stance'] - row['initial_stance']):+.2f} |")

    # 6. 拐点（从 Phase3 parser 输出）
    lines.append("\n【模拟关键变化点】")
    if not inflection_points:
        lines.append("本轮模拟未发现显著模拟关键变化点。")
        lines.append("Markdown 报告不得声称存在模拟关键变化点，不得使用其他阈值自行识别模拟关键变化点。")
    else:
        lines.append("以下表格是 Markdown 报告中模拟关键变化点的唯一来源；不得新增其他模拟关键变化点。")
        lines.append("| 轮次 | Agent | 群体 | 影响 |")
        lines.append("|---:|---:|---|---|")
        for p in inflection_points:
            lines.append(f"| {p.get('tick', '')} | {p.get('agent_id', '')} | {p.get('group_name', '')} | {p.get('description', '')} |")

    # 7. 风险判定（从 Phase3 parser 输出的 risk_verdict）
    lines.append("\n【风险判定】（由 Phase3 RiskAnalyzer 计算）")
    lines.append(f"风险等级: {rv.get('level', 'unknown')}")
    lines.append(f"风险标签: {rv.get('label', '')}")
    lines.append(f"风险依据: {rv.get('basis_text', '')}")

    # 8. 最终风险类型
    if rt:
        lines.append("\n【风险类型分类】")
        for t, l in zip(rt.get("primary_types", []), rt.get("type_labels", [])):
            lines.append(f"  - {l}（{t}）")

    # 9. x(t) 序列
    lines.append(f"\n【x(t) 序列】{' → '.join(f'{x:.2f}' for x in x_t_sequence)}")
    if x_t_sequence:
        lines.append(f"起始 x(0): {x_t_sequence[0]:.2f} → 最终 x(t): {x_t_sequence[-1]:.2f}")

    # 10. 信号详情
    signals = rv.get("signals", {})
    if signals:
        lines.append("\n【风险信号详情】")
        for k, v in signals.items():
            lines.append(f"  {k}: {v}")

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
    build_code_owned_contract_block: Callable[..., str],
    parse_llm_report_response: Callable[..., Phase4Output],
    get_llm_client_func: Callable[[], object] = get_llm_client,
    simulation_dataset: Optional[dict[str, Any]] = None,
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
        simulation_dataset=simulation_dataset,
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
        simulation_dataset=simulation_dataset,
    )
    return phase4_output, response
