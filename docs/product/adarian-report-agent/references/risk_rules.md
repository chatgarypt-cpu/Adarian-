# Risk Rules

`risk_rules.yaml` is the single truth source. Use this file only as reading guidance.

## Two-Layer Method

1. Candidate layer: collect candidate `type_id` values from `source_evidence.worlds[].risk_type_classification.primary_types`.
2. Evidence layer: confirm candidates using `risk_verdict.signals`, `risk_level_distribution`, and evolution summaries.

Do not invent labels outside `risk_mapping.yaml`. Normally confirm 1 to 3 risks. If evidence is weak, downgrade or output fewer risks instead of forcing three.

If no candidate has enough evidence to become a confirmed risk, output:

- `risk_assessment.risks: []`
- `risk_assessment.no_confirmed_risks_reason`: a non-empty explanation of why the evidence does not support a confirmed risk
- `countermeasures.measures: []`

This is a strict evidence-insufficient exception, not the normal path.

## Risk Object Shape

Each confirmed risk should contain:

- `type_id`
- `type_label`
- `domain`
- `domain_label`
- `level_id`
- `level_label`
- `trigger_signals`
- `trigger_reason`
- `reality_translation`

`level_id` and `level_label` should follow upstream `risk_verdict.level` and `risk_verdict.label` where possible. When upstream evidence is insufficient to determine a level, the LLM may fall back to the `level_selection.fallback_level_id` and `fallback_level_label` values declared in `risk_rules.yaml` (these are LLM guidance only — the validation script does not enforce them).

`trigger_signals` must be a non-empty list or object. `reality_translation` must be a non-empty string that explains the real-world public-opinion risk implied by the evidence.

## Countermeasure Closure

Each countermeasure must point back to one confirmed risk. Match by `risk_type_id`, reuse the paired risk label, and set `trigger_reason_ref` / `level_id_ref` to the paired risk's `trigger_reason` / `level_id`. Do not choose a template only because the wording sounds plausible.

## Writing Boundary

Risk研判 should translate simulation evidence into realistic public-opinion risk. It must not describe the simulation process as if it were a real-world fact.
