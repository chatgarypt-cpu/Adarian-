"""
Memory Governance — Handoff 格式合规审计。

扫描 WorkflowBase/governance/handoffs/ 下所有存档文件，
检查 record_protocol 字段的存在性、枚举值合法性、时间戳格式。

用法：
    python3 WorkflowBase/governance/self-maint/audit_format.py

输出：
    合规文件数 / 不合规文件数 + 不合规明细
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

WORKYB = Path(__file__).resolve().parent.parent.parent.parent
HANDOFFS_DIR = WORKYB / "WorkflowBase" / "governance" / "handoffs"

# 当前合法的 record_protocol 枚举值
VALID_SKILLS = {
    "huihua-handoff", "closeout-gate", "post-review-framework",
    "code-reality-review", "memory-update",
}
VALID_RECORD_TYPES = {
    "session_handoff", "closeout", "review_report", "memory_update",
}
VALID_BLOCKER_STATUS = {"none", "present", "not_checked"}
VALID_ARTIFACT_QUALITY = {"pass", "pass_with_format_issues", "not_checked"}


def audit_file(path: Path) -> list[str]:
    """审计单个 handoff 文件。返回问题列表。"""
    issues = []
    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")

    # 1. 检查 record_protocol 区块
    rp_start = None
    rp_end = None
    for i, line in enumerate(lines):
        if line.strip() == "record_protocol:" and rp_start is None:
            rp_start = i
        elif rp_start is not None and rp_end is None:
            if line.startswith("---") or not line.strip():
                continue
            # 缩进的 YAML key
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("#"):
                continue
            # 检测下一个顶层 key（非缩进、非空行、非注释）
            if stripped and not line.startswith(" ") and not line.startswith("-"):
                rp_end = i
                break
    if rp_end is None:
        rp_end = len(lines)

    if rp_start is None:
        issues.append("missing_record_protocol")
        return issues

    # 提取 record_protocol 内容
    rp_lines = lines[rp_start + 1 : rp_end]
    rp_text = "\n".join(rp_lines)

    # 2. 检查 skill_loaded
    skill_match = re.search(r"skill_loaded:\s*(\S+)", rp_text)
    if not skill_match:
        issues.append("missing_skill_loaded")
    elif skill_match.group(1) not in VALID_SKILLS:
        issues.append(f"invalid_skill:{skill_match.group(1)}")

    # 3. 检查 record_type
    type_match = re.search(r"record_type:\s*(\S+)", rp_text)
    if not type_match:
        issues.append("missing_record_type")
    elif type_match.group(1) not in VALID_RECORD_TYPES:
        issues.append(f"invalid_record_type:{type_match.group(1)}")

    # 4. 检查 blocker_status
    bs_match = re.search(r"blocker_status:\s*(\S+)", rp_text)
    if not bs_match:
        issues.append("missing_blocker_status")
    elif bs_match.group(1) not in VALID_BLOCKER_STATUS:
        issues.append(f"invalid_blocker:{bs_match.group(1)}")

    # 5. 检查 artifact_quality
    aq_match = re.search(r"artifact_quality:\s*(\S+)", rp_text)
    if not aq_match:
        issues.append("missing_artifact_quality")
    elif aq_match.group(1) not in VALID_ARTIFACT_QUALITY:
        issues.append(f"invalid_quality:{aq_match.group(1)}")

    # 6. 检查 closeout_eligible
    ce_match = re.search(r"closeout_eligible:\s*(\S+)", rp_text)
    if not ce_match:
        issues.append("missing_closeout_eligible")
    elif ce_match.group(1) not in {"true", "false"}:
        issues.append(f"invalid_closeout_eligible:{ce_match.group(1)}")

    # 7. 检查头行时间戳格式
    first_line = lines[0].strip() if lines else ""
    time_match = re.search(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", first_line
    )
    if not time_match:
        issues.append("missing_timestamp_header")

    return issues


def main() -> int:
    if not HANDOFFS_DIR.exists():
        print(f"❌ handoffs 目录不存在: {HANDOFFS_DIR}")
        return 1

    files = sorted(HANDOFFS_DIR.glob("*.md"))
    if not files:
        print("❌ handoffs 目录下没有 .md 文件")
        return 1

    print(f"Memory Governance Handoff 格式合规审计")
    print(f"  目录: {HANDOFFS_DIR}")
    print(f"  文件数: {len(files)}")
    print()

    all_issues: dict[str, list[str]] = {}
    for f in files:
        issues = audit_file(f)
        if issues:
            all_issues[f.name] = issues

    # 输出
    clean = len(files) - len(all_issues)
    print(f"✅ 合规: {clean}/{len(files)}")
    print(f"❌ 不合规: {len(all_issues)}/{len(files)}")
    print()

    if all_issues:
        print("不合规明细:")
        for name, issues in sorted(all_issues.items()):
            print(f"  {name}:")
            for issue in issues:
                print(f"    - {issue}")
        print()

    # 按问题类型统计
    type_count: dict[str, int] = {}
    for issues in all_issues.values():
        for issue in issues:
            base = issue.split(":")[0]
            type_count[base] = type_count.get(base, 0) + 1

    if type_count:
        print("问题类型分布:")
        for t, c in sorted(type_count.items(), key=lambda x: -x[1]):
            print(f"  {t}: {c}")

    return 0 if not all_issues else 1


if __name__ == "__main__":
    sys.exit(main())
