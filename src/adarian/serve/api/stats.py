#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight stats endpoint — today's batch count from server local time.

Also serves /api/events SSE stream for frontend heartbeat detection.
"""

from __future__ import annotations

import time
from datetime import datetime

from flask import Blueprint, Response, jsonify, stream_with_context

from adarian.serve import db

stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/stats")
def stats():
    today_prefix = datetime.now().strftime("%Y-%m-%d")
    count = 0
    for batch in db.list_batches():
        created = (batch.get("created_at") or "").strip()
        if created.startswith(today_prefix):
            count += 1
    return jsonify({"todayBatches": count})


@stats_bp.get("/events")
def events():
    """SSE endpoint — sends a heartbeat every 5s so the frontend EventSource
    can detect backend death instantly via the TCP connection drop."""

    def generate():
        try:
            while True:
                yield "data: alive\n\n"
                time.sleep(5)
        except GeneratorExit:
            pass  # client disconnected, clean exit

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-store", "Connection": "keep-alive"},
    )
