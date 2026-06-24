"""白盒观测：风险分类摘要写入器。

单一职责：在分析层的 RiskClassifier 完成分类后，
将分类结果以结构化 JSON 写入 whitebox/ 目录。

可视化层从白盒文件读取数据，不自产。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def write_classification_summary(
    whitebox_dir: Path,
    *,
    primary_types: List[str],
    type_labels: List[str],
    primary_domain: Optional[str] = None,
    primary_domain_label: Optional[str] = None,
    **extra: Any,
) -> None:
    """将风险分类摘要写入 whitebox/classification_summary.json。

    Args:
        whitebox_dir: run_dir / whitebox 路径
        primary_types: Agent 输出的 top-3 类型 ID
        type_labels: 对应中文标签
        primary_domain: code 映射的一级域 ID
        primary_domain_label: 一级域中文标签
        extra: 额外字段（如 LLM 耗时、模型名等）
    """
    payload = {
        "primary_types": primary_types,
        "type_labels": type_labels,
        "primary_domain": primary_domain or "",
        "primary_domain_label": primary_domain_label or "",
    }
    payload.update(extra)

    whitebox_dir.mkdir(parents=True, exist_ok=True)
    path = whitebox_dir / "classification_summary.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
