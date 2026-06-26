#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared API schema helpers for v1.5.0b."""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field

WORLD_STATUS_MAP = {
    "success": "completed",
    "completed": "completed",
    "failed": "failed",
    "running": "running",
    "pending": "pending",
}


def normalize_status(status: str | None) -> str:
    return WORLD_STATUS_MAP.get((status or "pending").lower(), "pending")


DISCOVERY_PATHS = {
    "openai": ["/v1/models", "/models"],
    "anthropic": ["/v1/models"],
    "custom": ["/v1/models", "/models"],
}

HEALTH_PATHS = {
    "openai": "/v1/chat/completions",
    "anthropic": "/v1/messages",
    "custom": "/v1/chat/completions",
}


def build_api_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1") and path.startswith("/v1/"):
        path = path[3:]
    return f"{base}{path}"


def _is_portless_discovery_host(hostname: str | None) -> bool:
    host = hostname or ""
    return host.startswith("100.89.") or host.startswith("10.")


def portless_internal_base_url(base_url: str) -> str:
    """Return an internal discovery URL without explicit port when needed."""
    parts = urlsplit(base_url.rstrip("/"))
    if not parts.hostname or not _is_portless_discovery_host(parts.hostname) or parts.port is None:
        return base_url.rstrip("/")
    host = parts.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host
    if parts.username:
        auth = parts.username
        if parts.password:
            auth = f"{auth}:{parts.password}"
        netloc = f"{auth}@{netloc}"
    return urlunsplit((parts.scheme, netloc, parts.path.rstrip("/"), "", ""))


def build_discovery_urls(base_url: str, paths: list[str]) -> list[str]:
    """Build discovery URLs, trying portless internal URLs before configured URLs."""
    configured = base_url.rstrip("/")
    bases = [portless_internal_base_url(configured), configured]
    urls: list[str] = []
    for base in bases:
        for path in paths:
            url = build_api_url(base, path)
            if url not in urls:
                urls.append(url)
    return urls


def hello_model(model: str, base_url: str, api_key: str, timeout: float = 20.0,
                protocol: str = "openai") -> dict[str, Any]:
    """Real health check for one model, protocol-aware.

    Sends a minimal chat completion/messages request and reports status + latency.
    Handles internal-network NO_PROXY for IPs like 100.89.3.59.
    """
    if "100.89.3.59" in base_url:
        no_proxy = os.environ.get("NO_PROXY", "")
        merged = ",".join(["100.89.3.59", "localhost", "127.0.0.1", no_proxy]).strip(",")
        os.environ["NO_PROXY"] = merged
        os.environ["no_proxy"] = merged

    path = HEALTH_PATHS.get(protocol, "/v1/chat/completions")
    if protocol == "anthropic":
        payload = {
            "model": model,
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "hi"}],
        }
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    else:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10,
        }
        headers = {"Authorization": f"Bearer {api_key}"}

    t0 = time.perf_counter()
    try:
        import httpx
        resp = httpx.post(
            build_api_url(base_url, path),
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        elapsed = round(time.perf_counter() - t0, 2)
        if resp.status_code == 200:
            return {"status": "ok", "elapsed": elapsed}
        return {"status": "fail", "elapsed": elapsed, "error": f"HTTP {resp.status_code}"}
    except Exception as exc:
        elapsed = round(time.perf_counter() - t0, 2)
        return {"status": "fail", "elapsed": elapsed, "error": str(exc)}


def error_response(code: str, message: str, details: dict[str, Any] | None = None) -> tuple[dict[str, Any], int]:
    status = {
        "BAD_JSON": 400,
        "EMPTY_SEED": 400,
        "NO_MODELS": 400,
        "SEED_PATH_NOT_ALLOWED": 400,
        "SOURCE_NOT_SUPPORTED": 400,
        "VALIDATION_ERROR": 400,
        "SEED_FILE_NOT_FOUND": 404,
        "NOT_FOUND": 404,
        "BATCH_NOT_FOUND": 404,
        "GATEWAY_NOT_FOUND": 404,
        "READ_ONLY_GATEWAY": 403,
        "REPORT_SOURCE_NOT_FOUND": 409,
        "MODEL_DISCOVERY_FAILED": 502,
        "RUN_START_FAILED": 500,
    }.get(code, 500)
    return {"code": code, "message": message, "details": details or {}}, status


class SeedRequest(BaseModel):
    seed_text: str = ""
    seed_path: str = ""
    task_name: str = "adarian_batch"
    source: str = "manual"


class ConfigPayload(BaseModel):
    parallel_worlds: int = Field(default=3, ge=1, le=12)
    ticks: int = Field(default=5, ge=1, le=5)
    batch_name: str = "adarian_batch"
    focuses: list[str] = Field(default_factory=list)


class GatewayPayload(BaseModel):
    name: str
    baseUrl: str = ""
    base_url: str = ""
    protocol: str = "openai"  # openai | anthropic | custom
    provider: str = "openai-compatible"
    apiKey: str = ""
    api_key: str = ""
    enabled: bool = True

    def resolved_base_url(self) -> str:
        return (self.base_url or self.baseUrl).strip()

    def resolved_api_key(self) -> str:
        return self.api_key or self.apiKey

    def resolved_protocol(self) -> str:
        return self.protocol or "openai"


class RunPayload(BaseModel):
    seed_text: str = ""
    seed_path: str = ""
    models: list[str] = Field(default_factory=list)
    tag: str = "adarian_batch"
    base_url: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class ReportPayload(BaseModel):
    batch_id: str
    type: str = "risk_assessment"
    audience: str = "generic_government"


class SettingsPayload(BaseModel):
    maxConcurrent: int = Field(default=3, ge=1, le=12)
    outputDir: str = "outputs/runs/"
    retentionDays: int = Field(default=30, ge=1)
    technicalMode: bool = False
