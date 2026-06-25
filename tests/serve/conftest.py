#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import pytest


@pytest.fixture()
def app(tmp_path, monkeypatch):
    from adarian.serve import db
    from adarian.serve import paths

    monkeypatch.setattr(paths, "SERVE_DB_PATH", tmp_path / "serve.sqlite3")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "serve.sqlite3")
    db.init_db()

    from adarian.serve import create_app

    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()
