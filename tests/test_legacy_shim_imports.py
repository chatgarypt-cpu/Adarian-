"""Import checks for v1.2.5 legacy phase shims."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.phase1_entity_extraction import ANALYZER_SYSTEM_PROMPT
from src.phase1_entity_extraction import extract_entities_from_file
from src.phase2_topology_builder import build_topology_from_extraction
from src.phase3_tick_simulation import SimulationEngine
from src.phase4_report_agent import generate_report_with_llm


def main() -> None:
    assert callable(extract_entities_from_file)
    assert isinstance(ANALYZER_SYSTEM_PROMPT, str)
    assert ANALYZER_SYSTEM_PROMPT
    assert callable(build_topology_from_extraction)
    assert SimulationEngine is not None
    assert callable(generate_report_with_llm)


if __name__ == "__main__":
    main()
