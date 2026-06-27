#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json


def _dataset():
    return {
        "run_info": {"event_name": "测试事件", "event_scale": 0.6, "event_controversy": 0.7, "seed_text": "测试材料"},
        "source_context": {
            "event_summary": "测试事件引发讨论",
            "event_entities": [{"name": "主体A", "type": "organization"}],
            "opinion_spreaders": [{"group_name": "群体A"}],
        },
        "simulation_result": {
            "risk_verdict": {"level": "high", "label": "高风险", "signals": {"x": 1}},
            "risk_type_classification": {
                "primary_types": ["negative_narrative"],
                "type_labels": ["负向叙事聚合"],
            },
            "emotion_trajectory": [],
            "agent_stance_matrix": [],
            "inflection_points": [],
        },
    }


def _insert_batch(tmp_path):
    from adarian.serve import db

    batch_dir = tmp_path / "batch"
    world_dir = batch_dir / "world_0"
    world_dir.mkdir(parents=True)
    dataset_path = world_dir / "simulation_dataset.json"
    dataset_path.write_text(json.dumps(_dataset(), ensure_ascii=False), encoding="utf-8")
    db.upsert_batch({
        "id": "report_batch",
        "task_name": "测试事件",
        "seed_text": "测试材料",
        "seed_path": "",
        "models": '["m1"]',
        "tag": "case",
        "base_url": "",
        "batch_dir": str(batch_dir),
        "created_at": "2026-06-27 10:00:00",
        "completed_at": "2026-06-27 10:05:00",
        "status": "completed",
        "idempotency_key": "report-batch",
        "config_json": "{}",
    })
    db.upsert_world({
        "id": "report_batch:world_0",
        "batch_id": "report_batch",
        "world_index": 0,
        "model_name": "m1",
        "status": "completed",
        "raw_status": "success",
        "run_dir": str(world_dir),
        "dataset_path": str(dataset_path),
        "error_message": "",
        "log_tail": "",
        "started_at": "2026-06-27 10:00:00",
        "completed_at": "2026-06-27 10:05:00",
        "elapsed_seconds": 3.0,
    })


def test_report_job_generates_only_selected_versions(client, tmp_path, monkeypatch):
    from adarian.report import runner
    from adarian.report.config import ReportModelConfig

    _insert_batch(tmp_path)
    monkeypatch.setattr(runner, "resolve_model_config", lambda _payload: ReportModelConfig("m", "http://base", "key", 0.3, 1000, "env"))
    monkeypatch.setattr(runner, "write_body", lambda **_kwargs: "\n".join([
        "# 测试事件舆情风险研判",
        "## 一、舆情概要",
        "测试事件引发关注。",
        "## 二、演化分析",
        "讨论呈现分化态势。",
        "## 三、风险研判",
        "存在负向叙事聚合风险。",
        "## 四、对策意见",
        "事件主体与平台方应补充事实说明。",
    ]))

    response = client.post("/api/report", json={
        "batch_id": "report_batch",
        "versions": ["A", "C"],
        "appendix_mode": "both",
        "allow_partial": True,
    })
    assert response.status_code == 200
    body = response.get_json()
    names = [item["name"] for item in body["files"]]
    assert any(item["version"] == "A" and item["appendix"] == "none" for item in body["files"])
    assert any(item["version"] == "A" and item["appendix"] == "included" for item in body["files"])
    assert any(item["version"] == "C" and item["appendix"] == "none" for item in body["files"])
    assert not any(item.get("version") == "B" for item in body["files"])
    assert "appendix_b.json" in names


def test_report_job_blocks_partial_without_consent(client, tmp_path):
    from adarian.serve import db

    _insert_batch(tmp_path)
    db.upsert_world({
        "id": "report_batch:world_1",
        "batch_id": "report_batch",
        "world_index": 1,
        "model_name": "m2",
        "status": "failed",
        "raw_status": "failed",
        "run_dir": "",
        "dataset_path": "",
        "error_message": "failed",
        "log_tail": "",
        "started_at": "",
        "completed_at": "",
        "elapsed_seconds": None,
    })
    response = client.post("/api/report", json={"batch_id": "report_batch", "allow_partial": False})
    assert response.status_code == 409
    assert response.get_json()["code"] == "PARTIAL_COMPLETED_WORLDS"
