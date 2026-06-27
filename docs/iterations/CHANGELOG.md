
## 2026-06-07: Generator max_tokens 修复 + 平行世界调度器设计

- **task_id**: generator-max-tokens-fix + parallel-worlds-design
- **status**: committed (0fb089c)
- **changes**:
  - `src/phase1/generator.py`: Generator 实体提取的 LLMClient 单独设 max_tokens=16384（原默认 8192），防止推理链挤占 JSON 输出 budget
  - `docs/design/parallel_worlds_scheduler_v0.1.md`: 平行世界调度器设计文档 v0.1（5 进程并行 / 各自模型 / 失败兜底）
- **next**: 产品侧风险映射更新；平行世界调度器实现

## 2026-06-07: code-reality-review-v1.3.1 (Closeout)

- **task_id**: code-reality-review-v1.3.1
- **status**: closed
- **verdict**: REPAIRABLE_HOLD
- **outputs**: inventory(43K) + boundary(24K) + flow(25K) + design_alignment(24K) + final_report(32K) + phase3_concurrency(12K)
- **carryover**: Phase3→Phase4 reverse dependency, RiskAnalyzer 4-role split, mean_stance data dependency for concurrency
# Adarian MVP 变更日志 (CHANGELOG)

所有重要版本变更都会记录在此文档中。

---

## v1.5.1 (2026-06-27) — 后端可观测性补全 + 自持收口

**主题**：world 耗时 bugfix、batch 异常恢复、SSE 心跳、通用验收测试 skill、资产注册表全面补全

### 修复
- `world_progress()` 已完成世界取 PHASE END 耗时改为取 RUN END 总耗时
- 新增 `_recover_stale_batches()` 启动恢复，进程重启后自动纠正 stuck 的 running batch
- 新增信号处理器（SIGTERM/SIGINT + atexit），进程退出时标记运行中 batch 为 failed
- `register_static` 从万能 `/<path:path>` 路由改为 `@app.errorhandler(404)`，防止劫持 API 路由
- SPA 路由重构 — 允许 `/api/events` SSE 端点通过

### 新增
- **SSE 心跳** — `/api/events` 端点每 5s 发 `data: alive`，前端 `EventSource` 订阅，后端断线瞬时感知
- **`/api/stats`** — 今日批次计数（基于服务端本地时间）
- **`acceptance-test` skill** — 通用 YAML 驱动浏览器验收测试框架，不绑定项目
- 前端 `App.vue` 系统状态组件 — SSE 保活连接，三态显示（检测中/就绪/离线）
- 4 个 hook 脚本注册：closeout-gate-hook、debug-hook-payload、dispatch-skill-gate、mark-dispatch-ready
- 39 个缺失 Hermes skill 注册到 skill_registry.yaml

### 修改
- `src/adarian/serve/db.py` — 新增 `track_batch()` / `untrack_batch()` 进程级 batch 跟踪
- `frontend/src/App.vue` — `todayBatchCount` 从硬编码 `3` 改为 `/api/stats` 真实查询
- `frontend/src/api/client.ts` — 新增 `getStats()` API 方法
- `frontend/src/api/types.ts` — 新增 `StatsResponse` 类型
- `WorkflowBase/registry/` — 全部注册表更新：skill 194 / hook 25 / mcp 7 / executor 7
- `workflow_map.yaml` — 时间戳更新 + hook 注册表清单补充
- `docs/iterations/CHANGELOG.md` — 本版本记录

### 自持结果
```text
PM Runtime Self-Maint: ✅
Drift Check:           ✅ critical=0, 6 warnings（已标记过时注释）
Skills registered:     194
Hooks registered:      25
MCPs registered:       7
Executors registered:  7
```

**主题**：新前端入口收口 + 本地 seed 路径恢复 + test8 live E2E

### 新增

- `Makefile`：`rebuild` / `serve` 入口。
- `tests/e2e/test_entry_e2e.py`：覆盖 `seed_path=seeds/test8.txt` 的 API smoke、幂等、错误路径、review/history。

### 修改

- `adarian.sh` / `start.command` 改为 `PYTHONPATH=src .venv/bin/python -m adarian serve`。
- `/api/seed` 支持 `source=file` + 项目内本地 `seed_path`。
- `/api/run` 支持并校验项目内本地 `seed_path`，避免绕过 seed 保存接口。
- 01-seed 前端恢复“本地 seed 路径”和“本地 test8”入口；运行页按来源传递 `seed_text` 或 `seed_path`。
- 前端生产提示类从 `mock-note` 改为 `status-note`；StateTools 仍仅开发模式可见。
- 前端版本更新为 `1.5.0-c`，`/api/ping` 返回 `1.5.0c`。
- `docs/api_contract.md` 更新 seed/run 的 `seed_path` 契约。

### 删除

- `src/adarian/_legacy_serve.py`。

### 验收

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/serve/ tests/e2e/ -q
  19 passed

cd frontend && npm test -- --run
  6 passed

rm -rf frontend/dist && cd frontend && npm run build
  pass

Live E2E:
  seed_path: seeds/test8.txt
  model: minimax
  batch_id: test8-live-e2e-final_164414
  status: completed
  review: 200 complete=true
  report: 200 report.json
  history: includes batch
```

### 边界

- 未修改 Phase 1-4、analysis、parser、llm_client、schema 包。
- 未创建 git commit/tag；tag 待提交后处理。

## v1.4.0 (2026-06-22) — Scheduler MVP Proof / Parallel World Console R0

**主题**：平行世界推演控制台 R0

### 新增

- `scheduler/` 产品入口包。
- `scheduler/run.py`：基于 `PARALLEL_MODE=true` 的真实 batch runner，产物落到 `batch_dir/world_N/`。
- `scheduler/config_ui.py`：stdlib HTTP API，提供模型列表、hello test、launch、session status。
- `scheduler/config_ui.html`：深色科技风单页控制台。
- `tests/test_scheduler_mvp.py`：dataset evidence、batch config、磁盘 inspect 回归测试。
- `outputs/codex_receipt.yaml`、`runtime/result.json`、`runtime/pane_capture.log`、`summary/summary.md`：本轮 runtime evidence。

### 功能

- 支持 `python -m scheduler --help`。
- 支持 `python -m scheduler ui --host 127.0.0.1 --port 9788`。
- 支持输入 seed 文本、选择模型、发起多 world batch。
- UI 展示真实 `batch_dir`、world 状态、`simulation_dataset.json` existence、`risk_type_classification.primary_types`。
- 预留 disabled `Report Agent Consumer` 下游入口，contract 为 `batch_dir` 或 `worlds[].dataset_path`。

### 验收

```text
.venv/bin/python -m py_compile scheduler/*.py
  pass

.venv/bin/python -m scheduler --help
  pass

.venv/bin/python -m pytest tests/test_scheduler_mvp.py -v
  3 passed

2-model batch smoke:
  outputs/runs/2026-06-22/batch_smoke_183131/batch_config.yaml
  outputs/runs/2026-06-22/batch_smoke_183131/world_0/simulation_dataset.json
  outputs/runs/2026-06-22/batch_smoke_183131/world_1/simulation_dataset.json
```

### 边界

- 未修改 Phase 1-4。
- 未修改 `src/analysis/`。
- 未修改 `src/schemas/`。
- 未修改 `simulation_dataset.json` schema。
- 未实现 Report Agent Consumer。
- 未新增外部依赖。

### Known issues

- in-app browser `iab` 不可用，UI 可视 smoke 以 HTTP/API/HTML 检查替代。
- 误触发的 `batch_183510` 已停止，不作为验收证据。

### 状态

Owner-Control closeout 确认于 2026-06-24。UI 后续再逐步完善。

---

## v1.4.1 (2026-06-24) — 入口收敛 + 多世界实时面板

**主题**：统一入口 + batch 可视化

### 新增

- `adarian/` 产品入口包（`__init__.py`, `__main__.py`, `run.py`, `serve.py`, `batch.py`, `inspect.py`）
- `adarian.sh` 命令行统一入口（`up` / `run` / `serve` / `batch` / `inspect`）
- `start.command` macOS 双击入口
- batch 多世界实时面板（Rich Live，每秒刷新 Phase + 线程计时）

### 修改

- `src/parser.py` — `parse()` 加 `seed_text` 参数，写入 `run_info.seed_text`
- `main.py` — `main(seed_path)` 参数，保留 `if __name__` 向后兼容
- `src/llm_client.py` — `[llm_diag]` 从 stdout 改到 stderr
- `spec/dataset_fields.yaml` — 加 `run_info.seed_text` 规格
- `adarian/batch.py` — batch runner 子进程调用改为 `python -m adarian run`

### 删除

- `scheduler/` — 内容已迁入 `adarian/`

### 边界

- 未修改 `src/phase1/` 到 `src/phase4/`
- 未修改 `src/analysis/`
- 未修改 `src/schemas/`
- 未修改 `config.py`
- 未修改 `tools/probe_scheduler/`

---

## v1.4.1.1 (2026-06-24) — src layout 重构

**主题**：项目结构改为 src layout

### 变更

- `src/adarian/` 新建为唯一代码包
- `adarian/`（旧包）删除，内容迁入 `src/adarian/`
- `config.py`（根目录）迁入 `src/adarian/config.py`
- `src/phase*/`、`src/analysis/`、`src/display/` 等全部迁入 `src/adarian/`
- 所有 `from src.xxx` → `from adarian.xxx`
- `import config` → `from adarian import config`
- `pyproject.toml` 新建（`pip install -e .` 支持）
- `requirements.txt` 更新（精简为实际依赖）
- `modelslist.txt` 更新（完整 CATALOG 清单）
- `adarian.sh` / `start.command` 改用 `python -m src.adarian`

### 边界

- 未改业务逻辑
- 未改 `src/adarian/` 内部调用链
- 未改 `docs/archive/`、`profiling/`、`tools/` 等非核心目录

---

## v1.2.9 (2026-05-15) — Closeout

**主题**：Phase 4 Report Agent Decoupling R0

### 新增

- `src/phase4/report_normalizer.py`
- `src/phase4/report_narrative.py`
- `src/phase4/report_title.py`
- `tests/test_phase4_report_normalizer.py`
- `tests/test_phase4_report_agent_decoupling.py`

### 修改

- `report_agent.py` 降级为 Phase 4 façade / orchestrator。
- `src/phase4/__init__.py` 精简 re-export。
- closeout hygiene cleanup 执行 A1-A6。

### 验收结果

- tests/: 83 passed
- test8 smoke passed
- forbidden_files_touched: false
- audit_dirty_tree_mixed: false
- coupling_verdict: MODERATE_COUPLING_ACCEPTABLE_WITH_KNOWN_ISSUES

### Closeout

- closed / pass_with_known_issues
- blocks_next_version: no

---

## v1.2.9 (2026-05-15) — Phase 4 Report Agent Decoupling R0

**主题**：Phase 4 Report Agent 解耦 R0

### 新增

- `src/phase4/report_normalizer.py`：承接 Markdown normalizer pipeline、risk section code-owned 注入、指标术语替换、metric explanation prefill 拼接、现实化拐点表达拦截和 prompt/code-owned 指令泄漏过滤。
- `src/phase4/report_narrative.py`：承接 LLM 叙事生成与 prompt context 组装。
- `src/phase4/report_title.py`：承接报告标题生成、标题规范化和 metadata header helper。
- `tests/test_phase4_report_normalizer.py`：normalizer extraction / prefix guard / prompt leakage / metric prefill targeted tests。
- `tests/test_phase4_report_agent_decoupling.py`：Phase 4 facade、required functions、narrative/title/normalizer import boundary tests。

### 修改

- [src/phase4/report_agent.py] 保持 Phase 4 facade / orchestrator，对旧测试 import 的 helper 保留 re-export / wrapper。
- [src/phase4/report_agent.py] `generate_report_with_llm()` 仍作为对外入口，但 LLM 叙事生成实现迁入 `report_narrative.py`。
- [src/phase4/report_agent.py] `_normalize_saved_markdown()`、`_code_owned_risk_section()`、`_replace_report_metric_terms()` 等 normalizer helper 改由 `report_normalizer.py` 提供。
- [src/phase4/report_agent.py] `_ensure_metadata_header()`、`_normalize_report_title_line()`、`_normalized_report_title()` 改由 `report_title.py` 提供。
- [src/phase4/report_agent.py] closeout hygiene：移除 DS 标记 SAFE_TO_REMOVE 的 3 个死函数和 2 个冗余依赖项。
- [src/phase4/__init__.py] closeout hygiene：移除 4 个无外部消费者的 package-level re-export，保留主入口 re-export。
- [docs/iterations/v1.2.9-Phase-4-Report-Agent-Decoupling-R0.md] 更新执行与验证证据。
- [docs/iterations/TASK_LOG.md] 记录 v1.2.9 attempt 结果。
- [docs/iterations/CHANGELOG.md] 记录 v1.2.9 变更。

### 不变

- `main.py` 未修改。
- `src/phase4/report_prompts.py` 未修改，prompt 语义未改变。
- `config.py` / `src/llm_client.py` 未修改。
- `src/schemas/` 未修改，`final_report.json` contract 未改变。
- `src/whitebox/` 未修改，whitebox artifact contract 未改变。
- Phase 1 / Phase 2 / Phase 3 未修改。
- `assess_risk()` / `select_primary_risk_types()` / `identify_inflection_points()` / `parse_llm_report_response()` / `generate_fallback_report()` / `_llm_generated_markdown` 仍保留在 `report_agent.py`。
- 风险算法语义未改变。
- `final_report.md` 五章结构未改变。
- 未新增 runtime artifact contract。

### 验收

```text
.venv/bin/python -m py_compile src/phase4/report_agent.py src/phase4/report_normalizer.py
  pass

.venv/bin/python -m pytest tests/test_phase4_report_normalizer.py -v
  4 passed

.venv/bin/python -m pytest tests/test_inflection_point_output_guard.py -v
  5 passed

.venv/bin/python -m pytest tests/test_report_markdown_grounding.py tests/test_phase4_markdown_metric_grounding.py -v
  20 passed

.venv/bin/python -m py_compile src/phase4/report_agent.py src/phase4/report_narrative.py src/phase4/report_title.py src/phase4/report_normalizer.py
  pass

.venv/bin/python -m pytest tests/test_phase4_report_agent_decoupling.py -v
  4 passed

.venv/bin/python -m pytest tests/test_report_product_contract.py tests/test_report_markdown_grounding.py tests/test_phase4_markdown_metric_grounding.py tests/test_risk_assessment_directionality.py tests/test_inflection_point_output_guard.py -v
  46 passed

.venv/bin/python -m compileall src
  pass

.venv/bin/python -m pytest tests/ -v
  83 passed

.venv/bin/python main.py seeds/test8.txt
  pass

.venv/bin/python -m pytest tests/test_phase4_report_normalizer.py tests/test_phase4_report_agent_decoupling.py -v
  8 passed after closeout hygiene

.venv/bin/python -m pytest tests/test_report_markdown_grounding.py tests/test_report_product_contract.py -v
  28 passed after closeout hygiene

.venv/bin/python -m pytest tests/test_phase4_markdown_metric_grounding.py tests/test_risk_assessment_directionality.py tests/test_inflection_point_output_guard.py -v
  18 passed after closeout hygiene

.venv/bin/python -m pytest tests/test_run_dir_concurrency.py tests/test_whitebox_artifact_shell.py -v
  8 passed after closeout hygiene

.venv/bin/python -m pytest tests/ -v
  83 passed after closeout hygiene
```

### Smoke

```text
latest_run_dir: outputs/runs/test8_20260515_184351/run_964791_45220
final_report.json: exists
final_report.md: exists
whitebox_summary.json: exists
risk_level: high
risk_level_label: 高风险
primary_risk_types: group_polarization_risk
whitebox report_completeness: pass
whitebox artifact_check: pass
final_report.md 五章结构: pass
模拟模拟极化指数: not found
模拟模拟关键变化点: not found
prompt / code-owned instruction leakage: not found
```

### 已知遗留

- 风险阈值仍是工程初始阈值，待后续多 seed 标定。
- 模拟极化指数仍是工程 proxy。
- 模拟关键变化点仍未完整升级为多信号 framework。
- `external_risk_adjustment` 仅作为 future hook，未实现、未接入、未进入报告产物。
- `select_primary_risk_types()` 仍依赖 `risk_assessment` 文本 keyword matching。
- `single_run_summary` / `parallel_world_synthesis` / `batch_synthesis_context` 未实现。
- risk calculation 仍留在 `report_agent.py`，待后续 risk engine 解耦。

---

## v1.2.8.1.1 (2026-05-15) — Inflection Point Output Guard & Whitebox Alignment Patch

**主题**：模拟关键变化点输出安全与现有 whitebox 对齐

### 新增

- Inflection point reality-claim post-processing guard。
- `tests/test_inflection_point_output_guard.py`：正向 inflection_points 测试、现实化拐点表达拦截测试、重复“模拟模拟...”前缀回归测试、LLM 不得自行现实化生成拐点测试。
- `tests/test_run_dir_concurrency.py`：验证同秒快速连续创建 run_dir 时共享 batch 文件夹且子目录不撞名。
- 现有 whitebox report completeness 中的 inflection_points 一致性轻量检查。

### 修改

- [src/phase4/report_agent.py] Markdown normalizer 对现实化拐点表述进行模拟口径改写。
- [src/phase4/report_agent.py] 术语替换避免重复前缀：`模拟模拟极化指数`、`模拟模拟关键变化点`、`模拟模拟立场均值`。
- [src/whitebox/report_completeness.py] report_completeness detail 增加 inflection_points 相关检查字段。
- [src/whitebox/report_observer.py] 读取同目录 `final_report.json` 并传入 report completeness 检查；读取失败时 graceful degrade。
- [main.py] Owner-approved infra hotfix：同秒并发运行归入同一 batch 文件夹，并用 `run_{microseconds}_{pid}` 子目录隔离产物，修复并发 run_dir 秒级时间戳撞名，同时保留子目录 `exist_ok=False` 防覆盖。
- [tests/test_whitebox_artifact_shell.py] 增加 JSON / Markdown inflection consistency cases。

### 不变

- InflectionPoint schema 不变。
- identify_inflection_points() 算法不升级，仍保持 `polarization_delta > 0.1`、最多返回 3 个。
- final_report.json contract 不变。
- whitebox_summary 顶层 contract 不变。
- 不新增 whitebox artifact 文件。
- 不新增 whitebox 文件。

### 验收

```text
.venv/bin/python -m py_compile src/phase4/report_agent.py src/whitebox/report_completeness.py src/whitebox/report_observer.py
  pass

.venv/bin/python -m pytest tests/test_inflection_point_output_guard.py -v
  5 passed

.venv/bin/python -m pytest tests/test_report_product_contract.py tests/test_report_markdown_grounding.py tests/test_phase4_markdown_metric_grounding.py tests/test_risk_assessment_directionality.py -v
  41 passed

.venv/bin/python -m pytest tests/test_whitebox_artifact_shell.py -v
  7 passed

.venv/bin/python -m py_compile main.py
  pass

.venv/bin/python -m pytest tests/test_run_dir_concurrency.py -v
  1 passed

.venv/bin/python -m pytest tests/test_inflection_point_output_guard.py tests/test_whitebox_artifact_shell.py tests/test_run_dir_concurrency.py -v
  13 passed
```

### Smoke

```text
venv preflight: `.venv/bin/python -c "import rich; import config; print('OK')"` -> OK
5 次并发 test8 smoke 已复测。
command: .venv/bin/python main.py seeds/test8.txt
log_dir: /private/tmp/v12811_test8_parallel_grouped_venv_20260515_174955
run_dir collision: 未复现。
batch_dir: outputs/runs/test8_20260515_174956
created child run_dirs: run_124186_28033 / run_124186_28035 / run_124188_28031 / run_124356_28030 / run_124670_28028
结果：5/5 均因 Phase 1 LLM APIConnectionError 阻塞，未进入白盒汇总。
```

### 已知遗留

- identify_inflection_points() 仍只使用 polarization_delta 单一信号。
- 未实现 stance_mean_delta。
- 未实现 key_group_stance_shift。
- 未实现 risk_level_changed。
- 未实现 risk_type_changed。
- single_run_summary.json 仍未实现。
- 有 code-owned inflection_points 时，Markdown 与 JSON 数量严格一致性仍待后续框架治理。
- whitebox 只做轻量一致性检查，不做完整 Inflection Framework validation。

---

## v1.2.8.1 (2026-05-15) — Closeout

主题：Risk Assessment Directionality & Metric Explanation Patch

### 新增

- `tests/test_risk_assessment_directionality.py`
- `METRIC_EXPLANATION_PREFILL`

### 修改

- `assess_risk()` 风险方向性逻辑
- `prior_floor` 引入 `event_scale` / `event_controversy`
- `max_negative_shift` 关键群体负向迁移计算
- `final_report.md` 指标解释 code-owned 拼接
- 指标术语映射：模拟立场均值 / 模拟极化指数 / 模拟关键变化点
- 相关 targeted / regression tests

### 验收

- 43/43 tests passed
- 3 次 test8 smoke passed
- DS verdict: PASS
- acceptance_result: pass_with_known_issues
- DS_report: `audit/phase4大版本改造/DS_Agent_Team_Session_Full_Audit_Export_v1.2.8.1_2026-05-15.md`

### 已知遗留

- 风险阈值仍是工程初始阈值，待后续多 seed 标定。
- 模拟极化指数仍是工程 proxy。
- 模拟关键变化点仍未完整升级为多信号 framework。
- `external_risk_adjustment` 仅作为 future hook，未实现、未接入、未进入报告产物。
- `select_primary_risk_types()` 仍依赖 `risk_assessment` 文本 keyword matching，存在匹配盲区；后续应基于 `extraction_output` / `audience_mode` / `event_scale` / `event_controversy` / `tick_logs` / risk metrics 改为 code-owned signal source。
- `main.py:218` 存在并发 run_dir 撞名问题，原因是秒级时间戳 + `exist_ok=False`；这是既有基础设施问题，不属于 v1.2.8.1 回归。
- `_replace_report_metric_terms()` 存在“模拟模拟极化指数”重复前缀 bug；建议后续 Phase 4 normalizer 解耦时修复。

---

## v1.2.8.1 (2026-05-15) — Risk Assessment Directionality & Metric Explanation Patch

**主题**：Phase 4 风险等级方向性修复与指标解释可信化

### 新增

- [src/phase4/report_prompts.py] 新增 `METRIC_EXPLANATION_PREFILL`，由代码侧稳定拼接进 `final_report.md` 附录，不让 LLM 自由生成指标解释。
- [tests/test_risk_assessment_directionality.py] 新增 targeted tests，覆盖低模拟立场均值、负向趋势、模拟极化指数、关键群体负向迁移、event_scale/event_controversy prior floor、HIGH/CRITICAL 防误触发、OPPO 不误升 CRITICAL、risk labels code-owned、prompt 风险等级约束、metric prefill 去重与术语映射。

### 修改

- [src/phase4/report_agent.py] `assess_risk()` 新签名为 `def assess_risk(x_t_sequence, tick_logs, *, extraction_output=None) -> tuple`，三处调用点均同步传入 `extraction_output`。
- [src/phase4/report_agent.py] 风险等级逻辑从“final_x 高值升风险”改为低模拟立场均值、负向趋势、模拟极化指数、关键群体最大负向迁移和高敏先验综合判定。
- [src/phase4/report_agent.py] `event_scale` / `event_controversy` 仅从 `extraction_output` 读取并作为 code-owned MEDIUM floor，不写入新 JSON 字段，不接入外部数据源。
- [src/phase4/report_agent.py] `max_negative_shift` 复用 `_build_code_owned_agent_stance_matrix()` 的首尾立场矩阵逻辑；无足够 tick 或无共同 agent 时返回 `None` 并不参与计算。
- [src/phase4/report_agent.py] saved Markdown 输出层映射术语：情绪均值 / x(t) → 模拟立场均值，极化指数 → 模拟极化指数，拐点 → 模拟关键变化点，Tick → 轮次。
- [src/phase4/report_prompts.py] Prompt 术语同步更新为模拟立场均值、模拟极化指数、模拟关键变化点和轮次。

### 验收结果

```text
.venv/bin/python -m py_compile src/phase4/report_agent.py src/phase4/report_prompts.py
  pass

.venv/bin/python -m pytest tests/test_risk_assessment_directionality.py -v
  11 passed

.venv/bin/python -m pytest tests/test_report_product_contract.py tests/test_report_markdown_grounding.py -v
  28 passed

.venv/bin/python -m pytest tests/test_phase4_markdown_metric_grounding.py tests/test_schema_imports.py -v
  4 passed
```

### 兼容性

- ✅ 不修改 Phase 1 / Phase 2 / Phase 3
- ✅ 不修改 schemas / whitebox / main.py / seeds / outputs
- ✅ 不新增风险类型、不新增 `risk_taxonomy.py`
- ✅ 不接入外部态势感知、不写入 `external_risk_adjustment`
- ✅ `risk_level_label` / `risk_type_labels` 继续 code-owned

### 已知遗留

- 风险阈值仍是工程初始阈值，待后续多 seed 标定。
- 模拟极化指数仍是工程 proxy。
- 模拟关键变化点仍未完整升级为多信号 framework。
- `external_risk_adjustment` 仅作为 future hook，未实现、未接入、未进入报告产物。

---

## v1.2.8 (2026-05-13)（checkpoint — before narrative persuasiveness patch）

**主题**：Government-facing Detailed Report Narrative & Prompt Governance

### 新增

- [src/phase4/report_prompts.py] 新增 v1.2.8 静态 prompt assets：`REPORT_RULE_PRIORITY`、政府治理视角规则、政府承压主体识别规则、标题/概要/演化/风险/对策规则、指标业务标签映射、禁止虚构引语规则、企业品牌事件 section-level few-shot。
- [tests/test_report_markdown_grounding.py] 新增 v1.2.8 targeted tests，覆盖 prompt 静态边界、priority tier、metric label map、企业 PR 禁用、虚构引语禁用、raw metric field 防护、残缺/询问式 LLM Markdown fallback rebuild。
- [tests/test_report_product_contract.py] 新增产品 contract checks，覆盖短标题、阶段叙事、结构性风险点、政府治理动作语言、空拐点兜底和 v1.2.7 contract 延续。

### 修改

- [src/phase4/report_agent.py] 新增标题 normalization，保存前统一短标题并保留 `report_meta.event_name` 不变。
- [src/phase4/report_agent.py] 强化 saved Markdown normalization：企业 PR 句式、raw metric fields、虚构引语格式、`待评估` 残留清理。
- [src/phase4/report_agent.py] 风险章节仍使用 code-owned `risk_level_label` / `risk_type_labels`，并补入 `结构性风险点一/二`。
- [src/phase4/report_agent.py] fallback Markdown 升级为政府治理视角：演化分析包含阶段叙事，对策建议使用关注、研判、跟踪、协调、督促、预置、提示、监测、引导、避免过度介入等治理动作语言。
- [src/phase4/report_agent.py] 新增五章完整性检测；当 LLM Markdown 是询问式、残缺文本或只输出风险章节时，保存前触发现有 code-owned fallback rebuild，确保 final_report.md 至少保持五章完整。

### 验收结果

```text
.venv/bin/python -m py_compile src/phase4/report_agent.py src/phase4/report_prompts.py
.venv/bin/python -m pytest tests/test_report_product_contract.py tests/test_report_markdown_grounding.py -v
  result: 24 passed
.venv/bin/python -m pytest tests/test_phase4_markdown_metric_grounding.py tests/test_schema_imports.py -v
  result: 4 passed
git diff --check -- src/phase4/report_agent.py src/phase4/report_prompts.py tests/test_report_markdown_grounding.py tests/test_report_product_contract.py
  result: passed
```

### Smoke

```text
command: .venv/bin/python main.py seeds/test8.txt
exit_code: 0
run_dir: outputs/runs/test8_20260512_235016
artifact_check: pass
whitebox_summary: pass
whitebox_completeness_score: 1.0
final_report_words: 2505
```

### Checkpoint

```text
checkpoint_commit: cd59c235da4e01a1339282f69f85e482ed76e10c
message: checkpoint: v1.2.8 report narrative framework before quality patch
```

### 已知遗留

- 报告已满足五章完整、政府治理视角和机械禁用项 clean，但说服力、篇幅和叙事展开仍需 narrative persuasiveness & section length budget patch。
- test8 最新 Markdown 顶部仍有双 H1 标题，且短标题存在“营营销”重复字样，后续小补丁处理。
- 未进入 Phase 1-3、ReportContext、Prompt Registry、外部检索、政策知识库或双输出模式。

---

## v1.2.8 patch-02 (2026-05-13) — Main Body Expansion & Data-to-Judgment Elaboration Patch + H1 Hygiene

**主题**：主体正文扩容、数据转判断、报告展开能力增强 + H1 标题去重修复

### 新增

- [src/phase4/report_prompts.py] 新增正文展开规则常量：主体正文篇幅预算、数据转判断、展开链、演化分析二级结构、关键洞察、矛盾焦点与风险展开、对策建议四要素、H1 hygiene 规则。
- [src/phase4/report_agent.py] `generate_report_with_llm()` 在 LLM user prompt 上下文显式注入 `CODE_OWNED_REPORT_CONTRACT`（risk_level_label / risk_type_labels / audience_mode / primary_risk_types），不修改 `final_report.json` contract。

### 修改

- [src/phase4/report_agent.py] fallback Markdown 升级为详尽二级结构：演化分析含（一）主体与发声结构分析/（二）关键群体变化分析/（三）阶段演化分析/（四）关键洞察；风险研判含（一）矛盾焦点分析/（二）结构性风险点一/（三）结构性风险点二/（四）结构性风险点三/（五）短中期态势判断；对策建议至少 5 条，每条含治理动作、触发条件、介入边界、预期效果。
- [src/phase4/report_agent.py] 保存前 H1 去重：最终 Markdown 最多一个 H1，metadata header 已有 H1 时移除 body H1，不移除五章 `##` 标题。
- [src/phase4/report_agent.py] 标题拼接修复：test8 标题为"OPPO母亲节营销争议舆情风险研判报告"，无"营营销"等拼接重复。
- [src/phase4/report_agent.py] CODE_OWNED_REPORT_CONTRACT 如被 LLM 回显，保存前清理该内部 block。
- [tests/test_report_markdown_grounding.py] 新增 targeted tests：prompt 常量覆盖、篇幅预算、数据转判断、展开链、关键洞察、矛盾焦点、对策建议四要素、H1 hygiene、runtime contract 注入、fallback 二级结构验证。

### 验收结果

```text
.venv/bin/python -m py_compile src/phase4/report_agent.py src/phase4/report_prompts.py
  pass

.venv/bin/python -m pytest tests/test_report_product_contract.py tests/test_report_markdown_grounding.py -v
  28 passed

.venv/bin/python -m pytest tests/test_phase4_markdown_metric_grounding.py tests/test_schema_imports.py -v
  4 passed

git diff --check -- src/phase4/report_agent.py src/phase4/report_prompts.py tests/test_report_markdown_grounding.py tests/test_report_product_contract.py docs/iterations/v1.2.8-Government-facing-Detailed-Report-Narrative-Prompt-Governance.md
  pass
```

### Smoke

```text
command: .venv/bin/python main.py seeds/test8.txt
exit_code: 0
run_dir: outputs/runs/test8_20260513_012401
artifact_check: pass
whitebox_summary: pass
whitebox_completeness_score: 1.0
final_report_words: 5375
main_body_estimated_words: 4813
appendix_estimated_words: 268
five_chapter_template: yes
single_h1: yes
title: OPPO母亲节营销争议舆情风险研判报告
title_hygiene: clean（无"营营销"）
contains_key_insight: yes
contains_conflict_focus_analysis: yes
structural_risk_points: 3
recommendations: 5
recommendation_four_elements: yes
禁用项 clean: enterprise PR / raw metric / fabricated quote / 待评估
```

### 已知遗留

- 报告仍需进一步增强"数据解释表 / 关键群体解释表 / 矛盾焦点—风险路径表"。
- 可能需要下一小补丁：Interpretive Tables & Event-specific Grounding Patch。
- Phase 1 group generation quality debt 仍未处理。
- Report Asset Library / ReportContext / Prompt Registry 未进入本版本。
- 不修改 Phase 1-3 / schema / whitebox。

### 兼容性

- ✅ 不修改 Phase 1-3
- ✅ 不修改 schemas/phase4.py
- ✅ 不修改 whitebox/report_completeness.py
- ✅ 不破坏 v1.2.7 report contract

---

**主题**：Phase 4 Report Product Governance Sprint

### 新增

- [src/phase4/report_prompts.py] 新增静态 prompt asset — FIVE_CHAPTER_HEADINGS、SIMULATION_DISCLAIMER、FORBIDDEN_REALITY_PHRASES、MARKDOWN_GROUNDING_RULES、RISK_EXPRESSION_RULES、REPORT_SYSTEM_PROMPT、REPORT_USER_PROMPT_SUFFIX。AST 验证为纯数据（无函数/类/导入/调用）。
- [tests/test_report_product_contract.py] 新增 5 targeted tests — generated_at 一致性、audience_mode 关键词路由、risk_level_label 白名单、metadata header 注入、dual-path generated_at。
- [tests/test_report_markdown_grounding.py] 新增 7 targeted tests — 五章模板、风险表达结构、forbidden phrases、policy boundaries、whitebox section alignment、report_prompts AST 静态检查、dual-path generated_at。

### 修改

- [src/schemas/phase4.py] 新增 REPORT_TYPE、RISK_LEVEL_LABELS、RISK_TYPE_LABELS（13-type 白名单）、AudienceMode enum、ReportMeta model、Phase4Output validators。
- [src/schemas/__init__.py] 更新 re-exports：AudienceMode、ReportMeta、REPORT_TYPE、RISK_LEVEL_LABELS、RISK_TYPE_LABELS。
- [src/phase4/report_agent.py] 新增 determine_audience_mode()（关键词路由）、select_primary_risk_types()（确定性 keyword matching）、build_report_meta()、_ensure_metadata_header()、_metadata_header()、generate_markdown_report()（五章 fallback）、save_markdown_report() normalizer（risk-contract-consistency-patch）。generated_at 为 code-owned，audience_mode 支持 4 级枚举，risk_type_labels 受白名单约束。
- [src/whitebox/report_completeness.py] REQUIRED_SECTION_GROUPS 与 FINAL_SECTION_HEADINGS 对齐五章模板（舆情概要/演化分析/风险研判/对策建议/附录）。

### 功能

- ✅ final_report.md 采用五章模板，明确标注"模拟推演型舆情风险研判报告"及模拟推演口径
- ✅ final_report.json 新增 report_meta（generated_at / timezone / report_type / event_name / total_ticks / simulation_run_id）
- ✅ generated_at 为代码侧生成，Markdown 与 JSON 一致
- ✅ audience_mode 支持最小关键词路由（generic_government / law_enforcement_facing / regulator_facing / public_management_facing）
- ✅ risk_level_label 映射（低风险 / 中风险 / 高风险 / 重大风险）
- ✅ primary_risk_types 来自 13-type 轻量白名单，LLM 不得自由发明
- ✅ report_prompts.py 为纯 prompt asset，不含业务逻辑
- ✅ whitebox section headings 对齐五章模板
- ✅ 禁止 8 个新架构模块、禁止 6 个 forbidden phrases
- ✅ risk-contract-consistency-patch 通过 smoke rerun 验证

### 已知遗留

- 15 known issues 全部 defer 至 v1.2.12 Phase 4 Report Architecture Hardening
- 报告产品表达质量约 35/100（contract R0 骨架完成，详尽版叙事质量待提升）

### 兼容性

- ✅ 不修改 Phase 1-3
- ✅ 不修改 RuntimeLogger / speaker selector
- ✅ run artifact contract 保持不变
- ✅ 16 targeted tests + 2 regression tests 全部通过

**DS Review 证据**：
- attempt-01 DS Verify: PASS
- attempt-02 DS Verify: PASS + ACCEPTABLE_WITH_RECOMMENDATIONS
- Prompt Quality Review: PASS
- test8 Smoke Test: PASS_WITH_ISSUES → risk-contract-patch → PASS
- test8 Smoke Rerun: PASS（3 LLM compliance issues 全部修复）
- Closeout Record Patch: PASS

---

## v1.2.6 (2026-05-11)（✅ 已收口 — DS Accept pass）

**主题**：Schema Split Governance & Contract Library Boundary

### 新增

- [src/schemas/__init__.py] 新增 schema contract library public re-export 入口，保持 `from src.schemas import ...` 兼容。
- [src/schemas/common.py] 新增 shared/common schema contracts，包含 `EntityExtractionOutput` canonical object 与 `ConfirmationBiasLevel` public export。
- [src/schemas/phase1.py] 新增 Phase 1 new-path compatibility re-export。
- [src/schemas/phase2.py] 新增 Phase 2 schema contracts。
- [src/schemas/phase3.py] 新增 Phase 3 schema contracts。
- [src/schemas/phase4.py] 新增 Phase 4 schema contracts。
- [src/schemas/_legacy.py] 新增 dead/legacy schema boundary，不从 `src.schemas` 重新导出。
- [tests/test_schema_imports.py] 新增 old import surface、new submodule import、`src` public export、legacy direct import 与 legacy non-export checks。

### 删除

- [src/schemas.py] 删除单体 schema 文件，由 `src/schemas/` package 替代。

### 修改

- [src/__init__.py] 更新 schema authority 描述并继续导出当前 public active types，保留 `ConfirmationBiasLevel`。
- [src/phase3/tick_simulation.py] 移除 unused `NodeRole` import；不改变 Phase 3 行为。
- [docs/dev_spec.md] 同步当前 schema authority 为 `src/schemas/` package。

### 边界

- 未修改 Phase 1 prompt。
- 未修改 Phase 3 speaker selector 策略。
- 未修改 Phase 4 report prompt / generation 语义。
- 未修改 RuntimeLogger / whitebox 职责。
- 未改变 `outputs/runs/<run_id>/` artifact contract。
- 未进入 Parser / Compiler / Validator、Repair Loop、Prompt Library 或 Phase 4 Report Governance。

---

## Workflow Rule Update (2026-05-11)

**主题**：Dirty Tree Gate Granularity 修正

### 修改

- [docs/skills/workflow_core.md] 新增源码执行区 dirty gate 高层原则：schema / architecture / multi-file implementation 默认只以 `src tests main.py config.py scripts profiling seeds` 作为源码执行区 blocker 判定范围。
- [docs/skills/iteration_execution_guard.md] 将 dirty tree 响应协议改为分层判定：`SOURCE_DIRTY_BLOCKER` 阻塞源码实现，`DOC_DIRTY_ALLOWED_OR_NEEDS_CLASSIFICATION` 只要求报告和分类，不自动阻塞。
- [docs/skills/iteration_execution_guard.md] 新增标准检查命令，允许 Control Agent 或具体 attempt prompt 覆盖 dirty gate pathspec。

### 边界

- 未修改业务源码。
- 未修改全局 Codex skill：`/Users/gary/.codex/skills/adarian-iteration-safety-gate/SKILL.md`。
- 保留 destructive git 操作必须显式授权的规则。

---

## v1.2.5.2 (2026-05-07)

**主题**：LLM-Owned Score Audit & Report Metric Ownership Governance

### 新增

- [tests/test_phase4_markdown_metric_grounding.py] 新增 Phase 4 Markdown metric grounding targeted tests，覆盖 code-owned stance matrix 与空拐点声明。

### 修改

- [src/phase4/report_agent.py] 将 Phase 4 Markdown 报告的 per-agent stance 与 inflection point 来源约束到 code-owned blocks。
- [src/phase4/report_agent.py] `REPORT_SYSTEM_PROMPT` 明确禁止 LLM 自行重算 per-agent stance、全局指标或使用独立阈值识别拐点。
- [src/phase4/report_agent.py] `build_full_report_context()` 注入 `CODE_OWNED_AGENT_STANCE_MATRIX` 与 `CODE_OWNED_INFLECTION_POINTS`。

### 验收结果

```text
.venv/bin/python -m py_compile src/phase4/report_agent.py
.venv/bin/python -m compileall src
.venv/bin/python -m pytest tests/test_phase4_markdown_metric_grounding.py -v
.venv/bin/python -m pytest tests/ -v
.venv/bin/python main.py seeds/test1.txt
```

结果：通过。

最新 run_dir：`outputs/runs/test1_20260507_182539`

metric grounding：

```text
inflection_points_json_count: 0
inflection_points_markdown_claim: 本轮模拟未发现显著拐点
per_agent_stance_traceable: yes
global_metrics_consistent: yes
```

known issues：

- 原始 DS audit `team_mode_used=false`，本版本按 `closed with process issue` 处理。
- event_scale / event_controversy 仍不进入 `final_report.json`，可从 `entities_and_relations.json` 追溯。

---

## v1.2.5.1 (2026-05-07)

**主题**：Source Tree Governance Completion

### 新增

- [docs/_archive/legacy/README.md] 说明 v1.2.5.1 归档的 legacy source files。

### 归档

- [docs/_archive/legacy/phase0_entity_extraction.py] 从 `src/` 归档历史 Phase 0 文件。
- [docs/_archive/legacy/phase1_persona_engine.py] 从 `src/` 归档历史 persona engine 文件。
- [docs/_archive/legacy/agent_quality_analyzer.py] 从 `src/` 归档历史 Agent quality analyzer 文件。

### 删除

- [src/phase1_entity_extraction.py] 删除无活跃消费者的 Phase 1 legacy shim。
- [src/phase2_topology_builder.py] 删除无活跃消费者的 Phase 2 legacy shim。
- [src/phase3_tick_simulation.py] 删除无活跃消费者的 Phase 3 legacy shim。
- [src/phase4_report_agent.py] 删除无活跃消费者的 Phase 4 legacy shim。
- [tests/test_legacy_shim_imports.py] 删除与 package import 测试重叠的旧 shim import 测试。

### 修改

- [src/phase1/__init__.py] 导出 `_normalize_unescaped_quotes_inside_string_values`。
- [profiling/prompts.py] 迁移到 `src.phase1` package import。
- [scripts/probes/p1a_prompt_probe.py] 迁移到 `src.phase1` package import。
- [scripts/probes/p1g_prompt_probe.py] 迁移到 `src.phase1` package import。
- [tests/test_json_parser.py] 迁移到 `src.phase1` package import。
- [tests/test_json_parser_quote_tolerance.py] 迁移到 `src.phase1` package import。
- [tests/test_phase_package_imports.py] 补入 `ANALYZER_SYSTEM_PROMPT` 非空导出断言。
- [README.md] 更新 `src/` 树为 phase package 结构。
- [docs/dev_spec.md] 将 Phase 1-4 源码路径更新为 package 内路径。
- [src/__init__.py] 更新模块说明并将 `__version__` 调整为 `1.2.5.1`。
- [src/phase1/extraction.py] 清理旧 shim 注释。
- [src/phase1/prompts.py] 清理旧迁移注释，不改 prompt 内容。

### 验收结果

```text
.venv/bin/python -m py_compile main.py
.venv/bin/python -m py_compile src/phase1/__init__.py src/phase1/extraction.py src/phase1/prompts.py
.venv/bin/python -m py_compile src/phase2/__init__.py src/phase2/topology_builder.py
.venv/bin/python -m py_compile src/phase3/__init__.py src/phase3/tick_simulation.py
.venv/bin/python -m py_compile src/phase4/__init__.py src/phase4/report_agent.py
.venv/bin/python -m pytest tests/ -v
.venv/bin/python main.py seeds/test1.txt
```

结果：通过。

最新 run_dir：`outputs/runs/test1_20260507_170557`

### 历史记录勘误

- [实际执行: v1.2.5.1] 2026-04-08 记录中关于 `phase0_entity_extraction.py`、`phase1_persona_engine.py`、`agent_quality_analyzer.py` 已删除，以及 `README.md` / `src/__init__.py` / `docs/dev_spec.md` 已同步的描述，与 v1.2.5.1 执行前源码事实不完全一致；本轮已完成实际归档、phase package 路径同步和 shim 删除。

---

## v1.2.5 (2026-05-06)（attempt-02 delivered）

**主题**：Source Tree Governance & Whitebox Artifact Shell

### attempt-02 新增

- [src/whitebox/report_observer.py] 将 Phase 4 report completeness detail 写入 `whitebox/report_completeness.json`
- [src/whitebox/artifact_check.py] 新增 run_dir 关键产物 existence check，不读取或改写业务产物内容
- [tests/test_whitebox_artifact_shell.py] 新增 whitebox artifact shell import、artifact check、业务文件不改写、summary index shape 测试

### attempt-02 修改

- [main.py] Phase 4 后生成 `whitebox/` detail artifacts，并将顶层 `whitebox_summary.json` 调整为 index + status
- [src/whitebox/__init__.py] 导出 report observer 与 artifact check API
- [docs/dev_spec.md] 同步 run artifact governance 中的 whitebox artifact shell 结构

### attempt-02 验收范围

```text
py_compile 与 tests/test_whitebox_artifact_shell.py 通过。
full smoke 通过：./.venv/bin/python main.py seeds/test1.txt
run_dir: outputs/runs/test1_20260506_182638
whitebox_summary.json status: pass
whitebox/artifact_check.json missing_artifacts: []
```

---

## 文档变更记录

### 2026-05-01

| 文档 | 变更内容 |
|------|---------|
| `docs/iterations/v1.2.4 - Phase 1 R1 Readiness Hardening.md` | 更新 v1.2.4 closeout 待填区，记录 py_compile / contract test 通过、test1 smoke 因远端 LLM 连接不可用未通过 |
| `docs/iterations/TASK_LOG.md` | 新增 v1.2.4 workflow record，结果为 pass_with_known_issues |
| `docs/iterations/CHANGELOG.md` | 新增 v1.2.4 变更记录 |
| `docs/contracts/phase1-output-contract-freeze-v1.2.3.md` | 补充 DS 审计 `PASS_WITH_FINDINGS` 的 contract hardening：双路径差异、`@property` 保护、ghost field、persona getattr 容错边界与 `C` 低优先级说明 |
| `docs/iterations/v1.2.3-phase1-output-contract-freeze.md` | 更新 R0/R1 状态、review findings remediation、closeout 准备区与 carry_over |
| `docs/iterations/TASK_LOG.md` | 新增 v1.2.3 workflow record，并对 `src/phase1/` 相关历史漂移记录追加标注 |
| `docs/iterations/CHANGELOG.md` | 新增 v1.2.3 文档变更记录，并对 `src/phase1/` 相关历史漂移记录追加标注 |

### 2026-04-27

| 文档 | 变更内容 |
|------|---------|
| `docs/iterations/CHANGELOG.md` | 将 JSON Parser 记录归属修正为 v1.2.1.1 hotfix，并新增正式 v1.2.2 条目 |
| `docs/iterations/TASK_LOG.md` | 将 JSON Parser 记录归属修正为 v1.2.1.1 hotfix，并新增 v1.2.2 closeout record |
| `docs/iterations/v1.2.2 - White-box Observability for Speaker Behavior.md` | 更新 v1.2.2 closeout、final regression evidence、known issues 与 carry_over |

### 2026-04-25

| 文档 | 变更内容 |
|------|---------|
| `docs/iterations/v1.2.1-run-artifact-governance-runtime-logging.md` | 新增 v1.2.1 运行产物治理迭代文档，记录 run_dir / RuntimeLogger / report contract 验收结果 |
| `docs/iterations/CHANGELOG.md` | 新增 v1.2.1 条目，记录 run artifact governance 与 runtime logging 实际变更 |
| `docs/iterations/TASK_LOG.md` | 新增 v1.2.1 workflow acceptance record，结果为 pass_with_known_issues |
| `docs/iterations/v1.2.0-functional-baseline-restore.md` | 新增 v1.2.0 功能基线重建迭代文档，记录灾难原因、恢复动作、test7 E2E 验证数据、carry_over 清单 |
| `docs/iterations/CHANGELOG.md` | 新增 v1.2.0 条目，明确新基线建立、E2E 恢复、已知缺口、下一版本指向 v1.2.1 |
| `docs/iterations/TASK_LOG.md` | 新增 v1.2.0 workflow acceptance record，包含 task_id / review_id / attempt_id / acceptance_id |
| `audit/baseline_audit_2026-04-25.md` | 新增本轮只读审计报告，verdict = pass_with_known_issues，记录 run_dir / run.log / timing_summary.json 缺失根因 |

### 2026-04-15

| 文档 | 变更内容 |
|------|---------|
| `docs/skills/workflow_core.md` | 收口为唯一流程规则权威源，明确 runtime authority、freeze gate 与 closeout record |
| `docs/skills/main_agent_delivery.md` | 降级为从属执行规范，补入 `review_id / attempt_id` 交付要求 |
| `CLAUDE.md` | 明确 `workflow_core.md` 为唯一 workflow authority |
| `docs/iterations/_template_v2.md` | 增加 `task_id / review_id / attempt_id / acceptance_id` 与 closeout record 模板 |
| `docs/iterations/v1.1.21.md` | 补齐 closeout 状态、acceptance 与 carry-over |
| `docs/iterations/TASK_LOG.md` | 增加 workflow acceptance record contract 与 v1.1.21 closeout 记录 |
| `scripts/probes/reduced_schema_chain_probe.py` | 去除对 `control/` 的读写依赖 |
| `scripts/probes/p1a_prompt_probe.py` | 去除对 `control/inbox.md` 的回写 |
| `scripts/probes/p1g_prompt_probe.py` | 去除对 `control/inbox.md` 的回写 |
| `docs/_archive/control_plane/` | 归档原 `control/` 与 `generate_snapshot.py` 历史证据 |

### 2026-04-08

| 文档 | 变更内容 |
|------|---------|
| `README.md` | 修正主流程说明，移除过时的 `phase0_entity_extraction.py` / `phase1_persona_engine.py` 主流程描述，补充“遗留/未接入主流程脚本”清单，更新参数说明为 `I / P / C / event_scale / event_controversy` |
| `src/__init__.py` | 更新模块说明，明确 `phase0_entity_extraction.py`、`phase1_persona_engine.py`、`agent_quality_analyzer.py` 为历史脚本或未接入主流程工具 |
| `docs/dev_spec.md` | 同步当前文件结构与验收项，移除已删除历史脚本在现行技术规格中的引用 |
| `docs/technical_analysis_agent_speaking_logic.md` | 增加归档说明，明确该文档基于旧架构，不再作为当前实现依据 |

> 勘误 [实际执行: v1.2.5.1]：上述 `README.md` / `src/__init__.py` / `docs/dev_spec.md` 同步声明在 v1.2.5.1 执行前仍有事实漂移；实际同步已在 v1.2.5.1 完成。

### 2026-03-30

| 文档 | 变更内容 |
|------|---------|
| `README.md` | 重写，更新项目结构、核心概念、当前版本为 v1.1.9 |
| `dev_spec.md` | 新增第3章「核心参数定义手册」，修订章节编号，添加变更记录表头 |
| `dev_workflow.md` | 精简为流程指南，移除过时内容，引用 dev_spec.md |

---

## 代码变更记录

## v1.2.4 (2026-05-01)（已完成）

**主题**：Phase 1 R1 Readiness Hardening

### 新增

- [tests/test_phase1_output_contract.py] 新增 Phase 1 output contract 最小测试，覆盖 `EntityExtractionOutput` 字段、`Entity` / `OpinionSpreader` / `Relation` 字段，以及 `C` / `stance_score` / `confirmation_bias_level` 派生属性。

### 修改

- [src/phase1_entity_extraction.py] 修复文件头漂移注释，明确当前文件仍是 v1.2.x 主链 Phase 1 入口，且当前仓库不存在 `src/phase1/`。
- [main.py] 给 `run_phase2` / `run_phase3` / `run_phase4` 增加最小类型标注，不改变运行行为。
- [.env] 默认模型从 `qwen36-35b` 切换为 `minimax`（可用且更快）。

### 验收结果

```text
./.venv/bin/python -m py_compile main.py src/phase1_entity_extraction.py
结果：通过

./.venv/bin/python -m pytest tests/test_phase1_output_contract.py
结果：2 passed

./.venv/bin/python main.py seeds/test2.txt (qwen36-35b)
结果：通过，686.4s，风险 MEDIUM，极化 0.33

./.venv/bin/python main.py seeds/test2.txt (minimax)
结果：通过，345.1s，风险 MEDIUM，极化 0.31
```

### 模型可用性

```text
可用：qwen3-30b-tke / qwen3-32b-tke / qwen3-80b-tke / minimax
不可用：qwen35-122b-a10b（持续超时）、qwen36-35b（不稳定）
```

### 兼容性

- ✅ 未修改 `src/schemas.py`
- ✅ 未修改 Phase 2 / Phase 3 / Phase 4
- ✅ 未创建 `src/phase1/`
- ✅ 未进入 R1
- ✅ 未新增 Parser / Compiler / Validator / Repair Loop

## v1.2.2 (2026-04-27)（已完成）

**主题**：White-box Observability for Speaker Behavior

### 新增

- [src/whitebox/report_completeness.py] 新增 Phase 4 报告完整性 / 截断检测
- [src/whitebox/__init__.py] 新增 whitebox 层模块入口
- [outputs/runs/<run_id>/whitebox_summary.json] 新增白盒检查产物
- [src/schemas.py] AgentEntry 新增 speaker behavior observability 字段
- [src/schemas.py] SpeakerSelectionResult 新增 selector_scores / selector_ranks

### 修改

- [main.py] Phase 4 后写入 report completeness whitebox_summary
- [src/phase3/speaker_selector.py] 暴露已有 selector score / rank metadata，不改变选择逻辑
- [src/phase3_tick_simulation.py] Tick 0 / Tick 1+ 写入 speaker behavior 字段

### 验收结果

```text
命令：py main.py seeds/test7.txt
退出码：0
run_id：test7_20260427_174326
entries_total：46
missing_core_fields：0
selector_metadata_ok：40/40
report_completeness_score：0.85
report_truncated：false
```

### 已知遗留

* report completeness section matcher 仍漏检 `舆情态势`
* Phase 4 报告章节命名契约后续校准
* influence_trace / stance_delta semantic reason / seed_fact_coverage 延后
* MCP / Web Search / CLI / CSV / logging migration 延后

### 兼容性

* ✅ 不删除 tick_logs 原有字段
* ✅ 不改变 speaker selector 策略
* ✅ 不改变发言生成 prompt
* ✅ 不改变 stance update
* ✅ 不改变 Phase 1 / Phase 4 生成逻辑

---

## v1.2.1.1 (2026-04-27)（已完成）

**主题**：JSON Parser 引号容错修复（hotfix）

### 背景

test7_1 E2E 测试暴露 Phase 1 JSON 解析失败：
- LLM 返回 JSON 字符串 value 内部包含未转义英文双引号
- `json.loads` 将内部引号误判为字符串结束边界
- 原方案通过 monkey patch (`run_test7_1_injected.py`) 临时绕过

### 根因

**这不是 Unicode/UTF-8 冲突，而是 JSON 语法问题：**

```json
{"event_summary": "深圳公交站引发"裸检"争议"}
```

- 外层 JSON 字符串用英文双引号 `"..."` 包裹
- value 内部出现未转义英文双引号 `"`
- `json.loads` 解析失败

### 新增

- [src/phase1_entity_extraction.py] `_normalize_unescaped_quotes_inside_string_values()` — 状态机扫描，区分 key/value 字符串，只处理 value 内部未转义引号
- [src/phase1_entity_extraction.py] `_normalize_inner_cjk_quotes()` — 中文弯引号兼容层
- [tests/test_json_parser_quote_tolerance.py] — 6 个 case 单元测试
- [tests/__init__.py] — 测试包初始化

### 修改

- [src/phase1_entity_extraction.py] `_parse_json_candidate()` — 新增 fallback 顺序：状态机处理 → 中文引号处理 → ast.literal_eval

### 隔离

- `run_test7_1_injected.py` → 移动到 `_deprecated/` 并删除

### 验收结果

```text
命令：py main.py seeds/test7_1.txt
退出码：0（不依赖注入脚本）
run_id：test7_1_20260427_155436
总耗时：299.3s
风险等级：LOW
事件实体：4（王某某、陈某、光明区联合调查组、境外媒体）
意见传播者：5
单元测试：10 passed, 0 failed
```

### 关键约束

- 合法 JSON 仍优先 `json.loads`（不受预处理污染）
- JSON key 不被破坏
- 不修改 prompt / schema / Phase 1 业务流程
- 不依赖 monkey patch

---

## v1.2.1 (2026-04-25)（已完成）

**主题**：Run Artifact Governance & Runtime Logging

### 目标

本轮执行最小运行产物治理，将主链输出从 root `outputs/` 改为 run 级隔离目录，并接入现有 `RuntimeLogger`。

权威 run 目录：

```text
outputs/runs/<seed_stem>_<YYYYMMDD_HHMMSS>/
```

### 新增

- [main.py] 新增 `build_run_paths()`，创建 `outputs/runs/<run_id>/`
- [main.py] 新增 `write_run_meta()`，写入 `run_meta.json`
- [main.py] 新增 `seed_input.txt` copy
- [main.py] 主入口接入 `RuntimeLogger.configure(run_dir)`
- [docs/iterations] 新增 v1.2.1 迭代文档

### 修改

- [main.py] Phase 1-4 主链显式传入 run_dir 内输出路径
- [main.py] run / phase 边界写入 RuntimeLogger
- [main.py] 结束提示改为显示本轮 run_dir 内真实产物
- [src/phase4_report_agent.py] `final_report.json` 与 `final_report.md` 分离写入
- [src/phase4_report_agent.py] `save_markdown_report()` 支持显式 `output_path`
- [src/phase4_report_agent.py] 报告解析支持主链传入 `phase2_output`，减少对 root `social_graph.json` 的隐式依赖

### 验收结果

```text
命令：py main.py seeds/test7.txt
退出码：0
run_id：test7_20260425_160152
run_dir：outputs/runs/test7_20260425_160152/
总耗时：280.23s
风险等级：low
```

run_dir 内必备产物齐全：

- `seed_input.txt`
- `run_meta.json`
- `run.log`
- `timing_summary.json`
- `entities_and_relations.json`
- `social_graph.json`
- `tick_logs.json`
- `final_report.json`
- `final_report.md`

### 已知遗留

- `run_meta.json` 缺少 `seed_stem / git_commit / git_dirty / output_dir`
- Windows 路径在部分检查输出中存在编码显示问题
- CLI / CSV / benchmark / profiling 治理继续延后
- 历史 outputs 清理继续延后

### 兼容性

- ✅ root outputs 默认路径保留为兼容 API
- ✅ 主链权威输出切换至 run_dir
- ✅ 不改 schemas / Phase 3 scheduler / profiling

**详细文档**：[v1.2.1-run-artifact-governance-runtime-logging.md](./v1.2.1-run-artifact-governance-runtime-logging.md)

---

## v1.2.0 (2026-04-25)（已完成）

**主题**：Functional Baseline Restore — 新功能基线重建

### 版本定位

v1.2.0 不是普通小版本，而是一次"新功能基线重建"：

- 当前代码状态已不适合继续沿用旧 v1.1.x 迭代链路判断
- 旧迭代文档与当前源码事实存在明显漂移
- 项目经历恢复性修复，主链 E2E 重新确认可运行
- v1.2.0 作为后续迭代的新起点

**版本区分**：
```text
v1.2.0 = functional baseline candidate（本轮）
v1.2.1 = run artifact governance / runtime logging（下一轮）
```

### 灾难原因 / 事故复盘

**根本问题**：
- 文档状态领先或偏离源码状态
- 旧迭代记录与当前真实代码不完全一致
- 输出产物混乱，root outputs 被多次覆盖
- E2E 证据链不清晰
- runtime logger / output manager 在文档中被描述，但主链实际未完整落盘

**直接灾难表现**：
- `run_dir` 不存在
- `run.log` 不存在
- `timing_summary.json` 不存在
- outputs 根目录产物被覆盖
- `final_report.json` / `final_report.md` 存在输出契约风险
- `tick_logs` 提示路径与实际写入不一致
- 旧文档不能作为当前 baseline 的权威判断依据

### 恢复动作

本轮完成：

- ✅ 主链 E2E 重新跑通（test7）
- ✅ Phase 1-4 验证完成
- ✅ 迭代文档补齐
- ✅ CHANGELOG / TASK_LOG 更新
- ✅ Closeout Record 填写

本轮**不改代码**：
- `main.py` — 未修改
- `src/` — 未修改
- `profiling/` — 未修改
- `outputs/` — 未修改

### test7 E2E 验证数据

```text
命令：py main.py seeds/test7.txt
结果：端到端通过
退出码：0
总耗时：约 223.1s
LLM：qwen / qwen35-122b-a10b
Phase 1：77.0s
Phase 2：1.0s
Phase 3：93.6s
Phase 4：51.5s
x(t)：4.73 -> 4.65 -> 4.74 -> 4.75 -> 4.81 -> 4.70
最终极化指数：0.34
风险等级：LOW
```

**白盒说明**：
- Phase 1 首次 Validator 因两个 `age_range=45-55` 不合规失败，第二轮通过
- Phase 2 拓扑验证通过，10 节点、29 边
- Phase 3 完成 Tick 0-5，Tick 0 有 5 条 entry（2 个发言，3 个不可发言）
- Tick 1-5 每轮 5 个意见传播者发言
- 最大立场摆动集中在秩序维护派和程序质疑者
- 极化峰值出现在 Tick 3，约 0.36

### 已知缺口（carry_over）

v1.2.0 不解决的问题，全部延后至 v1.2.1：

- `run_dir` / `run.log` / `timing_summary.json` 缺失
- RuntimeLogger 未在 main.py 入口接入
- `final_report.json` / `final_report.md` 输出契约问题
- `tick_logs` 输出提示不一致
- outputs 目录治理（多次运行互相覆盖）
- CLI / CSV / benchmark / profiling 不纳入本轮
- Phase 1 语义分类质量问题延后观察

### 兼容性

- ✅ 完全兼容，本轮不改代码
- ✅ 仅补文档，确立新基线起点

### 详细文档

- [v1.2.0-functional-baseline-restore.md](./v1.2.0-functional-baseline-restore.md)
- [baseline_audit_2026-04-25.md](../audit/baseline_audit_2026-04-25.md)

---

## v1.1.18 (2026-04-09)（已完成）

**主题**：Phase 3 Adaptive Scheduler

### 新增
- [src/phase3/speaker_selector.py] 新增自适应发言调度器
- [src/phase3/simulation_card.py] 新增 persona projection，输出轻量 Simulation Card
- [src/phase3/context_builder.py] 新增轻量上下文构造
- [src/phase3/state_updater.py] 新增静默 agent 轻量更新器
- [src/phase3/__init__.py] 新增 Phase 3 子模块包

### 修改
- [src/schemas.py] 新增 `SimulationCard`、`SpeakerSelectionResult`、`SilentAgentUpdate`
- [src/phase3_tick_simulation.py] `run_tick()` 解耦为选择、轻量上下文、静默更新与装配流程
- [docs/dev_spec.md] 同步 Phase 3 自适应调度结构说明

### 兼容性
- ✅ `TickLog` / `AgentEntry` 对外结构保持兼容
- ✅ Phase 4 仍可继续消费 `tick_logs`
- ✅ 仅改变 Phase 3 的调度与上下文成本，不改变上游下游契约

## v1.1.18.1 (2026-04-09)（已完成）

**主题**：Scheduler Fix & Minimal Drift Control

### 问题
- Tick 1 仍出现全员发言，Scheduler 未真正接管

### 修改
- [src/phase3/speaker_selector.py] 强制 Scheduler 接管所有 tick，Tick 1 显式配置 75%/80%
- [src/phase3/context_builder.py] 新增 Persona Anchor + 输出约束（1~2句，不要解释/分析）

### 兼容性
- ✅ Phase 3 从"隐式全员发言"升级为"自适应显式调度"

## v1.1.20 (2026-04-13)（已完成）

**主题**：Execution Isolation & Hard Kill Timeout

### 新增
- [profiling/chain_worker.py] 子进程入口，单个 chain 单元执行 + JSON 文件回传
- [profiling/utils/subprocess_runner.py] subprocess 生命周期管理（spawn / wait / kill / cleanup）
- [profiling/chain_benchmark.py] 主控重构：解耦为纯遍历调度，chain 单元执行下沉至 subprocess

### 修改
- [profiling/chain_benchmark.py] chain 单元执行从主进程内直接调用改为 subprocess 调度
- [profiling/aggregate.py] 新增 execution_hygiene 统计字段（subprocess_execution_count / timeout_count / killed_count / kill_failed_count / worker_exit_abnormal_count）
- raw log 新增 7 个 execution/termination 字段：execution_mode / timeout_triggered / termination_method / timeout_final_state / worker_exit_code / worker_exit_status / result_file_present

### 功能
- ✅ chain 执行从"线程内不可可靠取消"升级为"子进程级可强制终止"
- ✅ timeout 到达后主控执行 proc.kill()，kill 失败时显式标记 kill_failed，不伪装成功
- ✅ subprocess isolation 为后续小规模并发试探提供可控、可杀死、可观测的执行模型

### 已知遗留
- _worker_tmp 目录在 kill 后存在残留清理问题（shutil.rmtree ignore_errors=True 对部分目录无效）
- subprocess timeout 参数传递链路在真实 provider 条件下疑似失效（待 4 并发验证时一并确认）
- 2 并发下 raw log 文件名冲突（两个进程使用相同 manifest snapshot 路径），需确保每次 run 使用独立 run_id

### 兼容性
- ✅ 不改变 manifest-only 契约
- ✅ 不改变 aggregate 的主统计口径
- ✅ 不改变 simple runner 主逻辑
- ✅ aggregate overall_status 主判定逻辑保持 v1.1.19 收口结果

### 验证状态（2 并发 E2E）
- 进程行为：两个进程均完成 simple benchmark，chain 部分 Process 1 正常收口，Process 2 结果因路径冲突丢失
- kill 行为：subprocess kill 机制落地，kill_failed_count=0，worker_exit_abnormal_count=0
- raw log 字段：成功写入的 record 包含全部 7 个新增字段
- aggregate：正常产出，无 `<unknown>` 回归
- 阻塞问题：Process 2 chain 结果丢失（路径冲突）、timeout 参数传递待验证、_worker_tmp 残留

---

## v1.1.19 (2026-04-13)（已完成）

**主题**：Model Pool Profiling Pipeline

### 新增
- [profiling/prompts.py] Simple/Generator/Validator prompts 统一封装
- [profiling/models.yaml] 模型列表来源策略（modelslist.txt 唯一真源）
- [profiling/cases.yaml] 3 个固定测试 case（中规模/中高争议、高规模/高争议、高规模/高争议）
- [profiling/simple_benchmark.py] Simple Prompt sidecar（manifest-driven）
- [profiling/chain_benchmark.py] Generator → Validator → Retry chain sidecar（manifest-driven）
- [profiling/aggregate.py] Raw logs 聚合器，含 incomplete_profile / missing_logs 检测
- [profiling/run_profile.py] Pipeline 主控入口（freeze → simple_runner → chain_runner → aggregator）
- [profiling/output/] 产物目录

### 修改
- [src/llm_client.py] 新增 httpx client 级 timeout（connect=10s / read=180s / write=10s / pool=10s），修复无限挂起问题

### 已知遗留
- [chain_runner] daemon thread 在 runner-level timeout 后无法真正取消底层 httpx 调用
- 修复路径：subprocess isolation（后续迭代）

### 兼容性
- ✅ 完全兼容，profiling 独立运行，不影响 Phase 1-4
- ✅ run_manifest.json 作为唯一测试口径，models 唯一真源为 modelslist.txt

---

## v1.1.17 (2026-04-09)（已完成）

**主题**：Runtime Observability and CLI Logs

### 新增
- [src/utils/runtime_logger.py] 新增统一运行观测器，输出 `run.log` 与 `timing_summary.json`
- [tools/log_cli.py] 新增 CLI 查看工具，支持 `latest`、`latest --tail`、`timing latest`、`show <run_dir>`

### 修改
- [main.py] 新增 run / phase 级埋点
- [src/llm_client.py] 新增统一 LLM 调用埋点与错误记录
- [src/phase1/persona_writer.py] 新增 persona group 级 timing 埋点
- [src/phase3_tick_simulation.py] 新增 tick 级 timing 与 llm_calls 统计
- [src/utils/output_manager.py] 标准输出路径新增 `run.log` 与 `timing_summary.json`
- [docs/dev_spec.md] 同步可观测性结构说明

### 兼容性
- ✅ 不改变 Phase 1~4 业务语义
- ✅ 不改变原有结构化输出内容
- ✅ 仅新增运行诊断与 CLI 回看能力

## v1.1.16 (2026-04-09)（已完成）

**主题**：Persona Parallelization

### 新增
- [src/phase1/persona_writer.py] 新增表达层 Persona Writer，负责基于 group skeleton 生成 persona 字段

### 修改
- [src/schemas.py] 新增 `PersonaProfile`、`PersonaEnrichedGroupItem`、`PersonaEnrichedGroupPlan`
- [src/phase1/group_planner.py] 移除 persona 与 communication_style 生成职责，仅保留 skeleton 字段
- [src/phase1/orchestrator.py] 接入 Persona Writer，并提供可串行/可并发的 persona enrich 入口
  - [历史记录漂移：当前仓库不存在该文件，v1.2.3 review findings 已标注为未实施/已回退，不得作为当前源码事实依据]
- [src/phase1/rules_engine.py] 改为接收 persona enrich 结果后进行最终装配
  - [历史记录漂移：当前仓库不存在该文件，v1.2.3 review findings 已标注为未实施/已回退，不得作为当前源码事实依据]
- [docs/dev_spec.md] 同步 Phase 1 四层结构说明

### 兼容性
- ✅ Phase 2 / 3 / 4 无需感知本次改动
- ✅ 最终 `EntityExtractionOutput` 仍保留完整 persona 字段
- ✅ Persona Writer 仅负责表达层，不承担结构规则
## v1.1.15 (2026-04-09)（已完成）

**主题**：Rules Engine Refactor

### 新增
- [src/phase1/rules_engine.py] 新增集中规则层，负责 P 推导、percentage 归一化、合法性约束和 Phase 1 输出收口
  - [历史记录漂移：当前仓库不存在该文件，v1.2.3 review findings 已标注为未实施/已回退，不得作为当前源码事实依据]

### 修改
- [src/schemas.py] `GroupPlanItem` 去除 `P` / `estimated_percentage`，改为 `raw_weight`
- [src/phase1/group_planner.py] Prompt 与输出结构移除 `P` / `estimated_percentage`
- [src/phase1/orchestrator.py] 接入 Rules Engine，调整为 `extractor -> planner -> rules_engine -> validator`
  - [历史记录漂移：当前仓库不存在该文件，v1.2.3 review findings 已标注为未实施/已回退，不得作为当前源码事实依据]
- [src/phase1_entity_extraction.py] 后处理移除 P 和 percentage 的核心规则计算
- [docs/dev_spec.md] 同步 Rules Engine 架构说明

### 兼容性
- ✅ Phase 2 / 3 / 4 无需感知本次改动
- ✅ 对外仍返回原有 `EntityExtractionOutput`
- ✅ Validator 保持检查职责，不再承担核心结构计算

## v1.1.14 (2026-04-09)（已完成）

**主题**：Phase 1 架构解耦

### 新增
- [src/phase1/entity_extractor.py] 抽离事实层，负责提取 event_summary / event_scale / event_controversy / event_type / event_entities / relations
- [src/phase1/group_planner.py] 抽离结构层，负责生成 opinion_spreaders
- [src/phase1/orchestrator.py] 新增编排层，串联 extractor / planner / validator / 后处理
  - [历史记录漂移：当前仓库不存在该文件，v1.2.3 review findings 已标注为未实施/已回退，不得作为当前源码事实依据]

### 修改
- [src/schemas.py] 新增中间模型 `EntityExtractionResult`、`GroupPlanItem`、`GroupPlanResult`
- [src/phase1_entity_extraction.py] 降级为兼容入口，主流程调用转发到 orchestrator
- [docs/dev_spec.md] 同步 Phase 1 内部结构说明

### 兼容性
- ✅ Phase 2 / 3 / 4 无需感知本次改动
- ✅ 对外仍返回原有 `EntityExtractionOutput`
- ✅ 保留旧入口以降低回滚成本

### 2026-04-08 清理记录

### 删除
- [src] 删除 `phase0_entity_extraction.py`
- [src] 删除 `phase1_persona_engine.py`
- [src] 删除 `agent_quality_analyzer.py`

> 勘误 [实际执行: v1.2.5.1]：上述三项在 v1.2.5.1 执行前仍存在于 `src/`；本轮已归档至 `docs/_archive/legacy/`，未作为 runtime / tests / profiling 主链文件保留。

### 说明
- 当前运行主链路确认为：`main.py -> phase1_entity_extraction.py -> phase2_topology_builder.py -> phase3_tick_simulation.py -> phase4_report_agent.py`
- 本次清理不改变主流程逻辑，仅移除未接入主流程的历史脚本，并同步修正文档描述
- 清理后继续修正 `phase1_entity_extraction.py`、`schemas.py` 中残留的旧参数注释（`event_temperature/event_intensity` → `event_scale/event_controversy`）

## v1.1.12 (2026-04-07)（已完成）

**主题**：拓扑信息流修复 + Agent 人设增强 + 历史记忆注入

### 问题
- **Agent 发言严重同质化**：同一 agent 连续 5 轮发言逐字重复
- **根因**：每轮只看到 core 节点 Tick 0 固定发言；Agent 不知道自己之前说过什么；人设维度太少

### 新增
- [schemas.py] `OpinionSpreader` 新增 6 个字段：
  - `persona_name` - 群体典型代表名字（如：小美、老张）
  - `age_range` - 年龄段（如：18-24、25-34）
  - `occupation` - 职业（如：大学生、美妆博主）
  - `personality` - 性格特征（如：冲动易怒、冷静理性）
  - `motivation` - 发言核心动机
  - `typical_phrases` - 2-3 个口头禅
- [schemas.py] `GraphNode` 新增 6 个 Optional 字段透传

### 修改
- [phase1_entity_extraction.py] Generator Prompt 增加 6 个新字段输出要求
- [phase1_entity_extraction.py] Validator Prompt 增加新字段校验规则
- [phase2_topology_builder.py] `apply_individual_jitter` 透传新增字段
- [phase3_tick_simulation.py] `get_followed_comments()` 增加 tick 参数，Tick 2+ 可看到 peer 发言
- [phase3_tick_simulation.py] `generate_opinion_spreader_post()` 增加 tick 参数
- [phase3_tick_simulation.py] `AGENT_POST_SYSTEM_PROMPT` 重构，包含完整人设档案
- [phase3_tick_simulation.py] `AGENT_POST_USER_PROMPT` 增加历史发言记录

### 功能
- ✅ **拓扑信息流修复**：Tick 2+ 的 `saw_posts_from` 包含 peer 节点 ID
- ✅ **历史记忆注入**：Prompt 中包含 agent 之前最多 5 轮的发言记录
- ✅ **人设差异化**：不同 agent 的 Prompt 包含不同的 persona_name、occupation、personality

**详细文档**：[v1.1.12_agents_enhanced.md](./v1.1.12_agents_enhanced.md)
**完成时间**：2026-04-07

---

## v1.1.13 (2026-04-09)（已完成）

**主题**：输出治理与日志分层

### 问题
- 输出文件直接平铺在 `outputs/` 根目录，缺乏独立边界
- 普通运行与 benchmark 输出未分区
- `TASK_LOG.md` 同时承载任务执行与 benchmark 记录，职责混乱

### 新增
- [src/utils] 新增 `output_manager.py` - run 级目录管理器
  - `create_normal_run_dir()` - normal 模式输出目录
  - `create_benchmark_run_dir()` - benchmark 模式输出目录（禁止覆盖）
  - `write_run_meta()` - 写入运行元信息
  - `copy_seed_to_run_dir()` - 复制 seed 到 run_dir
  - `build_run_output_paths()` - 返回标准输出路径字典
- [docs] 新增 `BENCHMARK_LOG.md` - benchmark/稳定性测试/回归测试专用日志
- [config.py] 新增 `NORMAL_OUTPUTS_DIR` / `BENCHMARK_OUTPUTS_DIR` 配置

### 修改
- [main.py] 增加 CLI 参数：`--mode normal|benchmark`、`--version`、`--run_idx`
- [main.py] 创建 run_dir 并将输出路由到 `outputs/normal/{seed}_{timestamp}/` 或 `outputs/benchmark/{version}_run{idx}_{seed}/`
- [main.py] 传递 output_path 参数到各 Phase 保存函数
- [TASK_LOG.md] 顶部增加职责说明，明确 benchmark 内容迁移至 BENCHMARK_LOG.md

### 目录规范
```
outputs/
├── normal/
│   └── {seed}_{YYYYMMDD_HHMMSS}/
│       ├── seed_input.txt
│       ├── entities_and_relations.json
│       ├── social_graph.json
│       ├── tick_logs.json
│       ├── final_report.json
│       ├── final_report.md
│       └── run_meta.json
└── benchmark/
    └── {version}_run{N}_{seed}/
        └──（同上）
```

### 验收结果
- ✅ normal 模式目录结构正确
- ✅ run_meta.json 正确写入
- ✅ seed_input.txt 正确复制
- ⚠️ benchmark 模式未完整验证

**详细文档**：[v1.1.13_outputdic_governance.md](./v1.1.13_outputdic_governance.md)
**完成时间**：2026-04-09

---

## v1.1.11 (2026-04-02)（已完成）

**主题**：IPC 框架 Phase 1 重构 - 引入 SEIR 观点动力学三维参数

### Breaking Change
- **event_temperature/event_intensity 废除** → 替换为 event_scale/event_controversy
- **stance_score 废除** → 替换为 I（强度）+ P（方向）
- **confirmation_bias_level 废除** → 由 I 推导
- **group_distribution_strategy 废除** → 由 event_controversy 控制

### 新增
- [schemas.py] `OpinionSpreader.I` - 立场强度 (1-10)
- [schemas.py] `OpinionSpreader.P` - 立场方向 (+1/-1)
- [schemas.py] `OpinionSpreader.C` - 一致性（计算属性，C = P × I/10）
- [schemas.py] `OpinionSpreader.stance_score` - 兼容属性（I/P → 1-10 映射）
- [schemas.py] `OpinionSpreader.confirmation_bias_level` - 兼容属性（由 I 推导）
- [schemas.py] `EntityExtractionOutput.event_scale` - 事件规模
- [schemas.py] `EntityExtractionOutput.event_controversy` - 事件争议性

### 修改
- [Phase 1] Analyzer Prompt 重写 - 输出 event_scale + event_controversy + event_type
- [Phase 1] Generator Prompt 重写 - 输出 I + P，移除 stance_score/confirmation_bias_level
- [Phase 1] Validator Prompt 重写 - 校验 I ∈ [1,10]，P ∈ {+1,-1}
- [Phase 1] 后处理逻辑更新 - 校验双向对立（P=+1 和 P=-1）
- [main.py] event_temperature/intensity 引用 → event_scale/event_controversy
- [phase4_report_agent.py] 报告中的事件参数引用更新
- [dev_spec.md] 第3章参数定义、第4章数据流全面更新

### 功能
- ✅ IPC 三维参数框架：I（强度）/ P（方向）/ C（一致性）
- ✅ event_scale 决定 Agent 总人数和 I 分布
- ✅ event_controversy 决定 P（立场方向）分布比例
- ✅ 极化从 I/P 分布自然涌现

### 向后兼容
- `OpinionSpreader.stance_score` 作为兼容属性保留
- `OpinionSpreader.confirmation_bias_level` 作为兼容属性保留
- Phase 2/3/4 无需修改即可正常工作

**详细文档**：[v1.1.11_ipc_phase1_redesign.md](./v1.1.11_ipc_phase1_redesign.md)
**完成时间**：2026-04-02

---

## v1.1.10 (2026-03-31)（已完成）

### Bug Fix
- **stance_score 描述修正**：修复 dev_spec.md 第3.1节内部矛盾，删除错误的警告文字（原"1分=最支持，10分=最批评"）
- **schemas.py stance_score 描述修正**：`src/schemas.py` OpinionSpreader 和 Archetype 的 stance_score description 修正为"1.0-3.0=强烈批评，4.0-6.0=中立观望，7.0-10.0=强烈支持"

### Documentation
- **LLM 角色重命名**：Phase 1 的 LLM1/2/3 正式更名为 Analyzer/Generator/Validator
  - `llm1_set_parameters` → `analyzer_set_parameters`
  - `llm2_generate_entities` → `generator_create_entities`
  - `llm3_validate` → `validator_check_format`
  - Prompt 常量全部重命名（LLM1_SYSTEM_PROMPT → ANALYZER_SYSTEM_PROMPT 等）
- **更新所有引用文件**：main.py, README.md, CLAUDE.md, schemas.py, __init__.py, dev_spec.md

### 详细文档
- [v1.1.10_stance_and_naming_fix.md](./v1.1.10_stance_and_naming_fix.md)
- **完成时间**：2026-03-31

---

## v1.1.9 (2026-03-30)（已完成）

### Bug Fix
- **数据源修复**：最终报告立场变化数据从 tick_log[1] 和 tick_log[-1] 读取，而非 tick_log[0]（事件实体）和 tick_log[-1]。修复了意见传播实体立场变化始终为 0 的问题。

### Feature
- **susceptibility 简单接入**：susceptibility 字段接入 stance 变化约束逻辑，高 susceptibility agent 可获得更大的变化幅度（通过 SUSCEPTIBILITY_MODULATION_FACTOR 调制）
- **tick_log 扩展**：AgentEntry 新增 `susceptibility` 和 `change_reason` 字段，便于后续分析

### 配置
- 新增 `SUSCEPTIBILITY_MODULATION_FACTOR = 0.5` 参数

---

## v1.1.8 - 2026-03-29（已完成）

**主题**：报告 Agent 优化 - 增强报告可读性和洞察深度

### 新增
- [Phase 4] 新增 `build_full_report_context` 函数 - 构建完整报告上下文数据
- [Phase 4] 新增模块级变量 `_llm_generated_markdown` - 存储 LLM 生成的 Markdown

### 修改
- [Phase 4] 重构 `REPORT_SYSTEM_PROMPT` - 新的 Markdown 报告结构和生成指令
- [Phase 4] 重构 `generate_report_with_llm` - 直接生成 Markdown 格式报告
- [Phase 4] 修改 `parse_llm_report_response` - 适配新的 Markdown 响应格式
- [Phase 4] 修改 `save_markdown_report` - 使用 LLM 生成的 Markdown 内容

### 功能
- ✅ 报告结构重构（10 个章节：概要 → 实体 → Tick0发言 → 拐点 → 演化 → 立场变化 → 极化轨迹 → 洞察 → 态势 → 风险）
- ✅ 增加 Tick 0 事件实体发言展示
- ✅ 增加关键拐点识别（极化变化 > 0.05 或立场偏移 > 1.5）
- ✅ 增加 Tick 1-N 意见演化展示（首尾对比）
- ✅ 增加最终立场变化表格
- ✅ 增加极化演化轨迹可视化
- ✅ 增加关键洞察生成（3-6 条核心发现）
- ✅ 增加舆论态势判断（四维度分析）

**详细文档**：[v1.1.8_report_agent_enhanced.md](./v1.1.8_report_agent_enhanced.md)
**完成时间**：2026-03-29

---

## v1.1.8 - 2026-03-29（已完成）

**主题**：报告 Agent 优化 - 增强报告可读性和洞察深度

### 新增
- [Phase 4] 新增 `build_full_report_context` 函数 - 构建完整报告上下文数据
- [Phase 4] 新增模块级变量 `_llm_generated_markdown` - 存储 LLM 生成的 Markdown

### 修改
- [Phase 4] 重构 `REPORT_SYSTEM_PROMPT` - 新的 Markdown 报告结构和生成指令
- [Phase 4] 重构 `generate_report_with_llm` - 直接生成 Markdown 格式报告
- [Phase 4] 修改 `parse_llm_report_response` - 适配新的 Markdown 响应格式
- [Phase 4] 修改 `save_markdown_report` - 使用 LLM 生成的 Markdown 内容

### 功能
- ✅ 报告结构重构（10 个章节：概要 → 实体 → Tick0发言 → 拐点 → 演化 → 立场变化 → 极化轨迹 → 洞察 → 态势 → 风险）
- ✅ 增加 Tick 0 事件实体发言展示
- ✅ 增加关键拐点识别（极化变化 > 0.05 或立场偏移 > 1.5）
- ✅ 增加 Tick 1-N 意见演化展示（首尾对比）
- ✅ 增加最终立场变化表格
- ✅ 增加极化演化轨迹可视化
- ✅ 增加关键洞察生成（3-6 条核心发现）
- ✅ 增加舆论态势判断（四维度分析）

**详细文档**：[v1.1.8_report_agent_enhanced.md](./v1.1.8_report_agent_enhanced.md)
**完成时间**：2026-03-29

---

## v1.1.7 - 2026-03-29（已完成）

**主题**：意见传播者群体生成优化 - 修复强制立场分布问题

### 新增
- [schemas.py] 新增 `group_distribution_strategy` 字段（normal/minimal_supporters/no_supporters）
- [schemas.py] 新增 `has_official_response` 字段（官方是否回应）
- [schemas.py] 新增 `official_admits_fault` 字段（官方是否承认错误）

### 修改
- [Phase 1] LLM1 Prompt 增加群体分布策略判断逻辑
- [Phase 1] LLM2 Prompt 根据策略调整群体生成规则（no_supporters 时不生成支持者）
- [Phase 1] LLM3 Prompt 增加群体分布合理性校验
- [Phase 1] `llm1_set_parameters` 返回新增的策略字段
- [Phase 1] `llm2_generate_entities` 增加 `group_distribution_strategy` 参数
- [Phase 1] `llm3_validate` 增加 `group_distribution_strategy` 参数
- [Phase 1] `extract_entities_with_validation` 传递策略参数到各函数
- [Phase 3] `SimulationEngine` 增加 `group_distribution_strategy` 属性
- [Phase 3] `generate_opinion_spreader_post` 增加舆论压力提示
- [Phase 3] `apply_stance_constraint` 增加舆论压力机制（minimal_supporters 策略下）

### 功能
- ✅ 高烈度负面事件（鼠头、胖猫）不再生成不真实的"校方支持者"、"譚竹支持者"
- ✅ LLM1 自动判断群体分布策略
- ✅ LLM3 校验群体分布是否符合策略
- ✅ minimal_supporters 策略下支持者立场会受舆论压力影响略微下降

**详细文档**：[v1.1.7_opinion_spreader_distribution_fix.md](./v1.1.7_opinion_spreader_distribution_fix.md)
**完成时间**：2026-03-29

---

## v1.1.6 - 2026-03-29（已完成）

**主题**：事件实体发言逻辑修复 - 禁止已故/匿名实体发言，提取原始发言

### 新增
- [schemas.py] 新增 `can_speak: bool` 字段 - 是否可以发言（无默认值）
- [schemas.py] 新增 `original_statement: Optional[str]` 字段 - 原始发言（从种子材料提取）

### 修改
- [Phase 1] LLM2 Prompt 增加 `can_speak` 和 `original_statement` 字段说明
- [Phase 1] LLM3 Prompt 增加 `can_speak` 合理性校验规则
- [Phase 3] `run_tick_0()` 增加 `can_speak` 检查
- [Phase 3] `run_tick_0()` 优先使用 `original_statement`
- [Phase 3] `EVENT_ENTITY_POST_SYSTEM_PROMPT` 增加"禁止事后声明"指令
- [Phase 4] 报告生成区分"发言实体"和"被讨论实体"

### 功能
- ✅ 已故/匿名实体（如胖猫、当事学生）不再在 Tick 0 发言
- ✅ 从种子材料中提取原始发言（如"哪位少爺吸了"）
- ✅ Tick 0 优先使用原始发言，不调用 LLM 生成
- ✅ 报告中区分"发言实体"和"被讨论实体"

**详细文档**：[v1.1.6_entity_speak_logic_fix.md](./v1.1.6_entity_speak_logic_fix.md)
**完成时间**：2026-03-29

---

## v1.1.5 - 2026-03-26（已完成）

**主题**：Agent 多样性增强与发言差异化

### 新增
- [src] 新增 `agent_quality_analyzer.py` Agent 质量分析模块

### 修改
- [Phase 1] LLM2 temperature=0.7（输出更发散）
- [Phase 1] description 长度约束 15-50 字
- [Phase 1] communication_style 要求多样化
- [Phase 3] 事件实体使用 temperature=0.3（输出更稳定）
- [Phase 3] 意见传播者使用 temperature=0.8（输出更多样化）

### 功能
- ✅ Agent 质量分析工具：立场分布、描述多样性、风格多样性、逻辑一致性
- ✅ Phase 3 差异化温度配置

---

## v1.1.4 - 2026-03-26（已完成）

**主题**：实体分类与LLM1/2/3协作架构

### 新增
- [schemas.py] 新增 `EntityCategory` 枚举（event_entity / opinion_spreader）
- [schemas.py] 新增 `OpinionSpreader` 模型
- [Phase 1] `phase1_entity_extraction.py` 实现 LLM1/2/3 三阶段协作架构

### 修改
- [schemas.py] `Entity` 模型增加 `entity_category` 字段
- [schemas.py] `EntityExtractionOutput` 输出改为 event_entities + opinion_spreaders 双列结构
- [schemas.py] 新增 `event_intensity` 字段
- [Phase 1] LLM1：设置 event_temperature + event_intensity
- [Phase 1] LLM2：提取事件实体 + 生成意见传播者
- [Phase 1] LLM3：格式校验，失败则 LLM2 重试（最多3次）
- [Phase 2] 事件实体作为 Core 节点，意见传播实体作为 Periphery 节点
- [Phase 2] 事件实体之间互相关注（Core ↔ Core）
- [Phase 3] Tick 0 只有事件实体发言
- [Phase 3] Tick 1+ 只有意见传播实体发言（必须看到 Tick 0 的事件实体发言）

### 功能
- ✅ 两种实体类型区分：事件实体 vs 意见传播实体
- ✅ LLM1/2/3 迭代校验机制
- ✅ 事件实体=Core，传播实体=Periphery 的拓扑结构
- ✅ Tick 0/1+ 分阶段发言机制

**详细文档**：[v1.1.4_entity_classification.md](./v1.1.4_entity_classification.md)
**完成时间**：2026-03-26

---

## v1.1.3 - 2026-03-25（已完成）

**主题**：Stance 语义修复与社交拓扑优化

### 修改
- [schemas.py] `GraphNode` 增加 `confirmation_bias_level` 字段
- [schemas.py] `EdgeType` 增加 `FOLLOWS_CROSS_GROUP` 和 `FOLLOWS_CORE_CROSS` 边类型
- [Phase 1] `phase1_persona_engine.py` 传递 `confirmation_bias_level` 到 GraphNode
- [Phase 2] `phase2_topology_builder.py` 新增跨圈层关注机制（50% 概率 + 30% Core 互关）
- [Phase 2] `phase2_topology_builder.py` 新增 Agent 个体差异化扰动（Core ±5%, Periphery ±15%）
- [Phase 3] `phase3_tick_simulation.py` 新增 stance_score 语义定义（1-3 批评，4-6 中立，7-10 支持）
- [Phase 3] `phase3_tick_simulation.py` 新增确认偏差 Prompt 约束
- [Phase 3] `phase3_tick_simulation.py` 新增代码层 stance 变化硬性限制

### 功能
- ✅ 跨圈层信息传递：65% Agent 能看到不同群体的发言
- ✅ stance_delta 约束：strong=±0.3, weak=±1.0, none=±2.0 全部生效
- ✅ 同群体 Agent 差异化：stance_score 不再完全相同

**详细文档**：[v1.1.3_stance_and_topology_fix.md](./v1.1.3_stance_and_topology_fix.md)
**完成时间**：2026-03-25

---

## v1.1.2 - 2026-03-25（已完成）

**主题**：Phase3 发言中体现实体信息

### 修改
- [schemas.py] `GraphNode` 增加 `related_entity` 字段
- [Phase 2] `phase2_topology_builder.py` 传递 `related_entity` 到 GraphNode
- [Phase 3] `phase3_tick_simulation.py` 发言 Prompt 加入实体信息
- [schemas.py] `Phase1Output` 验证器增加自动校正百分比逻辑

### 功能
- ✅ Agent 发言中包含关联实体名称（如"某知名美妆品牌"）
- ✅ 发言内容与实体相关

### 验收结果
- ✅ GraphNode 有 related_entity 字段
- ✅ Phase3 发言 Prompt 包含实体信息
- ✅ Agent 发言中出现关联实体名称
- ✅ 端到端运行成功

**详细文档**：[v1.1.2_entity_in_post.md](./v1.1.2_entity_in_post.md)
**完成时间**：2026-03-25

---

## v1.1.1 - 2026-03-25（已完成）

**主题**：引入实体提取与基于实体的 Agent 生成

### 新增
- [Phase 0] `phase0_entity_extraction.py` - 实体提取模块
- [Phase 1] `related_entity` 字段 - 关联核心实体
- [Phase 1] `confirmation_bias_level` 字段 - 确认偏差强度
- [Phase 1] `event_temperature` 参数 - 事件热度控制
- [schemas.py] 新增 `Entity`, `Relation`, `EntityExtractionOutput` 模型
- [schemas.py] 新增 `ConfirmationBiasLevel` 枚举

### 修改
- [Phase 1] `phase1_persona_engine.py` - 基于实体生成 Agent
- [schemas.py] `Archetype` 增加 `related_entity` 和 `confirmation_bias_level` 字段
- [main.py] 增加 Phase 0 调用逻辑

### 修复
- Agent 生成与事件脱节的问题
- Agent 数量无法根据事件热度动态调整的问题

### 功能
- ✅ Phase 0: 从种子文本提取 3-5 个核心实体
- ✅ Phase 0: 输出 event_temperature (0.0-1.0)
- ✅ Phase 1: 基于实体生成 Agent，每个 Agent 关联 core_entity
- ✅ Phase 1: confirmation_bias_level 字段 (none/weak/strong)
- ✅ Phase 1: 根据 event_temperature 动态决定 Agent 数量

### 验收结果
- ✅ Phase 0 能够提取 3-5 个核心实体
- ✅ event_temperature 在 0.0-1.0 范围内
- ✅ 每个 archetype 都有 related_entity 字段
- ✅ 每个 archetype 都有 confirmation_bias_level 字段
- ✅ archetypes 百分比之和 = 100
- ✅ 端到端运行成功

**详细文档**：[v1.1.1_entity_extraction.md](./v1.1.1_entity_extraction.md)
**完成时间**：2026-03-25

---

## v1.1.0 - 2026-03-25（已完成）

**主题**：MVP 基线版本 - Phase 1-4 基础功能

### 新增
- [Phase 1] `phase1_persona_engine.py` - 动态人群生成器
- [Phase 2] `phase2_topology_builder.py` - 微型社交拓扑构建
- [Phase 3] `phase3_tick_simulation.py` - 异步时间步推演
- [Phase 4] `phase4_report_agent.py` - 宏观洞察生成器
- [Core] `schemas.py` - Pydantic 数据模型定义
- [Core] `llm_client.py` - LLM 统一调用封装
- [Main] `main.py` - 四阶段串联主入口

### 修改
- [Config] `config.py` - 全局配置（API、路径、参数）
- [Docs] 新增 `docs/PROJECT_SPEC_v1.1.md` - 项目技术规格书
- [Docs] 新增 `docs/skills/dev_workflow.md` - 开发规范文档

### 功能
- ✅ Phase 1: 从种子文本识别 3-8 类人群原型，生成 5-15 个 Agent
- ✅ Phase 2: 构建核心-边缘社交网络拓扑
- ✅ Phase 3: 多轮 Agent 交互模拟，计算 x(t) 序列
- ✅ Phase 4: 生成 Markdown 舆情报告，包含风险评估
- ✅ 端到端闭环：从 `main.py` 一键运行，输入 txt，输出报告

### 验收结果
- ✅ Pydantic 校验通过
- ✅ Archetypes 数量 3-8，占比之和 = 100
- ✅ Agent 数量符合 5-15 约束
- ✅ 社交网络拓扑验证通过
- ✅ 多轮模拟收敛检测正常
- ✅ 最终报告生成成功

**详细文档**：[v1.1.0_baseline.md](./v1.1.0_baseline.md)
**完成时间**：2026-03-25
## 2026-06-04: review-v1.3.0-plan (unknown)

- 状态：completed
## 2026-06-06: v1.3.1 Phase4 Streamlining & Entrypoint Unification

- **task_id**: task-v1.3.1-phase4-streamlining
- **executor**: claude (MiniMax backend via CC Switch)
- **status**: completed (closed 2026-06-06)
- **summary**: 5-Goal DAG. Phase4 收束为纯消费端（report_agent.py 1309→283行），入口归一（main.py 替换, main_new.py→legacy/），函数抽取（paths.py, run_meta.py），测试迁移（17更新+4新建），136 passed/0 failed
- **smoke**: test8 exit 0, 632s, 35 LLM calls all qwen36-35b
| **carryover**: whitebox_summary.json 自引用（v1.3.2）, detail version stale v1.2.5

## 2026-06-08: v1.3.2 风险类型分类扩展 + 平行世界调度器

- **task_id**: v1.3.2-risk-classifier + parallel-worlds-bypass
- **executor**: Claude Code (MiniMax) + Qwen cluster
- **status**: completed (closed 2026-06-08)
- **summary**: 两轮 DAG 派发，核心产出：
  - `spec/risk_mapping.yaml` — 6 域 26 类型风险映射表（唯一源）
  - `src/analysis/classifier.py` — RiskClassifier Agent（单次 LLM 分拣 top-3）
  - `src/schemas/phase4.py` — RiskDomain enum + TYPE_TO_DOMAIN_MAP
  - `tools/probe_scheduler/` — 平行世界调度器（产品入口 bypass 版）
  - `src/output_paths.py` — OCP 输出路径（ParallelRunPaths）
  - `src/phase1/repair_agent.py` — 4 层 error recovery（Compiler → Repair → Repair Agent → Generator retry）
  - `src/model_router.py` — 内网模型路由
  - `spec/dataset_fields.yaml` — dataset 字段规格文档
  - `tools/check_dataset_spec.py` — 规格校验工具
- **smoke**: 6 模型平行推演全部跑通（qwen36-35b/qwen3-30b-tke/qwen3-80b-tke/minimax/ds/122b-sg）
- **findings**:
  - ds 唯一发现 transparency_risk（盲区探测价值确认）
  - 122b-sg 1800s 太慢 + 疑似 herd bias，淘汰
  - TKE 后缀模型比内部集群快（287s vs 410s）
- **carryover**: probe_scheduler 前端对比展示 tab（v1.4）, Report Agent 下游 skill 编写

## 2026-06-26: v1.5.0b 后端 API + 前端真实数据接入

- **status**: completed
- **summary**: 将 v1.5.0a mock-first Vue 前端接入真实 Flask API，完成最小真实链路：seed/config/models/model-gateways/run/status/history/review/report/settings。
- **added**:
  - `docs/api_contract.md`
  - SQLite 状态库：batches/worlds/settings/model_gateways
  - 业务 API 蓝图：seed/config/models/model_gateways/run/history/review/report/settings
  - `tests/serve/` API 测试
- **changed**:
  - `frontend/src/api/client.ts` 从 mock 切到 fetch
  - 前端 stores/pages 接入真实 API
  - `StateTools` 限 dev 构建可见
  - seed file/history 来源、cancel/retry 等未上线能力降级
  - frontend package version → `1.5.0-b`
- **verification**:
  - 14 serve tests passed
  - 6 frontend tests passed
  - frontend production build passed
  - light Flask API smoke passed
- **carryover**: cancel/retry、`_run_world` Popen 改造、v1.5.0c 入口整合和 E2E。

## 2026-06-26: v1.5.1 后端观测能力 + 运行台收口

- **status**: verified_pending_owner
- **summary**: 补齐 Review / World Detail / Observability / Report placeholder 链路；Run 页接入真实 batch/world 事件、metrics、error reason 和 raw log tail。
- **added**:
  - `src/adarian/serve/observability.py`
  - `src/adarian/serve/api/world.py`
  - `frontend/src/pages/09-world.vue`
  - `frontend/src/stores/world.ts`
  - `tests/serve/api/test_observability.py`
- **changed**:
  - `POST /api/report`：本轮不生成新报告；有已有报告文件则返回下载 URL，无文件返回 `REPORT_GENERATION_DEFERRED`，报告重构进入 v1.5.2。
  - `GET /api/run/active`：支持 client session 恢复；带 session 时不再 fallback 到其他 running batch。
  - `/run`：总览只显示批次级状态和日志；单 world 展示 phase/tick/agent/error 信息流；raw log 独立滚动。
  - `/review`：真实风险标签与 world detail 跳转。
- **verification**:
  - 21 serve tests passed
  - 8 frontend tests passed
  - frontend production build passed
  - API smoke passed
  - in-app browser E2E passed
- **carryover**:
  - v1.5.2 报告生成/报告页重构
  - SSE、cancel/retry、多 world 同框对比

## 2026-06-27: v1.5.2 报告生成真实链路

- **status**: verified_pending_owner
- **summary**: 报告生成由 v1.5.1 占位升级为真实 job 链路，前端可基于 completed worlds 的 `simulation_dataset.json` 生成报告。
- **added**:
  - `src/adarian/report/` 轻量报告包：appendix builder、writer、quality、runner、skill。
  - `report_jobs` SQLite 表与报告 job API：创建、轮询、恢复、下载。
  - `tests/serve/api/test_report_jobs.py`。
- **changed**:
  - `/report` 页面接入真实 API，支持 A/B/C、附录模式、skill 切换和会话恢复。
  - `POST /api/report` 不再返回占位，改为兼容执行真实 job。
  - run metrics 的 `report_count` 计入新 `reports/**/*.md`。
  - LLM 502/超时/路由问题归类为 `REPORT_MODEL_UNAVAILABLE`。
- **verification**:
  - 23 serve tests passed
  - 8 frontend tests passed
  - frontend production build passed
  - in-app browser dogfood passed：`report_a24102c105aa` completed，正式 Markdown + appendix + audit 均可下载。
