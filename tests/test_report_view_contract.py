# -*- coding: utf-8 -*-
from __future__ import annotations

from adarian.report.view_builder import build_native_report_view


def _appendix_b() -> dict:
    return {
        "meta": {"event_name": "测试事件", "worlds_count": 2},
        "evolution_analysis": {
            "worst_reasonable_level": "high",
            "worst_reasonable_level_label": "高风险",
            "risk_level_distribution": {"high": 1, "medium": 1},
        },
        "risk_assessment": {
            "risks": [
                {
                    "type_label": "负向叙事聚合",
                    "trigger_reason": "2 个 completed world 将该类型列为主要风险候选。",
                }
            ]
        },
    }


def test_build_native_report_view_contract() -> None:
    body = "\n".join([
        "# 测试事件舆情风险研判",
        "## 一、舆情概要",
        "测试事件引发关注。",
        "## 二、演化分析",
        "- 讨论呈现分化态势。",
        "## 三、风险研判",
        "### （一）负向叙事聚合风险",
        "存在负向叙事聚合风险。",
        "## 四、对策意见",
        "**责任主体**：事件主体应补充事实说明。",
    ])
    view = build_native_report_view(
        body=body,
        appendix_b=_appendix_b(),
        audit={"passed": 1, "blocked_reasons": []},
        job={
            "id": "report_test",
            "batch_id": "batch_test",
            "completed_worlds_count": 2,
            "failed_worlds_count": 0,
            "skill_id": "default_government",
            "model_config_resolved_from": "env",
        },
        version="B",
        appendix_mode="none",
        model_label="env:qwen",
        public_appendix="\n".join([
            "# 附录：方法说明",
            "## 一、数据说明",
            "### （一）计算方法",
            "```python",
            "# 优先级判定",
            "risk = max(levels)",
            "```",
            "| 风险类型 | 典型场景 |",
            "|----------|----------|",
            "| 监管信任风险 | 处置过程受到质疑 |",
        ]),
        skill_snapshot={"label": "政府研判", "version": "2", "checksum": "abc"},
    )

    assert view["id"] == "report_test:B"
    assert view["title"] == "测试事件舆情风险研判"
    assert view["source"]["batch_id"] == "batch_test"
    assert view["source"]["model"] == "env:qwen"
    assert view["source"]["skill_label"] == "政府研判"
    assert "completed worlds" not in view["subtitle"]
    assert [section["heading"] for section in view["sections"]] == ["一、舆情概要", "二、演化分析", "三、风险研判", "四、对策意见"]
    assert view["sections"][1]["blocks"][0]["type"] == "list"
    assert view["sections"][2]["blocks"][0] == {"type": "subheading", "text": "（一）负向叙事聚合风险"}
    assert view["sections"][3]["blocks"][0]["text"] == "责任主体：事件主体应补充事实说明。"
    assert view["appendix"]["mode"] == "hidden"
    assert view["appendix"]["title"] == "附录：方法说明"
    assert view["appendix"]["sections"][0]["heading"] == "一、数据说明"
    assert view["appendix"]["sections"][0]["blocks"][1] == {
        "type": "preformatted",
        "text": "# 优先级判定\nrisk = max(levels)",
    }
    assert view["appendix"]["sections"][0]["blocks"][2] == {
        "type": "table",
        "headers": ["风险类型", "典型场景"],
        "rows": [["监管信任风险", "处置过程受到质疑"]],
    }
    assert view["quality"][0]["status"] == "passed"
