#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from adarian.serve.schemas import normalize_status


def test_status_mapping_success_to_completed():
    assert normalize_status("success") == "completed"
    assert normalize_status("weird") == "pending"
