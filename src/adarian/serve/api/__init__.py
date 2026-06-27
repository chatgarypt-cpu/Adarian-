#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API route registration for the Adarian web console."""

from __future__ import annotations

from flask import Flask

from adarian.serve.api.config import config_bp
from adarian.serve.api.history import history_bp
from adarian.serve.api.model_gateways import model_gateways_bp
from adarian.serve.api.models import models_bp
from adarian.serve.api.ping import ping_bp
from adarian.serve.api.report import report_bp
from adarian.serve.api.review import review_bp
from adarian.serve.api.run import run_bp
from adarian.serve.api.seed import seed_bp
from adarian.serve.api.settings import settings_bp
from adarian.serve.api.stats import stats_bp
from adarian.serve.api.world import world_bp


def register_api(app: Flask) -> None:
    app.register_blueprint(ping_bp, url_prefix="/api")
    app.register_blueprint(seed_bp, url_prefix="/api")
    app.register_blueprint(config_bp, url_prefix="/api")
    app.register_blueprint(models_bp, url_prefix="/api")
    app.register_blueprint(model_gateways_bp, url_prefix="/api")
    app.register_blueprint(run_bp, url_prefix="/api")
    app.register_blueprint(world_bp, url_prefix="/api")
    app.register_blueprint(history_bp, url_prefix="/api")
    app.register_blueprint(review_bp, url_prefix="/api")
    app.register_blueprint(report_bp, url_prefix="/api")
    app.register_blueprint(settings_bp, url_prefix="/api")
    app.register_blueprint(stats_bp, url_prefix="/api")
