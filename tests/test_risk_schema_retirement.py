#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ensure schemas.phase4 is fully retired — no active imports remain."""

from __future__ import annotations

import importlib.util


def test_schemas_phase4_no_longer_importable():
    """phase4.py was archived; its active schemas moved to schemas.risk."""
    assert importlib.util.find_spec("adarian.schemas.phase4") is None


def test_schemas_risk_importable():
    """New risk schema module replaces phase4.py for active schemas."""
    import adarian.schemas.risk  # noqa: F401


def test_risk_schema_exports():
    """Verify all expected symbols are available from schemas.risk."""
    from adarian.schemas.risk import (
        AudienceMode,
        DOMAIN_LABELS,
        RiskDomain,
        RiskLevel,
        RISK_LEVEL_LABELS,
        RISK_TYPE_LABELS,
        TYPE_TO_DOMAIN_MAP,
    )
    assert RiskLevel.LOW.value == "low"
    assert RiskLevel.CRITICAL.value == "critical"
    assert AudienceMode.GENERIC_GOVERNMENT.value == "generic_government"
    assert DOMAIN_LABELS["governance_trust"] == "治理信任类"
    assert TYPE_TO_DOMAIN_MAP["transparency_risk"] == "governance_trust"
    assert RISK_TYPE_LABELS["transparency_risk"] == "处置透明度风险"
    assert RISK_LEVEL_LABELS["high"] == "高风险"


def test_schemas_init_re_exports_risk():
    """schemas/__init__.py still re-exports RiskLevel and labels."""
    from adarian.schemas import (
        AudienceMode,
        RiskLevel,
        RISK_LEVEL_LABELS,
        RISK_TYPE_LABELS,
    )
    assert RiskLevel is not None
    assert AudienceMode is not None


def test_adarian_init_no_phase4_dead_types():
    """adarian/__init__.py no longer exports Phase4Output etc."""
    import adarian
    assert not hasattr(adarian, "Phase4Output")
    assert not hasattr(adarian, "EmotionTrajectory")
    assert not hasattr(adarian, "InflectionPoint")


def test_risk_imports_from_new_location():
    """Verify all consumers import from schemas.risk, not schemas.phase4."""
    import adarian.analysis.risk_analyzer
    import adarian.analysis.classifier
    import adarian.parser
    assert adarian.analysis.risk_analyzer.RiskAnalyzer is not None
