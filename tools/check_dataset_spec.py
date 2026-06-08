#!/usr/bin/env python3
"""
dataset 字段完整性检查 — 静态验证 parser.py 中的 dataset 字段
都在 spec/dataset_fields.yaml 中有标注。

双模：
  1. Standalone:   ./check_dataset_spec.py
  2. Hook (stdin JSON -> stdout JSON):
     echo '{"hook_event_name":"pre_tool_call",...}' | ./check_dataset_spec.py

用法：
  python3 tools/check_dataset_spec.py          # 完整检查
  python3 tools/check_dataset_spec.py --hook   # hook 模式
"""

import ast
import json
import re
import sys
from pathlib import Path


# ── 项目根 ───────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
PARSER_PATH = REPO_ROOT / "src" / "parser.py"
SPEC_PATH = REPO_ROOT / "spec" / "dataset_fields.yaml"


# ── parser.py 字段提取 ────────────────────────
def _extract_dataset_keys_from_parser() -> set:
    """用 AST 提取 parser.py 中 dataset dict 的所有叶子路径。"""
    source = PARSER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    dataset_node = _find_dataset_assignment(tree)
    if dataset_node is None:
        print("⚠  未在 parser.py 中找到 dataset = {...} 赋值", file=sys.stderr)
        return set()

    paths = set()
    _walk_dict(dataset_node, paths, prefix="")
    return paths


def _find_dataset_assignment(tree):
    """找到 dataset = { ... } 那个赋值节点。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "dataset":
                    return node.value
    return None


def _walk_dict(node, paths: set, prefix: str):
    """递归遍历 dict 字面量，收集叶子路径。"""
    if isinstance(node, ast.Dict):
        for key_node, val_node in zip(node.keys, node.values):
            if key_node is None:  # **kwargs
                continue
            key = _extract_key(key_node)
            if key is None:
                continue
            full_path = f"{prefix}.{key}" if prefix else key
            if isinstance(val_node, ast.Dict):
                _walk_dict(val_node, paths, full_path)
            elif isinstance(val_node, ast.List) and val_node.elts:
                # 检查 list element 是不是 dict
                first = val_node.elts[0]
                if isinstance(first, ast.Dict):
                    # 这是个 list[dict] —— 用 [*] 占位
                    list_prefix = f"{full_path}[*]"
                    _walk_dict(first, paths, list_prefix)
                else:
                    paths.add(full_path)
            else:
                paths.add(full_path)
    elif isinstance(node, ast.IfExp):
        _walk_dict(node.body, paths, prefix)
        _walk_dict(node.orelse, paths, prefix)


_KEY_PATTERNS = [
    re.compile(r"^['\"](.+)['\"]$"),          # "foo" or 'foo'
    re.compile(r"^f['\"](.+)['\"]$"),         # f"foo"
]


def _extract_key(key_node) -> str | None:
    if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
        return key_node.value
    if isinstance(key_node, ast.JoinedStr):  # f-string
        parts = []
        for part in key_node.values:
            if isinstance(part, ast.Constant):
                parts.append(str(part.value))
            else:
                parts.append("{expr}")
        return "".join(parts)
    return None


# ── YAML spec 读取 ────────────────────────────
def _load_spec_paths() -> set:
    """从 dataset_fields.yaml 加载所有 path。"""
    import yaml
    spec_data = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    paths = set()
    for entry in spec_data:
        if isinstance(entry, dict) and "path" in entry:
            paths.add(entry["path"])
    return paths


# ── 检查流程 ──────────────────────────────────
def check():
    """主检查。返回 (spec_paths, parser_paths, missing_in_spec, missing_in_parser)。"""
    if not PARSER_PATH.exists():
        print(f"✗ parser.py 不存在: {PARSER_PATH}", file=sys.stderr)
        sys.exit(1)
    if not SPEC_PATH.exists():
        print(f"✗ dataset_fields.yaml 不存在: {SPEC_PATH}", file=sys.stderr)

    spec_paths = _load_spec_paths()
    parser_paths = _extract_dataset_keys_from_parser()

    # parser 有但 spec 没有 → 缺标注
    missing_in_spec = sorted(parser_paths - spec_paths)
    # spec 有但 parser 没有 → 可能是正确的（废弃字段）
    # 不报错，只当 info

    return spec_paths, parser_paths, missing_in_spec


# ── 输出格式化 ────────────────────────────────
def format_report(spec_paths, parser_paths, missing):
    lines = []
    lines.append(f"spec 标注字段: {len(spec_paths)}")
    lines.append(f"parser 实际字段: {len(parser_paths)}")
    if missing:
        lines.append(f"\n⚠  以下 {len(missing)} 个字段在 parser.py 中存在，")
        lines.append(f"   但在 spec/dataset_fields.yaml 中未标注：")
        for p in missing:
            lines.append(f"  ─ {p}")
    else:
        lines.append("\n✓ 所有 parser 字段都已标注在 dataset_fields.yaml 中")
    return "\n".join(lines)


# ── 入口 ──────────────────────────────────────
def main():
    is_hook = "--hook" in sys.argv

    if not PARSER_PATH.exists():
        msg = f"✗ 未找到 {PARSER_PATH}"
        if is_hook:
            json.dump({"action": "block", "message": msg}, sys.stdout)
        else:
            print(msg)
        sys.exit(1)

    spec_paths, parser_paths, missing = check()

    if is_hook:
        if missing:
            json.dump({
                "action": "warn",
                "message": (
                    f"dataset 字段与 spec 不同步。\n"
                    f"以下 {len(missing)} 个字段在 parser.py 中存在，"
                    f"但未在 spec/dataset_fields.yaml 中标注：\n"
                    + "\n".join(f"  ─ {p}" for p in missing)
                ),
            }, sys.stdout, ensure_ascii=False)
        else:
            json.dump({"action": "continue"}, sys.stdout)
    else:
        print(format_report(spec_paths, parser_paths, missing))

    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
