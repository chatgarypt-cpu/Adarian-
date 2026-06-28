#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib.util
from pathlib import Path


def test_legacy_phase4_package_is_not_importable_from_runtime_src():
    assert importlib.util.find_spec("adarian.phase4") is None
    assert not Path("src/adarian/phase4").exists()
    assert Path("docs/archive/legacy/phase4_runtime_package").is_dir()
