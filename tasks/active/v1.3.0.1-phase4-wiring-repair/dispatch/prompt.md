# v1.3.0.1 Phase 4 New Consumer Wiring Repair

Repair 3 P0 wiring blockers in the Phase 4 new consumer path.

## File Scope

### Allowed modifications:
- `src/phase4/report_agent.py` — only: add `markdown` param to `save_markdown_report`, add `simulation_dataset` param to `parse_llm_report_response` and `_build_code_owned_report_contract_block`, new/old path isolation wrappers
- `src/phase4/report_narrative.py` — only: pass `simulation_dataset` to contract block and parse response
- `main_new.py` — only: pass `markdown` to `save_markdown_report`, pass `dataset` to Phase 4 consumer
- `tools/run_pipeline_new.py` — same as main_new.py
- `tests/test_phase4_new_consumer_wiring.py` — new file for targeted tests

### Forbidden:
- src/phase1/, src/phase2/, src/phase3/ (all files), src/schemas/, src/whitebox/, src/llm_client.py, config.py
- Do NOT modify prompt semantics, risk algorithm semantics, Phase4Output schema, or five-chapter report structure
- Do NOT delete old path functions
- Do NOT let old Phase 4 consume new interface

## Three Fixes (sequential)

### B1: save_markdown_report accepts explicit markdown param
- Add `markdown: str | None = None` keyword parameter to `save_markdown_report()`
- Priority: explicit markdown > `_llm_generated_markdown` global > `generate_markdown_report()` fallback
- In `main_new.py:run_phase4` and `tools/run_pipeline_new.py:run_phase4_new`, pass the returned markdown explicitly

### B2: parse_llm_report_response accepts simulation_dataset
- Add `simulation_dataset: dict | None = None` parameter
- When dataset is provided: use dataset's `risk_verdict`, `inflection_points`, `emotion_trajectory`, `risk_type_classification` directly — do NOT call `assess_risk()` or `identify_inflection_points()` for these fields
- When dataset is None: keep old path behavior unchanged

### B3: _build_code_owned_report_contract_block accepts simulation_dataset
- Add `simulation_dataset: dict | None = None` parameter
- When dataset is provided: read `risk_level/audience_mode/primary_types/risk_type_labels` from dataset instead of calling old inline functions
- When dataset is None: keep old path behavior unchanged

### B4 (integration): Wire everything together
- `generate_report_with_llm_narrative()` must pass dataset to both contract block builder and parse response
- `main_new.py` and `tools/run_pipeline_new.py` must pass dataset + markdown properly

## Verification

### 0. Static Check
```bash
.venv/bin/python -m py_compile src/phase4/report_agent.py src/phase4/report_narrative.py main_new.py tools/run_pipeline_new.py
.venv/bin/python -m compileall src
```

### 1. Targeted Tests (new file: tests/test_phase4_new_consumer_wiring.py)
Create tests that verify:
1. Explicit markdown param takes priority over global variable
2. Old path without dataset keeps legacy behavior
3. `parse_llm_report_response` uses dataset risk_verdict when dataset is provided
4. `_build_code_owned_report_contract_block` uses dataset values when dataset is provided

### 2. Bypass Verification
```bash
.venv/bin/python tools/bypass_compare_phase3.py seeds/test8.txt
```
Save output to `tasks/active/v1.3.0.1-phase4-wiring-repair/outputs/bypass_comparison.json`

### 3. New Path Smoke
```bash
.venv/bin/python main_new.py seeds/test8.txt
```

## Reporting
After all steps, write execution evidence to `tasks/active/v1.3.0.1-phase4-wiring-repair/outputs/repair_evidence.md`:
- Files modified with diff summary
- Test results (pass/fail counts)
- Bypass comparison pass/fail
- Any forbidden files touched
