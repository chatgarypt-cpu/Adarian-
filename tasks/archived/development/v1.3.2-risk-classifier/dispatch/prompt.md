@skill karpathy-coding

use a workflow to: Implement RiskClassifier and integrate into parser

## Context

You are in the Adarian MVP project. The v1.3.2 iteration expands risk classification from 13 keyword-matched types to 26 LLM-classified types with 6 first-level risk domains.

The schema layer is already done:
- `src/schemas/phase4.py`: Has `RiskDomain` enum (6 domains), `DOMAIN_LABELS`, `TYPE_TO_DOMAIN_MAP` (26 types → domains), `RISK_TYPE_LABELS` (13 old + 26 new = 39 entries), `Phase4Output.primary_domain` + `primary_domain_label`
- `spec/risk_mapping.yaml`: Complete 6-domain, 26-type taxonomy registry
- `src/whitebox/token_tracker.py`: `_PHASE_MAP` has `"classify": "Phase 3 Parser"` registered

Your task: implement the RiskClassifier and wire it into the parse pipeline.

## Files to create

### 1. `src/analysis/classifier.py` — RiskClassifier

Single file, three methods:

```python
class RiskClassifier:
    def _build_query_text(
        self,
        extraction_output: EntityExtractionOutput,
        tick_logs: List[TickLog],
        x_t_sequence: List[float],
        simulation_result: Dict[str, Any],
    ) -> str:
        """
        Compress simulation data into a stable query text for LLM classification.

        Include:
        - event_name, event_type, event_scale, event_controversy
        - risk_level
        - key entities (name + type + role)
        - key groups with final stance and max delta
        - representative comments: pick 3-5 from active speakers in final ticks
          - comment text (truncate to 80 chars), group_name, stance_score
        - final polarization_index
        - final_x (mean stance)
        - negative_trend
        - max_negative_shift

        Output format: plain text with labeled sections, 400-500 tokens max.
        """
        pass

    def _build_type_catalog(self) -> str:
        """
        Build the compressed 26-type catalog for LLM prompt.

        Each type gets exactly 1 line:
          <type_id>: <label> | <domain_label> | <typical_scenario>

        Read from src.schemas.phase4:
          - RISK_TYPE_LABELS (for label)
          - TYPE_TO_DOMAIN_MAP (for domain mapping)
          - DOMAIN_LABELS (for domain label)
        """
        pass

    def classify(
        self,
        extraction_output: EntityExtractionOutput,
        tick_logs: List[TickLog],
        x_t_sequence: List[float],
        simulation_result: Dict[str, Any],
    ) -> ClassificationOutput:
        """
        Orchestrate: _build_query_text → LLM → parse response.

        1. Build query_text from simulation data
        2. Build type catalog from RISK_TYPE_LABELS + TYPE_TO_DOMAIN_MAP
        3. Call LLM once with system prompt + user prompt
        4. Parse LLM response into ClassificationOutput
        5. Validate: all primary_types must be valid keys in RISK_TYPE_LABELS
        6. Validate: exactly 3 primary_types (no duplicates)
        7. Return ClassificationOutput

        LLM system prompt:
        - You are a risk classification expert for a government governance simulation system.
        - You will receive a compressed summary of a simulated public opinion event.
        - You will also receive a catalog of 26 risk types with brief descriptions.
        - Your task: select the top 3 most applicable risk types for this event.
        - Output ONLY valid type IDs from the catalog. Do not invent new types.
        - Output exactly 3 types, ordered by relevance (most relevant first).
        - Return a JSON object with a "primary_types" array.

        LLM user prompt:
        - The query_text
        - The type catalog
        - Strict instruction: "Select exactly 3 risk types from the catalog above.
          Output as JSON: {\"primary_types\": [\"type_id_1\", \"type_id_2\", \"type_id_3\"]}"
        """
        pass
```

### 2. Create ClassificationOutput schema

In `src/schemas/phase3.py` or as a new schema file:

```python
class ClassificationOutput(BaseModel):
    primary_types: List[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Top 3 risk types from the 26-type taxonomy, ordered by relevance",
    )
```

Or use a separate `src/schemas/classification.py` file. Your choice.

### 3. Create `src/analysis/__init__.py` if it doesn't exist

Export RiskClassifier.

### 4. Update `src/parser.py`

In `SimulationDatasetParser.parse()`, after the existing analysis steps (after `StanceAnalyzer.build_agent_stance_matrix()`), add:

```python
# RiskClassifier — LLM-based risk type classification
from src.analysis.classifier import RiskClassifier
classifier = RiskClassifier()
classification_output = classifier.classify(
    extraction_output,
    tick_logs,
    x_t_sequence,
    dataset["simulation_result"],
)
```

Then in the `risk_type_classification` dict build, write:

```python
"risk_type_classification": {
    "primary_types": classification_output.primary_types,
    "type_labels": [RISK_TYPE_LABELS[t] for t in classification_output.primary_types],
    "primary_domain": TYPE_TO_DOMAIN_MAP.get(classification_output.primary_types[0], ""),
    "primary_domain_label": DOMAIN_LABELS.get(
        TYPE_TO_DOMAIN_MAP.get(classification_output.primary_types[0], ""), ""
    ),
},
```

Import `RISK_TYPE_LABELS`, `TYPE_TO_DOMAIN_MAP`, `DOMAIN_LABELS` from `src.schemas.phase4`.

## Verification

1. `python -m py_compile src/analysis/classifier.py src/parser.py` — no syntax errors
2. `python -c "from src.analysis.classifier import RiskClassifier; print('OK')"` — import works
3. `python -c "from src.parser import SimulationDatasetParser; print('OK')"` — import chain works

## Done condition

Write completion summary to `outputs/receipt.md` listing:
- Files created/modified
- Key design decisions
- Verification results
- Any risks or open issues
