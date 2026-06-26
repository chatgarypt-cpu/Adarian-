#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations


def _app(tmp_path, monkeypatch):
    from adarian.serve import db
    from adarian.serve import paths

    monkeypatch.setattr(paths, "SERVE_DB_PATH", tmp_path / "serve.sqlite3")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "serve.sqlite3")
    db.init_db()

    from adarian.serve import create_app

    app = create_app()
    app.config.update(TESTING=True)
    return app


def _install_fake_batch(monkeypatch):
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
        batch_id = "fake_e2e_batch"
        batch_dir = "/tmp/fake_e2e_batch"
        seed_path = "/project/seeds/test8.txt"
        worlds = [FakeWorld()]
        states = {"world_0": FakeState()}
        status = "pending"
        started_at = "2026-06-26 12:00:00"
        completed_at = ""

        def log(self, _message):
            pass

    monkeypatch.setattr("adarian.batch.start_batch", lambda **_kwargs: FakeSession())
    monkeypatch.setattr(run_api._EXECUTOR, "submit", lambda fn, session: None)


def test_entry_api_smoke_with_test8_seed_path(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    _install_fake_batch(monkeypatch)
    client = app.test_client()

    seed = client.post("/api/seed", json={"source": "file", "seed_path": "seeds/test8.txt", "task_name": "test8-e2e"})
    assert seed.status_code == 200
    assert seed.get_json()["seed_path"].endswith("seeds/test8.txt")

    first = client.post("/api/run", json={"seed_path": "seeds/test8.txt", "models": ["m1"], "tag": "test8-e2e"})
    assert first.status_code == 202
    batch_id = first.get_json()["batch_id"]
    assert first.get_json()["worlds"][0]["status"] == "running"

    second = client.post("/api/run", json={"seed_path": "seeds/test8.txt", "models": ["m1"], "tag": "test8-e2e"})
    assert second.status_code == 200
    assert second.get_json()["batch_id"] == batch_id

    status = client.get(f"/api/run/{batch_id}/status")
    assert status.status_code == 200
    assert status.get_json()["worlds"][0]["status"] == "running"

    review = client.get(f"/api/review/{batch_id}")
    assert review.status_code == 200
    assert review.get_json()["complete"] is False

    history = client.get("/api/history")
    assert history.status_code == 200
    assert history.get_json()[0]["batchId"] == batch_id


def test_entry_api_error_smoke(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()

    no_models = client.post("/api/run", json={"seed_path": "seeds/test8.txt", "models": []})
    assert no_models.status_code == 400
    assert no_models.get_json()["code"] == "NO_MODELS"

    invalid_json = client.post("/api/run", data="not json", content_type="application/json")
    assert invalid_json.status_code == 400

    unknown_review = client.get("/api/review/no-such-batch")
    assert unknown_review.status_code == 404

    history = client.get("/api/history")
    assert history.status_code == 200
    assert history.get_json() == []
