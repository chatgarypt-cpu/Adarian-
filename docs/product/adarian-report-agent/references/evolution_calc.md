# Evolution Calculation

`aggregation_config.yaml` is the single truth source for deterministic calculations. This file explains how the Agent should read the script output.

## T1 Script Output

The script reads all `simulation_dataset.json` files and writes:

- `meta`
- `evolution_analysis`
- `source_evidence`

The Agent should not recompute raw metrics from full datasets after T1. Use `appendix_b.json` as the data anchor.

## Multi-World Aggregation

| Output | Meaning |
|---|---|
| `worlds_count` | Number of loaded simulation worlds. |
| `event_scale_avg` | Mean of all valid `run_info.event_scale` values. |
| `event_scale_distribution` | Per-world scale values in input order. |
| `event_controversy_avg` | Mean of all valid `run_info.event_controversy` values. |
| `event_controversy_distribution` | Per-world controversy values in input order. |
| `risk_level_distribution` | Count of upstream `risk_verdict.level` values. |
| `risk_type_frequency` | Count of all upstream primary risk type candidates. |
| `worst_reasonable_level` | Highest observed risk level by `aggregation_config.risk_level_order`. |
| `worst_reasonable_level_label` | Display label paired with `worst_reasonable_level`. |
| `outlier_worlds` | Internal labels for worlds where the highest level is not the majority scenario. Use for checking multi-world divergence only; do not expose these labels in正文. |

## LLM Check

After T1, perform only a sanity check:

- averages match distributions;
- world count matches input world count;
- risk labels later used in text are present in `source_evidence` or T2 output;
- placeholder fields such as `inflection_points` are not overstated.

Do not expose raw stance scores, polarization indices, group counts, tick numbers, or percentages in the text report正文.
