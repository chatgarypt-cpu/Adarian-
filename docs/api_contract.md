# Adarian v1.5.0b/c API Contract

> Scope: v1.5.0b replaces the v1.5.0a mock frontend data path with real Flask APIs where backend evidence exists. Features without backend support remain `pending`, `disabled`, or `mock-only`.

## Response Envelope

Successful endpoints return JSON objects or arrays documented below. Error responses use:

```json
{
  "code": "ERROR_CODE",
  "message": "Human readable message",
  "details": {}
}
```

## Status Mapping

Backend batch status values are normalized before returning to the frontend:

| Raw | API |
|---|---|
| `success` | `completed` |
| `completed` | `completed` |
| `failed` | `failed` |
| `running` | `running` |
| `pending` | `pending` |
| unknown | `pending` |

Responses may include `raw_status` for diagnostics.

## Security Rules

- The frontend never writes `.env`.
- API keys are write-only. GET responses return `has_api_key`, never the key.
- If `ADARIAN_ENCRYPTION_KEY` is present and `cryptography` is installed, API keys use Fernet encryption.
- Without `ADARIAN_ENCRYPTION_KEY`, dev/test may store an obfuscated value for local smoke tests only; the API reports the gateway as non-production-safe via `key_storage_mode`.

## Endpoints

### `GET /api/ping`

Returns:

```json
{"status":"ok","version":"1.5.0c"}
```

### `POST /api/seed`

Request:

```json
{"seed_text":"事件文本","seed_path":"seeds/test8.txt","task_name":"任务名","source":"manual"}
```

Rules:

- Empty `seed_text` returns `400` with `EMPTY_SEED`.
- `source=manual` is supported.
- `source=file` is supported for local server-side seed paths under the Adarian project directory, for example `seeds/test8.txt`.
- Empty `seed_path` with `source=file` returns `400 EMPTY_SEED`.
- Missing local seed path returns `404 SEED_FILE_NOT_FOUND`.
- Paths outside the project directory return `400 SEED_PATH_NOT_ALLOWED`.
- `source=history` returns `400` with `SOURCE_NOT_SUPPORTED`.

Returns:

```json
{
  "id": "seed_xxx",
  "seed_id": "seed_xxx",
  "checks": [
    {"label":"事件背景已填写","note":"可以进入下一步","status":"passed"},
    {"label":"核心主体识别","note":"v1.5.0b 暂未接入主体抽取","status":"pending"},
    {"label":"时间线可补充","note":"建议补充首发时间和官方回应时间","status":"suggested"}
  ]
}
```

### `GET /api/config`

Returns persisted config with defaults:

```json
{
  "parallel_worlds": 3,
  "ticks": 5,
  "batch_name": "adarian_batch",
  "focuses": [],
  "pending_fields": ["ticks", "focuses"]
}
```

### `POST /api/config`

Persists config. `ticks` is capped to `1..5`; fields not consumed by the current batch backend are returned in `pending_fields`.

### `GET /api/models`

Returns built-in catalog models from the existing backend catalog:

```json
[
  {"id":"qwen36-35b","name":"qwen36-35b","description":"...","selected":false,"available":true,"advice":"内置模型"}
]
```

### `POST /api/models/health`

Performs lightweight local availability classification. This does not mutate gateway settings.

### `GET /api/model-gateways`

Returns `.env` default gateway plus user gateways:

```json
[
  {
    "id":"env-default",
    "name":".env 默认网关",
    "baseUrl":"http://localhost:8000/v1",
    "provider":"openai-compatible",
    "status":"partial",
    "note":"来自环境变量，前端只读",
    "hasApiKey":true,
    "source":"env",
    "models":[]
  }
]
```

### `POST /api/model-gateways`

Creates a user gateway. Request:

```json
{"name":"本地服务","baseUrl":"http://localhost:8000/v1","provider":"openai-compatible","apiKey":"optional"}
```

### `PUT /api/model-gateways/<id>`

Updates a user gateway. `env-default` is read-only and returns `403`.

### `POST /api/model-gateways/<id>/discover-models`

Requests `<base_url>/models`. Returns discovered model rows. Timeout/error responses return `MODEL_DISCOVERY_FAILED`.

### `POST /api/model-gateways/<id>/health`

Returns status, latency and error if available.

### `POST /api/run`

Request:

```json
{
  "seed_text": "事件文本",
  "seed_path": "seeds/test8.txt",
  "models": ["qwen36-35b"],
  "tag": "任务名",
  "base_url": "optional",
  "config": {"ticks": 5}
}
```

Rules:

- Empty `models` returns `400` with `NO_MODELS`.
- Empty `seed_text` and `seed_path` returns `400` with `EMPTY_SEED`.
- `seed_path` reuses the existing batch local-file path support.
- Repeated `(seed_text, seed_path, models, tag, base_url)` returns the same `batch_id`.
- v1.5.0b starts execution asynchronously and reports progress through status polling.

Returns:

```json
{"batch_id":"batch_xxx","status":"running","worlds":[]}
```

### `GET /api/run/<batch_id>/status`

Returns:

```json
{
  "batch_id": "batch_xxx",
  "status": "running",
  "raw_status": "running",
  "all_completed": false,
  "worlds": [
    {
      "id":"world_0",
      "round":"第 1 轮",
      "model":"qwen36-35b",
      "status":"running",
      "raw_status":"running",
      "rows": [],
      "errorSummary": ""
    }
  ],
  "logs": []
}
```

### `GET /api/history`

Returns batches from SQLite, newest first. Empty database returns `[]`.

### `GET /api/review/<batch_id>`

Aggregates world evidence from SQLite and batch output. Unknown batch returns `404`. Partial data returns available rows and `complete=false`; it does not fabricate mock risks.

### `POST /api/report`

Request:

```json
{"batch_id":"batch_xxx","type":"risk_assessment","audience":"generic_government"}
```

Finds completed worlds with `simulation_dataset.json` and creates a dataset-only report job. The legacy inline Phase 4 report path is retired; report artifacts are generated by the `/api/report` job pipeline and exposed through report job file/view endpoints. If no dataset exists, returns `409 REPORT_SOURCE_NOT_FOUND`.

### `GET /api/settings`

Returns persisted settings:

```json
{"maxConcurrent":3,"outputDir":"outputs/runs/","retentionDays":30,"technicalMode":false,"systemChecks":[]}
```

### `PUT /api/settings`

Persists supported settings. Retention cleanup and technical detail expansion remain pending in v1.5.0b.

## Explicitly Unsupported in v1.5.0b

- `POST /api/cancel/<batch_id>`
- `POST /api/cancel/<batch_id>/<world_id>`
- `POST /api/run/<batch_id>/worlds/<world_id>/retry`
- File upload source for seed
- History reuse source for seed
