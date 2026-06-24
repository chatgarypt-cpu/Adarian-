import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
_src = str(_root / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from adarian.schemas import Entity, EntityExtractionOutput, OpinionSpreader, Relation


DERIVED_FIELDS = {"C", "stance_score", "confirmation_bias_level"}


def minimal_phase1_payload():
    return {
        "event_summary": "Consumer dispute around brand response",
        "event_scale": 0.6,
        "event_controversy": 0.7,
        "event_type": "consumer dispute",
        "event_entities": [
            {
                "name": "Brand A",
                "type": "organization",
                "role": "disputed merchant",
                "can_speak": True,
                "original_statement": "We will review the issue.",
                "can_speak_reason": None,
            }
        ],
        "opinion_spreaders": [
            {
                "group_name": "Brand defenders",
                "related_event_entity": "Brand A",
                "description": "Waits for evidence and defends the brand",
                "I": 8.0,
                "P": 1,
                "susceptibility": 0.2,
                "estimated_percentage": 45,
                "communication_style": "calm but defensive",
                "persona_name": "Alex",
                "age_range": "25-34",
                "occupation": "long-term customer",
                "personality": "careful and firm",
                "motivation": "preserve trust",
                "typical_phrases": ["show evidence first", "wait for facts"],
            },
            {
                "group_name": "Rights supporters",
                "related_event_entity": "Brand A",
                "description": "Criticizes opaque handling",
                "I": 3.0,
                "P": -1,
                "susceptibility": 0.6,
                "estimated_percentage": 55,
                "communication_style": "direct and procedural",
                "persona_name": "Casey",
                "age_range": "35-45",
                "occupation": "consumer",
                "personality": "direct and persistent",
                "motivation": "push for transparency",
                "typical_phrases": ["show the process", "customers need answers"],
            },
        ],
        "relations": [
            {"source": "Brand A", "target": "Brand defenders", "type": "brand affinity"}
        ],
    }


def test_phase1_output_contract_minimal_object_fields():
    output = EntityExtractionOutput(**minimal_phase1_payload())

    assert set(EntityExtractionOutput.model_fields) == {
        "event_summary",
        "event_scale",
        "event_controversy",
        "event_type",
        "event_entities",
        "opinion_spreaders",
        "relations",
    }
    assert set(Entity.model_fields) == {
        "name",
        "type",
        "role",
        "entity_category",
        "can_speak",
        "original_statement",
        "can_speak_reason",
    }
    assert set(OpinionSpreader.model_fields) == {
        "group_name",
        "related_event_entity",
        "description",
        "I",
        "P",
        "susceptibility",
        "estimated_percentage",
        "communication_style",
        "entity_category",
        "persona_name",
        "age_range",
        "occupation",
        "personality",
        "motivation",
        "typical_phrases",
    }
    assert set(Relation.model_fields) == {"source", "target", "type"}

    assert output.event_entities[0].entity_category == "event_entity"
    assert output.opinion_spreaders[0].entity_category == "opinion_spreader"


def test_opinion_spreader_derived_properties_are_not_raw_fields():
    output = EntityExtractionOutput(**minimal_phase1_payload())
    support, oppose = output.opinion_spreaders

    assert support.C == 0.8
    assert support.stance_score == 8.0
    assert support.confirmation_bias_level == "strong"

    assert oppose.C == -0.3
    assert oppose.stance_score == 8.0
    assert oppose.confirmation_bias_level == "none"

    assert DERIVED_FIELDS.isdisjoint(OpinionSpreader.model_fields)
    assert DERIVED_FIELDS.isdisjoint(support.model_dump())
