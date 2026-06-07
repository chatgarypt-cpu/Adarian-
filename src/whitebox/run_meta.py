"""运行元数据写入器。

单一职责：在 run_dir 根下写入 run_meta.json（机器索引用）。
不再管理 whitebox 产物观测。
"""

import json
from pathlib import Path

import config


def write_run_meta(run_context: dict, seed_file: Path, status: str, started_at: str, **extra) -> None:
    """写入 run_meta.json（run_dir 根，下游机器索引用）。"""
    outputs = run_context["outputs"]
    payload = {
        "batch_id": run_context.get("batch_id"),
        "batch_dir": str(run_context.get("batch_dir")) if run_context.get("batch_dir") else None,
        "run_id": run_context["run_id"],
        "seed_file": str(seed_file),
        "seed_copy": str(run_context["seed_copy"]),
        "run_dir": str(run_context["run_dir"]),
        "started_at": started_at,
        "provider": config.LLM_PROVIDER,
        "model": config.get_model_name(),
        "status": status,
        "outputs": {key: str(path) for key, path in outputs.items()},
    }
    payload.update(extra)
    with open(outputs["run_meta"], "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
