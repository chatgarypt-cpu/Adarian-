"""Small report config helpers."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adarian import config as adarian_config
from adarian.serve import db
from adarian.serve.api.model_gateways import _get_gateway_or_env, _unprotect_secret


REPORT_TASK_TYPE = "phase4_report"


@dataclass
class ReportModelConfig:
    model: str
    base_url: str
    api_key: str
    temperature: float
    max_tokens: int
    resolved_from: str
    gateway_id: str = ""


def safe_slug(text: str, fallback: str = "adarian_report") -> str:
    raw = (text or fallback).strip().replace("\n", " ")
    raw = re.sub(r"[\\/:*?\"<>|]+", "", raw)
    raw = re.sub(r"\s+", "", raw)
    return raw[:28] or fallback


def parse_versions(value: Any) -> list[str]:
    allowed = {"A", "B", "C"}
    versions = [str(v).upper() for v in (value or ["B"])]
    versions = [v for v in versions if v in allowed]
    return versions or ["B"]


def parse_appendix_mode(value: Any) -> str:
    mode = str(value or "none")
    return mode if mode in {"none", "included", "both"} else "none"


def resolve_skill_id(payload: dict[str, Any]) -> str:
    settings = db.get_setting("settings", {}) or {}
    return (
        str(payload.get("skill_id") or "").strip()
        or str(settings.get("report_skill_id") or "").strip()
        or os.getenv("ADARIAN_REPORT_SKILL_ID", "").strip()
        or "default_government"
    )


def resolve_model_config(payload: dict[str, Any]) -> ReportModelConfig | None:
    settings = db.get_setting("settings", {}) or {}
    gateway_id = str(payload.get("gateway_id") or settings.get("report_gateway_id") or "").strip()
    model = str(payload.get("model_id") or settings.get("report_model_id") or "").strip()
    temperature = float(payload.get("temperature") or settings.get("report_temperature") or os.getenv("ADARIAN_REPORT_TEMPERATURE") or 0.3)
    max_tokens = int(payload.get("max_tokens") or settings.get("report_max_tokens") or os.getenv("ADARIAN_REPORT_MAX_TOKENS") or 8192)

    if gateway_id:
        gateway = _get_gateway_or_env(gateway_id)
        if gateway:
            base_url = str(gateway.get("base_url") or "").rstrip("/")
            enc_key = gateway.get("api_key_encrypted") or ""
            api_key = _unprotect_secret(enc_key, str(gateway.get("key_storage_mode") or "dev-obfuscated")) if enc_key else ""
            if gateway.get("source") == "env":
                api_key = adarian_config.LLM_API_KEY or os.getenv("LLM_API_KEY", "")
            if base_url and model and api_key:
                return ReportModelConfig(model, base_url, api_key, temperature, max_tokens, "payload" if payload.get("model_id") else "settings", gateway_id)

    env_model = os.getenv("ADARIAN_REPORT_MODEL", "").strip()
    env_base = os.getenv("ADARIAN_REPORT_BASE_URL", "").strip()
    env_key = os.getenv("ADARIAN_REPORT_API_KEY", "").strip()
    if env_model and env_base and env_key:
        return ReportModelConfig(env_model, env_base, env_key, temperature, max_tokens, "env")

    # Reuse the existing Adarian LLM env as the project-level report default.
    default_model = adarian_config.get_model_name(REPORT_TASK_TYPE)
    if adarian_config.LLM_BASE_URL and adarian_config.LLM_API_KEY and default_model:
        return ReportModelConfig(default_model, adarian_config.LLM_BASE_URL, adarian_config.LLM_API_KEY, temperature, max_tokens, "env", "env-default")
    return None


def skill_path(skill_id: str) -> Path:
    return Path(__file__).resolve().parent / "skills" / skill_id / "skill.md"


def appendix_a_path() -> Path:
    return adarian_config.PROJECT_ROOT / "docs/product/adarian-report-agent/references/appendix_a.md"
