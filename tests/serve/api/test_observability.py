#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json


def _insert_observable_batch(tmp_path):
    from adarian.serve import db

    batch_dir = tmp_path / "batch"
    world_dir = batch_dir / "world_0"
    world_dir.mkdir(parents=True)
    dataset = {
        "source_context": {
            "event_summary": "测试事件",
            "event_entities": [{"name": "主体A"}],
            "opinion_spreaders": [{"group_name": "群体A"}],
        },
        "simulation_result": {
            "risk_verdict": {"level": "high", "label": "高风险"},
            "risk_type_classification": {
                "primary_types": ["negative_narrative"],
                "type_labels": ["负向叙事聚合"],
                "primary_domain": "public_opinion",
            },
            "agent_stance_matrix": [{"group_name": "群体A", "final_stance": 2.0}],
        },
    }
    (world_dir / "simulation_dataset.json").write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
    (world_dir / "tick_logs.json").write_text(json.dumps([
        {
            "tick": 1,
            "entries": [
                {
                    "group_name": "群体A",
                    "previous_stance": 3.0,
                    "current_stance": 2.0,
                    "comment": "风险正在扩散",
                    "speaker_status": "传播者",
                }
            ],
        }
    ], ensure_ascii=False), encoding="utf-8")
    (world_dir / "run.log").write_text(
        "\n".join([
            "2026-06-26 12:00:00 RUN START mode=normal seed=seed.txt run_dir=/tmp/world_0",
            "2026-06-26 12:00:01 PHASE START name=phase1_entity_extraction",
            "2026-06-26 12:00:02 PHASE END name=phase1_entity_extraction elapsed=1.20s",
            "2026-06-26 12:00:03 TICK END tick=1 elapsed=2.00s speakers=1 llm_calls=1",
            "2026-06-26 12:00:04 RUN END status=success elapsed=3.40s",
            "===== TOKEN SUMMARY =====",
            "  total_calls:    2",
            "  prompt_tokens:  10",
            "  completion_tokens: 5",
            "  total_tokens:   15",
            "  llm_elapsed:    3.0s",
            "",
            "  per_phase:",
            "    phase3_tick_simulation: 2 calls, 15 tokens, 3.0s",
        ]) + "\n",
        encoding="utf-8",
    )
    (world_dir / "run_meta.json").write_text(json.dumps({"status": "success", "elapsed_seconds": 3.4, "model": "m1"}), encoding="utf-8")
    (batch_dir / "scheduler_batch.log").write_text("[12:00:00] Batch execution started\n[12:00:04] world_0 success\n", encoding="utf-8")
    (batch_dir / "report.json").write_text('{"ok": true}\n', encoding="utf-8")

    db.upsert_batch(
        {
            "id": "observable_batch",
            "task_name": "case",
            "seed_text": "事件",
            "seed_path": "",
            "models": '["m1"]',
            "tag": "case",
            "base_url": "",
            "batch_dir": str(batch_dir),
            "created_at": "2026-06-26 12:00:00",
            "completed_at": "2026-06-26 12:00:04",
            "status": "completed",
            "idempotency_key": "observable-batch",
            "config_json": "{}",
        }
    )
    db.upsert_world(
        {
            "id": "observable_batch:world_0",
            "batch_id": "observable_batch",
            "world_index": 0,
            "model_name": "m1",
            "status": "completed",
            "raw_status": "success",
            "run_dir": str(world_dir),
            "dataset_path": str(world_dir / "simulation_dataset.json"),
            "error_message": "",
            "log_tail": "",
            "started_at": "2026-06-26 12:00:00",
            "completed_at": "2026-06-26 12:00:04",
            "elapsed_seconds": 3.4,
        }
    )


def test_review_uses_real_dataset(client, tmp_path):
    _insert_observable_batch(tmp_path)
    response = client.get("/api/review/observable_batch")
    assert response.status_code == 200
    row = response.get_json()["rows"][0]
    assert row["risks"] == "负向叙事聚合"
    assert row["level"] == "高风险"
    assert row["entities"] == 1
    assert row["opinions"] == 1


def test_world_detail_and_events(client, tmp_path):
    _insert_observable_batch(tmp_path)
    summary = client.get("/api/run/observable_batch/worlds/0/summary")
    assert summary.status_code == 200
    assert summary.get_json()["dataset"]["event_entities_count"] == 1

    ticks = client.get("/api/run/observable_batch/worlds/0/ticks")
    assert ticks.status_code == 200
    assert ticks.get_json()["ticks"][0]["entries"][0]["comment"] == "风险正在扩散"

    events = client.get("/api/run/observable_batch/worlds/0/events")
    assert events.status_code == 200
    kinds = {event["kind"] for event in events.get_json()["events"]}
    assert "phase_start" in kinds
    assert "agent" in kinds


def test_metrics_errors_and_report_download(client, tmp_path):
    _insert_observable_batch(tmp_path)
    metrics = client.get("/api/run/observable_batch/metrics")
    assert metrics.status_code == 200
    payload = metrics.get_json()
    assert payload["tokens"]["total_tokens"] == 15
    assert payload["tokens"]["per_phase"]["phase3_tick_simulation"]["total_tokens"] == 15
    assert payload["tokens"]["per_phase"]["phase3_tick_simulation"]["calls"] == 2
    assert payload["report_count"] == 0

    errors = client.get("/api/run/observable_batch/errors")
    assert errors.status_code == 200
    assert errors.get_json()["errors"] == []

    download = client.get("/api/report/observable_batch/files/report.json")
    assert download.status_code == 200
    assert b"ok" in download.data

    forbidden = client.get("/api/report/observable_batch/files/secret.txt")
    assert forbidden.status_code == 404


def test_error_reason_classifier_covers_common_cases():
    from adarian.serve.observability import classify_error

    assert classify_error("request timeout after 30s") == "timeout"
    assert classify_error("KeyboardInterrupt 用户中断") == "keyboard_interrupt"
    assert classify_error("HTTP 401 unauthorized api key") == "api_auth"
    assert classify_error("ConnectError network unreachable") == "api_network"
    assert classify_error("HTTP 429 rate limit") == "api_rate_limit"
    assert classify_error("simulation_dataset.json missing") == "dataset_missing"
