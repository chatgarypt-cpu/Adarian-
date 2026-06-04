"""
Memory Governance — Handoff 里程碑压缩。

由 closeout-gate 触发（也可手动运行）：
  1. 扫描 handoffs/ 下所有存档
  2. 提取 task_id + closeout 信息
  3. 去 tasks/archived/ 查找对应 closeout 证据
  4. 无 closeout 证据 → 跳过
  5. 有 closeout 证据 → 合并成 milestone 摘要

用法：
    python3 WorkflowBase/governance/self-maint/compress_handoffs.py

输出：
    milestones/<milestone_id>/
      milestone_snapshot.md
      task_index.yaml

规则：
  - 不删除原始 handoff
  - 有 closeout 才压缩
  - milestone 按任务分区，不按时间分区
"""
from __future__ import annotations

import re
import sys
import yaml
from datetime import datetime
from pathlib import Path

WORKYB = Path(__file__).resolve().parent.parent.parent.parent
HANDOFFS_DIR = WORKYB / "WorkflowBase" / "governance" / "handoffs"
MILESTONES_DIR = WORKYB / "WorkflowBase" / "governance" / "milestones"
ARCHIVED_TASKS_DIR = WORKYB / "tasks" / "archived"

# 从 handoff 文件名提取日期的正则
DATE_FROM_FILENAME = re.compile(r"(\d{4}-\d{2}-\d{2})T")


def extract_task_ids(content: str) -> list[str]:
    """从 handoff 内容中提取 task_id 引用（支持多种格式）。"""
    ids = []
    # task_id: xxx
    for m in re.finditer(r"task_id[:\s]+(\S+)", content):
        ids.append(m.group(1))
    # tasks/active/<id>/ 或 tasks/archived/<domain>/<id>/
    for m in re.finditer(r"tasks/(?:active|archived)/[^/]+/([^/\s]+)", content):
        ids.append(m.group(1))
    return list(set(ids))


def has_closeout_evidence(task_id: str) -> bool:
    """检查 task_id 在 archived 目录下是否有 closeout 记录。"""
    # 在所有 archived 子目录中搜索
    if not ARCHIVED_TASKS_DIR.exists():
        return False
    for domain_dir in ARCHIVED_TASKS_DIR.iterdir():
        if not domain_dir.is_dir():
            continue
        task_dir = domain_dir / task_id
        if not task_dir.exists():
            continue
        # 检查 closeout 证据文件
        task_status = task_dir / "task_status.yaml"
        if task_status.exists():
            content = task_status.read_text(encoding="utf-8")
            if "closeout" in content or "closed" in content or "status: closed" in content:
                return True
        # 也检查 summary
        summary = task_dir / "summary" / "summary.md"
        if summary.exists():
            content = summary.read_text(encoding="utf-8")
            if "closeout" in content or "closed" in content:
                return True
        # 也检查 result.json
        result = task_dir / "runtime" / "result.json"
        if result.exists():
            try:
                import json
                data = json.loads(result.read_text(encoding="utf-8"))
                if data.get("runtime_state") in ("executor_completed",):
                    return True
            except Exception:
                pass
    return False


def collect_milestones() -> dict[str, list[Path]]:
    """扫描 handoff 文件，按可压缩的任务分区。"""
    if not HANDOFFS_DIR.exists():
        print(f"❌ handoffs 目录不存在: {HANDOFFS_DIR}")
        return {}

    files = sorted(HANDOFFS_DIR.glob("*.md"))
    if not files:
        print("handoffs 目录为空")
        return {}

    # 按分区 accumulating
    partitions: dict[str, list[Path]] = {}

    for f in files:
        content = f.read_text(encoding="utf-8")
        task_ids = extract_task_ids(content)

        # 检查是否有 closeout 证据
        has_closeout = any(has_closeout_evidence(tid) for tid in task_ids)

        if not has_closeout:
            # 无 closeout → 不可压缩，跳过
            continue

        # 确定分区 key：取第一个有关闭证据的 task_id
        closeout_key = "unknown"
        for tid in task_ids:
            if has_closeout_evidence(tid):
                closeout_key = tid
                break

        # 从 task_id 推断分区名（取前缀部分）
        partition = closeout_key.split("-")[0] if "-" in closeout_key else closeout_key

        if partition not in partitions:
            partitions[partition] = []
        partitions[partition].append(f)

    return partitions


def generate_milestone(partition: str, files: list[Path]) -> None:
    """为分区生成 milestone。"""
    milestone_id = f"{partition}-{datetime.now().strftime('%Y%m%d')}"
    milestone_dir = MILESTONES_DIR / milestone_id
    milestone_dir.mkdir(parents=True, exist_ok=True)

    # 提取覆盖的时间范围
    dates = []
    for f in files:
        m = DATE_FROM_FILENAME.search(f.name)
        if m:
            dates.append(m.group(1))

    # 提取调用的 task_id 汇总
    all_task_ids: list[str] = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        all_task_ids.extend(extract_task_ids(content))
    all_task_ids = sorted(set(all_task_ids))

    # 提取有关闭证据的 task_id
    closed_ids = [tid for tid in all_task_ids if has_closeout_evidence(tid)]

    time_range = f"{min(dates)} → {max(dates)}" if dates else "unknown"

    # 写入 milestone_snapshot.md
    snapshot = f"""# Milestone — {milestone_id}

> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 覆盖
- 分区: {partition}
- 时间范围: {time_range}
- 原始 handoff 数: {len(files)}

## 已 closeout 任务
"""
    for tid in closed_ids:
        snapshot += f"- {tid}\n"

    snapshot += f"""
## 提及的其他任务
"""
    for tid in all_task_ids:
        if tid not in closed_ids:
            snapshot += f"- {tid} (无 closeout 证据)\n"

    snapshot += f"""
## 原始 handoff
"""
    for f in files:
        snapshot += f"- {f.name}\n"

    (milestone_dir / "milestone_snapshot.md").write_text(snapshot, encoding="utf-8")

    # 写入 task_index.yaml
    index = {
        "milestone_id": milestone_id,
        "generated_at": datetime.now().isoformat(),
        "handoff_count": len(files),
        "handoff_files": [f.name for f in files],
        "tasks_closed": closed_ids,
        "tasks_mentioned": all_task_ids,
    }
    (milestone_dir / "task_index.yaml").write_text(
        yaml.dump(index, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    print(f"  ✅ 生成 milestone: {milestone_id}/")
    print(f"     - milestone_snapshot.md")
    print(f"     - task_index.yaml")
    print(f"     覆盖 {len(files)} 个 handoff，{len(closed_ids)} 个已 closeout 任务")


def main() -> int:
    print("=" * 60)
    print("  Memory Governance — Handoff 里程碑压缩")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    partitions = collect_milestones()

    if not partitions:
        print("没有可压缩的 handoff（所有手写记录均无 closeout 证据）")
        print("或 handoffs/ 目录为空")
        return 0

    print(f"发现 {len(partitions)} 个可压缩分区:")
    for partition, files in sorted(partitions.items()):
        print(f"  {partition}: {len(files)} 个 handoff")
    print()

    MILESTONES_DIR.mkdir(parents=True, exist_ok=True)

    for partition, files in sorted(partitions.items()):
        generate_milestone(partition, files)

    print()
    print(f"milestones 目录: {MILESTONES_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
