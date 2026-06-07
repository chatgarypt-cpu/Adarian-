"""Lightweight model router for the internal LLM gateway.

Route task types to specific models on the lab's internal gateway
(http://100.89.3.59:8090/v1, OpenAI-compatible, --noproxy '*' to bypass proxy).

Usage:
    from src.model_router import select
    model = select("phase4_report")     # → "qwen3-80b-tke"
    model = select("quick_test")        # → "qwen3-30b-tke"
    model = select("phase4_report", override="fast")  # → "qwen3-30b-tke"
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
    "phase4_report":      "qwen36-35b",         # narrative generation

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
    "qwen3-30b-tke":      "Qwen 3 30B TKE — fast (0.3s), recommended default",
    "qwen3-80b-tke":      "Qwen 3 80B TKE — strong, same speed (0.3s)",
    "qwen3-30b-a3b":      "Qwen 3 30B A3B MoE (0.3s)",
    "qwen3-80b-a3b":      "Qwen 3 80B A3B MoE (0.3s)",
    "qwen36-35b":         "Qwen 3.6 35B (0.3s)",
    "qwen36-35b-tke":     "Qwen 3.6 35B TKE (0.4s)",
    "qwen36-35b-claude":  "Qwen 3.6 35B Claude-style (0.4s)",
    "qwen36-27b":         "Qwen 3.6 27B (0.5s)",
    "qwen36-27b-jyt":     "Qwen 3.6 27B JYT (0.6s)",
    "qwen3-32b-tke":      "Qwen 3 32B TKE (0.5s)",
    "qwen3-32b":          "Qwen 3 32B (0.6s)",
    "qwen-35-122b-sg":    "Qwen 3.5 122B SG — largest (0.8s)",
    "qwen36-35b-tzb":     "Qwen 3.6 35B TZB (0.6s)",
    "minimax":            "MiniMax (0.4s)",
    "minimax-openai":     "MiniMax OpenAI-compatible (0.7s)",
    "vllm":               "vLLM (0.2s, may respond empty)",
    "sg":                 "SG model (0.9s)",
    "bge-m3-tke":         "BAAI bge-m3 TKE embedding 1024d (0.3s)",
    "bge-m3":             "BAAI bge-m3 embedding 1024d (0.5s)",
    # External fallback
    "deepseek-v4-flash":  "DeepSeek v4 Flash (external API)",
}


def select(task_type: str = "default", override: Optional[str] = None) -> str:
    """Select the best model ID for *task_type*.

    Parameters
    ----------
    task_type : str
        Description of what you're doing, e.g. 'phase4_report', 'code_review'.
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
