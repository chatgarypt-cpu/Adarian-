"""
Phase 4: 宏观洞察生成器
---
根据 Phase 3 的模拟结果，生成舆情演化洞察报告。

v1.1.4 变化：
- 使用 EntityExtractionOutput 替代 Phase1Output
- 事件实体和意见传播者的分布信息

输出内容包括：
1. 事件概述
2. 利益相关方图谱
3. 情绪演化轨迹表
4. 拐点分析
5. 风险评估
6. x(t) 序列（用于后续 AD/SEIR 模块）

修改于：v1.1.4
"""

import json
from pathlib import Path
from typing import List
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

你必须严格按照以下 JSON 格式输出：
{{
  "risk_level": "low/medium/high/critical",
  "risk_assessment": "风险评估说明（100字以内）",
  "stakeholder_map": "利益相关方图谱说明（150字以内）",
  "inflection_points": [
    {{
      "tick": 轮次号,
      "agent_id": 引发拐点的agent编号,
      "group_name": "群体名称",
      "pivotal_comment": "关键发言摘要",
      "impact_description": "影响说明"
    }}
  ]
}}

注意：
1. risk_level 必须选择: low, medium, high, critical 之一
2. inflection_points 应识别 1-3 个关键拐点
3. 风险评估应基于 x(t) 走势和极化指数
"""

REPORT_USER_PROMPT = """请分析以下舆情模拟数据，生成报告：

事件摘要：{event_summary}
事件类型：{event_type}
事件温度：{temperature}（0-1，1=最热）
事件烈度：{intensity}（0-1，1=最强）

情绪演化数据：
{emotion_table}

实体分布：
- 事件实体（直接参与者）：{event_entity_count} 个
- 意见传播者（评论者）：{spreader_count} 个

请输出完整的报告 JSON。
"""


def build_emotion_table(tick_logs: List[TickLog]) -> str:
    """构建情绪演化表格文本

    Args:
        tick_logs: TickLog 列表

    Returns:
        格式化表格字符串
    """
    lines = ["Tick | x(t)均值 | 标准差 | 极化指数 | 关键事件"]
    lines.append("-" * 70)

    prev_mean = None
    for log in tick_logs:
        if not log.entries:
            continue

        # 找出本轮最关键的发言
        max_delta_entry = max(log.entries, key=lambda e: abs(e.stance_delta))
        key_event = f"#{max_delta_entry.agent_id}: {max_delta_entry.comment[:20]}..."

        mean = log.global_metrics.mean_stance
        std = log.global_metrics.std_stance
        pol = log.global_metrics.polarization_index

        # 标记均值变化
        change = ""
        if prev_mean is not None:
            delta = mean - prev_mean
            change = f"({delta:+.1f})"
        prev_mean = mean

        lines.append(f"{log.tick:4d} | {mean:5.2f} {change:6s} | {std:5.2f} | {pol:6.2f} | {key_event}")

    return "\n".join(lines)


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


def generate_report_with_llm(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
) -> Phase4Output:
    """使用 LLM 生成报告

    Args:
        extraction_output: 实体提取结果
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        Phase4Output 对象
    """
    llm = get_llm_client()

    # 构建 prompt
    emotion_table = build_emotion_table(tick_logs)

    user_prompt = REPORT_USER_PROMPT.format(
        event_summary=extraction_output.event_summary,
        event_type=extraction_output.event_type,
        temperature=extraction_output.event_temperature,
        intensity=extraction_output.event_intensity,
        emotion_table=emotion_table,
        event_entity_count=len(extraction_output.event_entities),
        spreader_count=len(extraction_output.opinion_spreaders),
    )

    console.print("[cyan]正在调用 LLM 生成报告...[/cyan]")

    response = llm.generate(
        system=REPORT_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=None,
    )

    # 解析响应
    return parse_llm_report_response(response, extraction_output, tick_logs, x_t_sequence)


def parse_llm_report_response(
    response: str,
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
) -> Phase4Output:
    """解析 LLM 报告响应

    Args:
        response: LLM 返回的原始字符串
        extraction_output: 实体提取结果
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        Phase4Output 对象
    """
    import re

    # 提取 JSON
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)

    if not json_match:
        console.print("[yellow]警告：[/yellow] 无法解析 LLM 报告，使用自动分析")
        return generate_fallback_report(extraction_output, tick_logs, x_t_sequence)

    try:
        data = json.loads(json_match.group())

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
        from src.phase3_tick_simulation import load_phase2_output
        phase2_output = load_phase2_output()
        inflection_points = identify_inflection_points(tick_logs, phase2_output)

        # 风险评估
        risk_level_str = data.get("risk_level", "medium")
        try:
            risk_level = RiskLevel(risk_level_str)
        except ValueError:
            risk_level = RiskLevel.MEDIUM

        return Phase4Output(
            event_summary=data.get("event_summary", extraction_output.event_summary),
            stakeholder_map=data.get("stakeholder_map", ""),
            emotion_trajectory=emotion_trajectory,
            inflection_points=inflection_points,
            risk_level=risk_level,
            risk_assessment=data.get("risk_assessment", ""),
            x_t_sequence=x_t_sequence,
        )

    except (json.JSONDecodeError, ValueError) as e:
        console.print(f"[yellow]警告：[/yellow] 解析报告失败: {e}，使用自动分析")
        return generate_fallback_report(extraction_output, tick_logs, x_t_sequence)


def generate_fallback_report(
    extraction_output: EntityExtractionOutput,
    tick_logs: List[TickLog],
    x_t_sequence: List[float]
) -> Phase4Output:
    """生成自动报告（当 LLM 失败时）

    Args:
        extraction_output: 实体提取结果
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        Phase4Output 对象
    """
    from src.phase3_tick_simulation import load_phase2_output

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
    stakeholder_map = f"事件实体: {event_entities_str} | 传播者: {spreader_count}"

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
        f"**事件温度**: {extraction_output.event_temperature:.2f}",
        f"**事件烈度**: {extraction_output.event_intensity:.2f}",
        "",
        "## 二、利益相关方图谱",
        "",
        "### 事件实体（直接参与者）",
        "",
    ]

    for entity in extraction_output.event_entities:
        lines.append(f"- **{entity.name}** ({entity.type}): {entity.role}")

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
        output_path: 输出路径，默认使用 config.FINAL_REPORT_PATH
    """
    output_path = output_path or config.FINAL_REPORT_PATH

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(phase4_output.model_dump(), f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/green] JSON 报告已保存至: {output_path}")


def save_markdown_report(phase4_output: Phase4Output, extraction_output: EntityExtractionOutput):
    """保存 Markdown 格式报告

    Args:
        phase4_output: Phase4 输出
        extraction_output: 实体提取结果
    """
    md_content = generate_markdown_report(phase4_output, extraction_output)

    md_path = config.FINAL_REPORT_PATH.with_suffix(".md")
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
    from src.phase3_tick_simulation import load_extraction_output, load_phase2_output

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
