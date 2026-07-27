# -*- coding: utf-8 -*-
"""Report job runner."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from adarian.serve import db
from adarian.serve.schemas import normalize_status

from .appendix_builder import build_appendix_b, load_dataset, write_appendix_b
from .config import parse_appendix_mode, parse_versions, resolve_model_config, resolve_skill_id, safe_slug
from .document_export import write_report_docx, write_report_pdf
from .quality import assemble_report, audit_body, is_blocked, write_audit
from .skills_registry import resolve_report_skill
from .view_builder import build_native_report_view, write_report_html, write_report_view
from .view_model import artifact_metadata, build_artifact_manifest, load_native_report_view
from .writer import write_body, write_debug_body


def create_job(payload: dict[str, Any], client_session_id: str = "") -> dict[str, Any]:
    payload = dict(payload)
    now = db.now()
    versions = parse_versions(payload.get("versions") or (["B"] if not payload.get("version") else [payload.get("version")]))
    appendix_mode = parse_appendix_mode(payload.get("appendix_mode"))
    skill_id = resolve_skill_id(payload)
    skill = resolve_report_skill(skill_id)
    payload["skill_id"] = skill.id
    payload["skill_snapshot"] = skill.snapshot()
    job = {
        "id": f"report_{uuid.uuid4().hex[:12]}",
        "client_session_id": client_session_id or str(payload.get("client_session_id") or ""),
        "batch_id": str(payload.get("batch_id") or ""),
        "skill_id": skill_id,
        "versions": json.dumps(versions, ensure_ascii=False),
        "appendix_mode": appendix_mode,
        "allow_partial": 1 if payload.get("allow_partial") else 0,
        "partial": 0,
        "status": "idle",
        "progress": 0,
        "current_step": "等待生成",
        "completed_worlds_count": 0,
        "failed_worlds_count": 0,
        "model_config_resolved_from": "missing",
        "output_dir": "",
        "files_json": "[]",
        "appendix_json": "{}",
        "audit_json": "{}",
        "request_json": json.dumps(payload, ensure_ascii=False),
        "error_code": "",
        "error_message": "",
        "created_at": now,
        "updated_at": now,
        "completed_at": "",
    }
    db.upsert_report_job(job)
    return job


def run_job(job_id: str) -> dict[str, Any]:
    job = db.get_report_job(job_id)
    if not job:
        raise ValueError(f"report job not found: {job_id}")
    try:
        payload = json.loads(job.get("request_json") or "{}")
    except json.JSONDecodeError:
        payload = {}

    try:
        _update(job, status="running", progress=5, current_step="读取 batch")
        batch = db.get_batch(job["batch_id"])
        if not batch:
            return _block(job, "BATCH_NOT_FOUND", "Batch not found")
        worlds = db.list_worlds(job["batch_id"])
        completed = [w for w in worlds if normalize_status(w.get("raw_status") or w.get("status")) == "completed"]
        failed = [w for w in worlds if normalize_status(w.get("raw_status") or w.get("status")) == "failed"]
        partial = bool(failed)
        _update(job, completed_worlds_count=len(completed), failed_worlds_count=len(failed), partial=1 if partial else 0)
        if not completed:
            return _block(job, "NO_COMPLETED_WORLDS", "没有已完成样本可用于报告生成")
        if failed and not job.get("allow_partial"):
            return _block(job, "PARTIAL_COMPLETED_WORLDS", "存在失败样本，请确认仅基于已完成样本生成")

        _update(job, progress=18, current_step="读取结构化数据")
        dataset_paths = [_dataset_path(w) for w in completed]
        missing = [str(p) for p in dataset_paths if not p.exists()]
        if missing:
            return _block(job, "DATASET_MISSING", "已完成样本缺少结构化数据", {"missing": missing})
        datasets = [load_dataset(path) for path in dataset_paths]

        event_name = _event_name(datasets, batch)
        output_dir = Path(batch.get("batch_dir") or "") / "reports" / job["id"]
        output_dir.mkdir(parents=True, exist_ok=True)
        skill_snapshot = payload.get("skill_snapshot") or resolve_report_skill(job["skill_id"]).snapshot()
        (output_dir / "skill_snapshot.json").write_text(
            json.dumps(skill_snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _update(job, output_dir=str(output_dir), progress=30, current_step="聚合报告依据")
        appendix_b = build_appendix_b(datasets, event_name)
        appendix_path = write_appendix_b(appendix_b, output_dir / "appendix_b.json")
        appendix_file = artifact_metadata({"id": "appendix_b", "version": "data", "appendix": "data", "name": "appendix_b.json", "url": f"/api/report/jobs/{job['id']}/files/appendix_b.json", "previewable": False})
        _update(
            job,
            appendix_json=json.dumps(_appendix_summary(appendix_b, appendix_path), ensure_ascii=False),
            files_json=json.dumps([appendix_file], ensure_ascii=False),
        )

        model_config = resolve_model_config(payload)
        if not model_config:
            _update(job, appendix_json=json.dumps(_appendix_summary(appendix_b, appendix_path), ensure_ascii=False))
            return _block(job, "REPORT_MODEL_NOT_CONFIGURED", "未配置报告模型，请在 03-models 或 .env 中配置")
        model_label = f"{model_config.resolved_from}:{model_config.model}"
        payload["resolved_model"] = {
            "resolved_from": model_config.resolved_from,
            "gateway_id": model_config.gateway_id,
            "model_id": model_config.model,
            "temperature": model_config.temperature,
            "max_tokens": model_config.max_tokens,
        }
        _update(
            job,
            request_json=json.dumps(payload, ensure_ascii=False),
            model_config_resolved_from=model_config.resolved_from,
            progress=42,
            current_step="调用报告模型",
        )

        versions = json.loads(job.get("versions") or '["B"]')
        appendix_mode = job.get("appendix_mode") or "none"
        files = [appendix_file]
        combined_audit = {"fatal": 0, "high": 0, "medium": 0, "passed": 0, "blocked_reasons": []}

        for index, version in enumerate(versions):
            _update(job, progress=45 + int(index * 40 / max(len(versions), 1)), current_step=f"生成 {version} 版正文")
            body = write_body(
                appendix_b=appendix_b,
                version=version,
                skill_id=job["skill_id"],
                model_config=model_config,
                skill_snapshot=skill_snapshot,
            )
            audit = audit_body(body, skill_snapshot.get("checklist") or {})
            combined_audit = _merge_audit(combined_audit, audit)
            if is_blocked(audit):
                write_debug_body(body, output_dir, version)
                write_audit(combined_audit, output_dir)
                _update(
                    job,
                    audit_json=json.dumps(combined_audit, ensure_ascii=False),
                    appendix_json=json.dumps(_appendix_summary(appendix_b, appendix_path), ensure_ascii=False),
                )
                return _block(job, "REPORT_QUALITY_BLOCKED", "报告质量审核阻断")

            version_dir = output_dir / f"{version}版"
            version_dir.mkdir(parents=True, exist_ok=True)
            display_mode = "included" if appendix_mode in {"included", "both"} else "none"
            report_view = build_native_report_view(
                body=body,
                appendix_b=appendix_b,
                audit=audit,
                job=job,
                version=version,
                appendix_mode=display_mode,
                model_label=model_label,
                public_appendix=str(skill_snapshot.get("appendix") or ""),
                skill_snapshot=skill_snapshot,
            )
            view_name = f"report_view_{version}.json"
            view_path = write_report_view(report_view, version_dir / view_name)
            view_rel = f"{version}版/{view_name}"
            view_id = f"report_view_{version}"
            files.append(artifact_metadata({
                "id": view_id,
                "kind": "report_view",
                "version": version,
                "appendix": "data",
                "internal": True,
                "name": view_name,
                "url": f"/api/report/jobs/{job['id']}/files/{view_rel}",
                "previewable": True,
                "downloadable": False,
                "source_view_id": view_id,
            }))
            export_stem = f"{safe_slug(event_name)}_舆情风险研判_{datetime.now().strftime('%Y%m%d')}_v1"
            html_name = f"{export_stem}.html"
            html_path = write_report_html(report_view, version_dir / html_name)
            html_rel = f"{version}版/{html_name}"
            files.append(artifact_metadata({
                "id": f"{version}_html",
                "version": version,
                "appendix": "export",
                "name": html_name,
                "url": f"/api/report/jobs/{job['id']}/files/{html_rel}",
                "format": "html",
                "label": "HTML",
                "source_view_id": view_id,
                "note": "交互报告轻量导出",
                "size_bytes": html_path.stat().st_size,
            }))
            _update(job, current_step=f"生成 {version} 版可下载文件")
            docx_name = f"{export_stem}.docx"
            docx_path = write_report_docx(report_view, version_dir / docx_name)
            docx_rel = f"{version}版/{docx_name}"
            files.append(artifact_metadata({
                "id": f"{version}_docx",
                "version": version,
                "appendix": "export",
                "name": docx_name,
                "url": f"/api/report/jobs/{job['id']}/files/{docx_rel}",
                "format": "docx",
                "label": "DOCX",
                "source_view_id": view_id,
                "note": "可编辑正式文档",
                "size_bytes": docx_path.stat().st_size,
            }))
            pdf_name = f"{export_stem}.pdf"
            pdf_path = write_report_pdf(report_view, version_dir / pdf_name)
            pdf_rel = f"{version}版/{pdf_name}"
            files.append(artifact_metadata({
                "id": f"{version}_pdf",
                "version": version,
                "appendix": "export",
                "name": pdf_name,
                "url": f"/api/report/jobs/{job['id']}/files/{pdf_rel}",
                "format": "pdf",
                "label": "PDF",
                "source_view_id": view_id,
                "note": "固定版式正式文档",
                "size_bytes": pdf_path.stat().st_size,
            }))
            modes = ["none", "included"] if appendix_mode == "both" else [appendix_mode]
            for mode in modes:
                content = assemble_report(body, mode, str(skill_snapshot.get("appendix") or ""))
                suffix = "含附录" if mode == "included" else "无附录"
                name = f"{safe_slug(event_name)}_舆情风险研判_{datetime.now().strftime('%Y%m%d')}_v1_{suffix}.md"
                path = version_dir / name
                path.write_text(content, encoding="utf-8")
                rel = f"{version}版/{name}"
                files.append(artifact_metadata({
                    "id": f"{version}_{mode}",
                    "version": version,
                    "appendix": mode,
                    "name": name,
                    "url": f"/api/report/jobs/{job['id']}/files/{rel}",
                    "format": "md",
                    "label": "Markdown",
                    "source_view_id": view_id,
                    "note": "MVP 兼容导出",
                }))

        audit_path = write_audit(combined_audit, output_dir)
        files.append(artifact_metadata({"id": "audit", "version": versions[0], "appendix": "data", "name": audit_path.name, "url": f"/api/report/jobs/{job['id']}/files/{audit_path.name}", "previewable": False}))
        return _complete(job, files, appendix_b, appendix_path, combined_audit)
    except Exception as exc:
        return _fail(job, *_classify_report_error(exc))


def status_response(job: dict[str, Any]) -> dict[str, Any]:
    try:
        files = json.loads(job.get("files_json") or "[]")
    except json.JSONDecodeError:
        files = []
    files = [artifact_metadata(file) for file in files]
    try:
        appendix = json.loads(job.get("appendix_json") or "{}")
    except json.JSONDecodeError:
        appendix = {}
    try:
        audit = json.loads(job.get("audit_json") or "{}")
    except json.JSONDecodeError:
        audit = {}
    versions = json.loads(job.get("versions") or '["B"]')
    try:
        request_payload = json.loads(job.get("request_json") or "{}")
    except json.JSONDecodeError:
        request_payload = {}
    skill_snapshot = request_payload.get("skill_snapshot") or {}
    resolved_model = request_payload.get("resolved_model") or {}
    version = (versions or ["B"])[0]
    report_view = load_native_report_view(job, version) if job.get("status") == "completed" else None
    artifacts = build_artifact_manifest(files, job.get("output_dir") or "")
    legacy_view_missing = job.get("status") == "completed" and not report_view
    return {
        "job_id": job["id"],
        "report_id": f"{job['batch_id']}:{job['id']}",
        "batch_id": job["batch_id"],
        "status": job.get("status") or "idle",
        "ui_state": _ui_state(job, report_view),
        "progress": int(job.get("progress") or 0),
        "current_step": job.get("current_step") or "",
        "events": _status_events(job),
        "selected_versions": versions,
        "version": version,
        "appendix_mode": job.get("appendix_mode") or "none",
        "partial": bool(job.get("partial")),
        "completed_worlds_count": int(job.get("completed_worlds_count") or 0),
        "failed_worlds_count": int(job.get("failed_worlds_count") or 0),
        "skill_id": job.get("skill_id") or "default_government",
        "skill": {
            "id": job.get("skill_id") or "default_government",
            "label": skill_snapshot.get("label") or job.get("skill_id") or "default_government",
            "version": skill_snapshot.get("version") or "1",
            "source": skill_snapshot.get("source") or "builtin",
            "directory": skill_snapshot.get("directory") or "",
            "checksum": skill_snapshot.get("checksum") or "",
        },
        "model": {
            "resolved_from": resolved_model.get("resolved_from") or job.get("model_config_resolved_from") or "missing",
            "gateway_id": resolved_model.get("gateway_id") or request_payload.get("gateway_id") or "",
            "model_id": resolved_model.get("model_id") or request_payload.get("model_id") or "",
            "temperature": resolved_model.get("temperature", request_payload.get("temperature")),
            "max_tokens": resolved_model.get("max_tokens", request_payload.get("max_tokens")),
        },
        "files": files,
        "artifacts": artifacts,
        "report_view": report_view,
        "appendix_b": appendix or {"available": False, "worlds_count": 0, "confirmed_risks": 0, "preview": {}},
        "audit_summary": audit or {"fatal": 0, "high": 0, "medium": 0, "passed": 0, "blocked_reasons": []},
        "error_code": job.get("error_code") or ("REPORT_VIEW_NOT_FOUND" if legacy_view_missing else ""),
        "error_message": job.get("error_message") or ("历史报告缺少交互阅读数据，请重新生成报告。" if legacy_view_missing else ""),
    }


def _ui_state(job: dict[str, Any], report_view: dict[str, Any] | None) -> str:
    status = job.get("status") or "idle"
    if status in {"idle", "running"}:
        return "generating"
    if status == "completed" and report_view:
        return "report"
    if status == "completed" and not report_view:
        return "blocked"
    if status == "blocked":
        return "blocked"
    if status == "failed":
        return "failed"
    return "generating"


def _status_events(job: dict[str, Any]) -> list[dict[str, str]]:
    progress = int(job.get("progress") or 0)
    current = job.get("current_step") or ""
    stages = [
        (5, "读取 batch", "定位报告来源 batch。"),
        (18, "读取结构化数据", "读取已完成样本的报告数据。"),
        (30, "聚合报告依据", "聚合风险、主体、对策和演化摘要。"),
        (42, "调用报告模型", "生成报告正文。"),
        (70, "构建交互报告", "准备浏览器阅读所需的结构化内容。"),
        (82, "生成可下载文件", "生成 HTML、Markdown、DOCX 和 PDF。"),
        (100, "报告生成完成", "报告正文和导出入口已就绪。"),
    ]
    events = []
    for threshold, label, detail in stages:
        if progress >= threshold:
            status = "done"
        elif current and label in current:
            status = "current"
        else:
            status = "pending"
        events.append({"label": label, "detail": detail, "status": status})
    if job.get("status") in {"blocked", "failed"}:
        events.append({"label": job.get("current_step") or "报告生成失败", "detail": job.get("error_message") or "", "status": "current"})
    return events


def _dataset_path(world: dict[str, Any]) -> Path:
    if world.get("dataset_path"):
        return Path(world["dataset_path"])
    return Path(world.get("run_dir") or "") / "simulation_dataset.json"


def _event_name(datasets: list[dict[str, Any]], batch: dict[str, Any]) -> str:
    first = datasets[0]
    return (
        first.get("run_info", {}).get("event_name")
        or first.get("source_context", {}).get("event_summary")
        or batch.get("task_name")
        or "舆情事件"
    )


def _appendix_summary(appendix_b: dict[str, Any], path: Path) -> dict[str, Any]:
    risks = appendix_b.get("risk_assessment", {}).get("risks") or []
    return {
        "available": True,
        "path": str(path),
        "worlds_count": int(appendix_b.get("meta", {}).get("worlds_count") or 0),
        "confirmed_risks": len(risks),
        "preview": {
            "event_name": appendix_b.get("meta", {}).get("event_name"),
            "risk_level_distribution": appendix_b.get("evolution_analysis", {}).get("risk_level_distribution"),
            "risk_type_frequency": appendix_b.get("evolution_analysis", {}).get("risk_type_frequency"),
        },
    }


def _merge_audit(base: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    return {
        "fatal": int(base.get("fatal") or 0) + int(item.get("fatal") or 0),
        "high": int(base.get("high") or 0) + int(item.get("high") or 0),
        "medium": int(base.get("medium") or 0) + int(item.get("medium") or 0),
        "passed": int(base.get("passed") or 0) + int(item.get("passed") or 0),
        "blocked_reasons": [*(base.get("blocked_reasons") or []), *(item.get("blocked_reasons") or [])],
    }


def _update(job: dict[str, Any], **patch: Any) -> dict[str, Any]:
    current = db.get_report_job(job["id"]) or job
    merged = {**current, **patch, "updated_at": db.now()}
    db.upsert_report_job(merged)
    job.update(merged)
    return merged


def _block(job: dict[str, Any], code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    audit = json.loads(job.get("audit_json") or "{}") if job.get("audit_json") else {}
    if not audit:
        audit = {"fatal": 1, "high": 0, "medium": 0, "passed": 0, "blocked_reasons": [message]}
    else:
        audit.setdefault("blocked_reasons", []).append(message)
    return _update(
        job,
        status="blocked",
        progress=max(int(job.get("progress") or 0), 85),
        current_step=message,
        audit_json=json.dumps(audit, ensure_ascii=False),
        error_code=code,
        error_message=message if not details else f"{message}: {details}",
        completed_at=db.now(),
    )


def _fail(job: dict[str, Any], code: str, message: str) -> dict[str, Any]:
    return _update(job, status="failed", progress=max(int(job.get("progress") or 0), 80), current_step="报告生成失败", error_code=code, error_message=message, completed_at=db.now())


def _classify_report_error(exc: Exception) -> tuple[str, str]:
    message = str(exc)
    lowered = message.lower()
    if "report_pdf_font_not_found" in lowered:
        return (
            "REPORT_EXPORT_UNAVAILABLE",
            f"{message}；请通过 ADARIAN_REPORT_FONT_PATH 配置可用的中文 TrueType 字体",
        )
    if any(marker in lowered for marker in ("502", "503", "504", "timeout", "timed out", "connection", "network")):
        return "REPORT_MODEL_UNAVAILABLE", f"{message}；请检查内网路由、模型网关或稍后重试"
    if any(marker in lowered for marker in ("401", "403", "api key", "api-key", "auth", "unauthorized", "forbidden")):
        return "REPORT_MODEL_UNAVAILABLE", f"{message}；请检查报告模型的网关鉴权配置"
    return "REPORT_WRITE_FAILED", message


def _complete(job: dict[str, Any], files: list[dict[str, Any]], appendix_b: dict[str, Any], appendix_path: Path, audit: dict[str, Any]) -> dict[str, Any]:
    return _update(
        job,
        status="completed",
        progress=100,
        current_step="报告生成完成",
        files_json=json.dumps(files, ensure_ascii=False),
        appendix_json=json.dumps(_appendix_summary(appendix_b, appendix_path), ensure_ascii=False),
        audit_json=json.dumps(audit, ensure_ascii=False),
        error_code="",
        error_message="",
        completed_at=db.now(),
    )
