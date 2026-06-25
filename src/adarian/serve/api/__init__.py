#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API route registration for the Adarian web console."""

from __future__ import annotations

from flask import Flask

from adarian.serve.api.ping import ping_bp


def register_api(app: Flask) -> None:
    app.register_blueprint(ping_bp, url_prefix="/api")
