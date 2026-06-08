"""v1.3.1: src.phase4 public API export shape — exactly the 5 consumer symbols."""

import importlib


def test_exports_contain_exactly_five_symbols():
    import src.phase4
    assert isinstance(src.phase4.__all__, list)
    assert len(src.phase4.__all__) == 5


def test_exports_match_expected_set():
    import src.phase4
    expected = {
        "_build_report_contract_block",
        "_build_phase4_output_from_simulation_dataset",
        "parse_llm_report_response",
        "save_markdown_report",
        "save_report",
    }
    assert set(src.phase4.__all__) == expected


def test_each_exported_symbol_is_importable():
    import src.phase4
    for name in src.phase4.__all__:
        obj = getattr(src.phase4, name, None)
        assert obj is not None, f"src.phase4.{name} is None or missing"
        assert callable(obj) or hasattr(obj, "__class__"), (
            f"src.phase4.{name} is not a function/class"
        )


def test_old_compute_symbols_not_accessible_via_src_phase4():
    """Even via attribute access, src.phase4 should not expose compute symbols."""
    import src.phase4
    forbidden = [
        "assess_risk",
        "generate_report_with_llm",
        "generate_fallback_report",
        "generate_markdown_report",
        "identify_inflection_points",
        "run_old_path",
        "run_new_path",
        "load_tick_logs",
    ]
    for name in forbidden:
        assert not hasattr(src.phase4, name), (
            f"src.phase4 still leaks {name} via attribute access"
        )


def test_no_double_underscore_dunders_exported():
    """Public API must not contain Python dunders except __all__ itself."""
    import src.phase4
    leaks = [name for name in src.phase4.__all__ if name.startswith("__") and name != "__all__"]
    assert leaks == [], f"Dunder leaks: {leaks}"
