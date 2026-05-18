from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ChangePoint:
    """模拟关键变化点。

    对应审计文件 v1.2.8-metric-system-technical-audit-2026-05-13.md §7：
    当相邻两轮 polarization_index 变化绝对值 > 0.1 时触发，取该轮次中
    stance_delta 绝对值最大的 agent 作为关联实体。最多返回 3 个。
    """
    tick: int
    polarization_change: float
    pivotal_group_name: Optional[str]
    pivotal_stance_delta: Optional[float]
    description: str


def detect_change_points(tick_logs: List[dict]) -> List[ChangePoint]:
    """检测模拟关键变化点。

    遍历 tick_logs，当 |Δpolarization_index| > 0.1 时判定为模拟关键变化点。
    取该轮次中 stance_delta 绝对值最大的 entry 作为关联群体。
    最多返回 3 个。

    Args:
        tick_logs: 完整 tick 日志列表，每项含 global_metrics.polarization_index
                   和 entries[].stance_delta / entries[].group_name。

    Returns:
        List[ChangePoint]: 按 tick 顺序排列的模拟关键变化点，最多 3 个。
    """
    change_points: List[ChangePoint] = []

    for i in range(1, len(tick_logs)):
        prev_pol = tick_logs[i - 1]["global_metrics"]["polarization_index"]
        curr_pol = tick_logs[i]["global_metrics"]["polarization_index"]
        pol_change = curr_pol - prev_pol

        if abs(pol_change) > 0.1:
            entries = tick_logs[i].get("entries", [])
            if entries:
                max_entry = max(entries, key=lambda e: abs(e.get("stance_delta", 0.0)))
                pivotal_group = max_entry.get("group_name")
                pivotal_delta = max_entry.get("stance_delta", 0.0)
                direction = "上升" if pivotal_delta > 0 else "下降"
                desc = (
                    f"模拟极化指数变化 {pol_change:+.2f}，"
                    f"关联群体 {pivotal_group} 立场{direction} {abs(pivotal_delta):.2f}"
                )
            else:
                pivotal_group = None
                pivotal_delta = None
                desc = f"模拟极化指数变化 {pol_change:+.2f}（该轮次无发言记录）"

            change_points.append(ChangePoint(
                tick=i,
                polarization_change=pol_change,
                pivotal_group_name=pivotal_group,
                pivotal_stance_delta=pivotal_delta,
                description=desc,
            ))

    return change_points[:3]


def generate_change_point_analysis(tick_logs: List[dict]) -> str:
    """生成模拟关键变化点分析文本。

    Args:
        tick_logs: 完整 tick 日志列表。

    Returns:
        str: 面向报告的模拟关键变化点分析段落。
    """
    points = detect_change_points(tick_logs)

    if not points:
        return "本次模拟周期内未出现满足识别标准（|Δ模拟极化指数| > 0.1）的显著模拟关键变化点。"

    lines = []
    for p in points:
        lines.append(
            f"轮次 {p.tick} 出现模拟关键变化点：{p.description}。"
            f"触发条件：模拟极化指数变化 {p.polarization_change:+.2f}"
            f"（绝对值 > 0.1 阈值）。"
        )

    return " ".join(lines)
