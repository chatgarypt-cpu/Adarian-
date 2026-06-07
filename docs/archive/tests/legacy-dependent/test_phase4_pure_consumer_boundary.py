"""v1.3.1: Pure consumer boundary — src.phase4 must not expose old compute functions."""

import pytest


def test_src_phase4_all_is_exactly_five_consumer_symbols():
    import src.phase4
    expected = {
        "_build_code_owned_report_contract_block",
        "_build_phase4_output_from_simulation_dataset",
        "parse_llm_report_response",
        "save_markdown_report",
        "save_report",
    }
    assert set(src.phase4.__all__) == expected, f"got {set(src.phase4.__all__)}"
    assert len(src.phase4.__all__) == 5


def test_src_phase4_does_not_expose_old_compute_functions():
    import src.phase4
    forbidden = {
        "assess_risk",
        "identify_inflection_points",
        "determine_audience_mode",
        "select_primary_risk_types",
        "generate_report_with_llm",
        "generate_fallback_report",
        "generate_markdown_report",
        "run_old_path",
        "run_new_path",
        "load_tick_logs",
        "_llm_generated_markdown",
    }
    for name in forbidden:
        assert name not in src.phase4.__all__, f"{name} leaked into src.phase4.__all__"


def test_src_phase4_report_agent_does_not_define_old_functions():
    from src.phase4 import report_agent
    forbidden = [
        "assess_risk",
        "identify_inflection_points",
        "generate_report_with_llm",
        "generate_fallback_report",
        "generate_markdown_report",
        "run_old_path",
        "run_new_path",
        "load_tick_logs",
        "_llm_generated_markdown",
        "determine_audience_mode",
        "select_primary_risk_types",
    ]
    for name in forbidden:
        assert not hasattr(report_agent, name), f"report_agent still defines {name}"


def test_save_markdown_report_requires_explicit_markdown():
    """Goal B: save_markdown_report must not silently fall back to legacy markdown."""
    from src.phase4.report_agent import save_markdown_report
    import inspect
    sig = inspect.signature(save_markdown_report)
    markdown_param = sig.parameters.get("markdown")
    assert markdown_param is not None, "save_markdown_report must accept a markdown parameter"
    # markdown must be keyword-only and have no default that would let it be optional
    assert markdown_param.kind == inspect.Parameter.KEYWORD_ONLY, (
        "save_markdown_report.markdown must be keyword-only"
    )


def test_parse_llm_report_response_requires_simulation_dataset():
    """Goal B: parse_llm_report_response must not allow dataset=None fallback."""
    from src.phase4.report_agent import parse_llm_report_response
    import inspect
    sig = inspect.signature(parse_llm_report_response)
    ds = sig.parameters.get("simulation_dataset")
    assert ds is not None, "parse_llm_report_response must require simulation_dataset"
    assert ds.default is inspect.Parameter.empty, (
        "parse_llm_report_response.simulation_dataset must have no default"
    )


def test_build_code_owned_report_contract_block_requires_simulation_dataset():
    """Goal B: contract block builder must not allow non-dataset path."""
    from src.phase4.report_agent import _build_code_owned_report_contract_block
    import inspect
    sig = inspect.signature(_build_code_owned_report_contract_block)
    ds = sig.parameters.get("simulation_dataset")
    assert ds is not None, "contract block must require simulation_dataset"
    assert ds.default is inspect.Parameter.empty, (
        "contract block.simulation_dataset must have no default"
    )
