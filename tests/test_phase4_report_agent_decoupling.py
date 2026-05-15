"""Integrity checks for v1.2.9 Phase 4 report-agent decoupling."""

import inspect

from src.phase4 import report_agent
from src.phase4 import report_narrative, report_normalizer, report_title


def test_report_agent_uses_extracted_modules_as_facade():
    assert report_agent._normalize_saved_markdown is report_normalizer._normalize_saved_markdown
    assert report_agent._code_owned_risk_section is report_normalizer._code_owned_risk_section
    assert report_agent._normalized_report_title is report_title._normalized_report_title
    assert report_agent._ensure_metadata_header is report_title._ensure_metadata_header


def test_required_functions_remain_in_report_agent():
    for name in (
        "assess_risk",
        "select_primary_risk_types",
        "identify_inflection_points",
        "parse_llm_report_response",
        "generate_fallback_report",
        "generate_report_with_llm",
    ):
        assert callable(getattr(report_agent, name))
    assert hasattr(report_agent, "_llm_generated_markdown")


def test_narrative_module_owns_llm_prompt_assembly():
    narrative_source = inspect.getsource(report_narrative)
    agent_source = inspect.getsource(report_agent.generate_report_with_llm)

    assert "REPORT_SYSTEM_PROMPT" in narrative_source
    assert "REPORT_USER_PROMPT_SUFFIX" in narrative_source
    assert "generate_report_with_llm_narrative" in agent_source
    assert "REPORT_USER_PROMPT_SUFFIX" not in agent_source


def test_no_forbidden_phase4_modules_import_new_decoupled_modules_backwards():
    agent_source = inspect.getsource(report_agent)

    assert "from .report_normalizer import" in agent_source
    assert "from .report_narrative import" in agent_source
    assert "from .report_title import" in agent_source
