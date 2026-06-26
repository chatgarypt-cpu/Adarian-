#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations


def test_run_requires_models(client):
    response = client.post("/api/run", json={"seed_text": "x", "models": []})
    assert response.status_code == 400
    assert response.get_json()["code"] == "NO_MODELS"


def test_run_idempotency_and_status(client, monkeypatch):
    import adarian.serve.api.run as run_api
    captured = {}

    class FakeState:
        status = "pending"
        model_name = "m1"
        output_dir = "/tmp/world_0"
        dataset_path = "/tmp/world_0/simulation_dataset.json"
        error_summary = ""
        log_tail = ""
        elapsed_seconds = None

    class FakeWorld:
        name = "world_0"
        model = "m1"
        base_url = "http://example.test/v1"

    class FakeSession:
        batch_id = "fake_batch"
        batch_dir = "/tmp/fake_batch"
        seed_path = "/tmp/seed.txt"
        worlds = [FakeWorld()]
        states = {"world_0": FakeState()}
        status = "pending"
        started_at = "2026-06-26 12:00:00"
        completed_at = ""

        def log(self, _message):
            pass

    def fake_start_batch(**kwargs):
        captured.update(kwargs)
        return FakeSession()

    monkeypatch.setattr("adarian.batch.start_batch", fake_start_batch)
    monkeypatch.setattr(run_api._EXECUTOR, "submit", lambda fn, session: None)

    payload = {"seed_text": "事件", "models": ["m1"], "tag": "case", "client_session_id": "session-a"}
    first = client.post("/api/run", json=payload)
    second = client.post("/api/run", json=payload)
    assert first.status_code == 202
    assert second.status_code == 200
    assert first.get_json()["batch_id"] == second.get_json()["batch_id"]

    status = client.get("/api/run/fake_batch/status")
    assert status.status_code == 200
    assert status.get_json()["worlds"][0]["status"] == "running"

    active = client.get("/api/run/active")
    assert active.status_code == 200
    active_json = active.get_json()
    assert active_json["active"] is True
    assert active_json["batch"]["batch_id"] == "fake_batch"

    from adarian.serve import db
    db.upsert_batch(
        {
            "id": "other_batch",
            "task_name": "other",
            "seed_text": "事件",
            "seed_path": "",
            "models": '["m2"]',
            "tag": "other",
            "base_url": "",
            "batch_dir": "/tmp/other_batch",
            "created_at": "2026-06-26 12:01:00",
            "completed_at": "",
            "status": "running",
            "idempotency_key": "other-session-key",
            "config_json": '{"client_session_id":"session-b"}',
        }
    )
    session_active = client.get("/api/run/active?client_session_id=session-a")
    assert session_active.status_code == 200
    assert session_active.get_json()["batch"]["batch_id"] == "fake_batch"

    missed_session_active = client.get("/api/run/active?client_session_id=session-missing")
    assert missed_session_active.status_code == 200
    assert missed_session_active.get_json() == {"active": False, "batch": None}

    legacy_active = client.get("/api/run/active")
    assert legacy_active.status_code == 200
    assert legacy_active.get_json()["active"] is True


def test_run_accepts_seed_path(client, monkeypatch):
    import adarian.serve.api.run as run_api
    captured = {}

    class FakeState:
        status = "pending"
        model_name = "m1"
        output_dir = "/tmp/world_0"
        dataset_path = "/tmp/world_0/simulation_dataset.json"
        error_summary = ""
        log_tail = ""
        elapsed_seconds = None

    class FakeWorld:
        name = "world_0"
        model = "m1"
        base_url = "http://example.test/v1"

    class FakeSession:
        batch_id = "fake_path_batch"
        batch_dir = "/tmp/fake_path_batch"
        seed_path = "/project/seeds/test8.txt"
        worlds = [FakeWorld()]
        states = {"world_0": FakeState()}
        status = "pending"
        started_at = "2026-06-26 12:00:00"
        completed_at = ""

        def log(self, _message):
            pass

    def fake_start_batch(**kwargs):
        captured.update(kwargs)
        return FakeSession()

    monkeypatch.setattr("adarian.batch.start_batch", fake_start_batch)
    monkeypatch.setattr(run_api._EXECUTOR, "submit", lambda fn, session: None)

    response = client.post("/api/run", json={"seed_path": "seeds/test8.txt", "models": ["m1"], "tag": "case"})
    assert response.status_code == 202
    assert captured["seed_text"] == ""
    assert captured["seed_path"].endswith("seeds/test8.txt")


def test_unknown_status_404(client):
    response = client.get("/api/run/nope/status")
    assert response.status_code == 404
    assert response.get_json()["code"] == "BATCH_NOT_FOUND"
