# -*- coding: utf-8 -*-
from __future__ import annotations

import zipfile

from adarian.report.document_export import write_report_docx, write_report_pdf
from adarian.report.runner import _classify_report_error


def _report_view() -> dict:
    return {
        "id": "report_test:B",
        "job_id": "report_test",
        "batch_id": "batch_test",
        "version": "B",
        "title": "测试事件舆情风险研判",
        "subtitle": "标准研判报告，基于 completed worlds 的 simulation_dataset 生成。",
        "generated_at": "2026-07-27 10:00:00",
        "source": {"batch_id": "batch_test"},
        "kpis": [
            {"label": "综合风险", "value": "高风险", "note": "completed worlds 聚合"},
            {"label": "world 覆盖", "value": "2", "note": "completed worlds"},
        ],
        "sections": [
            {
                "id": "summary",
                "heading": "一、舆情概要",
                "blocks": [{"type": "paragraph", "text": "测试事件引发持续关注。"}],
            },
            {
                "id": "risk",
                "heading": "二、风险研判",
                "blocks": [
                    {"type": "subheading", "text": "（一）负向叙事聚合风险"},
                    {"type": "list", "items": ["及时补充事实说明。", "持续监测误读扩散。"]},
                ],
            },
        ],
        "appendix": {
            "mode": "references",
            "event_name": "测试事件",
            "worlds_count": 2,
            "confirmed_risks": 1,
            "risk_distribution": "high:1 / medium:1",
            "references": ["2 个 completed world 将该类型列为主要风险候选。"],
        },
    }


def test_docx_export_is_editable_ooxml(tmp_path) -> None:
    path = write_report_docx(_report_view(), tmp_path / "report.docx")

    assert path.stat().st_size > 1000
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "测试事件舆情风险研判" in document_xml
    assert "负向叙事聚合风险" in document_xml


def test_pdf_export_is_readable(tmp_path) -> None:
    path = write_report_pdf(_report_view(), tmp_path / "report.pdf")

    assert path.stat().st_size > 1000
    payload = path.read_bytes()
    assert payload.startswith(b"%PDF-")
    assert payload.rstrip().endswith(b"%%EOF")


def test_missing_pdf_font_has_actionable_error() -> None:
    code, message = _classify_report_error(RuntimeError("REPORT_PDF_FONT_NOT_FOUND"))

    assert code == "REPORT_EXPORT_UNAVAILABLE"
    assert "ADARIAN_REPORT_FONT_PATH" in message
