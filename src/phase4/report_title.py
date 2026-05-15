"""Title and metadata header helpers for Phase 4 reports."""

import re

from src.schemas import Phase4Output


REPORT_TITLE_SUFFIX = "舆情风险研判报告"
TITLE_MAX_CHARS = 25


def _normalized_report_title(event_name: str) -> str:
    """Create a short government-report title without changing report_meta."""
    subject = _extract_title_subject(event_name)
    controversy = _infer_title_controversy(event_name)
    subject = _normalize_title_subject_for_controversy(subject, controversy, event_name)
    title = _compose_report_title(subject, controversy)
    if len(title) <= TITLE_MAX_CHARS:
        return title

    connector = _title_controversy_connector(subject, controversy)
    available = max(2, TITLE_MAX_CHARS - len(connector) - len(REPORT_TITLE_SUFFIX))
    return f"{subject[:available]}{connector}{REPORT_TITLE_SUFFIX}"


def _extract_title_subject(event_name: str) -> str:
    text = re.sub(r"\s+", "", event_name or "")
    text = re.sub(r"^\d{4}年?\d{0,2}月?\d{0,2}日?", "", text)
    for delimiter in ("因", "就", "在", "发布", "回应", "被", "引发", "涉嫌", "出现", "发生"):
        if delimiter in text:
            text = text.split(delimiter, 1)[0]
            break
    text = re.split(r"[，,。；;：:、（）()【】\[\]\s]", text, maxsplit=1)[0]
    text = re.sub(r"(事件|争议|舆情|相关|问题)+$", "", text)
    if not text:
        return "相关事件"
    return text[:8]


def _normalize_title_subject_for_controversy(subject: str, controversy: str, event_name: str) -> str:
    text = re.sub(r"\s+", "", event_name or "")
    if controversy == "营销争议" and "营销" in text:
        prefix = text.split("营销", 1)[0]
        prefix = re.sub(r"(文案|海报|广告|内容)+$", "", prefix)
        candidate = re.split(r"[，,。；;：:、（）()【】\[\]\s]", prefix + "营销", maxsplit=1)[0]
        candidate = re.sub(r"(文案|海报|广告|内容|事件|争议)+$", "", candidate)
        if candidate:
            return candidate[:10]
    return subject


def _infer_title_controversy(event_name: str) -> str:
    text = event_name or ""
    rules = [
        (("营销", "海报", "广告", "母亲节"), "营销争议"),
        (("执法", "劝烟", "公安", "交警", "处罚"), "执法争议"),
        (("质量", "产品", "消费", "投诉"), "产品质量争议"),
        (("学校", "校园", "教育"), "校园治理争议"),
        (("食品", "安全", "事故"), "安全事件"),
        (("人事", "招聘", "裁员"), "人事争议"),
        (("回应", "声明", "道歉"), "舆情回应争议"),
    ]
    for keywords, label in rules:
        if any(keyword in text for keyword in keywords):
            return label
    return "舆情争议"


def _title_controversy_connector(subject: str, controversy: str) -> str:
    stems = {
        "营销争议": "营销",
        "执法争议": "执法",
        "产品质量争议": "产品质量",
        "校园治理争议": "校园治理",
        "安全事件": "安全",
        "人事争议": "人事",
        "舆情回应争议": "舆情回应",
        "舆情争议": "舆情",
    }
    stem = stems.get(controversy, "")
    if subject.endswith(controversy):
        return ""
    if stem and subject.endswith(stem):
        if controversy.endswith("争议"):
            return "争议"
        if controversy.endswith("事件"):
            return "事件"
    return controversy


def _compose_report_title(subject: str, controversy: str) -> str:
    return f"{subject}{_title_controversy_connector(subject, controversy)}{REPORT_TITLE_SUFFIX}"


def _metadata_header(phase4_output: Phase4Output) -> str:
    meta = phase4_output.report_meta
    return "\n".join([
        f"# {_normalized_report_title(meta.event_name)}",
        "",
        f"报告类型：{meta.report_type}",
        f"生成时间：{meta.generated_at}",
        f"模拟轮次：{meta.total_ticks}轮",
        f"风险等级：{phase4_output.risk_level_label}",
        f"阅读模式：{phase4_output.audience_mode.value}",
        "",
        "---",
        "",
    ])


def _ensure_metadata_header(markdown: str, phase4_output: Phase4Output) -> str:
    generated_at = phase4_output.report_meta.generated_at
    if generated_at in markdown[:800]:
        return markdown
    return _metadata_header(phase4_output) + markdown.lstrip()


def _normalize_report_title_line(markdown: str, phase4_output: Phase4Output) -> str:
    title = _normalized_report_title(phase4_output.report_meta.event_name)
    normalized_lines = []
    h1_seen = False
    for line in markdown.splitlines():
        if re.match(r"^#\s+", line):
            if not h1_seen:
                normalized_lines.append(f"# {title}")
                h1_seen = True
            continue
        normalized_lines.append(line)
    if h1_seen:
        return "\n".join(normalized_lines)
    return f"# {title}\n\n{markdown.lstrip()}"
