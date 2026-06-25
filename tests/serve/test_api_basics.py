#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations


def test_ping_and_basic_reads(client):
    assert client.get("/api/ping").get_json()["version"] == "1.5.0b"
    assert client.get("/api/config").status_code == 200
    assert isinstance(client.get("/api/models").get_json(), list)
    assert isinstance(client.get("/api/model-gateways").get_json(), list)
    assert client.get("/api/history").get_json() == []
    settings = client.get("/api/settings").get_json()
    assert settings["ticks"] if "ticks" in settings else True
    assert "systemChecks" in settings


def test_config_caps_ticks_and_marks_pending(client):
    response = client.post(
        "/api/config",
        json={"parallel_worlds": 2, "ticks": 5, "batch_name": "case", "focuses": ["风险扩散"]},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["ticks"] == 5
    assert "ticks" in data["pending_fields"]


def test_settings_put_persists(client):
    response = client.put(
        "/api/settings",
        json={"maxConcurrent": 2, "outputDir": "outputs/runs/", "retentionDays": 7, "technicalMode": True},
    )
    assert response.status_code == 200
    assert response.get_json()["technicalMode"] is True
    assert client.get("/api/settings").get_json()["retentionDays"] == 7


def test_model_gateway_create_is_write_only(client):
    response = client.post(
        "/api/model-gateways",
        json={"name": "local", "baseUrl": "http://localhost:8000/v1", "provider": "openai-compatible", "apiKey": "secret"},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["hasApiKey"] is True
    assert "secret" not in response.get_data(as_text=True)

    listed = client.get("/api/model-gateways").get_json()
    assert any(gateway["id"] == data["id"] for gateway in listed)
