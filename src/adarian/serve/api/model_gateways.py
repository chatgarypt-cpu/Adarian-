#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Model gateway management API."""

from __future__ import annotations

import base64
import os
import time
import uuid
from typing import Any

import httpx
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from adarian import config as adarian_config
from adarian.serve import db
from adarian.serve.schemas import DISCOVERY_PATHS, GatewayPayload, error_response, hello_model

model_gateways_bp = Blueprint("model_gateways", __name__)


def _storage_mode() -> str:
    if os.getenv("ADARIAN_ENCRYPTION_KEY"):
        try:
            import cryptography.fernet  # type: ignore  # noqa: F401

            return "fernet"
        except Exception:
            return "dev-obfuscated"
    return "dev-obfuscated"


def _protect_secret(secret: str) -> str:
    if not secret:
        return ""
    key = os.getenv("ADARIAN_ENCRYPTION_KEY", "adarian-dev-key").encode("utf-8")
    if _storage_mode() == "fernet":
        from cryptography.fernet import Fernet  # type: ignore

        return Fernet(key).encrypt(secret.encode("utf-8")).decode("utf-8")
    raw = secret.encode("utf-8")
    protected = bytes(ch ^ key[i % len(key)] for i, ch in enumerate(raw))
    return base64.urlsafe_b64encode(protected).decode("ascii")


def _gateway_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "baseUrl": row["base_url"],
        "provider": row["provider"],
        "status": "partial" if row.get("enabled", 1) else "offline",
        "note": "用户新增网关，API key 不回显" if row.get("source") == "user" else "来自环境变量，前端只读",
        "hasApiKey": bool(row.get("api_key_encrypted")),
        "source": row.get("source", "user"),
        "keyStorageMode": row.get("key_storage_mode", "none"),
        "models": [],
    }


def _env_gateway() -> dict[str, Any]:
    base_url = adarian_config.LLM_BASE_URL or os.getenv("LLM_BASE_URL", "")
    return {
        "id": "env-default",
        "name": ".env 默认网关",
        "baseUrl": base_url,
        "provider": "openai-compatible",
        "status": "partial" if base_url else "offline",
        "note": "来自环境变量，前端只读",
        "hasApiKey": bool(adarian_config.LLM_API_KEY or os.getenv("LLM_API_KEY")),
        "source": "env",
        "keyStorageMode": "env",
        "models": [],
    }


def _get_gateway_or_env(gateway_id: str) -> dict[str, Any] | None:
    if gateway_id == "env-default":
        env = _env_gateway()
        return {
            "id": env["id"],
            "name": env["name"],
            "base_url": env["baseUrl"],
            "provider": env["provider"],
            "source": "env",
            "enabled": 1,
            "api_key_encrypted": "",
            "key_storage_mode": "env",
        }
    return db.get_gateway(gateway_id)


@model_gateways_bp.get("/model-gateways")
def list_gateways():
    rows = [_gateway_response(row) for row in db.list_user_gateways()]
    return jsonify([_env_gateway(), *rows])


@model_gateways_bp.post("/model-gateways")
def create_gateway():
    try:
        payload = GatewayPayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        body, status = error_response("VALIDATION_ERROR", "Invalid gateway payload", {"errors": exc.errors()})
        return jsonify(body), status
    base_url = payload.resolved_base_url()
    if not payload.name.strip() or not base_url:
        body, status = error_response("VALIDATION_ERROR", "Gateway name and base_url are required")
        return jsonify(body), status
    mode = _storage_mode()
    now = db.now()
    row = {
        "id": f"gw_{uuid.uuid4().hex[:12]}",
        "name": payload.name.strip(),
        "base_url": base_url.rstrip("/"),
        "provider": payload.provider,
        "api_key_encrypted": _protect_secret(payload.resolved_api_key()),
        "enabled": 1 if payload.enabled else 0,
        "source": "user",
        "key_storage_mode": mode,
        "created_at": now,
        "updated_at": now,
    }
    db.create_gateway(row)
    return jsonify(_gateway_response(row)), 201


@model_gateways_bp.put("/model-gateways/<gateway_id>")
def update_gateway(gateway_id: str):
    if gateway_id == "env-default":
        body, status = error_response("READ_ONLY_GATEWAY", ".env gateway is read-only")
        return jsonify(body), status
    existing = db.get_gateway(gateway_id)
    if not existing:
        body, status = error_response("GATEWAY_NOT_FOUND", "Gateway not found")
        return jsonify(body), status
    try:
        payload = GatewayPayload.model_validate({**existing, **(request.get_json(silent=True) or {})})
    except ValidationError as exc:
        body, status = error_response("VALIDATION_ERROR", "Invalid gateway payload", {"errors": exc.errors()})
        return jsonify(body), status
    secret = payload.resolved_api_key()
    patch = {
        "name": payload.name.strip(),
        "base_url": payload.resolved_base_url().rstrip("/"),
        "provider": payload.provider,
        "enabled": 1 if payload.enabled else 0,
        "api_key_encrypted": _protect_secret(secret) if secret else existing.get("api_key_encrypted", ""),
        "key_storage_mode": _storage_mode() if secret else existing.get("key_storage_mode", "none"),
    }
    db.update_gateway(gateway_id, patch)
    return jsonify(_gateway_response(db.get_gateway(gateway_id) or {**existing, **patch}))


def _resolve_auth_headers(gateway: dict[str, Any]) -> dict[str, str]:
    """Build auth headers for a gateway, handling encrypted and env keys."""
    headers: dict[str, str] = {}
    enc_key = gateway.get("api_key_encrypted") or ""
    protocol = str(gateway.get("protocol", "openai"))
    if enc_key and gateway.get("key_storage_mode") == "fernet":
        from cryptography.fernet import Fernet
        key = os.getenv("ADARIAN_ENCRYPTION_KEY", "adarian-dev-key").encode("utf-8")
        try:
            decrypted = Fernet(key).decrypt(enc_key.encode()).decode()
            if protocol == "anthropic":
                headers["x-api-key"] = decrypted
            else:
                headers["Authorization"] = f"Bearer {decrypted}"
        except Exception:
            pass
    elif not enc_key and gateway.get("source") == "env":
        ak = adarian_config.LLM_API_KEY or os.getenv("LLM_API_KEY", "")
        if ak:
            if protocol == "anthropic":
                headers["x-api-key"] = ak
            else:
                headers["Authorization"] = f"Bearer {ak}"
    return headers


@model_gateways_bp.post("/model-gateways/<gateway_id>/discover-models")
def discover_models(gateway_id: str):
    gateway = _get_gateway_or_env(gateway_id)
    if not gateway:
        body, status = error_response("GATEWAY_NOT_FOUND", "Gateway not found")
        return jsonify(body), status
    base_url = str(gateway.get("base_url", "")).rstrip("/")
    if not base_url:
        body, status = error_response("MODEL_DISCOVERY_FAILED", "Gateway base_url is empty")
        return jsonify(body), status

    # Handle NO_PROXY for internal IPs
    if "100.89.3" in base_url or "10." in base_url:
        no_proxy = os.environ.get("NO_PROXY", "")
        merged = ",".join(["100.89.3.59", "localhost", "127.0.0.1", no_proxy]).strip(",")
        os.environ["NO_PROXY"] = merged
        os.environ["no_proxy"] = merged

    # Try protocol-appropriate discovery paths
    protocol = str(gateway.get("protocol", "openai"))
    headers = _resolve_auth_headers(gateway)
    urls = [f"{base_url}{p}" for p in DISCOVERY_PATHS.get(protocol, DISCOVERY_PATHS["custom"])]
    payload = None
    latency = 0
    for url in urls:
        try:
            start = time.perf_counter()
            response = httpx.get(url, headers=headers, timeout=5)
            latency = round((time.perf_counter() - start) * 1000)
            response.raise_for_status()
            payload = response.json()
            break
        except Exception:
            continue

    if not payload:
        body, status = error_response("MODEL_DISCOVERY_FAILED", "Could not discover models", {"urls_tried": urls})
        return jsonify(body), status

    data = payload.get("data", payload if isinstance(payload, list) else [])
    models = [
        {
            "id": str(item.get("id") if isinstance(item, dict) else item),
            "name": str(item.get("id") if isinstance(item, dict) else item),
            "description": "discovered from gateway",
            "selected": False,
            "available": True,
            "latency": f"{latency}ms",
            "advice": "动态发现模型",
            "gatewayId": gateway_id,
        }
        for item in data
    ]
    return jsonify({"gateway_id": gateway_id, "models": models, "latency_ms": latency})


@model_gateways_bp.post("/model-gateways/<gateway_id>/health")
def gateway_health(gateway_id: str):
    """Sends hi to gateway's first model to verify it's really working."""
    gateway = _get_gateway_or_env(gateway_id)
    if not gateway:
        return jsonify({"id": gateway_id, "status": "offline", "latency_ms": None, "message": "gateway not found"})
    base_url = str(gateway.get("base_url", "")).rstrip("/")
    if not base_url:
        return jsonify({"id": gateway_id, "status": "offline", "latency_ms": None, "message": "empty base_url"})
    # Try a quick hello with common models, protocol-aware
    protocol = str(gateway.get("protocol", "openai"))
    api_key = ""
    headers = _resolve_auth_headers(gateway)
    if protocol == "anthropic":
        api_key = headers.get("x-api-key", "")
    else:
        api_key = headers.get("Authorization", "").replace("Bearer ", "")

    probes = ("qwen36-35b", "gpt-4o-mini", "deepseek-chat", "claude-sonnet-4-20250514")
    for probe in probes:
        result = hello_model(probe, base_url, api_key, timeout=8, protocol=protocol)
        if result["status"] == "ok":
            return jsonify({"id": gateway_id, "status": "connected", "latency_ms": round(result["elapsed"] * 1000)})
    return jsonify({
        "id": gateway_id,
        "status": "offline",
        "latency_ms": None,
        "message": "no model responded",
    })
