"""v1.3.1 Phase 4 pure-consumer boundary checks.

This test verifies that ``src.phase4`` is a thin pure-consumer facade
exposing only the 5 expected symbols, and that the legacy compute
helpers are NOT importable from ``src.phase4`` at all.
"""

import importlib

import src.phase4


EXPECTED_EXPORTS = {
    "_build_code_owned_report_contract_block",
    "_build_phase4_output_from_simulation_dataset",
    "parse_llm_report_response",
    "save_markdown_report",
    "save_report",
}

# These names used to be importable from src.phase4.report_agent in
# pre-v1.3.1 versions. They are now archived under legacy.phase4 and
# must NOT be exposed by src.phase4 in any form.
FORBIDDEN_FROM_SRC_PHASE4 = {
    "assess_risk",
    "determine_audience_mode",
    "select_primary_risk_types",
    "identify_inflection_points",
    "generate_fallback_report",
    "generate_report_with_llm",
    "run_old_path",
    "run_new_path",
    "_llm_generated_markdown",
}


def test_src_phase4_exposes_exactly_five_consumer_symbols():
    assert set(src.phase4.__all__) == EXPECTED_EXPORTS
    assert len(src.phase4.__all__) == 5


def test_src_phase4_submodules_do_not_export_old_compute_names():
    submodules = [
        "src.phase4",
        "src.phase4.report_agent",
        "src.phase4.report_narrative",
        "src.phase4.report_normalizer",
        "src.phase4.report_title",
        "src.phase4.report_prompts",
        "src.phase4.paths",
    ]
    for name in submodules:
        mod = importlib.import_module(name)
        attrs = {a for a in dir(mod) if not a.startswith("__")}
        leaked = FORBIDDEN_FROM_SRC_PHASE4 & attrs
        assert not leaked, (
            f"src.phase4 leaked old compute names via {name}: {sorted(leaked)}"
        )


def test_src_phase4_does_not_carry_assess_risk_under_any_name():
    """The name ``assess_risk`` is forbidden everywhere under src.phase4."""
    import src.phase4.report_agent as report_agent

    assert not hasattr(report_agent, "assess_risk")
    assert "assess_risk" not in dir(report_agent)


def test_src_phase4_save_markdown_requires_explicit_markdown_argument():
    """v1.3.1 contract: save_markdown_report must reject missing markdown."""
    import inspect

    from src.phase4.report_agent import save_markdown_report

    sig = inspect.signature(save_markdown_report)
    assert "markdown" in sig.parameters
    # The new contract makes ``markdown`` keyword-only and required.
    assert sig.parameters["markdown"].kind == inspect.Parameter.KEYWORD_ONLY


def test_src_phase4_parse_llm_report_response_consumes_dataset_only():
    """parse_llm_report_response must require a simulation_dataset."""
    import inspect

    from src.phase4.report_agent import parse_llm_report_response

    sig = inspect.signature(parse_llm_report_response)
    assert "simulation_dataset" in sig.parameters
    assert sig.parameters["simulation_dataset"].default is inspect.Parameter.empty
