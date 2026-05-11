"""Schema import compatibility checks for v1.2.6."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_schema_import_compatibility():
    from src import EntityExtractionOutput as SrcEntityExtractionOutput
    from src import Phase2Output as SrcPhase2Output
    from src import Phase4Output as SrcPhase4Output
    from src import TickLog as SrcTickLog
    from src.schemas import ConfirmationBiasLevel
    from src.schemas import EntityExtractionOutput, OpinionSpreader
    from src.schemas import Phase2Output, Phase4Output, TickLog
    from src.schemas._legacy import Phase1Output, SimulationCard
    from src.schemas.phase1 import EntityExtractionOutput as Phase1EntityExtractionOutput
    from src.schemas.phase1 import OpinionSpreader as Phase1OpinionSpreader
    from src.schemas.phase2 import EdgeType, NodeRole, Phase2Output as Phase2ModuleOutput
    from src.schemas.phase3 import AgentEntry, TickLog as Phase3TickLog
    from src.schemas.phase4 import Phase4Output as Phase4ModuleOutput
    from src.schemas.phase4 import RiskLevel

    assert SrcEntityExtractionOutput is EntityExtractionOutput
    assert SrcPhase2Output is Phase2Output
    assert SrcTickLog is TickLog
    assert SrcPhase4Output is Phase4Output
    assert Phase1EntityExtractionOutput is EntityExtractionOutput
    assert Phase1OpinionSpreader is OpinionSpreader
    assert Phase2ModuleOutput is Phase2Output
    assert Phase3TickLog is TickLog
    assert Phase4ModuleOutput is Phase4Output
    assert ConfirmationBiasLevel.STRONG.value == "strong"
    assert NodeRole.CORE.value == "core"
    assert EdgeType.FOLLOWS.value == "follows"
    assert AgentEntry.__name__ == "AgentEntry"
    assert RiskLevel.MEDIUM.value == "medium"
    assert Phase1Output.__name__ == "Phase1Output"
    assert SimulationCard.__name__ == "SimulationCard"

    assert not hasattr(__import__("src.schemas", fromlist=["Phase1Output"]), "Phase1Output")
    assert not hasattr(__import__("src.schemas", fromlist=["SimulationCard"]), "SimulationCard")


def test_opinion_spreader_compatibility_properties():
    from src.schemas import OpinionSpreader

    support = OpinionSpreader(
        group_name="Brand defenders",
        related_event_entity="Brand A",
        description="Waits for evidence and defends the brand",
        I=8.0,
        P=1,
        susceptibility=0.2,
        estimated_percentage=45,
        communication_style="calm but defensive",
        persona_name="Alex",
        age_range="25-34",
        occupation="long-term customer",
        personality="careful and firm",
        motivation="preserve trust",
        typical_phrases=["show evidence first", "wait for facts"],
    )
    oppose = support.model_copy(update={"I": 3.0, "P": -1})

    assert support.C == 0.8
    assert support.stance_score == 8.0
    assert support.confirmation_bias_level == "strong"
    assert oppose.C == -0.3
    assert oppose.stance_score == 8.0
    assert oppose.confirmation_bias_level == "none"


if __name__ == "__main__":
    test_schema_import_compatibility()
    test_opinion_spreader_compatibility_properties()
    print("schema import compatibility ok")
