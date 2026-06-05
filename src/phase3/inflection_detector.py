"""Phase 3: 拐点检测器 — 独立重建"""

from typing import List

from src.schemas.phase3 import TickLog
from src.schemas.phase2 import Phase2Output


class InflectionDetector:
    """检测模拟过程中的关键拐点（极化指数突变点）。"""

    def detect(
        self,
        tick_logs: List[TickLog],
        phase2_output: Phase2Output,
        *,
        pol_threshold: float = 0.1,
        max_points: int = 3,
    ) -> List[dict]:
        """识别模拟关键变化点

        算法（与 report_agent.identify_inflection_points 等价）：
        1. 计算每轮的极化指数变化（与前一轮的绝对差值）
        2. 变化超过阈值且有发言条目的轮次视为关键变化点
        3. 从该轮条目中找出立场偏移最大的 Agent

        Args:
            tick_logs: TickLog 列表
            phase2_output: Phase2 输出
            pol_threshold: 极化指数变化阈值，默认 0.1
            max_points: 最多返回的拐点数量，默认 3

        Returns:
            拐点字典列表，每个包含 tick, agent_id, group_name,
            pivotal_comment, impact_description, pol_delta, stance_delta
        """
        if len(tick_logs) < 2:
            return []

        inflection_points: List[dict] = []
        node_map = {n.id: n for n in phase2_output.nodes}

        for i in range(1, len(tick_logs)):
            prev_pol = tick_logs[i - 1].global_metrics.polarization_index
            curr_pol = tick_logs[i].global_metrics.polarization_index
            pol_delta = abs(curr_pol - prev_pol)

            if pol_delta > pol_threshold and tick_logs[i].entries:
                max_entry = max(
                    tick_logs[i].entries,
                    key=lambda e: abs(e.stance_delta),
                )

                node = node_map.get(max_entry.agent_id)

                inflection_points.append({
                    "tick": tick_logs[i].tick,
                    "agent_id": max_entry.agent_id,
                    "group_name": node.group_name if node else "未知",
                    "pivotal_comment": max_entry.comment[:50],
                    "impact_description": (
                        f"模拟极化指数变化 {pol_delta:.2f}，"
                        f"立场偏移 {max_entry.stance_delta:+.1f}"
                    ),
                    "pol_delta": pol_delta,
                    "stance_delta": max_entry.stance_delta,
                })

        return inflection_points[:max_points]
