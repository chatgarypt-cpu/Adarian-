@skill karpathy-coding
use a workflow to: 通过多 agent 串行实验，找到从 Qwen 集群获取可靠 JSON 输出的最佳路径。一共 5 个 agent 依次执行，每个 agent 完成后下一个才启动。不用 @agent 引用，所有 agent 定义在 workflow 的 agent 节中。

## 背景

Adarian MVP 的 Phase 1 Entity Generator（`src/phase1/generator.py`）用 LLM 生成 JSON 格式的实体抽取结果（`EntityExtractionOutput`），但会出现 JSON 截断问题——Qwen 的推理链消耗了 generation budget，导致 8192 max_tokens 不够用，输出被截断后 JSON 解析失败。

**Qwen 集群信息：**
- endpoint: `http://100.89.3.59:8090/v1`（内网，无需代理）
- API Key: `config.py` 中的 `LLM_API_KEY`
- 模型: `qwen36-35b`（主要测试对象）
- 已验证：endpoint 是 OpenAI 兼容 API（`/v1/chat/completions`），支持 `response_format` 参数

**关键代码文件：**
- `src/phase1/generator.py` — EntityGenerator，当前用自由 JSON 输出 + 后解析
- `src/phase1/compiler.py` — Compiler，后处理归一化（LLM修复前已经做了 Compiler 归一化）
- `src/phase1/prompts.py` — Generator 用到的 system/user prompt 模板
- `src/llm_client.py` — LLMClient，所有 LLM 调用的封装
- `src/schemas/common.py` — Pydantic schemas（`EntityExtractionOutput` 等）
- `src/schemas/social_network.py` — 社交网络 schema
- `tests/midPhaseTest.py` — 集成测试
- `config.py` — 配置（LLM_BASE_URL, LLM_API_KEY, DEFAULT_MAX_TOKENS 等）

## 实验要求

5 个 workflow step 依次串行执行：

Step 1 — baseline: 跑当前 Generator 的 JSON 输出 10 次，量化失败率
Step 2 — json-mode: 测试 `response_format=json_object`
Step 3 — json-schema: 测试 `response_format=json_schema`
Step 4 — guided-json: 测试 `guided_json` (vLLM)
Step 5 — fan-in: 汇总 4 份 report，推荐方案

---

### Step 1: baseline — 测试当前 Generator 的 JSON 输出成功率

**目标：** 只测 Entity Generator 最核心的 LLM 调用——发送 prompt + 拿回 JSON。不跑全 pipeline。每次测试就是一个 request 的事。

**做法：**
1. 读 `src/phase1/generator.py`（看 Generator 的 system prompt + user prompt 模板）和 `src/phase1/prompts.py`（实际 prompt 内容）
2. 读 `src/llm_client.py`（看当前调用参数——max_tokens=8192, response_model=None）
3. 创建 `tests/structured_output/baseline/test_baseline.py`：
   - **不能直接调 `generator_create_event_entities()`**——它内部硬编码了 LLMClient。需要独立复刻其行为：
     1. 从 `prompts.py` import `GENERATOR_SYSTEM_PROMPT` 和 `GENERATOR_USER_PROMPT`
     2. 手动拼 prompt（用相同的 `.format()` 参数）
     3. 从 `config.py` 读 `LLM_API_KEY`、`LLM_BASE_URL`
     4. 用 `requests.post` 直接调 API（不走 LLMClient）
     5. 用 `src/phase1/utils.py` 的 `_parse_llm_json_payload`、`_coerce_top_level_object` 解析结果
   - 从 `seeds/test8.txt` 读 seed 文本做输入
   - 发送 `chat/completions` 请求，不加任何 response_format 参数——完全复刻当前行为
   - 循环 10 次：
     - 记录每次：耗时、JSON 解析成功/失败、失败原因（truncation / parse error / schema mismatch）
     - 如果是 JSON 解析失败，检查 response `finish_reason` 是否为 `"length"`（截断标志）
   - 输出统计数据：成功率、平均耗时、失败分布
4. 写报告 `tests/structured_output/baseline/report.md`

**限制：**
- 不修改 `src/` 任何代码
- 用 `requests` 直调 API，不走 LLMClient
- 用 `.venv/bin/python` 运行

### Step 2: json-mode — JSON Mode response_format={"type":"json_object"}

**目标：** 测试 OpenAI JSON mode 是否能防止 JSON 截断——同样是单次 LLM 调用。

**做法：**
1. 读 `src/phase1/generator.py` 和 `src/phase1/prompts.py`，了解当前 system/user prompt 内容
2. 创建 `tests/structured_output/json_mode/test_json_mode.py`：
   - 同样是 `requests` 直调 API
   - 加 `response_format={"type": "json_object"}` 参数
   - 使用与 baseline 相同的 prompt + seed 文本
   - 循环 10 次，记录相同指标
   - **关键注意：** JSON mode 只保证合法 JSON 语法，不保证 schema 合规。所以需要两次检测：
     1. 是否是合法 JSON（json.loads 能解析）
     2. 是否包含预期的 key（name, entity_type 等）
3. 写报告 `tests/structured_output/json_mode/report.md`

**限制：**
- 不修改 `src/` 任何代码
- 用 `requests` 直调 API

### Step 3: json-schema — Structured Outputs response_format={"type":"json_schema", ...}

**目标：** 测试 Qwen endpoint 是否支持 OpenAI 兼容的 json_schema 结构化输出。

**做法：**
1. 创建 `tests/structured_output/json_schema/test_json_schema.py`：
   - 同样是 `requests` 直调 API
   - 构造 `response_format={"type": "json_schema", "json_schema": {"name": "entity_output", "schema": <EntityExtractionOutput 的 JSON Schema>, "strict": true}}`
   - 使用与 baseline 相同的 prompt + seed 文本
   - 循环 10 次，记录指标
   - **关键注意：** Qwen 的 vLLM/SGLang 后端可能不支持 json_schema（返回 400 或忽略参数）
2. 写报告 `tests/structured_output/json_schema/report.md`

### Step 4: guided-json — Guided JSON (vLLM) guided_json 参数

**目标：** 测试 vLLM 原生 guided_json 参数是否能在 Qwen endpoint 上工作。依赖 Step 3 完成后再执行。

**做法：**
1. 创建 `tests/structured_output/guided_json/test_guided_json.py`：
   - 同样是 `requests` 直调 API
   - 加 `guided_json=<EntityExtractionOutput 的 JSON Schema>` 参数
   - 使用与 baseline 相同的 prompt + seed 文本
   - 循环 10 次，记录指标
   - **关键注意：** guided_json 是 vLLM 原生参数，如果 Qwen 集群用 vLLM 部署则此方案最可靠。但 endpoint 可能不认识此参数（返回错误或忽略）
2. 写报告 `tests/structured_output/guided_json/report.md`

### Step 5: fan-in — 汇总并推荐最优方案

**依赖：Step 1, 2, 3, 4 全部完成**

**做法：**
1. 读取 A、B、C、D 四份 report
2. 按以下维度对比：

| 维度 | 权重 | 说明 |
|------|------|------|
| 成功率 | 30% | 合法 JSON + 合法 schema 的比例 |
| 实现复杂度 | 20% | 改几行代码？是否需要改底层 LLMClient？ |
| 延迟影响 | 15% | 比 baseline 慢多少？ |
| 可靠性 | 20% | 极端情况下（长推理链、高并发）是否仍可靠 |
| 可维护性 | 15% | 是否容易集成到现有 OCP 架构 |

3. 输出推荐方案到 `outputs/fan-in-recommendation.md`

### 加分项

如果某个方案对 Qwen endpoint 无效（API 返回 400 等），Agent 可以尝试：
- 其他模型（如 `qwen3-32b-tke`）
- 其他参数组合
- 降级方案（如 prompt engineering + Compiler 归一化增强）

## 运行约束

- 所有 Python 代码用 `.venv/bin/python` 运行
- 内网 Qwen endpoint 不走代理（API 调用时可设置 `proxies={"http": None, "https": None}`）
- 不要修改 `src/phase1/` 下的生产代码
- 产物统一写入 `tasks/active/dag-structured-output-pathfinding/outputs/` 目录（相对路径 `outputs/`）

## 完成条件

1. 所有 4 个 Agent 产出测试脚本 + 报告
2. Fan-in Agent 产出推荐方案到 `outputs/fan-in-recommendation.md`
