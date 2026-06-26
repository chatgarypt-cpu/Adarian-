# Appendix B Schema

Appendix B is the structured data report. It is written as JSON and later rendered in the final report.

`appendix_b_schema.yaml` is the machine-auditable contract. This Markdown file is the human-readable summary.

## Top-Level Keys

Exactly five top-level keys are allowed in final appendix B:

```json
{
  "meta": {},
  "evolution_analysis": {},
  "source_evidence": {},
  "risk_assessment": {},
  "countermeasures": {}
}
```

T1 writes `meta`, `evolution_analysis`, and `source_evidence`. T2 appends `risk_assessment` and `countermeasures`.

## T1 Branches

| Path | Kind | Source |
|---|---|---|
| `meta.event_name` | source | input JSON `event_name` |
| `meta.generated_at` | derived | current run timestamp |
| `meta.worlds_count` | derived | count of loaded worlds |
| `evolution_analysis.worlds_count` | derived | count of loaded worlds |
| `evolution_analysis.event_scale_avg` | derived | mean of `run_info.event_scale` |
| `evolution_analysis.event_scale_distribution` | source list | per-world `run_info.event_scale` |
| `evolution_analysis.event_controversy_avg` | derived | mean of `run_info.event_controversy` |
| `evolution_analysis.event_controversy_distribution` | source list | per-world `run_info.event_controversy` |
| `evolution_analysis.risk_level_distribution` | derived | counts of `simulation_result.risk_verdict.level` |
| `evolution_analysis.risk_type_frequency` | derived | counts of `risk_type_classification.primary_types` |
| `evolution_analysis.worst_reasonable_level` | derived | highest level by `aggregation_config.risk_level_order` |
| `evolution_analysis.worst_reasonable_level_label` | derived | label paired with `worst_reasonable_level` |
| `evolution_analysis.outlier_worlds` | derived | worlds where the highest level is not a majority scenario |
| `evolution_analysis.entities` | source | `source_context.event_entities` |
| `evolution_analysis.opinion_spreaders` | source | `source_context.opinion_spreaders`; appendix-only raw internal metrics |
| `evolution_analysis.emotion_trajectory` | source | bounded per-world trajectory; appendix-only raw internal metrics |
| `evolution_analysis.agent_stance_matrix` | source | bounded per-world stance matrix; appendix-only, 不入正文 |
| `evolution_analysis.inflection_points` | source | placeholder field, reference-only; appendix-only, 不入正文 |
| `source_evidence.worlds` | source | bounded risk verdict and type classification per world |

## T2 Branches

`risk_assessment.risks[]` must use risk IDs and labels from `risk_mapping.yaml`.

`risk_assessment.no_confirmed_risks_reason` is allowed only when no candidate has enough evidence to become a confirmed risk. In that branch, `risk_assessment.risks` and `countermeasures.measures` must both be empty.

`countermeasures.measures[]` must reference a `risk_type_id` that exists in `risk_assessment.risks[]` or is explicitly marked as a supporting measure. Each non-supporting measure must reuse the paired `risk_label` and include `trigger_reason_ref` and `level_id_ref`, equal to the paired risk's `trigger_reason` and `level_id`.
