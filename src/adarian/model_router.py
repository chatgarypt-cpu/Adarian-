"""Lightweight model router for the internal LLM gateway.

Route task types to specific models on a configurable LLM endpoint
(OpenAI-compatible, use --noproxy for internal gateways).

Usage:
    from adarian.model_router import select
    model = select("report_generation") # → "qwen36-35b"
    model = select("quick_test")        # → "qwen3-30b-tke"
    model = select("report_generation", override="fast")  # → "qwen36-35b"
"""

from __future__ import annotations

from typing import Optional

# ── Task → model ID ──────────────────────────────────────
# Keyed by task type. Value is either a direct model ID
# or an alias referencing the ALIASES dict below.

ROUTES: dict[str, str] = {
    # ── Adarian pipeline phases ──
    "phase1_extraction":  "qwen36-35b",         # fastest + newest (0.3s)
    "phase2_topology":    "qwen36-35b",         # fast enough
    "phase3_tick":        "qwen36-35b",         # simulation reasoning
    "phase3_parser":      "qwen36-35b",         # fast aggregation
    "report_generation":  "qwen36-35b",         # report narrative generation

    # ── Code & review ──
    "code_generation":    "qwen36-35b",
    "code_review":        "qwen36-35b",
    "analysis":           "qwen36-35b",
    "planning":           "qwen36-35b",

    # ── Lightweight / dev ──
    "format_check":       "qwen3-30b-tke",
    "bypass_compare":     "qwen3-30b-tke",
    "quick_test":         "qwen3-30b-tke",
    "embedding":          "bge-m3-tke",

    # ── Fallback ──
    "fallback":           "deepseek-v4-flash",

    # ── Alias shortcuts ──
    "fast":               "qwen36-35b",
    "strong":             "qwen36-35b",
    "cheap":              "qwen3-30b-tke",
    "largest":            "qwen-35-122b-sg",
}

DEFAULT = "qwen36-35b"

# ── Full model list for reference ────────────────────────

CATALOG: dict[str, str] = {
    # ── 对话 / 文本生成（19 + 3 新增） ──
    "vllm":               "vLLM (0.2s, 响应可能为空)",
    "qwen3-30b-tke":      "Qwen 3 30B TKE (0.3s, 推荐 ⭐)",
    "qwen3-80b-tke":      "Qwen 3 80B TKE (0.3s, 更强同速)",
    "qwen3-80b-tke-jyt":  "Qwen 3 80B TKE — JYT 版 (0.3s)",
    "qwen3-30b-a3b":      "Qwen 3 30B A3B MoE (0.3s)",
    "qwen3-80b-a3b":      "Qwen 3 80B A3B MoE (0.3s)",
    "qwen36-35b":         "Qwen 3.6 35B (0.3s)",
    "qwen36-35b-tke":     "Qwen 3.6 35B TKE (0.4s)",
    "qwen36-35b-claude":  "Qwen 3.6 35B Claude 风格 (0.4s)",
    "minimax":            "MiniMax (0.4s)",
    "qwen36-27b":         "Qwen 3.6 27B (0.5s)",
    "qwen36-27b-jyt":     "Qwen 3.6 27B JYT (0.6s)",
    "qwen36-35b-tzb":     "Qwen 3.6 35B TZB (0.6s)",
    "qwen3-32b-tke":      "Qwen 3 32B TKE (0.5s)",
    "qwen3-32b":          "Qwen 3 32B (0.6s)",
    "minimax-openai":     "MiniMax OpenAI 兼容 (0.7s)",
    "qwen36-27b-tke":     "Qwen 3.6 27B TKE (0.7s)",
    "qwen-35-122b-sg":    "Qwen 3.5 122B SG (0.8s, 最大)",
    "sg":                 "SG 模型 (0.9s)",
    # ── 新增（2026-06-06 内网部署） ──
    "deepseek-v4f":       "DeepSeek v4 Flash 内网版 (新增)",
    "deepseek-v4f-cc":    "DeepSeek v4 Flash — CC 变体 (新增)",
    "ds":                 "DeepSeek 内网基础版 (新增)",
    # ── Embedding ──
    "bge-m3-tke":         "BAAI bge-m3 TKE embedding 1024d (0.3s)",
    "bge-m3":             "BAAI bge-m3 embedding 1024d (0.5s)",
    # ── 不可用（未加载/超时） ──
    "qwen35-122b":        "Qwen 3.5 122B — ❌ 不可用（超时）",
    "qwen35-122b-a10b":   "Qwen 3.5 122B A10B 量化 — ❌ 不可用（超时）",
    "qwen35-122b-claude": "Qwen 3.5 122B Claude 风格 — ❌ 不可用（超时）",
    "minimax27":          "MiniMax 27 — ❌ 不可用（超时）",
    "minimax25":          "MiniMax 25 — ❌ 不可用（超时）",
    "minimax-27-tke-openai": "MiniMax 27 TKE OpenAI 兼容 — ❌ 不可用（超时）",
    "minimax-25-tke-openai": "MiniMax 25 TKE OpenAI 兼容 — ❌ 不可用（超时）",
    # ── 外网 fallback ──
    "deepseek-v4-flash":  "DeepSeek v4 Flash (外网 API fallback)",
}


def select(task_type: str = "default", override: Optional[str] = None) -> str:
    """Select the best model ID for *task_type*.

    Parameters
    ----------
    task_type : str
        Description of what you're doing, e.g. 'report_generation', 'code_review'.
        Falls back to DEFAULT if not found in ROUTES.
    override : str or None
        If given, bypass the route table and use this directly.
        Also resolved through ROUTES (so you can say override='fast').

    Returns
    -------
    str — a model ID to pass as the `model` parameter to the LLM gateway.
    """
    if override is not None:
        return ROUTES.get(override, override)
    return ROUTES.get(task_type, DEFAULT)


__all__ = ["select", "ROUTES", "CATALOG", "DEFAULT"]
