#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations


def test_run_requires_models(client):
    response = client.post("/api/run", json={"seed_text": "x", "models": []})
    assert response.status_code == 400
    assert response.get_json()["code"] == "NO_MODELS"


def test_run_idempotency_and_status(client, monkeypatch):
    import adarian.serve.api.run as run_api

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

    monkeypatch.setattr("adarian.batch.start_batch", lambda **_kwargs: FakeSession())
    monkeypatch.setattr(run_api._EXECUTOR, "submit", lambda fn, session: None)

    payload = {"seed_text": "事件", "models": ["m1"], "tag": "case"}
    first = client.post("/api/run", json=payload)
    second = client.post("/api/run", json=payload)
    assert first.status_code == 202
    assert second.status_code == 200
    assert first.get_json()["batch_id"] == second.get_json()["batch_id"]

    status = client.get("/api/run/fake_batch/status")
    assert status.status_code == 200
    assert status.get_json()["worlds"][0]["status"] == "running"


def test_unknown_status_404(client):
    response = client.get("/api/run/nope/status")
    assert response.status_code == 404
    assert response.get_json()["code"] == "BATCH_NOT_FOUND"
