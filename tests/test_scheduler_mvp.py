# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path

_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

import adarian.batch as batch_mod
import adarian.inspect as inspect_mod


def test_inspect_dataset_reads_primary_types(tmp_path):
    dataset = tmp_path / "simulation_dataset.json"
    dataset.write_text(
        json.dumps(
            {
                "simulation_result": {
                    "risk_type_classification": {
                        "primary_types": ["negative_narrative_aggregation_risk"]
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    evidence = batch_mod.inspect_dataset(dataset)

    assert evidence["dataset_exists"] is True
    assert evidence["primary_types_exists"] is True
    assert evidence["primary_types"] == ["negative_narrative_aggregation_risk"]


def test_start_batch_writes_config_and_seed_text(tmp_path, monkeypatch):
    monkeypatch.setattr(batch_mod.config, "OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        batch_mod,
        "available_models",
        lambda: {"model_a": "Model A", "model_b": "Model B"},
    )

    session = batch_mod.start_batch(
        models=["model_a", "model_b"],
        seed_text="测试事件",
        tag="unit test",
    )

    assert session.batch_dir.exists()
    assert session.seed_path.read_text(encoding="utf-8").strip() == "测试事件"
    assert (session.batch_dir / "batch_config.yaml").exists()
    assert session.states["world_0"].dataset_path.endswith("world_0/simulation_dataset.json")
    assert session.as_dict()["report_agent_consumer"]["enabled"] is False


def test_inspect_batch_marks_success_from_disk_evidence(tmp_path):
    batch_dir = tmp_path / "batch_demo"
    world_dir = batch_dir / "world_0"
    world_dir.mkdir(parents=True)
    (world_dir / "run_meta.json").write_text(
        json.dumps({"status": "success", "model": "model_a", "elapsed_seconds": 1.2}),
        encoding="utf-8",
    )
    (world_dir / "simulation_dataset.json").write_text(
        json.dumps(
            {
                "simulation_result": {
                    "risk_type_classification": {"primary_types": ["transparency_risk"]}
                }
            }
        ),
        encoding="utf-8",
    )

    status = inspect_mod.inspect_batch(batch_dir)

    assert status["status"] == "success"
    assert status["summary"]["success"] == 1
    assert status["worlds"][0]["model_name"] == "model_a"
