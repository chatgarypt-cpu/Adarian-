"""LLM narrative generation and prompt context assembly for Phase 4."""

from typing import Callable, Tuple

from rich.console import Console

from src.llm_client import get_llm_client
from src.schemas import Phase4Output
from .report_prompts import REPORT_SYSTEM_PROMPT, REPORT_USER_PROMPT_SUFFIX
from .report_agent import _build_report_contract_block, parse_llm_report_response


console = Console()


def build_report_context_new(dataset: dict) -> str:
    """Build the LLM report context entirely from simulation_dataset. No external parameters needed."""
    sim = dataset.get("simulation_result", {})
    source = dataset.get("source_context", {})
    run_info = dataset.get("run_info", {})
    rv = sim.get("risk_verdict", {})
    rt = sim.get("risk_type_classification", {})
    matrix = sim.get("agent_stance_matrix", [])
    inflection_points = sim.get("inflection_points", [])
    emotion_trajectory = sim.get("emotion_trajectory", [])
    x_t_sequence = sim.get("x_t_sequence", [])
    tick_entries = sim.get("tick_entries", [])

    lines = []

    # 1. 事件概要
    lines.append("【事件概要】")
    lines.append(f"事件摘要：{source.get('event_summary', '')}")
    lines.append(f"事件类型：{source.get('event_type', '')}")

    # 2. 实体图谱
    lines.append("\n【实体图谱】")
    entities = source.get("event_entities", [])
    lines.append(f"事件实体：{len(entities)} 个")
    for entity in entities:
        name = entity.get("name", "?")
        etype = entity.get("type", "?")
        role = entity.get("role", "?")
        can_speak = entity.get("can_speak", False)
        stmt = entity.get("original_statement", "")
        lines.append(f"  - {name}（{etype}）: {role} | can_speak={can_speak}")
        if stmt:
            lines.append(f"    原始发言：{stmt[:50]}...")
    spreaders = source.get("opinion_spreaders", [])
    lines.append(f"\n意见传播者：{len(spreaders)} 个")
    for s in spreaders:
        lines.append(f"  - {s.get('group_name', '?')} | 关联实体：{s.get('related_event_entity', '?')}，立场：{s.get('stance_score', 0)}，占比：{s.get('estimated_percentage', 0)}%")

    # 3. 轮次 0 发言
    lines.append("\n【轮次 0 事件实体发言】")
    if tick_entries:
        for entry in tick_entries[0].get("entries", []):
            comment = entry.get("comment", "")
            if comment:
                lines.append(f"  [{entry.get('group_name', '?')}]: {comment[:80]}...")

    # 4. 模拟立场演化
    lines.append("\n【模拟立场演化数据】")
    lines.append("轮次 | 模拟立场均值 | 标准差 | 模拟极化指数 | 关键变化")
    lines.append("-" * 70)
    prev_pol = None
    for et in emotion_trajectory:
        key_event = et.get("key_event", "")
        tick = et.get("tick", 0)
        ms = et.get("mean_stance", 5.0)
        ss = et.get("std_stance", 0.0)
        pi = et.get("polarization_index", 0.0)
        change = ""
        if prev_pol is not None:
            change = f"({pi - prev_pol:+.2f})"
        lines.append(f"{tick:4d} | {ms:5.2f} | {ss:5.2f} | {pi:5.2f} {change:8s} | {key_event}")
        prev_pol = pi

    # 5. 立场矩阵
    lines.append("\n【立场矩阵】")
    if not matrix:
        lines.append("无可用 opinion spreader 立场矩阵。")
    else:
        lines.append("以下表格是 Markdown 报告中最终立场变化的唯一数值来源；不得重算。")
        lines.append("| Agent | 群体 | 起始立场 | 结束立场 | Delta |")
        lines.append("|---|---:|---:|---:|---:|")
        for row in matrix:
            aid = row.get("agent_id", "?")
            gn = row.get("group_name", "?")
            ist = row.get("initial_stance", 5.0)
            fst = row.get("final_stance", 5.0)
            md = row.get("max_delta", fst - ist)
            lines.append(f"| #{aid} | {gn} | {ist:.2f} | {fst:.2f} | {md:+.2f} |")

    # 6. 拐点
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

    # 7. 风险判定
    lines.append("\n【风险判定】（由 Phase3 RiskAnalyzer 计算）")
    lines.append(f"风险等级: {rv.get('level', 'unknown')}")
    lines.append(f"风险标签: {rv.get('label', '')}")
    lines.append(f"风险依据: {rv.get('basis_text', '')}")

    # 8. 风险类型
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
    dataset: dict,
    *,
    build_report_context: Callable[..., str] = build_report_context_new,
    build_code_owned_contract_block: Callable[..., str] = _build_report_contract_block,
    parse_llm_report_response: Callable[..., Phase4Output] = parse_llm_report_response,
    get_llm_client_func: Callable[[], object] = get_llm_client,
) -> Tuple[Phase4Output, str]:
    """Run the LLM narrative path using only simulation_dataset.

    All Phase3-derived data (entities, spreaders, tick data, risk, inflection, stance)
    is consumed from the single dataset dict. No external pipeline artifacts needed.
    """
    llm = get_llm_client_func()

    report_context = build_report_context(dataset)
    code_owned_contract_block = build_code_owned_contract_block(dataset)
    user_prompt = build_report_user_prompt(code_owned_contract_block, report_context)

    console.print("[cyan]正在调用 LLM 生成报告...[/cyan]")

    response = llm.generate(
        system=REPORT_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,
    )

    phase4_output = parse_llm_report_response(
        response,
        dataset,
    )
    return phase4_output, response
