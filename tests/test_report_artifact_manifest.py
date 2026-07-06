from __future__ import annotations

import json

from adarian.report.runner import status_response
from adarian.report.view_model import build_artifact_manifest


def test_artifact_manifest_hides_internal_data_artifacts(tmp_path) -> None:
    output_dir = tmp_path / "report"
    output_dir.mkdir()
    md = output_dir / "report.md"
    html = output_dir / "report.html"
    md.write_text("# report", encoding="utf-8")
    html.write_text("<html></html>", encoding="utf-8")

    manifest = build_artifact_manifest([
        {"id": "appendix_b", "appendix": "data", "name": "appendix_b.json", "url": "/files/appendix_b.json"},
        {"id": "audit", "appendix": "data", "name": "audit_report.json", "url": "/files/audit_report.json"},
        {"id": "report_view_B", "kind": "report_view", "internal": True, "name": "report_view_B.json", "url": "/files/report_view_B.json"},
        {"id": "B_none", "version": "B", "appendix": "none", "name": "report.md", "url": "/files/report.md", "format": "md"},
        {"id": "B_html", "version": "B", "appendix": "none", "name": "report.html", "url": "/files/report.html", "format": "html"},
    ], output_dir)

    ids = {item["id"] for item in manifest}
    assert "appendix_b" not in ids
    assert "audit" not in ids
    assert "report_view_B" not in ids
    assert {"B_none", "B_html"} <= ids
    assert any(item["format"] == "pdf" and item["state"] == "planned" for item in manifest)


def test_status_response_includes_native_view_and_manifest(tmp_path) -> None:
    output_dir = tmp_path / "report"
    version_dir = output_dir / "B版"
    version_dir.mkdir(parents=True)
    view = {
        "id": "report_test:B",
        "job_id": "report_test",
        "batch_id": "batch_test",
        "version": "B",
        "title": "测试报告",
        "sections": [],
    }
    (version_dir / "report_view_B.json").write_text(json.dumps(view, ensure_ascii=False), encoding="utf-8")
    (version_dir / "report.md").write_text("# 测试报告", encoding="utf-8")
    job = {
        "id": "report_test",
        "batch_id": "batch_test",
        "status": "completed",
        "progress": 100,
        "current_step": "报告生成完成",
        "versions": '["B"]',
        "appendix_mode": "none",
        "partial": 0,
        "completed_worlds_count": 1,
        "failed_worlds_count": 0,
        "skill_id": "default_government",
        "model_config_resolved_from": "env",
        "output_dir": str(output_dir),
        "files_json": json.dumps([
            {
                "id": "report_view_B",
                "kind": "report_view",
                "version": "B",
                "appendix": "data",
                "internal": True,
                "name": "report_view_B.json",
                "url": "/api/report/jobs/report_test/files/B版/report_view_B.json",
            },
            {
                "id": "B_none",
                "version": "B",
                "appendix": "none",
                "name": "report.md",
                "url": "/api/report/jobs/report_test/files/B版/report.md",
                "format": "md",
            },
        ], ensure_ascii=False),
        "appendix_json": "{}",
        "audit_json": "{}",
        "error_code": "",
        "error_message": "",
    }

    response = status_response(job)

    assert response["ui_state"] == "report"
    assert response["report_view"]["title"] == "测试报告"
    assert response["artifacts"][0]["id"] == "B_none"
    assert all(item["id"] != "report_view_B" for item in response["artifacts"])


def test_status_response_blocks_legacy_completed_job_without_native_view(tmp_path) -> None:
    output_dir = tmp_path / "report"
    output_dir.mkdir()
    job = {
        "id": "legacy_report",
        "batch_id": "batch_test",
        "status": "completed",
        "progress": 100,
        "current_step": "报告生成完成",
        "versions": '["B"]',
        "appendix_mode": "none",
        "partial": 0,
        "completed_worlds_count": 1,
        "failed_worlds_count": 0,
        "skill_id": "default_government",
        "model_config_resolved_from": "env",
        "output_dir": str(output_dir),
        "files_json": "[]",
        "appendix_json": "{}",
        "audit_json": "{}",
        "error_code": "",
        "error_message": "",
    }

    response = status_response(job)

    assert response["ui_state"] == "blocked"
    assert response["report_view"] is None
    assert response["error_code"] == "REPORT_VIEW_NOT_FOUND"
