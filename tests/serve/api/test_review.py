#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations


def test_review_unknown_batch_404(client):
    response = client.get("/api/review/nope")
    assert response.status_code == 404
    assert response.get_json()["code"] == "BATCH_NOT_FOUND"


def test_report_unknown_batch_404(client):
    response = client.post("/api/report", json={"batch_id": "nope"})
    assert response.status_code == 404
    assert response.get_json()["code"] == "BATCH_NOT_FOUND"


def test_report_generation_is_deferred_without_existing_file(client):
    from adarian.serve import db

    db.upsert_batch(
        {
            "id": "batch_without_dataset",
            "task_name": "case",
            "seed_text": "事件",
            "seed_path": "",
            "models": '["m1"]',
            "tag": "case",
            "base_url": "",
            "batch_dir": "",
            "created_at": "2026-06-26 12:00:00",
            "completed_at": "",
            "status": "completed",
            "idempotency_key": "report-no-dataset",
            "config_json": "{}",
        }
    )
    response = client.post("/api/report", json={"batch_id": "batch_without_dataset"})
    assert response.status_code == 409
    body = response.get_json()
    assert body["code"] == "REPORT_GENERATION_DEFERRED"
    assert body["details"]["next_version"] == "v1.5.2"
