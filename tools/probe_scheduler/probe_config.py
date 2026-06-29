"""探针调度器配置模型 — WorldConfig / ProbeConfig dataclass。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class WorldConfig:
    """单个世界的配置。"""
    name: str                     # "world_0"
    label: str                    # "Qwen 36B 基线" — 显示用
    model: str                    # "qwen36-35b"
    base_url: str                 # "http://<your-llm-gateway>:port/v1"
    api_key_from_env: str = "LLM_API_KEY"
    max_tokens: int = 8192
    fallback_model: Optional[str] = None       # 兜底模型名
    fallback_base_url: Optional[str] = None    # 兜底算力池

    def resolve_api_key(self) -> str:
        return os.getenv(self.api_key_from_env, "")


@dataclass
class ProbeConfig:
    """一次探针运行的完整配置。"""
    worlds: List[WorldConfig] = field(default_factory=list)
    seed_path: str = "seeds/test8.txt"
    batch_tag: str = "probe"               # 自定义标识，如 "pool_probe_1"
    max_concurrent: int = 5
    skip_phase4: bool = True               # 探针不需要报告生成

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ProbeConfig":
        import yaml
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        worlds = []
        for i, w in enumerate(raw.get("worlds", [])):
            worlds.append(WorldConfig(
                name=w.get("name", f"world_{i}"),
                label=w.get("label", w.get("model", f"world_{i}")),
                model=w["model"],
                base_url=w.get("base_url", ""),
                api_key_from_env=w.get("api_key_from_env", "LLM_API_KEY"),
                max_tokens=w.get("max_tokens", 8192),
                fallback_model=w.get("fallback_model"),
                fallback_base_url=w.get("fallback_base_url"),
            ))
        return cls(
            worlds=worlds,
            seed_path=raw.get("seed_path", "seeds/test8.txt"),
            batch_tag=raw.get("batch_tag", "probe"),
            max_concurrent=raw.get("max_concurrent", len(worlds)),
            skip_phase4=raw.get("skip_phase4", True),
        )

    def save_yaml(self, path: str | Path) -> None:
        import yaml
        data = {
            "seed_path": self.seed_path,
            "batch_tag": self.batch_tag,
            "max_concurrent": self.max_concurrent,
            "skip_phase4": self.skip_phase4,
            "worlds": [
                {
                    "name": w.name,
                    "label": w.label,
                    "model": w.model,
                    "base_url": w.base_url,
                    "api_key_from_env": w.api_key_from_env,
                    "max_tokens": w.max_tokens,
                    "fallback_model": w.fallback_model,
                    "fallback_base_url": w.fallback_base_url,
                }
                for w in self.worlds
            ],
        }
        Path(path).write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
