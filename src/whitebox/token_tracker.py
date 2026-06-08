"""白盒观测：Token 消耗追踪（Observer 模式，不侵入 LLMClient/RuntimeLogger）。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# Phase 分类规则（caller 函数名 → phase 映射）
_PHASE_MAP: Dict[str, str] = {
    # Phase 1
    "generator_create_event_entities": "Phase 1",
    "generator_create_spreader": "Phase 1",
    "analyzer_set_parameters": "Phase 1",
    # Phase 3
    "run_tick_0": "Phase 3",
    "generate_opinion_spreader_post": "Phase 3",
    # Phase 4
    "generate_report_with_llm_narrative": "Phase 4",
    # 分析层 / RiskClassifier
    "classify": "分析层",
    # 默认
}


def _classify_caller(caller: str) -> str:
    """根据 caller 函数名判断所属阶段。"""
    return _PHASE_MAP.get(caller, "其他")


class TokenTracker:
    """Token 消耗追踪器。

    通过 LLMClient.register_observer() 注册回调，每次 LLM 调用完成后
    自动记录 token 用量。不修改 LLMClient 或 RuntimeLogger 的内部逻辑。
    """

    def __init__(self) -> None:
        self._calls: List[Dict[str, Any]] = []
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    def disable(self) -> None:
        self._enabled = False

    def on_llm_response(
        self,
        *,
        usage: Optional[Dict[str, int]],
        caller: str,
        elapsed: float,
        model: str,
    ) -> None:
        """LLMClient 调用完成后回调。"""
        if not self._enabled:
            return
        if not usage:
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self._calls.append({
            "caller": caller,
            "phase": _classify_caller(caller),
            "model": model,
            "elapsed_seconds": round(elapsed, 2),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    @property
    def total_calls(self) -> int:
        return len(self._calls)

    @property
    def total_tokens(self) -> int:
        return sum(c["total_tokens"] for c in self._calls)

    def get_per_phase_summary(self) -> Dict[str, Dict[str, Any]]:
        """按阶段汇总 token 消耗。"""
        phases: Dict[str, Dict[str, Any]] = {}
        for c in self._calls:
            phase = c["phase"]
            if phase not in phases:
                phases[phase] = {
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "elapsed_seconds": 0.0,
                }
            p = phases[phase]
            p["calls"] += 1
            p["prompt_tokens"] += c["prompt_tokens"]
            p["completion_tokens"] += c["completion_tokens"]
            p["total_tokens"] += c["total_tokens"]
            p["elapsed_seconds"] = round(p["elapsed_seconds"] + c["elapsed_seconds"], 2)
        return dict(sorted(phases.items()))

    def get_summary(self) -> Dict[str, Any]:
        """返回 Token 消耗摘要 dict（不自管落盘，由 run_log_writer 统一写入）。"""
        per_phase = self.get_per_phase_summary()
        total_model_tokens: Dict[str, int] = {}
        for c in self._calls:
            model = c["model"]
            total_model_tokens[model] = (
                total_model_tokens.get(model, 0) + c["total_tokens"]
            )

        return {
            "total_calls": self.total_calls,
            "total_prompt_tokens": sum(c["prompt_tokens"] for c in self._calls),
            "total_completion_tokens": sum(c["completion_tokens"] for c in self._calls),
            "total_tokens": self.total_tokens,
            "total_elapsed_seconds": round(sum(c["elapsed_seconds"] for c in self._calls), 2),
            "per_phase": per_phase,
            "per_model": {
                model: {"total_tokens": tokens}
                for model, tokens in sorted(total_model_tokens.items())
            },
        }
