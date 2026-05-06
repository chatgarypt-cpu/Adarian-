"""Import checks for v1.2.5 phase packages."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.phase1 import extract_entities_from_file, save_entities_output
from src.phase2 import build_topology_from_extraction
from src.phase3 import SimulationEngine
from src.phase4 import generate_report_with_llm


def main() -> None:
    assert callable(extract_entities_from_file)
    assert callable(save_entities_output)
    assert callable(build_topology_from_extraction)
    assert SimulationEngine is not None
    assert callable(generate_report_with_llm)


if __name__ == "__main__":
    main()
