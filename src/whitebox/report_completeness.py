"""Phase 4 report completeness checks."""

from __future__ import annotations

import re
from typing import Dict, List


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


def check_report_completeness(markdown_text: str) -> Dict[str, object]:
    """Check whether a Phase 4 markdown report is complete enough to deliver."""
    text = markdown_text or ""
    report_char_count = len(text)
    missing_required_sections = _missing_required_sections(text)
    report_ends_cleanly = _ends_cleanly(text)

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
    }
