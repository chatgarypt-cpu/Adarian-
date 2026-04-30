"""
Agent 生成质量分析器

功能：
1. 统计 Agent 立场分布
2. 检测 Agent 描述文本相似度
3. 验证 Agent 属性逻辑一致性
4. 生成质量分析报告

新增于：v1.1.5
"""

import json
from typing import List, Dict
from collections import Counter
import difflib


class AgentQualityAnalyzer:
    """Agent 质量分析器"""

    def __init__(self, phase1_output_path: str):
        """初始化分析器

        Args:
            phase1_output_path: Phase 1 输出文件路径
        """
        with open(phase1_output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.event_entities = data.get("event_entities", [])
        self.opinion_spreaders = data.get("opinion_spreaders", [])

    def analyze_stance_distribution(self) -> Dict:
        """分析立场分布"""
        stances = [s["stance_score"] for s in self.opinion_spreaders]
        return {
            "min": min(stances),
            "max": max(stances),
            "mean": round(sum(stances) / len(stances), 2),
            "range_coverage": {
                "批评区间(1-3)": len([s for s in stances if s <= 3]),
                "中立区间(4-6)": len([s for s in stances if 4 <= s <= 6]),
                "支持区间(7-10)": len([s for s in stances if s >= 7])
            }
        }

    def analyze_description_diversity(self) -> Dict:
        """分析描述文本多样性"""
        descriptions = [s["description"] for s in self.opinion_spreaders]

        if len(descriptions) < 2:
            return {
                "平均相似度": 0.0,
                "判定": "⚠️ Agent 数量不足，无法计算相似度"
            }

        # 计算两两相似度
        similarities = []
        for i in range(len(descriptions)):
            for j in range(i+1, len(descriptions)):
                ratio = difflib.SequenceMatcher(
                    None, descriptions[i], descriptions[j]
                ).ratio()
                similarities.append(ratio)

        avg_similarity = sum(similarities) / len(similarities) if similarities else 0

        return {
            "平均相似度": round(avg_similarity, 2),
            "判定": "✅ 多样性良好" if avg_similarity < 0.3 else "❌ 描述重复度过高"
        }

    def analyze_style_diversity(self) -> Dict:
        """分析说话风格多样性"""
        styles = [s["communication_style"] for s in self.opinion_spreaders]
        style_counts = Counter(styles)

        return {
            "风格种类数": len(style_counts),
            "风格分布": dict(style_counts),
            "判定": "✅ 风格多样" if len(style_counts) >= 3 else "❌ 风格单一"
        }

    def analyze_logic_consistency(self) -> List[Dict]:
        """分析逻辑一致性"""
        issues = []

        for s in self.opinion_spreaders:
            group_name = s.get("group_name", "")
            stance = s.get("stance_score", 5.0)
            bias = s.get("confirmation_bias_level", "none")
            susceptibility = s.get("susceptibility", 0.5)

            # 检查 1：死忠粉/支持者 stance 应 > 7
            if any(keyword in group_name for keyword in ["死忠", "支持者", "粉丝", "拥趸"]):
                if stance < 7:
                    issues.append({
                        "agent": group_name,
                        "问题": f"支持类群体 stance={stance} < 7"
                    })

            # 检查 2：批评者/维权 stance 应 < 3
            if any(keyword in group_name for keyword in ["批评", "维权", "反对", "质疑", "黑"]):
                if stance > 3:
                    issues.append({
                        "agent": group_name,
                        "问题": f"批评类群体 stance={stance} > 3"
                    })

            # 检查 3：strong bias 应对应低 susceptibility
            if bias == "strong" and susceptibility > 0.5:
                issues.append({
                    "agent": group_name,
                    "问题": f"strong bias 但 susceptibility={susceptibility} > 0.5"
                })

        return issues

    def analyze_related_entity_validity(self) -> List[Dict]:
        """验证 related_event_entity 有效性"""
        issues = []
        entity_names = {e["name"] for e in self.event_entities}

        for s in self.opinion_spreaders:
            related = s.get("related_event_entity", "")
            if related and related not in entity_names:
                issues.append({
                    "agent": s.get("group_name", ""),
                    "问题": f"related_event_entity '{related}' 不在事件实体列表中"
                })

        return issues

    def analyze_percentage_sum(self) -> Dict:
        """验证 estimated_percentage 之和是否为 100"""
        total = sum(s.get("estimated_percentage", 0) for s in self.opinion_spreaders)
        return {
            "总和": total,
            "判定": "✅ 百分比之和等于 100" if total == 100 else f"❌ 百分比之和不等于 100（实际：{total}）"
        }

    def generate_report(self) -> str:
        """生成质量分析报告"""
        report_lines = ["# Agent 生成质量分析报告\n"]

        # 基本信息
        report_lines.append("## 基本信息")
        report_lines.append(f"- 事件实体数量：{len(self.event_entities)}")
        report_lines.append(f"- 意见传播者数量：{len(self.opinion_spreaders)}")
        report_lines.append("")

        # 1. 立场分布
        stance_dist = self.analyze_stance_distribution()
        report_lines.append("## 1. 立场分布")
        report_lines.append(f"- 最小值：{stance_dist['min']}")
        report_lines.append(f"- 最大值：{stance_dist['max']}")
        report_lines.append(f"- 平均值：{stance_dist['mean']}")
        report_lines.append(f"- 批评区间(1-3)：{stance_dist['range_coverage']['批评区间(1-3)']} 个")
        report_lines.append(f"- 中立区间(4-6)：{stance_dist['range_coverage']['中立区间(4-6)']} 个")
        report_lines.append(f"- 支持区间(7-10)：{stance_dist['range_coverage']['支持区间(7-10)']} 个")
        report_lines.append("")

        # 2. 描述多样性
        desc_div = self.analyze_description_diversity()
        report_lines.append("## 2. 描述文本多样性")
        report_lines.append(f"- 平均相似度：{desc_div['平均相似度']}")
        report_lines.append(f"- {desc_div['判定']}\n")

        # 3. 风格多样性
        style_div = self.analyze_style_diversity()
        report_lines.append("## 3. 说话风格多样性")
        report_lines.append(f"- 风格种类数：{style_div['风格种类数']}")
        report_lines.append(f"- 风格分布：{style_div['风格分布']}")
        report_lines.append(f"- {style_div['判定']}\n")

        # 4. 百分比校验
        percent_check = self.analyze_percentage_sum()
        report_lines.append("## 4. 百分比校验")
        report_lines.append(f"- 百分比之和：{percent_check['总和']}")
        report_lines.append(f"- {percent_check['判定']}\n")

        # 5. 关联有效性
        entity_issues = self.analyze_related_entity_validity()
        report_lines.append("## 5. 关联实体有效性")
        if not entity_issues:
            report_lines.append("✅ 所有 opinion_spreader 都关联了有效的事件实体\n")
        else:
            report_lines.append(f"❌ 发现 {len(entity_issues)} 个问题：")
            for issue in entity_issues:
                report_lines.append(f"- {issue['agent']}：{issue['问题']}")

        # 6. 逻辑一致性
        issues = self.analyze_logic_consistency()
        report_lines.append("## 6. 逻辑一致性检查")
        if not issues:
            report_lines.append("✅ 未发现逻辑冲突\n")
        else:
            report_lines.append(f"❌ 发现 {len(issues)} 个问题：")
            for issue in issues:
                report_lines.append(f"- {issue['agent']}：{issue['问题']}")

        # 总结
        report_lines.append("## 总结")
        all_pass = (
            stance_dist['min'] <= 3 and stance_dist['max'] >= 7 and
            desc_div['平均相似度'] < 0.3 and
            style_div['风格种类数'] >= 3 and
            percent_check['总和'] == 100 and
            len(entity_issues) == 0 and
            len(issues) == 0
        )
        if all_pass:
            report_lines.append("✅ 所有验收标准通过，Agent 生成质量合格")
        else:
            report_lines.append("⚠️ 部分验收标准未通过，需要优化")

        return "\n".join(report_lines)


def analyze_agent_quality(phase1_output_path: str, output_report_path: str = None) -> str:
    """便捷函数：分析 Agent 质量并生成报告

    Args:
        phase1_output_path: Phase 1 输出文件路径
        output_report_path: 可选，报告输出路径

    Returns:
        报告内容
    """
    analyzer = AgentQualityAnalyzer(phase1_output_path)
    report = analyzer.generate_report()

    if output_report_path:
        with open(output_report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"质量分析报告已保存至：{output_report_path}")

    return report
