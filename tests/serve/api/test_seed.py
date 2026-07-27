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
    assert all(check["status"] != "pending" for check in data["checks"])


def test_seed_file_source_accepts_project_seed_path(client):
    response = client.post("/api/seed", json={"seed_path": "seeds/test8.txt", "task_name": "x", "source": "file"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["seed_id"].startswith("seed_")
    assert data["source"] == "file"
    assert data["seed_path"].endswith("seeds/test8.txt")
    assert data["checks"][0]["status"] == "passed"


def test_seed_file_source_rejects_missing_path(client):
    response = client.post("/api/seed", json={"seed_path": "seeds/missing.txt", "task_name": "x", "source": "file"})
    assert response.status_code == 404
    assert response.get_json()["code"] == "SEED_FILE_NOT_FOUND"


def test_seed_file_source_rejects_outside_project(client):
    response = client.post("/api/seed", json={"seed_path": "/tmp/outside.txt", "task_name": "x", "source": "file"})
    assert response.status_code == 400
    assert response.get_json()["code"] == "SEED_PATH_NOT_ALLOWED"
