"""Phase 3: 立场分析器 — 独立重建"""
from typing import List, Optional

from adarian.schemas.phase3 import TickLog


class StanceAnalyzer:
    """分析 agent 立场变化的分析器。

    提供两个核心方法：
    - build_agent_stance_matrix: 构建 agent 立场矩阵
    - max_negative_shift: 计算最大负面立场偏移
    """

    def build_agent_stance_matrix(self, tick_logs: List[TickLog]) -> List[dict]:
        """构建 agent 立场矩阵。

        从 tick_logs 中提取每个 agent 的起始立场和结束立场，
        计算 delta 并判断 attitude。

        Args:
            tick_logs: 模拟轮次日志列表

        Returns:
            列表，每个元素为 dict，包含：
            - agent_id: agent ID
            - group_name: 所属群体名称
            - initial_stance: 起始立场分
            - final_stance: 结束立场分
            - max_delta: |delta|（立场变化绝对值）
            - attitude: 立场态度（"stable" / "declining" / "rising"）
        """
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
            delta = final - initial
            abs_delta = abs(delta)

            # Phase 3 attitude heuristic based on delta magnitude
            if abs_delta < 0.01:
                attitude = "stable"
            elif delta < -0.01:
                attitude = "declining"
            else:  # delta > 0.01
                attitude = "rising"

            rows.append({
                "agent_id": agent_id,
                "group_name": end_entry.group_name,
                "initial_stance": initial,
                "final_stance": final,
                "max_delta": abs_delta,
                "attitude": attitude,
            })

        return rows

    def max_negative_shift(self, tick_logs: List[TickLog]) -> Optional[float]:
        """计算所有 agent 中最大的负面立场偏移。

        负面偏移定义为 initial_stance - final_stance（仅正值有意义）。
        若无数据则返回 None。

        Args:
            tick_logs: 模拟轮次日志列表

        Returns:
            最大负面偏移值，若无数据返回 None
        """
        if len(tick_logs) < 2:
            return None

        rows = self.build_agent_stance_matrix(tick_logs)
        if not rows:
            return None

        return max(max(0.0, row["initial_stance"] - row["final_stance"]) for row in rows)
