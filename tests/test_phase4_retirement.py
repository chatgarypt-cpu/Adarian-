#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path


def test_main_pipeline_does_not_run_legacy_phase4_report_agent():
    source = Path("main.py").read_text(encoding="utf-8")
    assert "generate_report_with_llm_narrative" not in source
    assert "phase4_report_agent" not in source
    assert "run_phase4" not in source
