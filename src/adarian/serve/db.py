#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite persistence for v1.5.0b web APIs."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from adarian.serve.paths import SERVE_DB_PATH, ensure_runtime_dirs

DB_PATH = Path(os.getenv("ADARIAN_SERVE_DB", str(SERVE_DB_PATH)))

# In-flight batch tracking — allows signal handlers to mark them "failed" on death.
_RUNNING_BATCH_IDS: set[str] = set()


def track_batch(batch_id: str) -> None:
    """Register a batch that is actively running."""
    _RUNNING_BATCH_IDS.add(batch_id)


def untrack_batch(batch_id: str) -> None:
    """Remove a finished batch from the live set."""
    _RUNNING_BATCH_IDS.discard(batch_id)


def running_batch_ids() -> set[str]:
    """Return a snapshot of currently-running batch IDs."""
    return set(_RUNNING_BATCH_IDS)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_runtime_dirs()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY,
                task_name TEXT NOT NULL,
                seed_text TEXT NOT NULL DEFAULT '',
                seed_path TEXT NOT NULL DEFAULT '',
                models TEXT NOT NULL DEFAULT '[]',
                tag TEXT NOT NULL DEFAULT '',
                base_url TEXT NOT NULL DEFAULT '',
                batch_dir TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                idempotency_key TEXT UNIQUE,
                config_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS worlds (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                world_index INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                raw_status TEXT NOT NULL DEFAULT 'pending',
                run_dir TEXT NOT NULL DEFAULT '',
                dataset_path TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                log_tail TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL DEFAULT '',
                completed_at TEXT NOT NULL DEFAULT '',
                elapsed_seconds REAL,
                FOREIGN KEY(batch_id) REFERENCES batches(id)
            );

            CREATE TABLE IF NOT EXISTS model_gateways (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT 'openai-compatible',
                api_key_encrypted TEXT NOT NULL DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'user',
                key_storage_mode TEXT NOT NULL DEFAULT 'none',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS report_jobs (
                id TEXT PRIMARY KEY,
                client_session_id TEXT NOT NULL DEFAULT '',
                batch_id TEXT NOT NULL,
                skill_id TEXT NOT NULL DEFAULT 'default_government',
                versions TEXT NOT NULL DEFAULT '["B"]',
                appendix_mode TEXT NOT NULL DEFAULT 'none',
                allow_partial INTEGER NOT NULL DEFAULT 0,
                partial INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'idle',
                progress INTEGER NOT NULL DEFAULT 0,
                current_step TEXT NOT NULL DEFAULT '',
                completed_worlds_count INTEGER NOT NULL DEFAULT 0,
                failed_worlds_count INTEGER NOT NULL DEFAULT 0,
                model_config_resolved_from TEXT NOT NULL DEFAULT 'missing',
                output_dir TEXT NOT NULL DEFAULT '',
                files_json TEXT NOT NULL DEFAULT '[]',
                appendix_json TEXT NOT NULL DEFAULT '{}',
                audit_json TEXT NOT NULL DEFAULT '{}',
                request_json TEXT NOT NULL DEFAULT '{}',
                error_code TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(batch_id) REFERENCES batches(id)
            );
            """
        )


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def get_setting(key: str, default: Any = None) -> Any:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except json.JSONDecodeError:
        return row["value"]


def set_setting(key: str, value: Any) -> None:
    init_db()
    payload = json.dumps(value, ensure_ascii=False)
    with connect() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, payload),
        )


def get_batch(batch_id: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
    return row_to_dict(row)


def get_batch_by_key(idempotency_key: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM batches WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
    return row_to_dict(row)


def upsert_batch(batch: dict[str, Any]) -> None:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO batches(id, task_name, seed_text, seed_path, models, tag, base_url, batch_dir,
                                created_at, completed_at, status, idempotency_key, config_json)
            VALUES(:id, :task_name, :seed_text, :seed_path, :models, :tag, :base_url, :batch_dir,
                   :created_at, :completed_at, :status, :idempotency_key, :config_json)
            ON CONFLICT(id) DO UPDATE SET
                task_name=excluded.task_name,
                seed_text=excluded.seed_text,
                seed_path=excluded.seed_path,
                models=excluded.models,
                tag=excluded.tag,
                base_url=excluded.base_url,
                batch_dir=excluded.batch_dir,
                completed_at=excluded.completed_at,
                status=excluded.status,
                config_json=excluded.config_json
            """,
            batch,
        )


def list_batches(limit: int = 100) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM batches ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_world(world: dict[str, Any]) -> None:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO worlds(id, batch_id, world_index, model_name, status, raw_status, run_dir, dataset_path,
                               error_message, log_tail, started_at, completed_at, elapsed_seconds)
            VALUES(:id, :batch_id, :world_index, :model_name, :status, :raw_status, :run_dir, :dataset_path,
                   :error_message, :log_tail, :started_at, :completed_at, :elapsed_seconds)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                raw_status=excluded.raw_status,
                run_dir=excluded.run_dir,
                dataset_path=excluded.dataset_path,
                error_message=excluded.error_message,
                log_tail=excluded.log_tail,
                completed_at=excluded.completed_at,
                elapsed_seconds=excluded.elapsed_seconds
            """,
            world,
        )


def list_worlds(batch_id: str) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM worlds WHERE batch_id = ? ORDER BY world_index ASC",
            (batch_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_gateway(gateway: dict[str, Any]) -> None:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO model_gateways(id, name, base_url, provider, api_key_encrypted, enabled, source,
                                       key_storage_mode, created_at, updated_at)
            VALUES(:id, :name, :base_url, :provider, :api_key_encrypted, :enabled, :source,
                   :key_storage_mode, :created_at, :updated_at)
            """,
            gateway,
        )


def update_gateway(gateway_id: str, patch: dict[str, Any]) -> bool:
    init_db()
    existing = get_gateway(gateway_id)
    if not existing:
        return False
    merged = {**existing, **patch, "updated_at": now()}
    with connect() as conn:
        conn.execute(
            """
            UPDATE model_gateways
            SET name=:name, base_url=:base_url, provider=:provider, api_key_encrypted=:api_key_encrypted,
                enabled=:enabled, key_storage_mode=:key_storage_mode, updated_at=:updated_at
            WHERE id=:id
            """,
            merged,
        )
    return True


def get_gateway(gateway_id: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM model_gateways WHERE id = ?", (gateway_id,)).fetchone()
    return row_to_dict(row)


def list_user_gateways() -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM model_gateways ORDER BY created_at DESC",
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_report_job(job: dict[str, Any]) -> None:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO report_jobs(id, client_session_id, batch_id, skill_id, versions, appendix_mode,
                                    allow_partial, partial, status, progress, current_step,
                                    completed_worlds_count, failed_worlds_count, model_config_resolved_from,
                                    output_dir, files_json, appendix_json, audit_json, request_json,
                                    error_code, error_message, created_at, updated_at, completed_at)
            VALUES(:id, :client_session_id, :batch_id, :skill_id, :versions, :appendix_mode,
                   :allow_partial, :partial, :status, :progress, :current_step,
                   :completed_worlds_count, :failed_worlds_count, :model_config_resolved_from,
                   :output_dir, :files_json, :appendix_json, :audit_json, :request_json,
                   :error_code, :error_message, :created_at, :updated_at, :completed_at)
            ON CONFLICT(id) DO UPDATE SET
                skill_id=excluded.skill_id,
                versions=excluded.versions,
                appendix_mode=excluded.appendix_mode,
                allow_partial=excluded.allow_partial,
                partial=excluded.partial,
                status=excluded.status,
                progress=excluded.progress,
                current_step=excluded.current_step,
                completed_worlds_count=excluded.completed_worlds_count,
                failed_worlds_count=excluded.failed_worlds_count,
                model_config_resolved_from=excluded.model_config_resolved_from,
                output_dir=excluded.output_dir,
                files_json=excluded.files_json,
                appendix_json=excluded.appendix_json,
                audit_json=excluded.audit_json,
                request_json=excluded.request_json,
                error_code=excluded.error_code,
                error_message=excluded.error_message,
                updated_at=excluded.updated_at,
                completed_at=excluded.completed_at
            """,
            job,
        )


def get_report_job(job_id: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM report_jobs WHERE id = ?", (job_id,)).fetchone()
    return row_to_dict(row)


def latest_report_job_for_session(client_session_id: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM report_jobs
            WHERE client_session_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (client_session_id,),
        ).fetchone()
    return row_to_dict(row)


def latest_report_job() -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM report_jobs
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()
    return row_to_dict(row)
