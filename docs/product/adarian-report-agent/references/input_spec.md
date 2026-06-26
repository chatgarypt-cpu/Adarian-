# Input Spec

`/adarian-report <input_json_path>` receives one JSON file from the user.

## JSON Schema

```json
{
  "event_name": "OPPO母亲节文案事件",
  "seed_input_path": "./seed_input.txt",
  "worlds": [
    {
      "label": "world_0",
      "simulation_dataset_path": "./world_0/simulation_dataset.json"
    }
  ]
}
```

## Fields

| Field | Required | Type | Rule |
|---|---:|---|---|
| `event_name` | yes | string | Report title and `appendix_b.meta.event_name`. 如包含引号，应使用中文弯引号 `"` (U+201C) / `"` (U+201D)，而非 ASCII 直引号 `"` (U+0022)，以避免 JSON 解析冲突。 |
| `seed_input_path` | yes | string | Relative paths resolve from the input JSON directory. T0 must verify the file exists. |
| `worlds` | yes | array | Must contain at least one world. |
| `worlds[].label` | yes | string | Stable world label used in evidence records. |
| `worlds[].simulation_dataset_path` | yes | string | Relative paths resolve from the input JSON directory. T0 must verify each file exists. |

## Seed File Responsibility

`seed_input_path` is the event source material for "一、舆情概要". The Python script only validates the field shape; the Agent T0 step validates file existence before running the script.

Demo data may not include a standalone `seed_input.txt`. For local smoke tests, create one beside the input JSON from the original event material or from `source_context.event_summary`. Do not silently fall back during formal report generation.

## Path Rules

- Prefer relative paths.
- Do not write Skill-internal absolute paths.
- `simulation_dataset_path` and `seed_input_path` are resolved relative to the input JSON file, not relative to the Skill directory.
