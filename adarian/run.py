#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single pipeline runner — wraps main.main() for library call."""

from __future__ import annotations

import sys
from pathlib import Path


def run_pipeline(seed_path: str = "seeds/test8.txt") -> None:
    """Run a full Adarian pipeline from seed file."""
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from main import main as pipeline_main
    pipeline_main(seed_path=seed_path)
