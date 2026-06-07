"""Phase 4 package — pure consumer of simulation_dataset."""

from .report_agent import (
    _build_code_owned_report_contract_block,
    _build_phase4_output_from_simulation_dataset,
    parse_llm_report_response,
    save_markdown_report,
    save_report,
)

__all__ = [
    "_build_code_owned_report_contract_block",
    "_build_phase4_output_from_simulation_dataset",
    "parse_llm_report_response",
    "save_markdown_report",
    "save_report",
]
