"""Phase 4 report completeness checks."""

from __future__ import annotations

import re
from typing import Any, Dict, List


REQUIRED_SECTION_GROUPS = [
    ("舆情概要",),
    ("演化分析",),
    ("风险研判",),
    ("对策建议",),
    ("附录",),
]

FINAL_SECTION_HEADINGS = {
    "## 五、附录",
    "## 附录",
    "### 五、附录",
    "### 附录",
}


def _count_chinese_chars(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def _missing_required_sections(markdown_text: str) -> List[str]:
    missing = []
    for group in REQUIRED_SECTION_GROUPS:
        if not any(section in markdown_text for section in group):
            missing.append(" / ".join(group))
    return missing


def _last_non_empty_line(markdown_text: str) -> str:
    for line in reversed(markdown_text.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _find_last_heading(markdown_text: str):
    matches = list(re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", markdown_text))
    if not matches:
        return None
    return matches[-1]


def _has_unclosed_code_fence(markdown_text: str) -> bool:
    fence_count = 0
    for line in markdown_text.splitlines():
        if line.strip().startswith("```"):
            fence_count += 1
    return fence_count % 2 == 1


def _is_table_half_line(line: str) -> bool:
    if "|" not in line:
        return False
    stripped = line.strip()
    return stripped.startswith("|") != stripped.endswith("|")


def _ends_cleanly(markdown_text: str) -> bool:
    last_line = _last_non_empty_line(markdown_text)
    if not last_line:
        return False
    if _has_unclosed_code_fence(markdown_text):
        return False
    if _is_table_half_line(last_line):
        return False
    if re.fullmatch(r"[-•]", last_line):
        return False
    if re.fullmatch(r"\d+\.", last_line):
        return False
    if last_line.endswith(("：", ":")):
        return False
    if re.fullmatch(r"#{1,6}\s+.+", last_line):
        return False
    return True


def _tail_truncation_reason(markdown_text: str) -> str:
    last_heading = _find_last_heading(markdown_text)
    if last_heading is None:
        return ""

    heading_text = last_heading.group(0).strip()
    if heading_text not in FINAL_SECTION_HEADINGS:
        return ""

    body_after_heading = markdown_text[last_heading.end():]
    if _count_chinese_chars(body_after_heading) < 80:
        return "final section has heading but insufficient body"

    return ""


REALITY_INFLECTION_PATTERNS = (
    r"现实舆情已经出现拐点",
    r"现实舆情出现拐点",
    r"全网舆情发生转折",
    r"全网舆情已经转向",
    r"公众态度已经改变",
    r"公众态度发生转折",
    r"舆情已经发生转折",
    r"传播拐点已经出现",
    r"真实舆情拐点",
    r"现实传播拐点",
)


def _count_json_inflection_points(final_report_data: Dict[str, Any] | None) -> int:
    if not isinstance(final_report_data, dict):
        return 0
    inflection_points = final_report_data.get("inflection_points")
    if isinstance(inflection_points, list):
        return len(inflection_points)
    return 0


def _reality_inflection_claim_detected(markdown_text: str) -> bool:
    return any(re.search(pattern, markdown_text) for pattern in REALITY_INFLECTION_PATTERNS)


def _inflection_points_markdown_claim(markdown_text: str) -> str:
    if _reality_inflection_claim_detected(markdown_text):
        return "reality_claim_detected"
    if "本轮模拟未发现显著模拟关键变化点" in markdown_text:
        return "empty_claim"
    if re.search(r"第[一二三四五六七八九十\d]+轮.*模拟关键变化点", markdown_text):
        return "non_empty_claim"
    if "以下变化点来自代码侧模拟关键变化点识别结果" in markdown_text:
        return "non_empty_claim"
    if "值得关注的模拟关键变化点" in markdown_text:
        return "non_empty_claim"
    if "模拟关键变化点" in markdown_text:
        return "non_empty_claim"
    return "no_claim"


def _inflection_points_consistency(
    json_count: int,
    markdown_claim: str,
    json_available: bool,
) -> str:
    if not json_available:
        return "not_applicable"
    if markdown_claim == "reality_claim_detected":
        return "mismatch"
    if json_count == 0 and markdown_claim == "empty_claim":
        return "match"
    if json_count == 0 and markdown_claim == "non_empty_claim":
        return "mismatch"
    if json_count > 0 and markdown_claim == "non_empty_claim":
        return "match"
    if json_count > 0 and markdown_claim == "empty_claim":
        return "mismatch"
    return "not_applicable"


def _inflection_consistency_issue(consistency: str) -> str:
    if consistency == "mismatch":
        return "inflection_points markdown claim does not match final_report.json"
    return ""


def check_report_completeness(
    markdown_text: str,
    final_report_data: Dict[str, Any] | None = None,
) -> Dict[str, object]:
    """Check whether a Phase 4 markdown report is complete enough to deliver."""
    text = markdown_text or ""
    report_char_count = len(text)
    missing_required_sections = _missing_required_sections(text)
    report_ends_cleanly = _ends_cleanly(text)
    json_available = isinstance(final_report_data, dict)
    inflection_points_json_count = _count_json_inflection_points(final_report_data)
    inflection_points_markdown_claim = _inflection_points_markdown_claim(text)
    inflection_points_consistency = _inflection_points_consistency(
        inflection_points_json_count,
        inflection_points_markdown_claim,
        json_available,
    )
    empty_inflection_text_present = "本轮模拟未发现显著模拟关键变化点" in text
    reality_inflection_claim_detected = _reality_inflection_claim_detected(text)
    inflection_consistency_issue = _inflection_consistency_issue(
        inflection_points_consistency
    )

    report_truncated = False
    truncation_reason = ""

    tail_reason = _tail_truncation_reason(text)
    if tail_reason:
        report_truncated = True
        truncation_reason = tail_reason

    if not report_ends_cleanly:
        report_truncated = True
        if not truncation_reason:
            truncation_reason = "report does not end cleanly"

    if report_char_count < 800:
        report_truncated = True
        if not truncation_reason:
            truncation_reason = "report too short"

    score = 1.0
    score -= 0.15 * len(missing_required_sections)
    if report_truncated:
        score -= 0.35
    if not report_ends_cleanly:
        score -= 0.20
    report_completeness_score = max(0.0, round(score, 2))

    return {
        "report_char_count": report_char_count,
        "report_truncated": report_truncated,
        "truncation_reason": truncation_reason,
        "report_ends_cleanly": report_ends_cleanly,
        "missing_required_sections": missing_required_sections,
        "report_completeness_score": report_completeness_score,
        "inflection_points_json_count": inflection_points_json_count,
        "inflection_points_markdown_claim": inflection_points_markdown_claim,
        "inflection_points_consistency": inflection_points_consistency,
        "empty_inflection_text_present": empty_inflection_text_present,
        "reality_inflection_claim_detected": reality_inflection_claim_detected,
        "inflection_consistency_issue": inflection_consistency_issue,
    }
