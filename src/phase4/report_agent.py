"""
Phase 4: 宏观洞察生成器
---
根据 Phase 3 的模拟结果，生成舆情演化洞察报告。

v1.1.8 变化：
- 重构报告结构（概要 → 实体 → 拐点 → 演化 → 洞察 → 风险）
- 增加 Tick 0 发言展示
- 增加关键拐点识别（以 identify_inflection_points() 的 code-owned 输出为准）
- 增加 Tick 1-N 演化展示
- 增加最终立场变化表格
- 增加极化演化轨迹
- 增加关键洞察生成（3-6 条）
- 增加舆论态势判断

修改于：v1.1.8
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

import config
from src.schemas import (
    EntityExtractionOutput, Phase2Output, TickLog,
    Phase4Output, EmotionTrajectory, InflectionPoint, RiskLevel
)
from src.llm_client import get_llm_client

console = Console()


# =============================================================================
# Prompt 模板
# =============================================================================

REPORT_SYSTEM_PROMPT = """你是一位资深的社会舆情分析师。你的任务是根据舆情模拟数据，生成一份专业的舆情洞察报告。

报告面向决策者，需要结论先行，每个章节使用 emoji 提升可读性。

【报告结构】
1. 📊 事件概要 - 一句话总结 + 核心指标
2. 🗺️ 实体图谱 - 事件实体和意见传播者列表
3. 🎬 Tick 0 · 事件实体发言 - 展示事件实体初始发言
4. 🔥 关键拐点 - 识别 1-2 个最关键的拐点
5. 📈 Tick 1-N · 意见演化 - 首尾 Tick 代表性发言对比
6. 📊 最终立场变化 - 各群体 Tick 0 → Tick N 的立场变化
7. 📉 极化演化轨迹 - 文字版极化指数可视化
8. 💡 关键洞察 - 3-6 条核心发现
9. 🎯 舆论态势判断 - 整体极化、矛盾焦点、演化趋势、风险提示
10. ⚠️ 风险评估 - 具体风险点和建议

【指标 Grounding 硬约束】
- “关键拐点”只能引用输入中的【CODE_OWNED_INFLECTION_POINTS】，不得自行按其他阈值重算或新增拐点。
- 如果【CODE_OWNED_INFLECTION_POINTS】声明“本轮模拟未发现显著拐点”，报告必须写同一结论，不得声称存在 1 个或多个拐点。
- “最终立场变化”只能引用输入中的【CODE_OWNED_AGENT_STANCE_MATRIX】，起始值、终值和 delta 必须逐字使用该表数值。
- 全局 x(t) 均值、标准差、极化指数只能引用输入中的【情绪演化数据】和【x(t) 序列】，不得自行重算。

【立场变化趋势符号】
- 变化 < -1.0：↓↓
- 变化 -1.0 ~ -0.5：↓
- 变化 -0.5 ~ +0.5：→
- 变化 +0.5 ~ +1.0：↑
- 变化 > +1.0：↑↑
- 变化 > +2.0：↑↑↑

【关键洞察要求】
- 每条 30-50 字
- 包含现象描述 + 数据支撑
- 按重要性排序

【舆论态势判断维度】
- 整体极化：<0.3 温和，0.3-0.5 中等，>0.5 高对立
- 矛盾焦点：识别对立双方的核心争议点
- 演化趋势：描述立场变化的主要方向
- 风险提示：根据批评者立场和比例给出预警

输出格式：直接输出完整 Markdown 报告，500-800 行。
"""


def build_full_report_context(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
) -> str:
    """构建完整的报告上下文数据

    Args:
        extraction_output: 实体提取结果
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        格式化的上下文字符串
    """
    lines = []

    # 1. 事件概要
    lines.append("【事件概要】")
    lines.append(f"事件摘要：{extraction_output.event_summary}")
    lines.append(f"事件类型：{extraction_output.event_type}")
    lines.append(f"事件规模：{extraction_output.event_scale:.2f}（0-1，1=全社会）")
    lines.append(f"事件争议性：{extraction_output.event_controversy:.2f}（0-1，1=高度对立）")

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

    # 3. Tick 0 发言
    lines.append("\n【Tick 0 事件实体发言】")
    tick_0_log = tick_logs[0] if tick_logs else None
    if tick_0_log:
        for entry in tick_0_log.entries:
            if entry.comment:
                lines.append(f"  [{entry.group_name}]: {entry.comment[:80]}...")

    # 4. 情绪演化数据
    lines.append("\n【情绪演化数据】")
    lines.append("Tick | x(t)均值 | 标准差 | 极化指数 | 关键变化")
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

    # 5. 极化演化轨迹
    lines.append("\n【极化演化轨迹】")
    pol_sequence = [f"{log.global_metrics.polarization_index:.2f}" for log in tick_logs if log.entries]
    lines.append(" → ".join(pol_sequence))
    if len(pol_sequence) >= 2:
        first_pol = float(pol_sequence[0])
        last_pol = float(pol_sequence[-1])
        change_pct = (last_pol - first_pol) / first_pol * 100 if first_pol > 0 else 0
        direction = "下降" if change_pct < 0 else "上升"
        lines.append(f"极化指数从 {pol_sequence[0]} 变化到 {pol_sequence[-1]}，{direction} {abs(change_pct):.0f}%")

    # 6. code-owned grounding blocks
    lines.append("\n【CODE_OWNED_AGENT_STANCE_MATRIX】")
    lines.extend(_format_code_owned_agent_stance_matrix(tick_logs))

    lines.append("\n【CODE_OWNED_INFLECTION_POINTS】")
    inflection_points = identify_inflection_points(tick_logs, phase2_output) if phase2_output else []
    lines.extend(_format_code_owned_inflection_points(inflection_points))

    # 7. x(t) 序列
    lines.append(f"\n【x(t) 序列】：{' → '.join([f'{x:.2f}' for x in x_t_sequence])}")

    return "\n".join(lines)


def _build_code_owned_agent_stance_matrix(tick_logs: List[TickLog]) -> List[Dict[str, Any]]:
    """Build the stance matrix used as the only Markdown source for per-agent values."""
    if not tick_logs:
        return []

    start_log = tick_logs[1] if len(tick_logs) >= 2 else tick_logs[0]
    end_log = tick_logs[-1]
    start_entries = {entry.agent_id: entry for entry in start_log.entries}
    end_entries = {entry.agent_id: entry for entry in end_log.entries}

    rows = []
    for agent_id in sorted(set(start_entries) & set(end_entries)):
        start_entry = start_entries[agent_id]
        end_entry = end_entries[agent_id]
        initial = start_entry.current_stance
        final = end_entry.current_stance
        rows.append({
            "agent_id": agent_id,
            "group_name": end_entry.group_name,
            "start_tick": start_log.tick,
            "end_tick": end_log.tick,
            "initial_stance": initial,
            "final_stance": final,
            "delta": final - initial,
        })

    return rows


def _format_code_owned_agent_stance_matrix(tick_logs: List[TickLog]) -> List[str]:
    rows = _build_code_owned_agent_stance_matrix(tick_logs)
    if not rows:
        return ["无可用 opinion spreader 立场矩阵。"]

    lines = [
        "以下表格是 Markdown 报告中最终立场变化的唯一数值来源；不得重算。",
        "| Agent | 群体 | 起始 Tick | 结束 Tick | 起始立场 | 结束立场 | Delta |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| #{row['agent_id']} | {row['group_name']} | {row['start_tick']} | "
            f"{row['end_tick']} | {row['initial_stance']:.2f} | "
            f"{row['final_stance']:.2f} | {row['delta']:+.2f} |"
        )
    return lines


def _format_code_owned_inflection_points(inflection_points: List[InflectionPoint]) -> List[str]:
    if not inflection_points:
        return [
            "本轮模拟未发现显著拐点。",
            "Markdown 报告不得声称存在拐点，不得使用其他阈值自行识别拐点。",
        ]

    lines = [
        "以下表格是 Markdown 报告中关键拐点的唯一来源；不得新增其他拐点。",
        "| Tick | Agent | 群体 | 影响 |",
        "|---:|---:|---|---|",
    ]
    for point in inflection_points:
        lines.append(
            f"| {point.tick} | #{point.agent_id} | {point.group_name} | "
            f"{point.impact_description} |"
        )
    return lines


def build_entity_distribution(extraction_output: EntityExtractionOutput) -> str:
    """构建实体分布文本

    Args:
        extraction_output: 实体提取结果

    Returns:
        格式化分布字符串
    """
    lines = ["事件实体（直接参与者）："]
    for entity in extraction_output.event_entities:
        lines.append(f"  - {entity.name} ({entity.type}): {entity.role}")

    lines.append("\n意见传播者（评论者）：")
    for spreader in extraction_output.opinion_spreaders:
        lines.append(f"  - {spreader.group_name}")
        lines.append(f"    关联实体: {spreader.related_event_entity}, 立场: {spreader.stance_score}, 偏差: {spreader.confirmation_bias_level}")

    return "\n".join(lines)


def identify_inflection_points(tick_logs: List[TickLog], phase2_output: Phase2Output) -> List[InflectionPoint]:
    """识别拐点

    算法：
    1. 计算每轮的极化指数变化
    2. 极化指数变化最大的轮次为拐点
    3. 找出该轮次中立场变化最大的 Agent

    Args:
        tick_logs: TickLog 列表
        phase2_output: Phase2 输出

    Returns:
        InflectionPoint 列表
    """
    if len(tick_logs) < 2:
        return []

    inflection_points = []
    node_map = {n.id: n for n in phase2_output.nodes}

    # 计算每轮的极化指数变化
    for i in range(1, len(tick_logs)):
        prev_pol = tick_logs[i - 1].global_metrics.polarization_index
        curr_pol = tick_logs[i].global_metrics.polarization_index
        pol_delta = abs(curr_pol - prev_pol)

        # 如果极化指数变化超过阈值，认为是拐点
        if pol_delta > 0.1 and tick_logs[i].entries:
            # 找出本轮立场变化最大的 Agent
            max_entry = max(tick_logs[i].entries, key=lambda e: abs(e.stance_delta))

            node = node_map.get(max_entry.agent_id)

            inflection_points.append(InflectionPoint(
                tick=tick_logs[i].tick,
                agent_id=max_entry.agent_id,
                group_name=node.group_name if node else "未知",
                pivotal_comment=max_entry.comment[:50],
                impact_description=f"极化指数变化 {pol_delta:.2f}，立场偏移 {max_entry.stance_delta:+.1f}",
            ))

    # 限制最多 3 个拐点
    return inflection_points[:3]


def assess_risk(x_t_sequence: List[float], tick_logs: List[TickLog]) -> tuple:
    """评估舆情风险等级

    算法：
    1. x(t) 持续上升 > 7.0 → 高风险
    2. x(t) > 5.0 且极化指数 > 0.5 → 中高风险
    3. x(t) > 5.0 → 中风险
    4. x(t) < 5.0 → 低风险

    Args:
        x_t_sequence: x(t) 序列
        tick_logs: TickLog 列表

    Returns:
        (risk_level, risk_assessment) tuple
    """
    if not x_t_sequence:
        return RiskLevel.LOW, "数据不足，无法评估"

    final_x = x_t_sequence[-1]
    final_pol = tick_logs[-1].global_metrics.polarization_index if tick_logs else 0

    # 计算趋势
    trend = final_x - x_t_sequence[0] if len(x_t_sequence) > 1 else 0

    if final_x > 7.5 or (final_x > 7.0 and trend > 1.0):
        return RiskLevel.CRITICAL, f"舆情危机状态，x(t)达{final_x:.1f}，极化严重"
    elif final_x > 6.5 or (final_x > 5.5 and final_pol > 0.5):
        return RiskLevel.HIGH, f"高风险舆情，x(t)={final_x:.1f}，需重点关注"
    elif final_x > 5.0 or (final_x > 4.5 and trend > 0.5):
        return RiskLevel.MEDIUM, f"中等风险，x(t)={final_x:.1f}，趋势需关注"
    else:
        return RiskLevel.LOW, f"舆情平稳，x(t)={final_x:.1f}，风险较低"


# 模块级变量，用于存储 LLM 生成的 Markdown 报告
_llm_generated_markdown: str = ""


def generate_report_with_llm(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
) -> Phase4Output:
    """使用 LLM 生成报告

    v1.1.8: 直接生成 Markdown 格式报告

    Args:
        extraction_output: 实体提取结果
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        Phase4Output 对象
    """
    global _llm_generated_markdown

    llm = get_llm_client()

    if phase2_output is None:
        from src.phase3 import load_phase2_output
        phase2_output = load_phase2_output()

    # 构建完整上下文
    report_context = build_full_report_context(
        extraction_output,
        tick_logs,
        x_t_sequence,
        phase2_output=phase2_output,
    )

    user_prompt = f"""请根据以下数据生成舆情洞察报告：

{report_context}

请生成完整的 Markdown 格式报告。报告应面向决策者，结论先行，包含所有章节（概要、实体图谱、Tick 0发言、关键拐点、意见演化、立场变化、极化轨迹、关键洞察、舆论态势、风险评估）。"""

    console.print("[cyan]正在调用 LLM 生成报告...[/cyan]")

    response = llm.generate(
        system=REPORT_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,
    )

    # 保存 LLM 生成的 Markdown
    _llm_generated_markdown = response

    # 解析响应并构建 Phase4Output
    phase4_output = parse_llm_report_response(
        response,
        extraction_output,
        tick_logs,
        x_t_sequence,
        phase2_output=phase2_output,
    )

    return phase4_output


def parse_llm_report_response(
    response: str,
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
) -> Phase4Output:
    """解析 LLM 报告响应

    v1.1.8: LLM 直接生成 Markdown，解析失败时使用 fallback

    Args:
        response: LLM 返回的原始字符串
        extraction_output: 实体提取结果
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        Phase4Output 对象
    """
    # 检查响应是否有效
    if not response or len(response) < 100:
        console.print("[yellow]警告：[/yellow] LLM 报告过短，使用自动分析")
        return generate_fallback_report(
            extraction_output,
            tick_logs,
            x_t_sequence,
            phase2_output=phase2_output,
        )

    # 构建情绪轨迹
    emotion_trajectory = [
        EmotionTrajectory(
            tick=log.tick,
            mean_stance=log.global_metrics.mean_stance,
            std_stance=log.global_metrics.std_stance,
            polarization_index=log.global_metrics.polarization_index,
            key_event=f"Agent #{max(log.entries, key=lambda e: abs(e.stance_delta)).agent_id} 发言",
        )
        for log in tick_logs if log.entries
    ]

    # 识别拐点
    if phase2_output is None:
        from src.phase3 import load_phase2_output
        phase2_output = load_phase2_output()
    inflection_points = identify_inflection_points(tick_logs, phase2_output)

    # 风险评估
    risk_level, risk_assessment = assess_risk(x_t_sequence, tick_logs)

    # 利益相关方图谱
    event_entities_str = ", ".join([e.name for e in extraction_output.event_entities])
    spreaders_str = ", ".join([s.group_name for s in extraction_output.opinion_spreaders])
    stakeholder_map = f"事件实体: {event_entities_str} | 传播者: {spreaders_str}"

    return Phase4Output(
        event_summary=extraction_output.event_summary,
        stakeholder_map=stakeholder_map,
        emotion_trajectory=emotion_trajectory,
        inflection_points=inflection_points,
        risk_level=risk_level,
        risk_assessment=risk_assessment,
        x_t_sequence=x_t_sequence,
    )


def generate_fallback_report(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    phase2_output: Phase2Output = None,
) -> Phase4Output:
    """生成自动报告（当 LLM 失败时）

    Args:
        extraction_output: 实体提取结果
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        Phase4Output 对象
    """
    if phase2_output is None:
        from src.phase3 import load_phase2_output
        phase2_output = load_phase2_output()

    # 识别拐点
    inflection_points = identify_inflection_points(tick_logs, phase2_output)

    # 风险评估
    risk_level, risk_assessment = assess_risk(x_t_sequence, tick_logs)

    # 构建情绪轨迹
    emotion_trajectory = [
        EmotionTrajectory(
            tick=log.tick,
            mean_stance=log.global_metrics.mean_stance,
            std_stance=log.global_metrics.std_stance,
            polarization_index=log.global_metrics.polarization_index,
            key_event=f"Agent #{max(log.entries, key=lambda e: abs(e.stance_delta)).agent_id}: {max(log.entries, key=lambda e: abs(e.stance_delta)).comment[:30]}...",
        )
        for log in tick_logs if log.entries
    ]

    # 利益相关方图谱
    event_entities_str = ", ".join([e.name for e in extraction_output.event_entities])
    spreaders_str = ", ".join([s.group_name for s in extraction_output.opinion_spreaders])
    stakeholder_map = f"事件实体: {event_entities_str} | 传播者: {spreaders_str}"

    return Phase4Output(
        event_summary=extraction_output.event_summary,
        stakeholder_map=stakeholder_map,
        emotion_trajectory=emotion_trajectory,
        inflection_points=inflection_points,
        risk_level=risk_level,
        risk_assessment=risk_assessment,
        x_t_sequence=x_t_sequence,
    )


def generate_markdown_report(phase4_output: Phase4Output, extraction_output: EntityExtractionOutput) -> str:
    """生成 Markdown 格式报告

    Args:
        phase4_output: Phase4 输出
        extraction_output: 实体提取结果

    Returns:
        Markdown 格式字符串
    """
    spreader_count = len(extraction_output.opinion_spreaders)

    # v1.1.6: Split entities into speaking and discussed
    speaking_entities = [e for e in extraction_output.event_entities if e.can_speak]
    discussed_entities = [e for e in extraction_output.event_entities if not e.can_speak]

    lines = [
        "# 舆情演化洞察报告",
        "",
        "---",
        "",
        "## 一、事件概述",
        "",
        extraction_output.event_summary,
        "",
        f"**事件类型**: {extraction_output.event_type}",
        f"**事件规模**: {extraction_output.event_scale:.2f}",
        f"**事件争议性**: {extraction_output.event_controversy:.2f}",
        "",
        "## 二、利益相关方图谱",
        "",
        "### 发言实体（{}个）".format(len(speaking_entities)),
        "",
        "| 实体 | 角色 | Tick 0 发言 |",
        "|------|------|------------|",
    ]

    for entity in speaking_entities:
        statement = entity.original_statement if entity.original_statement else "（无原始发言）"
        lines.append(f"| {entity.name} | {entity.role} | {statement} |")

    lines.extend([
        "",
        "### 被讨论实体（{}个）".format(len(discussed_entities)),
        "",
        "| 实体 | 角色 | 说明 |",
        "|------|------|------|",
    ])

    for entity in discussed_entities:
        reason = entity.can_speak_reason if entity.can_speak_reason else "不可发言"
        lines.append(f"| {entity.name} | {entity.role} | {reason} |")

    lines.extend([
        "",
        "### 意见传播者（评论者）",
        "",
        "| 群体 | 关联实体 | 立场分 | 确认偏差 |",
        "|------|---------|--------|----------|",
    ])

    for spreader in extraction_output.opinion_spreaders:
        lines.append(f"| {spreader.group_name} | {spreader.related_event_entity} | {spreader.stance_score} | {spreader.confirmation_bias_level} |")

    lines.extend([
        "",
        "## 三、情绪演化轨迹",
        "",
        "| Tick | x(t)均值 | 标准差 | 极化指数 | 关键事件 |",
        "|------|----------|--------|---------|---------|",
    ])

    for traj in phase4_output.emotion_trajectory:
        lines.append(f"| {traj.tick} | {traj.mean_stance:.2f} | {traj.std_stance:.2f} | {traj.polarization_index:.2f} | {traj.key_event} |")

    lines.extend([
        "",
        f"**x(t) 序列**: {' → '.join([f'{x:.2f}' for x in phase4_output.x_t_sequence])}",
        "",
        "## 四、拐点分析",
        "",
    ])

    if phase4_output.inflection_points:
        lines.extend([
            "| Tick | Agent | 群体 | 关键发言 | 影响 |",
            "|------|-------|------|---------|------|",
        ])
        for ip in phase4_output.inflection_points:
            lines.append(f"| {ip.tick} | #{ip.agent_id} | {ip.group_name} | {ip.pivotal_comment[:30]}... | {ip.impact_description} |")
    else:
        lines.append("（本轮模拟未发现显著拐点）")

    lines.extend([
        "",
        "## 五、风险评估",
        "",
        f"**风险等级**: {phase4_output.risk_level.value.upper()}",
        "",
        phase4_output.risk_assessment,
        "",
        "---",
        "",
        "*本报告由 Adarian 多智能体舆情预判系统自动生成*",
    ])

    return "\n".join(lines)


def save_report(phase4_output: Phase4Output, output_path: Path = None):
    """保存报告

    Args:
        phase4_output: Phase4 输出
        output_path: 输出路径，默认使用 config.FINAL_REPORT_PATH.with_suffix(".json")
    """
    output_path = output_path or config.FINAL_REPORT_PATH.with_suffix(".json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(phase4_output.model_dump(), f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/green] JSON 报告已保存至: {output_path}")


def save_markdown_report(
    phase4_output: Phase4Output,
    extraction_output: EntityExtractionOutput,
    output_path: Path = None,
):
    """保存 Markdown 格式报告

    Args:
        phase4_output: Phase4 输出
        extraction_output: 实体提取结果
        output_path: 输出路径，默认使用 config.FINAL_REPORT_PATH.with_suffix(".md")
    """
    global _llm_generated_markdown

    # 如果有 LLM 生成的 Markdown（长度 > 100），直接使用
    if _llm_generated_markdown and len(_llm_generated_markdown) > 100:
        md_content = _llm_generated_markdown
    else:
        # 否则生成默认格式
        md_content = generate_markdown_report(phase4_output, extraction_output)

    md_path = output_path or config.FINAL_REPORT_PATH.with_suffix(".md")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    console.print(f"[green]✓[/green] Markdown 报告已保存至: {md_path}")


def load_tick_logs(tick_dir: Path = None) -> List[TickLog]:
    """加载 tick 日志"""
    from src.schemas import TickLog

    tick_dir = tick_dir or config.TICK_LOGS_DIR

    tick_logs = []
    for tick_file in sorted(tick_dir.glob("tick_*.json"), key=lambda p: int(p.stem.split("_")[1])):
        with open(tick_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            tick_logs.append(TickLog(**data))

    return tick_logs


# =============================================================================
# 主入口（可独立运行）
# =============================================================================

if __name__ == "__main__":
    import sys

    # 确保输出目录存在
    config.ensure_dirs()

    console.print("[bold]Phase 4: 生成舆情洞察报告[/bold]\n")

    # 加载数据
    from src.phase3 import load_extraction_output, load_phase2_output

    extraction_output = load_extraction_output()
    phase2_output = load_phase2_output()

    # 检查是否有 tick 日志
    if not config.TICK_LOGS_DIR.exists() or not list(config.TICK_LOGS_DIR.glob("tick_*.json")):
        console.print("[yellow]错误：[/yellow] 未找到 tick 日志，请先运行 Phase 3")
        sys.exit(1)

    tick_logs = load_tick_logs()

    # 提取 x(t) 序列
    x_t_sequence = [log.global_metrics.mean_stance for log in tick_logs]

    # 生成报告
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("[cyan]生成报告...", total=None)
        phase4_output = generate_report_with_llm(extraction_output, tick_logs, x_t_sequence)

    # 保存
    save_report(phase4_output)
    save_markdown_report(phase4_output, extraction_output)

    # 打印摘要
    console.print(f"\n[bold green]报告生成完成！[/bold green]")
    console.print(f"  风险等级: {phase4_output.risk_level.value.upper()}")
    console.print(f"  x(t) 序列: {[f'{x:.2f}' for x in x_t_sequence]}")
