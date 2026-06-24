"""
simulation_dataset → YAML with spec comments 生成器。

读 simulation_dataset.json，对照 spec/dataset_fields.yaml 的规格定义，
生成一份带行内注释的 simulation_dataset_spec.yaml，给人读。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def _path_to_pattern(path: str) -> str:
    """把 'source_context.event_entities.0.name' 转成匹配模式 'source_context.event_entities[].name'。"""
    return re.sub(r"\.\d+", "[]", path)


def _indent(text: str, level: int) -> str:
    return "  " * level + text


def _format_value(val: Any, indent_level: int) -> str:
    """把 Python 值格式化为 YAML 内联值。"""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        # 多行字符串用 | 块格式
        if "\n" in val:
            lines = val.rstrip("\n").split("\n")
            result = "|\n"
            for line in lines:
                result += _indent(line, indent_level + 1) + "\n"
            return result.rstrip("\n")
        # 需要引号的情况
        if ":" in val or "#" in val or val.startswith(" ") or val.endswith(" ") or val == "":
            return json.dumps(val, ensure_ascii=False)
        return val
    return json.dumps(val, ensure_ascii=False)


def generate_spec_yaml(
    dataset: Dict[str, Any],
    spec: Dict[str, Any],
) -> str:
    """生成带注释的 YAML 字符串。"""
    lines: list[str] = []
    lines.append("")
    lines.append("# =============================================================================")
    lines.append("# simulation_dataset_spec.yaml — 带规格说明的仿真数据集 YAML 版")
    lines.append("#")
    lines.append("# 由 generator 根据 simulation_dataset.json + spec/dataset_fields.yaml 自动生成。")
    lines.append("# 字段定义见 spec/dataset_fields.yaml，此处嵌入注释以便人读。")
    lines.append("# JSON 版（simulation_dataset.json）是下游机器契约，本 YAML 仅为辅助阅读。")
    lines.append("# =============================================================================")
    lines.append("")

    _write_node(lines, dataset, spec, path="", indent=0)
    return "\n".join(lines)


def _write_node(
    lines: list[str],
    node: Any,
    spec: Dict[str, Any],
    *,
    path: str,
    indent: int,
    parent_key: Optional[str] = None,
) -> None:
    """递归写入 YAML 节点（含注释）。"""
    if isinstance(node, dict):
        for key, val in node.items():
            child_path = f"{path}.{key}" if path else key

            # 查找规格说明
            pattern = _path_to_pattern(child_path)
            spec_entry = spec.get(pattern)

            # 写注释块（如果有规格）
            if spec_entry:
                desc = spec_entry.get("description", "")
                source = spec_entry.get("source", "")
                usage = spec_entry.get("usage", "")
                computation = spec_entry.get("computation", "")
                allowed = spec_entry.get("allowed_values")

                if desc:
                    lines.append(_indent(f"# {desc}", indent))
                if source:
                    lines.append(_indent(f"# 来源: {source}", indent))
                if computation:
                    lines.append(_indent(f"# 计算: {computation}", indent))
                if usage:
                    lines.append(_indent(f"# 可用作: {usage}", indent))
                if allowed and isinstance(allowed, list):
                    vals_str = ", ".join(str(v) for v in allowed)
                    lines.append(_indent(f"# 枚举值: [{vals_str}]", indent))

            # 写 key
            key_yaml = f"{key}:"

            if isinstance(val, dict):
                lines.append(_indent(key_yaml, indent))
                _write_node(lines, val, spec, path=child_path, indent=indent + 1)

            elif isinstance(val, list):
                lines.append(_indent(key_yaml, indent))
                _write_node(lines, val, spec, path=child_path, indent=indent + 1)

            else:
                # 标量值，一行搞定
                val_str = _format_value(val, indent)
                lines.append(_indent(f"{key_yaml} {val_str}", indent))

    elif isinstance(node, list):
        for i, item in enumerate(node):
            item_path = f"{path}.{i}"

            # List item 用 - 开头
            if isinstance(item, dict):
                lines.append(_indent("-", indent))
                # dict item 的内容要缩进 +2（在 - 的基础上）
                for key, val in item.items():
                    child_path = f"{item_path}.{key}"
                    pattern = _path_to_pattern(child_path)
                    spec_entry = spec.get(pattern)

                    if spec_entry:
                        # 只写最核心的信息，避免 item 级别注释太多
                        desc = spec_entry.get("description", "")
                        if desc:
                            lines.append(_indent(f"# {desc}", indent + 1))

                    key_yaml = f"{key}:"
                    if isinstance(val, dict):
                        lines.append(_indent(key_yaml, indent + 1))
                        _write_node(lines, val, spec, path=child_path, indent=indent + 2)
                    elif isinstance(val, list):
                        lines.append(_indent(key_yaml, indent + 1))
                        _write_node(lines, val, spec, path=child_path, indent=indent + 2)
                    else:
                        val_str = _format_value(val, indent + 1)
                        lines.append(_indent(f"{key_yaml} {val_str}", indent + 1))

            elif isinstance(item, list):
                lines.append(_indent("-", indent))
                _write_node(lines, item, spec, path=item_path, indent=indent + 1)

            else:
                val_str = _format_value(item, indent)
                lines.append(_indent(f"- {val_str}", indent))

    # 标量不用额外处理（由上层 dict 写入）


def generate_spec_yaml_from_files(
    dataset_path: str | Path,
    spec_path: str | Path,
    output_path: str | Path,
) -> None:
    """从文件读写并生成。"""
    dataset_path = Path(dataset_path)
    spec_path = Path(spec_path)
    output_path = Path(output_path)

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f) or {}

    yaml_str = generate_spec_yaml(dataset, spec)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)
