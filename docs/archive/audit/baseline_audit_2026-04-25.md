# Adarian Current E2E Candidate Baseline Audit

> 审计日期：2026-04-25
> 审计员：内部只读审计
> 评估对象：当前工作区 `adarian mvp/`（HEAD = `035566d baseline: restore test1 e2e runnable`）
> 审计性质：只读实证审计，最终产物只有本报告

---

## 1. Executive Verdict

- **Baseline Verdict**：`pass_with_known_issues`
- **Current Status**：主链路跑通（Phase 1→2→3→4 在 2026-04-24 16:30 那次产出完整），代码全量 `py_compile` 通过，源码与 HEAD 无差异（仅 `audit/`、`outputs/run_test3_20260424_163044/`、`seeds/test7.txt` 三项未跟踪）。已知缺失：`run_dir / run.log / timing_summary.json` 全部不存在。
- **Can Freeze as Baseline**：是。可以以 `pass_with_known_issues` 名义冻结为新 baseline。
- **Main Reason**：缺失三件可观测产物的根因不是"功能回退"，而是 `src/utils/runtime_logger.py` 完整实现并在 `phase3_tick_simulation.py:35,749,829` 与 `llm_client.py:17,117` 已埋点，但 `main.py` 全程未调用 `logger.configure(run_dir)`（全工程 `grep "\.configure\("` 无任何匹配）。这是"接入断层"，而非主链路 blocker，不影响 E2E 功能正确性，因此不构成 baseline freeze 的硬阻塞。
- **Unique Next Action**：在 baseline 冻结之后的下一个版本，于 `main.py` 入口接入 `runtime_logger.configure(run_dir)` 一次，使既有埋点真正落盘。其他治理（输出目录治理、CSV 横向对比、CLI 工程师系统）一律延后。

---

## 2. Evidence Scope

### Authoritative Evidence

1. 当前工作区源码（HEAD = `035566d`，截至 2026-04-25）：
   - `main.py`、`config.py`
   - `src/phase1_entity_extraction.py`、`src/phase2_topology_builder.py`、`src/phase3_tick_simulation.py`、`src/phase3/*`、`src/phase4_report_agent.py`
   - `src/llm_client.py`、`src/utils/runtime_logger.py`、`src/schemas.py`
2. `git status --porcelain` / `git log --oneline -n 15`
3. 当前 `outputs/` 目录实际产物（含时间戳、文件大小、JSON 结构校验）
4. 跨模块只读 `grep` 结果（`run_dir`/`run.log`/`timing_summary`/`configure(`）

### Non-authoritative Historical References

- `audit/baseline_audit_2026-04-24.md`、`audit/baseline_audit_2026-04-24_final.md`（前一日同主题报告，仅作背景）
- `docs/iterations/`、`docs/dev_spec.md`、旧 `CHANGELOG.md`（按任务规则不作为本轮判定依据）
- `outputs/output1/`、`outputs/outputs_test2/`、`outputs/outputs_test2_v1.1.6/`、`outputs/outputs_test3/`、`outputs/outputs_test5/`（历史遗留产物）

### Commands / Checks Performed

```bash
# 工作区
ls -la
ls -la "adarian mvp"
ls -la "adarian mvp/src" "adarian mvp/outputs" "adarian mvp/audit" "adarian mvp/seeds"

# Git
git status --porcelain
git log --oneline -n 15
git log --oneline -n 3 -- main.py src/utils/runtime_logger.py

# 编译（只读、不修改源码）
py -3 -m py_compile main.py
py -3 -m py_compile config.py
py -3 -m py_compile src/phase1_entity_extraction.py src/phase2_topology_builder.py \
                   src/phase3_tick_simulation.py src/phase4_report_agent.py \
                   src/llm_client.py src/utils/runtime_logger.py src/schemas.py
py -3 -m py_compile src/phase3/speaker_selector.py src/phase3/context_builder.py \
                   src/phase3/state_updater.py src/phase3/simulation_card.py

# 实证：可观测组件接入情况
grep -nE "runtime_logger|run_dir|run\.log|timing_summary|configure\(\)|log_run_start" *.py src/**/*.py
grep -nE "logger\.configure|\.configure\(" *.py src/**/*.py    # 全工程 0 命中

# outputs 实证
find outputs -maxdepth 3 -type f | wc -l
stat -c "%n %y %s" outputs/{entities_and_relations.json,final_report.json,final_report.md,social_graph.json,tick_logs.json}
py -3 -c "import json; ..." (校验 JSON keys 与各 phase 输出形状)
```

未运行 `py main.py seeds/test1.txt`（避免再次污染 outputs 根目录），改以"已存在产物 + 源码静态审计"完成证据链。

---

## 3. E2E Evidence Completeness

### Known Missing Evidence

| 缺失项 | 当前状态 |
|---|---|
| `outputs/run_<id>/` (run_dir) | 不存在；仅有手动归档目录 `outputs/run_test3_20260424_163044/` |
| `run.log` | 全工程任何 `outputs/**/run.log` 不存在 |
| `timing_summary.json` | 全工程任何 `outputs/**/timing_summary.json` 不存在 |

### Actual Outputs Found

`outputs/` 根目录共 14 个子目录、68 个文件。最有意义的两组证据：

**(A) 2026-04-24 16:30 完整 E2E 归档（手动整理后保留）**
路径：[outputs/run_test3_20260424_163044/](adarian%20mvp/outputs/run_test3_20260424_163044/)

| 文件 | 大小 | 时间戳 |
|---|---:|---|
| `seed_test3.txt` | 690 B | 2026-04-22 |
| `entities_and_relations.json` | 7,865 B | 2026-04-24 16:27 |
| `social_graph.json` | 8,739 B | 2026-04-24 16:27 |
| `tick_logs.json` | 35,166 B | 2026-04-24 16:29 |
| `final_report.md` | 26,346 B | 2026-04-24 16:30 |
| `final_report.json` | 1,645 B | 2026-04-20 18:16（早于本次运行）|
| `tick_logs/` | 0 B | 空目录 |

→ 这是当前唯一**完整**的 E2E 证据快照。Phase 1/2/3/4 全部产出齐备。

**(B) 2026-04-25 14:53/14:54 部分覆盖（疑似中断或 Phase 4 未跑）**
路径：[outputs/](adarian%20mvp/outputs/)（根目录）

| 文件 | 时间戳 | 状态 |
|---|---|---|
| `entities_and_relations.json` | 2026-04-25 14:53:07 | 新（Phase 1）|
| `social_graph.json` | 2026-04-25 14:53:08 | 新（Phase 2）|
| `tick_logs.json` | 2026-04-25 14:54:42 | 新（Phase 3，6 ticks 0~5）|
| `final_report.md` | 2026-04-24 16:30:24 | **未刷新** |
| `final_report.json` | 2026-04-20 18:16:50 | **未刷新** |

→ 04-25 这次运行 Phase 1/2/3 跑通，Phase 4 未产出；与 04-24 完整 E2E 共享同一根目录，构成**输出污染**。

### Phase 1-4 Completion Evidence

以快照 (A) 为基准：

- Phase 1：`entities_and_relations.json` 包含 `event_summary / event_scale=0.65 / event_controversy=0.75 / event_type / event_entities (5) / opinion_spreaders (5) / relations`，符合 `phase1_entity_extraction.py:661 extract_entities_from_file` 与 schema 定义，无空字段。
- Phase 2：`social_graph.json` `nodes=10, edges=29`，节点同时含事件实体与意见传播者，与 `phase2_topology_builder.py:192 build_topology_from_extraction` 行为一致。
- Phase 3：`tick_logs.json` 共 6 项 (`tick=0..5`)，每项含 `entries` 与 `global_metrics(mean_stance/std_stance/polarization_index)`，最后一轮 `mean_stance=4.7`，与 `phase3_tick_simulation.py:819 run_simulation` 一致。
- Phase 4：`final_report.md` 26 KB（人读 markdown 报告齐全）；`final_report.json` 含 `event_summary / stakeholder_map / emotion_trajectory / inflection_points / risk_level=medium / risk_assessment / x_t_sequence`，结构完整。

**异常 / 脏输出 / 空结果**：
- Phase 3 子目录 `tick_logs/` 始终为空（路径定义于 `config.py:52 TICK_LOGS_DIR`，但 `phase3_tick_simulation.py:911 save_tick_logs` 实际只写单文件 `TICK_LOGS_PATH = OUTPUTS_DIR/tick_logs.json`）。这是历史遗留路径与当前实现不一致，但**不影响 E2E 完整性**。
- `outputs/final_report.json` 时间戳 2026-04-20 早于 (A) 中其他文件，疑似 Phase 4 在 04-24 那次运行中只更新 markdown 而未重写 json，需在源码中确认 `phase4_report_agent.py:555 save_report` 的实际行为。但 (A) 的 markdown 报告完整，可作为 Phase 4 完成的直接证据。

### Root Cause of Missing run_dir / run.log / timing_summary.json

**根因 = "runtime logger 已实现且已埋点，但 main.py 未启用"**。证据：

1. `src/utils/runtime_logger.py:21-25` 中 `RuntimeLogger.configure(run_dir)` 是写入 `run.log`、`timing_summary.json` 的唯一入口；未调用前 `self.log_path = None`，所有 `_append_log()`/`_write_summary()` 都直接 `return`（见 `runtime_logger.py:67-76`）——即"无副作用模式"。
2. 全工程 `grep "\.configure\("` 在 `*.py` 与 `src/**/*.py` 中**零命中**。
3. 但 logger 在以下位置已被持有/调用：
   - `src/llm_client.py:17,117,123,133`（LLM 调用计数与耗时埋点）
   - `src/phase3_tick_simulation.py:35,749,829,836,847,868,871`（tick 与 speaker 埋点）
4. `main.py:188-280 main()` 中只调用了 `ensure_dirs()`、`init_llm_client()`、四个 `run_phaseX(...)`，没有任何 `logger.configure(...)` 或等价语句，亦未生成 `run_id` 或 `run_dir`。

排除其他备选解释：
- ❌ "运行命令未走正确模式"：`main.py` 没有"模式"分支，无 normal/benchmark 切换。
- ❌ "当前修复版本回退了可观测能力"：观测代码完整，是入口未启动。
- ❌ "output manager 未接入"：本工程不存在 output manager 抽象，输出走 `config.py` 固定路径，不是 manager 缺失问题。

判定：**runtime logger 未在主入口接入**，单一原因。

### Impact on Baseline Freeze

不阻塞。

- 主链路 4 个 phase 已能完整产出业务交付物（实体、社交图、tick 日志、最终报告 md+json）。
- 缺失的只是"白盒可观测产物"，不是"业务产物"。
- 接入是一行 `logger.configure(...)` 级别的工作，属于下一版本治理。

但必须在 baseline 冻结说明里明确标注："E2E pass with observability gap"，以免后续误判 baseline 已具备 run.log。

---

## 4. Main Pipeline Architecture Audit

### main.py Actual Call Chain

`main.py:188 main()` 严格按下列顺序执行（直引源码行号）：

```
print_banner()                       # 40
ensure_dirs()                        # 193 → config.py:176
init_llm_client()                    # 202 → src/llm_client.py
run_phase1(seed_file)                # 226 → src/phase1_entity_extraction.py:661 extract_entities_from_file
                                     # 75       save_entities_output → ENTITIES_OUTPUT_PATH
run_phase2(extraction_output)        # 231 → src/phase2_topology_builder.py:192 build_topology_from_extraction
                                     # 113      save_social_graph → SOCIAL_GRAPH_PATH
run_phase3(extraction, p2, seed)     # 236 → src/phase3_tick_simulation.py: SimulationEngine.run_simulation
                                     # 147      save_tick_logs → TICK_LOGS_PATH
run_phase4(extraction, ticks, x_t)   # 241 → src/phase4_report_agent.py:286 generate_report_with_llm
                                     # 182      save_report / save_markdown_report → FINAL_REPORT_PATH(.json/.md)
```

四阶段间通过函数返回值传递结构化对象（`EntityExtractionOutput`、`Phase2Output`、`List[TickLog]`、`x_t_sequence`、`Phase4Output`），耦合方式是**值传递**，不是"全局状态"，已经是合理形态。

### Phase 1 Status

- 入口：`extract_entities_from_file(seed_file)` (`src/phase1_entity_extraction.py:661`)
- Analyzer/Generator/Validator 三阶段协作 (`:112-330`)，含 `MAX_RETRIES=3` 的 retry 循环 (`:577,594-621`)，并打印失败重试日志（控制台 stdout）。
- 输出固定写到 `config.ENTITIES_OUTPUT_PATH`（共享根 outputs/）。
- 当前产物形状正确，retry/validator 失败处理路径存在但只输出到控制台，没有持久化。
- **不构成 blocker**。

### Phase 2 Status

- 入口：`build_topology_from_extraction(extraction_output)` (`src/phase2_topology_builder.py:192`)
- 拓扑：事件实体 → Core，意见传播者 → Periphery；`apply_individual_jitter()` 处理度数扰动 (`:34-80`)。
- `validate_topology()` (`:210-270`) 在主链中被调用 (`main.py:112`)。
- 输出 `SOCIAL_GRAPH_PATH`，10 节点 / 29 边，与最近运行一致。
- **不构成 blocker**。

### Phase 3 Status

- 入口：`SimulationEngine.run_simulation(max_ticks)` (`src/phase3_tick_simulation.py:819`)
- Tick 0：事件实体发言 (`:259-315`)；Tick 1+：意见传播者发言、`select_speakers()` 委托给 `src/phase3/speaker_selector.py`，silent agent 通过 `update_silent_agent()` 被动更新立场 (`:787-808`)。
- 收敛检测被注释禁用 (`:884-891`)，固定跑满 `MAX_TICKS=5`（实际产出 6 个 tick，因为 tick 0 也算一项）。
- 已埋点 `runtime_logger`：`log_tick_start/end`、`log_speaker_selection`（tick 与 speaker 数据完整），但因 `configure()` 未调，全部空写。
- 该模块 ~900 行，是工程中最大的单文件；`SimulationEngine` 内部混合了：图操作、agent 状态、LLM 调用编排、metrics 计算。耦合偏重，但**不阻塞 baseline freeze**。

### Phase 4 Status

- 入口：`generate_report_with_llm(extraction_output, tick_logs, x_t_sequence)` (`src/phase4_report_agent.py:286`)
- 内部 `parse_llm_report_response()` (`:333-470`) 含 fallback 解析路径（LLM 输出不完整时退回自动分析）。
- 写 `FINAL_REPORT_PATH(.md)` 与 `.json`。当前 (A) 快照中 markdown 完整。
- **不构成 blocker**。

### Main-chain Architecture Risk

| 风险 | 严重程度 | 是否 baseline blocker |
|---|---|---|
| 观测组件未接入入口 | 中 | 否（功能不受影响）|
| Phase 3 单文件 ~900 行、内部高耦合 | 中 | 否（已稳定产出）|
| `outputs/tick_logs/` 子目录与 `tick_logs.json` 单文件并存（路径漂移）| 低 | 否 |
| Phase 4 fallback 路径无显式日志 | 低 | 否 |
| 全部产物写到固定 `OUTPUTS_DIR/...`，多次运行会互相覆盖 | 高（治理风险）| 否，但**强烈建议 baseline 后第一时间治理** |

主链架构整体稳定，无结构漂移到无法收敛的程度。**没有架构级 blocker**。

---

## 5. Module-level Decoupling Audit

### Modules That May Need Decoupling

| 模块 | 位置 | 描述 |
|---|---|---|
| `phase3_tick_simulation.py` | `src/phase3_tick_simulation.py` (~900 行) | `SimulationEngine` 内部承担：图初始化、agent 状态、context 构造、speaker 选择编排、LLM 调用、state 更新、global metrics、Tick 0 事件实体逻辑。已经部分外移到 `src/phase3/{speaker_selector,context_builder,state_updater,simulation_card}.py`，但 engine 主类仍然偏厚。|
| `phase4_report_agent.py` | `src/phase4_report_agent.py:333-470` | `parse_llm_report_response` 含大量 fallback 解析与正则，承担 LLM 输出修补职责，与"报告生成"职责混合。|
| `runtime_logger.py` | `src/utils/runtime_logger.py` | 单例 `_runtime_logger`，但无入口接入。属于"已就绪未启用"，不需解耦，需要的是"接入"。|

### Baseline-blocking Module Issues

无。无任何模块级 blocker 阻止 baseline freeze。

### Baseline-after Module Issues

- **Phase 3 进一步薄化**：把 `run_tick_0` / `run_tick` / metrics 计算等长流程进一步剥离到 `src/phase3/` 子包；engine 只保留装配。下一版本可做。
- **Phase 4 解析与生成解耦**：把 `parse_llm_report_response` 拆出独立的 `report_parser.py`。下一版本可做。
- **runtime_logger 接入**：`main.py` 入口加 `configure(run_dir)`，并在 `try/finally` 中 `log_run_start/log_run_end/log_phase_start/log_phase_end/log_error`。这是下一版本最值得做的一件事。

### Modules Not Worth Touching Now

- `config.py`：路径、参数集中且清晰。不要"顺手优化"为多环境配置。
- `src/llm_client.py`：埋点已就绪，调用约定稳定。不要现在引入异步、批量、缓存。
- `src/schemas.py`：pydantic 模型已被四个 phase 共享，不要在 baseline 期改字段。
- `src/phase0_entity_extraction.py`：旧入口，已无人调用，但保留无害；不建议现在删除（避免引入额外 diff 风险）。

---

## 6. Output & Observability Governance Audit

### Current Output Problems

1. **多个历史遗留目录混存**：`outputs/` 下同时有 `output1/`、`outputs_test2/`、`outputs_test2_v1.1.6/`、`outputs_test3/`、`outputs_test5/`、`run_test3_20260424_163044/` 与根目录散落产物。命名不一、版本号不一、是否归档不一。
2. **多次运行互相覆盖**：所有 phase 都写到 `OUTPUTS_DIR/` 固定路径（`config.py:46-58`）。最近一次运行（2026-04-25 14:53）覆盖了 Phase 1/2/3 产物，但 Phase 4 没跑，导致根目录 `entities/social_graph/tick_logs.json` 与 `final_report.{md,json}` 不属于同一次运行。
3. **空闲路径**：`outputs/tick_logs/` 子目录始终为空，与 `tick_logs.json` 并存，命名空间漂移。
4. **无 normal / benchmark 分区**：根目录与 `profiling/output/` 是两套体系，profiling 自有 raw_logs（Permission denied 子目录意味着 worker 残留），主链没有对应分区。
5. **复盘困难**：定位"哪一次 E2E 跑通"必须靠 `stat` 看时间戳；查"那次 LLM 调用了多少次"无任何来源。

### Is Current Output Too Dirty / Scattered / Hard to Replay?

**是。已经构成下一版本必须治理的问题**。但当前 baseline 仍可冻结——因为 (A) 快照（`outputs/run_test3_20260424_163044/`）保留了一次完整 E2E，可作为 baseline 复盘锚点。治理必须在 baseline 之后立刻进行。

### JSON Responsibility（建议，**不实现**）

- `run_meta.json`：run_id、git commit、dirty state、seed file、model、version、start/end time、status。
- `timing_summary.json`：每个 phase 的 start/end/elapsed；llm.count；llm.calls (caller, model, elapsed)；ticks (tick, speakers, llm_calls, speaker_selection)；errors。`runtime_logger.py` 已经定义了这个 schema 的雏形（`:26-44`），可直接沿用。
- 业务产物 JSON 维持现状：`entities_and_relations.json`、`social_graph.json`、`tick_logs.json`、`final_report.json`。

### CSV Responsibility（建议，**不实现**）

只用于"多次运行横向对比"，每行一次 run，列：

`run_id, started_at, seed, model, total_elapsed, phase1_elapsed, phase2_elapsed, phase3_elapsed, phase4_elapsed, llm_call_count, tick_count, selected_speaker_total, silent_agent_total, output_completeness(0/1 per artifact), final_status`

放在 `outputs/_index/runs.csv` 形式（**只是建议**）。

### Markdown Responsibility（建议，**不实现**）

- `final_report.md`：业务面向的人读报告（已有）。
- 每次 run 的 `summary.md`：人读运行摘要（status、phase 耗时、LLM 次数、x(t)、风险等级）。
- baseline audit / risk 类文档继续放 `audit/`。

### run.log Responsibility（建议，**不实现**）

顺序事件流：
- `RUN START / RUN END`
- `PHASE START / PHASE END`（含 elapsed）
- `LLM START / LLM END`（含 caller、model、elapsed）
- `SPEAKER SELECTION`（已有结构）
- `TICK START / TICK END`
- `ERROR`（含 stage）

`runtime_logger.py` 中 `_append_log()` 已经覆盖了上面全部事件类型，schema 不需新增。

### Need for Unified Schema

需要。但 schema 已经在 `runtime_logger.py` 中实质存在，只是没有人运行它。下一版本不要"重新设计 schema"，要"启用现有 schema"。

---

## 7. White-box Testing Field Requirements

### Required Fields（下一版本必须落盘）

| 字段 | 来源 | 当前是否已埋点 |
|---|---|---|
| seed (path / hash) | `main.py:206-218` | 已有变量，未持久化 |
| model | `config.get_model_name()` | 已有 |
| version | 需引入（暂用 git commit 替代）| 缺 |
| run_id | 需在 `main.py` 入口生成（`run_<UTC timestamp>`）| 缺 |
| git commit / dirty state | `git rev-parse HEAD`、`git status --porcelain` 子进程 | 缺 |
| phase start / end / duration | `runtime_logger.log_phase_start/end` | 已埋（待启用）|
| LLM 调用次数 | `runtime_logger.summary.llm.count` | 已埋（待启用）|
| 每次 LLM 调用耗时 | `runtime_logger.summary.llm.calls[*].elapsed_seconds` | 已埋（待启用）|
| parser failure / validator failure | `phase1_entity_extraction.py` 重试日志（控制台）| 缺持久化 |
| retry count | 同上 | 缺持久化 |
| fallback 行为 | `phase4_report_agent.py:333-470` 内部 fallback | 缺记录 |
| tick index | `runtime_logger.log_tick_start/end` | 已埋（待启用）|
| tick speaker selection | `log_speaker_selection`（含 expected/actual/computed/full）| 已埋（待启用）|
| selected speaker 数量 | `log_tick_end(speakers=...)` | 已埋（待启用）|
| silent agent 数量 | 需在 phase3 计算后送入 logger | 部分缺 |
| stance drift | `tick_logs[*].entries[*].stance_delta` | 已在产物 |
| global_metrics | `tick_logs[*].global_metrics` | 已在产物 |
| output completeness | 在 `log_run_end` 前对四个产物做 stat | 缺 |
| error / timeout | `runtime_logger.log_error` | 已埋（待启用）|
| final E2E status | `log_run_end(status=...)` | 已埋（待启用）|

→ 接入工作量小：**绝大多数字段已埋点，只缺 `configure()` 与少量字段补齐**。

### Optional Fields（按需）

- LLM tokens（prompt/completion/total）：`llm_client.py:140-144` 已返回，logger 暂未存。
- 每个 agent 的最终立场分布（按 group）。
- LLM 调用 prompt 长度 / response 长度（用于成本归因）。

### Fields Not Recommended Yet

- prompt 全文落盘（隐私/体积/scope 蔓延）。
- 每个 tick 的图快照（体积大、收益低）。
- 多模型 A/B 测试维度（baseline 之后再考虑）。

---

## 8. CLI Engineer System Assessment

### Should Build CLI System?

**不建议在 baseline 后第一版立刻做**。

### Why

1. 当前真正的瓶颈是"日志根本没落盘"，CLI 只是日志的展示层。先有数据，再谈 CLI。
2. CLI 工程师系统涉及："最新 run / 列举 run / 单 run 详情 / 横向对比 / 复盘 / 重放 / baseline 资格检查 / CSV 导出 / Markdown 导出"——这是一个独立的工程子系统，至少 200~400 行 + 一套 run 索引设计，超出 baseline 后第一波治理的合理 scope。
3. 在没有 `run_dir` / `runs.csv` 的前提下，CLI 没有数据可读。

### Minimal CLI Scope for Next Version

如果 baseline 后第一版完成 logger 接入并稳定输出 `outputs/run_<id>/{run.log,timing_summary.json,...}`，最小可用 CLI 只做两件事：

1. `adarian runs list`：扫描 `outputs/run_*/timing_summary.json`，按时间倒序列出 run_id + status + total_elapsed + llm_count。
2. `adarian runs show <run_id>`：cat `run.log`，并把 `timing_summary.json` 转成可读 markdown。

其他（diff、replay、baseline qualification check、CSV export）一律延后。

### What Not to Build Yet

- 不要 TUI / curses 界面。
- 不要"运行重放"（涉及 LLM 状态、不可重放本身就是预期）。
- 不要"自动 baseline 资格仲裁"——baseline 资格是人判，不是程序判。
- 不要"集成到 Web UI"。

---

## 9. Risk Classification

### Baseline 前必须处理

**无**。

当前唯一已知缺陷（run_dir / run.log / timing_summary.json 缺失）经实证审定不阻塞 baseline freeze——主链路已稳定产出业务结果，缺失的是观测产物而非业务产物。强行在 freeze 前接入会引入额外 diff 风险，违背"baseline = 现状快照"的原则。

### Baseline 后可以处理

按优先级：

1. **runtime_logger 接入主入口**（最高优先）。`main.py` 入口生成 `run_id` → `configure(run_dir)` → `log_run_start` → 在每个 `run_phaseX` 前后 `log_phase_start/end` → `log_run_end` 在 finally。phase3 / llm_client 现有埋点立刻开始落盘。
2. **outputs 目录治理**：`outputs/run_<id>/` 形式，主链产物全部进 run_dir；根目录历史散落产物归档到 `outputs/_archive/`。
3. **多次运行索引**：`outputs/_index/runs.csv` 由 `log_run_end` 触发追加。
4. **Phase 1/4 失败/fallback 记录**：把 retry/validator failure / Phase 4 解析 fallback 写入 `run.log`。
5. **`tick_logs/` 空目录路径漂移修复**：要么删掉路径定义，要么真正写分文件版本（择其一）。
6. **Phase 3 进一步薄化**（次低优）：engine 内部继续外移到 `src/phase3/` 子包。

### 不建议处理

- 不建议现在引入 normal / benchmark 双分区（无明确收益，容易过早抽象）。
- 不建议为 LLM 加缓存层（在 baseline 测量稳定前不做）。
- 不建议把 Phase 3 重写为事件驱动 / 异步（架构漂移风险高）。
- 不建议引入 CLI 工程师系统的高级特性（diff/replay/qualifier）。
- 不建议在 baseline 期间删除 `phase0_entity_extraction.py` / 历史 outputs 目录（避免 baseline diff 噪声）。
- 不建议在 baseline 期间重写 `schemas.py`。

---

## 10. Final Decision

- **Final Verdict**：`pass_with_known_issues` —— 当前 E2E candidate 具备 baseline freeze 资格，已知缺陷为 observability 接入断层、不阻塞业务功能。
- **Single Blocker**：无（不存在阻塞 baseline freeze 的 blocker）。
- **Single Next Action**：**baseline 冻结之后**，在 `main.py` 主入口接入 `runtime_logger.configure(run_dir)`（生成 `run_id`、创建 `outputs/run_<id>/`、`log_run_start/end` + 四个 `log_phase_start/end`），让现有埋点真正落盘 `run.log` 与 `timing_summary.json`。其余治理一律延后到该改动稳定之后。
- **Do Not Do**：
  - 不要在 baseline freeze 之前修任何代码。
  - 不要在第一波治理时同步做 outputs 目录重组、CLI 系统、Phase 3 重构、schemas 改动——只做 logger 接入这一件事。
  - 不要为了"顺手"删除历史 `outputs/output1` / `outputs_test*` 等目录，会污染 baseline diff。
  - 不要新增 CSV/CLI/normal-benchmark 分区机制——等数据先落盘再谈。
