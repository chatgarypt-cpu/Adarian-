from __future__ import annotations

from adarian.report.quality import assemble_report, audit_body
from adarian.report.writer import _normalize_report_title


BODY = """# 测试事件舆情风险研判
## 一、舆情概要
测试事件引发关注。
## 二、演化分析
相关讨论呈现分化。
## 三、风险研判
存在负向叙事聚合风险。
## 四、对策意见
相关主体应及时补充事实说明。
"""


def test_skill_checklist_blocks_configured_internal_term() -> None:
    audit = audit_body(BODY.replace("相关讨论", "completed world"), {
        "blocking": ["internal_simulation_fields_in_body"],
        "forbidden_terms": ["completed world"],
    })

    assert audit["fatal"] == 1
    assert audit["passed"] == 0
    assert audit["checks_applied"] == ["internal_simulation_fields_in_body"]


def test_formal_markdown_uses_public_appendix_only() -> None:
    report = assemble_report(BODY, "included", "# 附录\n\n公开方法说明。")

    assert "公开方法说明" in report
    assert "appendix_b" not in report


def test_title_length_is_blocking_and_writer_has_deterministic_fallback() -> None:
    long_body = BODY.replace("测试事件舆情风险研判", "北京女大学生被父母骗至河南戒网瘾机构遭暴力限制自由并引发广泛争议舆情风险研判")
    audit = audit_body(long_body, {
        "blocking": ["title_length"],
        "title_max_chars": 30,
    })

    assert audit["fatal"] == 1
    normalized = _normalize_report_title(long_body)
    title = normalized.splitlines()[0].removeprefix("# ")
    assert len(title) <= 30
    assert title.endswith("舆情风险研判")
