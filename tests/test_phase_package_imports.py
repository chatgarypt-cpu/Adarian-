"""Import checks for v1.3.1 phase packages.

v1.3.1 changes:
  - src.phase4 is a pure consumer: only 5 symbols are exposed (see src.phase4.__all__).
  - legacy.phase4 hosts the archived old compute/generation/markdown helpers.
  - This test asserts the new boundary: src.phase4 is shallow & minimal,
    and the legacy.phase4 package is importable for diagnostic / bypass use.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.phase1 import ANALYZER_SYSTEM_PROMPT, extract_entities_from_file, save_entities_output
from src.phase2 import build_topology_from_extraction
from src.phase3 import SimulationEngine
import src.phase4
from legacy import phase4 as legacy_phase4


EXPECTED_PHASE4_EXPORTS = {
    "_build_code_owned_report_contract_block",
    "_build_phase4_output_from_simulation_dataset",
    "parse_llm_report_response",
    "save_markdown_report",
    "save_report",
}


def main() -> None:
    assert callable(extract_entities_from_file)
    assert isinstance(ANALYZER_SYSTEM_PROMPT, str)
    assert ANALYZER_SYSTEM_PROMPT.strip()
    assert callable(save_entities_output)
    assert callable(build_topology_from_extraction)
    assert SimulationEngine is not None
    # v1.3.1: src.phase4 exposes only 5 consumer symbols — no old compute functions.
    assert set(src.phase4.__all__) == EXPECTED_PHASE4_EXPORTS
    # legacy.phase4 package is importable (for diagnostic / bypass tools only).
    assert legacy_phase4 is not None


def test_phase1_analyzer_prompt_export():
    assert isinstance(ANALYZER_SYSTEM_PROMPT, str)
    assert ANALYZER_SYSTEM_PROMPT.strip()


def test_src_phase4_all_is_exactly_five_consumer_symbols():
    assert set(src.phase4.__all__) == EXPECTED_PHASE4_EXPORTS
    assert len(src.phase4.__all__) == 5


def test_legacy_phase4_package_is_importable():
    # The legacy package exists; its submodules host archived compute helpers.
    assert hasattr(legacy_phase4, "legacy_analytics")
    assert hasattr(legacy_phase4, "legacy_generation")
    assert hasattr(legacy_phase4, "legacy_markdown")


if __name__ == "__main__":
    main()
