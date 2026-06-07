"""v1.3.1: E2E — when the legacy package is shielded (imports blocked), the
clean Phase4 consumer pipeline still imports and runs end-to-end.
"""

import importlib
import sys
from unittest import mock


class _LegacyShield:
    """Import hook that blocks any import of legacy.* modules."""

    def __init__(self):
        self.blocked_attempts = []

    def find_spec(self, name, path=None, target=None):
        if name == "legacy" or name.startswith("legacy."):
            self.blocked_attempts.append(name)
            raise ImportError(f"legacy blocked: {name}")
        return None


def test_src_phase4_imports_without_legacy():
    """src.phase4 must not import legacy transitively."""
    # Force a fresh import: clear any cached legacy modules
    for mod_name in list(sys.modules):
        if mod_name == "legacy" or mod_name.startswith("legacy."):
            del sys.modules[mod_name]

    shield = _LegacyShield()
    sys.meta_path.insert(0, shield)
    try:
        # Importing the clean path should not require legacy
        from src.phase4 import (
            _build_code_owned_report_contract_block,
            _build_phase4_output_from_simulation_dataset,
            parse_llm_report_response,
            save_markdown_report,
            save_report,
        )
        assert _build_code_owned_report_contract_block is not None
        assert save_markdown_report is not None
        assert save_report is not None
    finally:
        sys.meta_path.remove(shield)

    # The shield should not have been triggered by any of the clean imports
    assert shield.blocked_attempts == [], (
        f"src.phase4 transitively touched legacy: {shield.blocked_attempts}"
    )


def _extraction():
    from src.schemas import EntityExtractionOutput, Entity, OpinionSpreader, Relation
    return EntityExtractionOutput(
        event_summary="shielded test",
        event_scale=0.5,
        event_controversy=0.5,
        event_type="public",
        event_entities=[
            Entity(
                name="某品牌",
                type="organization",
                role="涉事主体",
                can_speak=True,
                original_statement="我们会核查。",
            ),
        ],
        opinion_spreaders=[
            OpinionSpreader(
                group_name="支持方",
                related_event_entity="某品牌",
                description="等待核查",
                I=6.0,
                P=1,
                susceptibility=0.4,
                estimated_percentage=50,
                communication_style="克制",
                persona_name="路人",
                age_range="20-30",
                occupation="市民",
                personality="中性",
                motivation="关注",
                typical_phrases=["先看证据", "等待回应"],
            ),
            OpinionSpreader(
                group_name="质疑方",
                related_event_entity="某品牌",
                description="关注流程",
                I=3.0,
                P=-1,
                susceptibility=0.5,
                estimated_percentage=50,
                communication_style="直接",
                persona_name="老周",
                age_range="35-45",
                occupation="消费者",
                personality="较真",
                motivation="透明",
                typical_phrases=["流程要公开", "回应要快"],
            ),
        ],
        relations=[Relation(source="某品牌", target="支持方", type="舆论关联")],
    )


def test_clean_save_report_succeeds_when_legacy_blocked(tmp_path):
    """End-to-end: save_report with a simulation_dataset-driven Phase4Output
    works without legacy being importable.
    """
    for mod_name in list(sys.modules):
        if mod_name == "legacy" or mod_name.startswith("legacy."):
            del sys.modules[mod_name]

    shield = _LegacyShield()
    sys.meta_path.insert(0, shield)
    try:
        from src.phase4.report_agent import (
            _build_phase4_output_from_simulation_dataset,
            save_report,
        )

        extraction = _extraction()
        dataset = {
            "run_info": {"audience_mode": "generic_government"},
            "simulation_result": {
                "risk_verdict": {
                    "level": "low",
                    "label": "低风险",
                    "basis_text": "shielded basis",
                    "signals": {},
                },
                "risk_type_classification": {
                    "primary_types": ["negative_narrative_risk"],
                    "type_labels": ["负面叙事聚合风险"],
                },
                "inflection_points": [],
                "emotion_trajectory": [],
                "agent_stance_matrix": [],
            },
        }
        out = _build_phase4_output_from_simulation_dataset(
            dataset, extraction, [], [5.0, 4.8],
        )
        json_path = tmp_path / "final_report.json"
        save_report(out, output_path=json_path)
        assert json_path.exists()
        content = json_path.read_text(encoding="utf-8")
        assert "shielded basis" in content
        assert "低风险" in content
    finally:
        sys.meta_path.remove(shield)
