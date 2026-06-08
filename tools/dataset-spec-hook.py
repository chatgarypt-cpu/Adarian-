#!/usr/bin/env python3
"""
Dataset Spec Gate — pre_tool_call hook

检测 write_file/patch 目标为 parser.py 或 dataset_fields.yaml 时，
自动运行 dataset spec 完整性检查。新增 dataset 字段后未更新 spec 则 block。

Wire protocol (stdin JSON -> stdout JSON):
  Input:  {"hook_event_name":"pre_tool_call","tool_name":"write_file","tool_input":{"path":"...",...}}
  Output: {"action":"block","message":"..."}  or  {"action":"continue"}
"""

import json
import subprocess
import sys
from pathlib import Path


HOOK_SCRIPT = Path(__file__).resolve()
REPO_ROOT = HOOK_SCRIPT.parent.parent  # tools/ -> 项目根


def _should_check(path: str) -> bool:
    """判断是否需要触发 spec 完整性检查。"""
    p = Path(path).resolve()
    try:
        rel = p.relative_to(REPO_ROOT)
    except ValueError:
        return False
    # parser.py 修改，或 spec 文件本身修改
    return str(rel) in (
        "src/parser.py",
        "spec/dataset_fields.yaml",
    )


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        return

    event = payload.get("hook_event_name", "")
    if event != "pre_tool_call":
        return

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("write_file", "patch"):
        return

    tool_input = payload.get("tool_input", {}) or {}
    target = (tool_input.get("path") or tool_input.get("file_path") or "")

    if not _should_check(target):
        return

    # 运行完整性检查
    check_script = str(REPO_ROOT / "tools" / "check_dataset_spec.py")
    result = subprocess.run(
        [sys.executable, check_script],
        capture_output=True, text=True, timeout=15,
    )

    if result.returncode != 0:
        json.dump({
            "action": "block",
            "message": (
                f"⛔ dataset 字段与 spec/dataset_fields.yaml 不同步。\n\n"
                f"你正在修改 {target}，但以下字段在 parser.py 中存在、"
                f"在 spec 中未标注：\n\n"
                f"{result.stdout}\n"
                f"请在 spec/dataset_fields.yaml 中补全标注后再修改。"
            ),
        }, sys.stdout, ensure_ascii=False)
    else:
        json.dump({"action": "continue"}, sys.stdout)


if __name__ == "__main__":
    main()
