#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import io


CUSTOM_SKILL = b"""---
id: concise_public
label: Concise Public
description: User imported concise style.
version: 3
---

# Writing rules

Use short, factual paragraphs and the four required report chapters.
"""


def test_report_skill_markdown_import_update_and_delete(client, tmp_path, monkeypatch):
    monkeypatch.setenv("ADARIAN_REPORT_SKILLS_DIR", str(tmp_path / "skills"))

    location = client.get("/api/report/skills/locations")
    assert location.status_code == 200
    assert location.get_json()["user"] == str(tmp_path / "skills")

    imported = client.post(
        "/api/report/skills/import",
        data={"file": (io.BytesIO(CUSTOM_SKILL), "concise.md")},
        content_type="multipart/form-data",
    )
    assert imported.status_code == 201
    skill = imported.get_json()
    assert skill["id"] == "concise_public"
    assert skill["source"] == "user"
    assert skill["version"] == "3"
    assert skill["deletable"] is True
    assert skill["directory"] == str((tmp_path / "skills" / "concise_public").resolve())

    duplicate = client.post(
        "/api/report/skills/import",
        data={"file": (io.BytesIO(CUSTOM_SKILL), "concise.md")},
        content_type="multipart/form-data",
    )
    assert duplicate.status_code == 409
    assert duplicate.get_json()["code"] == "REPORT_SKILL_EXISTS"

    updated = client.post(
        "/api/report/skills/import",
        data={"file": (io.BytesIO(CUSTOM_SKILL.replace(b"version: 3", b"version: 4")), "concise.md"), "replace": "true"},
        content_type="multipart/form-data",
    )
    assert updated.status_code == 201
    assert updated.get_json()["version"] == "4"

    listed = client.get("/api/report/skills").get_json()
    assert any(item["id"] == "concise_public" for item in listed)

    deleted = client.delete("/api/report/skills/concise_public")
    assert deleted.status_code == 204
    assert not (tmp_path / "skills" / "concise_public").exists()


def test_report_skill_import_rejects_non_markdown_and_builtin_override(client, tmp_path, monkeypatch):
    monkeypatch.setenv("ADARIAN_REPORT_SKILLS_DIR", str(tmp_path / "skills"))

    wrong_type = client.post(
        "/api/report/skills/import",
        data={"file": (io.BytesIO(b"not markdown"), "skill.zip")},
        content_type="multipart/form-data",
    )
    assert wrong_type.status_code == 400
    assert wrong_type.get_json()["code"] == "REPORT_SKILL_INVALID"

    override = CUSTOM_SKILL.replace(b"id: concise_public", b"id: default_government")
    response = client.post(
        "/api/report/skills/import",
        data={"file": (io.BytesIO(override), "default.md")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json()["code"] == "REPORT_SKILL_INVALID"
