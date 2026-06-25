#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations


def test_seed_empty_returns_400(client):
    response = client.post("/api/seed", json={"seed_text": "", "task_name": "x", "source": "manual"})
    assert response.status_code == 400
    assert response.get_json()["code"] == "EMPTY_SEED"


def test_seed_manual_returns_checks(client):
    response = client.post("/api/seed", json={"seed_text": "校园食品安全争议", "task_name": "x", "source": "manual"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["seed_id"].startswith("seed_")
    assert data["checks"][0]["status"] == "passed"
    assert any(check["status"] == "pending" for check in data["checks"])


def test_seed_file_source_not_supported(client):
    response = client.post("/api/seed", json={"seed_text": "x", "task_name": "x", "source": "file"})
    assert response.status_code == 400
    assert response.get_json()["code"] == "SOURCE_NOT_SUPPORTED"
