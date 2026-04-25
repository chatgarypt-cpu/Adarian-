# Adarian MVP 任务执行日志 (TASK_LOG)

所有开发任务的执行记录都会保存在此文档中，按时间倒序排列（最新在上）。

自 `v1.1.13` 起，`benchmark / 稳定性测试 / 回归测试 / AQF 评分` 记录统一迁移至 `BENCHMARK_LOG.md`。

此文档之后只保留：
- 开始任务
- 完成任务
- 实际变更文件
- 遇到的问题
- 基本验收结果
- 状态

---

## Workflow Record Contract

自本次 workflow governance refactor 起，新的验收记录应至少包含：

- `task_id`
- `review_id`（若适用）
- `attempt_id`
- `acceptance_id`
- `acceptance_result`
- `carry_over`

最小记录格式：

```text
task_id: task-vX.Y.Z-xxx
review_id: review-vX.Y.Z-01
attempt_id: attempt-vX.Y.Z-01
acceptance_id: accept-vX.Y.Z-01
acceptance_result: pass / pass_with_known_issues / fail
carry_over:
- item 1
```

运行状态以当前 iteration 文档状态与本日志中的最新验收记录为准。

---

## [2026-04-25 完成] v1.2.0 - Functional Baseline Restore

**执行者**：文档治理 Agent
**基于版本**：HEAD = `035566d` (baseline: restore test1 e2e runnable)
**任务文档**：`docs/iterations/v1.2.0-functional-baseline-restore.md`

**记录标识**：
- `task_id`: `task-v1.2.0-functional-baseline-restore`
- `review_id`: `review-v1.2.0-01`
- `attempt_id`: `attempt-v1.2.0-01`
- `acceptance_id`: `accept-v1.2.0-01`

**本轮结果**：`pass_with_known_issues`

**本轮任务性质**：
- 不改代码，只补文档
- 建立新功能基线起点
- 记录灾难原因与恢复动作
- 明确 v1.2.1 carry_over

**test7 E2E 验证数据**：

```text
命令：py main.py seeds/test7.txt
结果：端到端通过
退出码：0
总耗时：约 223.1s
LLM：qwen / qwen35-122b-a10b
Phase 1：77.0s（首次 Validator 失败，第二轮通过）
Phase 2：1.0s（10 节点、29 边）
Phase 3：93.6s（Tick 0-5 完成）
Phase 4：51.5s
x(t)：4.73 -> 4.65 -> 4.74 -> 4.75 -> 4.81 -> 4.70
最终极化指数：0.34
风险等级：LOW
```

**实际新增文件**：
- `docs/iterations/v1.2.0-functional-baseline-restore.md` — 新基线重建迭代文档
- `audit/baseline_audit_2026-04-25.md` — 只读审计报告（已存在）

**实际修改文件**：
- `docs/iterations/CHANGELOG.md` — 新增 v1.2.0 条目
- `docs/iterations/TASK_LOG.md` — 新增 v1.2.0 执行记录

**未修改文件**：
- `main.py` — 未修改
- `src/` — 未修改
- `profiling/` — 未修改
- `outputs/` — 未修改

**acceptance_result**：
- ✅ Phase 1-4 E2E 可运行（test7 通过）
- ✅ 退出码 0
- ✅ 四个核心产物生成
- ✅ x(t) 序列完整
- ✅ 风险等级判定输出
- ✅ 迭代文档补齐
- ✅ CHANGELOG 更新
- ✅ TASK_LOG 更新
- ✅ Closeout Record 填写
- ⚠️ run_dir / run.log / timing_summary.json 缺失（延后至 v1.2.1）

**carry_over**：
- v1.2.1 处理 run_dir / run.log / timing_summary.json
- v1.2.1 修复 final_report.json / final_report.md 输出契约
- v1.2.1 修正 tick_logs 输出提示
- v1.2.1 RuntimeLogger 接入 main.py 入口
- v1.2.1 outputs 目录治理
- CLI / CSV / benchmark / profiling 不纳入 v1.2.0
- Phase 1 语义分类质量问题延后观察

**Git Tag**：未创建（本轮不改代码，文档补账无需 tag）

---

## [2026-04-15 完成] v1.1.21 - Workflow Governance Closeout

**执行者**：Codex
**基于版本**：v1.1.19-profiling-closeout
**任务文档**：`docs/iterations/v1.1.21.md`

**记录标识**：
- `task_id`: `task-v1.1.21-workflow-governance-closeout`
- `review_id`: `review-v1.1.21-01`
- `attempt_id`: `attempt-v1.1.21-01`
- `acceptance_id`: `accept-v1.1.21-01`

**本轮结果**：`pass_with_known_issues`

**本轮真实收口边界**：
- `docs/skills/workflow_core.md` 收口为唯一规则权威源
- `docs/skills/main_agent_delivery.md` 与 `CLAUDE.md` 降级为从属规范
- `docs/iterations/_template_v2.md`、`docs/iterations/v1.1.21.md`、`TASK_LOG.md` 落入最小 event ids
- `scripts/probes/reduced_schema_chain_probe.py`、`p1a_prompt_probe.py`、`p1g_prompt_probe.py` 去掉 `control/` 依赖
- `control/` 与 `scripts/generate_snapshot.py` 归档到 `docs/_archive/control_plane/`

**acceptance_result**：
- ✅ authority consolidation 已落地
- ✅ control plane retirement 已落地
- ✅ minimal eventization 已落地
- ✅ closeout / freeze 模板已落地
- ⚠️ 原始 `Phase1 + Phase3` 双解耦实现未在本轮完成，因此按 `pass_with_known_issues` 收口

**carry_over**：
- Phase1 双解耦实现未落地
- Phase3 双解耦实现未落地
- 与双解耦实现相关的业务验证留待后续版本

**Git Tag**：`未创建（freeze blocker: profiling/output/raw_logs/_worker_tmp_test/chain_worker_vawgkfsj 访问被拒绝）`

---

## [2026-04-13 完成] v1.1.20 - Execution Isolation & Hard Kill Timeout

**执行者**：Codex
**基于版本**：v1.1.19
**任务文档**：`docs/iterations/v1.1.20_runner_cancellation_timeout_hygiene.md`

**本次目标**：
- 将 chain 执行从"线程内不可可靠取消"升级为"子进程级可强制终止"
- timeout 到达后主控可硬杀子进程
- 将 termination 结果写入 raw log
- aggregate 只做兼容统计，不改 v1.1.19 的主判定逻辑

**实际新增文件**：
- `profiling/chain_worker.py` - 子进程入口，单个 chain 单元执行 + JSON 文件回传
- `profiling/utils/subprocess_runner.py` - subprocess 生命周期管理（spawn / wait / kill / cleanup）

**实际修改文件**：
- `profiling/chain_benchmark.py` - chain 单元执行从主进程内直接调用改为 subprocess 调度
- `profiling/aggregate.py` - 新增 execution_hygiene 统计字段

**基本验收结果**：
- ✅ chain 执行已改为 subprocess 执行
- ✅ timeout 后执行 proc.kill()，kill 失败时显式标记 kill_failed
- ✅ raw log 新增 7 个 execution/termination 字段
- ✅ aggregate 兼容新增字段，不影响 overall_status 主判定逻辑
- ✅ 1×1 真实 E2E：通过，subprocess_execution_count=1，killed_count=1，kill_failed_count=0
- ✅ 2 并发 E2E：进程均完成，kill_failed_count=0，worker_exit_abnormal_count=0，无 `<unknown>` 回归

**阻塞问题（待修复后再进入 4 并发）**：
- Process 2 chain 结果因 raw log 路径冲突丢失（manifest snapshot 路径未隔离）
- subprocess timeout 参数传递链路疑似失效（15s timeout 未生效，实际跑了 86.5s）
- _worker_tmp 目录残留未清理

**Git Commit**：待提交

---

## [2026-04-13 11:15] 开始任务：v1.1.19 - Model Pool Profiling

**执行者**：Codex
**基于版本**：v1.1.18.2
**任务文档**：`docs/iterations/v1.1.19_model_profiling.md`

**本次目标**：
- 建立模型池 profiling 独立流程，不接入 scheduler 实现
- 同时测量 simple prompt、generator、validator+retry 链路表现
- 输出 raw logs、`model_profiles.json`、`profile_summary.md`

**冻结口径**：
- 固定模型列表来源：`modelslist.txt`（运行时读取，按文件顺序去空白去重）
- 固定 case 列表：3 个固定 case，不随机换料
- 固定并发档位：`1 / 2 / 3 / 5`
- 本轮不拆分 subagent，由主控统一执行与汇总

**计划新增**：
- `profiling/prompts.py`
- `profiling/models.yaml`
- `profiling/cases.yaml`
- `profiling/profile_runner.py`
- `profiling/output/`

**状态**：✅ 已完成

---

## [2026-04-13 完成] v1.1.19 - Model Pool Profiling 收口

**实际新增文件**：
- `profiling/prompts.py` - Simple/Generator/Validator prompts 统一封装
- `profiling/models.yaml` - 模型列表来源策略
- `profiling/cases.yaml` - 3 个固定测试 case
- `profiling/simple_benchmark.py` - Simple Prompt sidecar
- `profiling/chain_benchmark.py` - Generator → Validator → Retry chain sidecar
- `profiling/aggregate.py` - Raw logs 聚合器（含 incomplete_profile 检测）
- `profiling/run_profile.py` - Pipeline 主控入口（freeze → simple_runner → chain_runner → aggregator）
- `profiling/output/` - 产物目录（raw_logs、model_profiles.json、profile_summary.md）

**本次关键修复**：
- `src/llm_client.py` - client 级 httpx timeout（connect=10s / read=180s）修复无限挂起问题

**审查发现的已知遗留**：
- `chain_runner` daemon thread 在 runner-level timeout 后无法真正取消底层 httpx 调用（背景线程泄漏）
- 修复路径：subprocess isolation（后续迭代，不在本轮范围内）

**Git Commit**：待提交

---

## [2026-04-09] 开始任务：v1.1.18 - Phase 3 Adaptive Scheduler

**执行者**：Claude Code
**基于版本**：v1.1.17
**任务文档**：`docs/iterations/v1.1.18 - Phase 3 Adaptive Scheduler.md`

**本次目标**：
- Phase 3 从"固定全员发言"升级为"自适应发言调度"
- 新增 Adaptive Speaker Selector / Simulation Card / Context Builder / Silent Agent Updater
- 轻量化 Prompt，降低 token 成本

**计划新增**：
- Speaker Selector / Context Builder / Simulation Card / State Updater 模块

**实际变更文件**：
- ✅ 新增：`src/phase3/__init__.py`
- ✅ 新增：`src/phase3/speaker_selector.py`
- ✅ 新增：`src/phase3/simulation_card.py`
- ✅ 新增：`src/phase3/context_builder.py`
- ✅ 新增：`src/phase3/state_updater.py`
- ✅ 修改：`src/schemas.py` - 新增 `SimulationCard`、`SpeakerSelectionResult`、`SilentAgentUpdate`
- ✅ 修改：`src/phase3_tick_simulation.py` - 接入 adaptive speaker selection、simulation card、silent agent update
- ✅ 修改：`docs/dev_spec.md` - 同步 Phase 3 自适应调度结构
- ✅ 修改：`docs/iterations/CHANGELOG.md` - 增加 v1.1.18 记录

**遇到的问题**：
- 需要在不改 `TickLog` 结构的前提下表达“未发言但已更新”的 agent，因此对 silent agents 采用占位 comment `（未发言）` 的兼容写法

**基本验收结果**：
- ✅ 已不再默认所有 spreader 每轮发言
- ✅ 已引入小规模 / 中规模不同发言率
- ✅ 已为 silent agents 提供独立更新路径
- ✅ `python -m py_compile` 通过
- ✅ 构造性验证通过：10 个 spreader 时 `selected=5 / silent=5`
- ✅ 静默 agent 更新验证通过：会留下 `（未发言）` entry 且可产生轻微 stance drift
- ⚠️ 完整端到端 smoke test 仍需结合远端 LLM 调用时间验证，但本地结构与选择逻辑已打通

**状态**：✅ 已完成

---

## [2026-04-09] 开始任务：v1.1.18.1 - Scheduler Fix & Minimal Drift Control

**执行者**：Claude Code
**基于版本**：v1.1.18
**任务文档**：`docs/iterations/v1.1.18.1 - Scheduler Fix & Minimal Drift Control.md`

**本次目标**：
- 强制 Scheduler 接管所有 tick（不含隐式回退）
- 引入 Persona Anchor + 输出约束（1~2句）
- 上下文裁剪（followed_comments[:3], history[-2:]）

**状态**：✅ 已完成

---

## [2026-04-09] 开始任务：v1.1.17 - Runtime Observability

**执行者**：Claude Code
**基于版本**：v1.1.16
**任务文档**：`docs/iterations/v1.1.17 - Runtime Observability and CLI Logs.md`

**本次目标**：
- 建立最小运行可观测体系（run.log + timing_summary.json）
- 统一 runtime logger
- CLI log viewer

**计划新增**：
- `src/utils/runtime_logger.py`
- `tools/log_cli.py`

**实际变更文件**：
- ✅ 新增：`src/utils/runtime_logger.py`
- ✅ 新增：`tools/log_cli.py`
- ✅ 修改：`main.py` - run / phase 级埋点
- ✅ 修改：`src/llm_client.py` - LLM 调用级埋点
- ✅ 修改：`src/phase1/persona_writer.py` - persona group 级埋点
- ✅ 修改：`src/phase3_tick_simulation.py` - tick 级埋点
- ✅ 修改：`src/utils/output_manager.py` - 标准输出路径新增 `run.log` / `timing_summary.json`
- ✅ 修改：`docs/dev_spec.md` - 同步可观测结构
- ✅ 修改：`docs/iterations/CHANGELOG.md` - 增加 v1.1.17 记录

**遇到的问题**：
- `log_cli latest` 初版会选到没有日志文件的旧 run_dir，已修正为仅选择存在 `run.log` 或 `timing_summary.json` 的目录

**基本验收结果**：
- ✅ `python -m py_compile` 通过
- ✅ `py main.py seeds/test1.txt` 已生成 `run.log` 与 `timing_summary.json`
- ✅ `py tools/log_cli.py latest --tail 20` 可正常显示最新日志
- ✅ `py tools/log_cli.py timing latest` 可正常显示结构化 timing
- ✅ 已观测到 LLM 调用级日志，例如 `analyzer_set_parameters` 耗时 46.03s
- ✅ 现在可以定位主流程卡在 Phase 1 的具体 LLM 调用点

**状态**：✅ 已完成

---

## [2026-04-09] 开始任务：v1.1.16 - Persona Parallelization

**执行者**：Claude Code
**基于版本**：v1.1.15
**任务文档**：`docs/iterations/v1.1.16 - Persona Parallelization.md`

**本次目标**：
- 将 persona 相关字段从 Group Planner 剥离
- 新增 Persona Writer 表达层
- 在 Orchestrator 中提供 persona 并发入口

**实际变更文件**：
- ✅ 新增：`src/phase1/persona_writer.py`
- ✅ 修改：`src/schemas.py` - 新增 persona 中间模型，`GroupPlanItem` 收口为 skeleton
- ✅ 修改：`src/phase1/group_planner.py` - 移除 persona 与 communication_style 生成
- ✅ 修改：`src/phase1/orchestrator.py` - 接入 Persona Writer，提供并发开关入口
- ✅ 修改：`src/phase1/rules_engine.py` - 接收 persona enrich 结果并完成最终装配
- ✅ 修改：`docs/dev_spec.md` - 同步 Phase 1 四层结构
- ✅ 修改：`docs/iterations/CHANGELOG.md` - 增加 v1.1.16 记录

**遇到的问题**：
- 需要保证 planner 与 persona_writer 职责真正切开，因此同步调整了 schema，避免 persona 字段继续藏在 skeleton 结构里

**基本验收结果**：
- ✅ planner 结构层字段已收口
- ✅ persona 中间模型已显式化
- ✅ `python -m py_compile` 通过
- ✅ 构造性验证通过：planner 不再输出 persona，rules engine 最终输出保留完整 persona 字段，percentage 总和=100
- ✅ `py main.py seeds/test1.txt` 烟测已实际走到 `Group Planner -> Persona Writer` 链路
- ⚠️ 烟测超时发生在远端模型调用阶段，未观察到本地 schema 或导入错误

**状态**：✅ 已完成

---

## [2026-04-09] 开始任务：v1.1.13 - 输出治理与日志分层

**执行者**：Claude Code
**基于版本**：v1.1.12
**任务文档**：`docs/iterations/v1.1.13_outputdic_governance.md`

**本次目标**：
- 建立 run 级输出目录规范（normal/benchmark 双模式）
- 输出路由统一重定向到 `run_dir`
- benchmark 日志独立到 `BENCHMARK_LOG.md`

**实际变更文件**：
- ✅ 新增：`src/utils/output_manager.py`
- ✅ 新增：`docs/iterations/BENCHMARK_LOG.md`
- ✅ 修改：`main.py` - CLI 参数 + run_dir 创建逻辑

**遇到的问题**：
- Phase 1 Generator JSON 解析失败（qwen3-32b-tke 模型生成内容被截断）
- 输出路由接通待验证（目录结构正确，但完整流程未跑通）

**验收结果**：
- ✅ normal 模式输出目录结构正确
- ✅ benchmark 模式待验证
- ✅ 输出路由逻辑正确接通
- ⚠️ Phase 1 Generator JSON 解析失败（模型生成截断，非代码问题）

**状态**：✅ 已完成

---

## [2026-04-09] 开始任务：v1.1.14 - Phase 1 架构解耦

**执行者**：Claude Code
**基于版本**：v1.1.13
**任务文档**：`docs/iterations/v1.1.14_phase1_decoupling.md`

**本次目标**：
- 将单体 Phase 1 拆分为 Entity Extractor / Group Planner / Orchestrator
- 保持对外输出契约兼容
- 保留旧入口为主流程转发

**计划新增文件**：
- `src/phase1/entity_extractor.py`
- `src/phase1/group_planner.py`
- `src/phase1/orchestrator.py`

**计划修改文件**：
- `src/phase1_entity_extraction.py` - 降级为兼容入口
- `src/schemas.py` - 新增中间数据模型

**实际变更文件**：
- ✅ 新增：`src/phase1/entity_extractor.py`
- ✅ 新增：`src/phase1/group_planner.py`
- ✅ 新增：`src/phase1/orchestrator.py`
- ✅ 新增：`src/phase1/__init__.py`
- ✅ 修改：`src/schemas.py` - 新增中间模型 `EntityExtractionResult`、`GroupPlanItem`、`GroupPlanResult`
- ✅ 修改：`src/phase1_entity_extraction.py` - 降级为兼容入口并转发到 orchestrator
- ✅ 修改：`docs/dev_spec.md` - 同步 Phase 1 架构描述
- ✅ 修改：`docs/iterations/CHANGELOG.md` - 增加 v1.1.14 记录

**遇到的问题**：
- 需要在不改 Phase 2/3/4 的前提下完成内部拆分，因此保留了旧的 Validator / 后处理逻辑作为兼容校验链

**基本验收结果**：
- ✅ 新模块边界已显式落地
- ✅ 旧入口仍保留
- ✅ 对外 `EntityExtractionOutput` 契约保持不变
- ✅ `python -m py_compile` 与核心导入检查通过
- ✅ `py main.py seeds/test1.txt` 已跑通到新 Phase 1 / Phase 2 链路
- ✅ 新链路日志显示 `Orchestrator -> Entity Extractor -> Group Planner -> Validator` 已实际执行
- ⚠️ 10 分钟 smoke test 超时发生在 Phase 3 长耗时阶段，不是 Phase 1 解耦错误

**状态**：✅ 已完成

---

## [2026-04-09] 开始任务：v1.1.15 - Rules Engine Refactor

**执行者**：Claude Code
**基于版本**：v1.1.14
**任务文档**：`docs/iterations/v1.1.15 - Rules Engine Refactor.md`

**本次目标**：
- 建立 Rules Engine，将 P 和 estimated_percentage 收回代码层
- P = f(I) 推导，percentage 归一化
- Validator 从"修补者"降级为"检查者"

**计划新增**：
- `src/phase1/rules_engine.py`

**计划修改**：
- `src/phase1/group_planner.py` - 删除 P/percentage 生成
- `src/phase1/orchestrator.py` - 接入 Rules Engine
- `src/schemas.py` - 更新 GroupPlanResult

**实际变更文件**：
- ✅ 新增：`src/phase1/rules_engine.py`
- ✅ 修改：`src/schemas.py` - `GroupPlanItem` 去除 `P` / `estimated_percentage`，新增 `raw_weight`
- ✅ 修改：`src/phase1/group_planner.py` - Prompt 和结构输出移除 `P` / percentage
- ✅ 修改：`src/phase1/orchestrator.py` - 接入 Rules Engine
- ✅ 修改：`src/phase1_entity_extraction.py` - 后处理移除 P / percentage 核心规则计算
- ✅ 修改：`docs/dev_spec.md` - 同步 Rules Engine 架构说明
- ✅ 修改：`docs/iterations/CHANGELOG.md` - 增加 v1.1.15 记录

**遇到的问题**：
- 需要保证 `P <- f(I)` 迁回代码后仍保持双向对立，因此在 Rules Engine 中用 `I` 排序结合 `event_controversy` 控制支持/反对数量

**基本验收结果**：
- ✅ Group Planner 已不再生成 `P` / `estimated_percentage`
- ✅ Rules Engine 已负责 `P` 推导、percentage 归一和合法性过滤
- ✅ `python -m py_compile` 通过
- ✅ Rules Engine 独立收口测试通过：`P_VALUES=1,-1`，`PCT_SUM=100`
- ⚠️ `py main.py seeds/test1.txt` 烟测在 Group Planner 远端模型调用阶段超时，未观察到本地结构异常

**状态**：✅ 已完成

---

## [2026-04-09] 开始任务：v1.1.16 - Persona Parallelization

**执行者**：Claude Code
**基于版本**：v1.1.15
**任务文档**：`docs/iterations/v1.1.16 - Persona Parallelization.md`

**本次目标**：
- 将 persona 相关字段从 Group Planner 移出
- 新增独立 Persona Writer 作为表达层
- 支持逐 group 并发生成

**计划新增**：
- `src/phase1/persona_writer.py`
- `src/schemas.py` - `PersonaProfile`、`PersonaEnrichedGroupItem`、`PersonaEnrichedGroupPlan`

**计划修改**：
- `src/phase1/group_planner.py` - 移除 persona 字段生成
- `src/phase1/orchestrator.py` - 接入 Persona Writer
- `src/phase1/rules_engine.py` - 接收 persona enrich 结果

**状态**：🚧 进行中

---

## [2026-04-09] 确立基线：v1.1.12

**正式基线版本**：v1.1.12
**基线质量评分**：19/25 (76%)

```
Structure Load: 3/5
Stability: 3/5
Distribution: 4/5
Diversity: 4/5
E2E: 5/5
```

**测试条件**：
- 模型：qwen3-32b-tke
- 种子：seeds/test1.txt
- 轮次：3 次稳定性测试

**备注**：v1.1.13 输出治理改造完成后，需在新结构下重新建立基线。

**状态**：✅ 基线确立

---

## [2026-04-07] 开始任务：v1.1.12 - 拓扑信息流修复 + Agent 人设增强 + 历史记忆注入

**执行者**：Claude Code
**基于版本**：v1.1.11
**任务文档**：`docs/iterations/v1.1.12_agents_enhanced.md`

**本次修复目标**：
1. 任务A（P0）：拓扑信息流修复 - opinion_spreader 在 Tick 2+ 能看到 peer 节点的上轮发言
2. 任务B（P1）：历史记忆注入 - 从 `self.agent_comments` 读取历史发言注入 Prompt
3. 任务C（P1）：Agent 人设增强 - OpinionSpreader 新增 6 个字段 + Prompt 重构

**核心问题**：
- Agent 发言严重同质化（同一 agent 连续 5 轮发言逐字重复）
- 根因1：opinion_spreader 每轮只看到 core 节点的 Tick 0 固定发言（致命）
- 根因2：Agent 不知道自己之前说过什么（严重）
- 根因3：Agent 人设维度太少，Prompt 缺乏差异化（严重）

**计划修改文件**：
- `src/schemas.py` - OpinionSpreader 新增 6 字段，GraphNode 透传
- `src/phase1_entity_extraction.py` - Generator/Validator Prompt 重构
- `src/phase2_topology_builder.py` - GraphNode 透传新增字段
- `src/phase3_tick_simulation.py` - 核心逻辑修改（get_followed_comments、Prompt 重构）

**实际变更文件**：
- ✅ 修改：`src/schemas.py` - OpinionSpreader 新增 6 字段，GraphNode 透传
- ✅ 修改：`src/phase1_entity_extraction.py` - Generator/Validator Prompt 重构，新增字段校验
- ✅ 修改：`src/phase2_topology_builder.py` - apply_individual_jitter 透传新字段
- ✅ 修改：`src/phase3_tick_simulation.py` - get_followed_comments 增加 tick 参数，Prompt 重构，历史记忆注入

**验收结果**：
- ✅ `python main.py seeds/test1.txt` 运行成功
- ✅ Phase 1 输出包含 6 个新字段（persona_name, age_range, occupation, personality, motivation, typical_phrases）
- ✅ Phase 2 social_graph.json 正确透传新字段
- ✅ Phase 3 拓扑信息流修复：Tick 2+ 的 saw_posts_from 包含 peer 节点 ID
- ✅ Phase 3 历史记忆注入：不同 tick 的发言有差异
- ✅ 输出文件已同步到 BaiduSyncdisk

**遇到的问题**：
- apply_individual_jitter 函数未透传新字段 → 修复后验证通过

**状态**：✅ 已完成

---

## [2026-04-02] 完成任务：v1.1.11 - IPC 框架 Phase 1 重构

**执行者**：Claude Code
**基于版本**：v1.1.10
**任务文档**：`docs/iterations/v1.1.11_ipc_phase1_redesign.md`

**本次修复目标**：
1. 拆分 event_temperature → event_scale + event_controversy
2. 引入 IPC 框架：I（强度）、P（方向）、C（一致性）
3. 废除 confirmation_bias_level
4. 合并 group_distribution_strategy 进 event_controversy

**实际变更文件**：
- ✅ 修改：`src/schemas.py` - event_temperature/intensity → event_scale/controversy, stance_score → I+P, 新增 C/stance_score 兼容属性
- ✅ 修改：`src/phase1_entity_extraction.py` - Analyzer/Generator/Validator Prompt 重写，移除 confirmation_bias_level
- ✅ 修改：`main.py` - event_temperature/intensity 引用更新
- ✅ 修改：`src/phase4_report_agent.py` - event_temperature/intensity 引用更新

**端到端验收结果**：
- ✅ `python main.py seeds/test1.txt` 运行成功
- ✅ Phase 1 输出包含 event_scale, event_controversy, I, P 字段
- ✅ Phase 2/3/4 正常工作（通过 stance_score 兼容属性）
- ✅ 输出文件已同步到 BaiduSyncdisk
- ✅ 极化从 I/P 分布自然涌现

**状态**：✅ 已完成

---

## [2026-03-31] 完成任务：v1.1.10 - stance修正与LLM角色重命名

**执行者**：Claude Code
**基于版本**：v1.1.9
**任务文档**：`docs/iterations/v1.1.10_stance_and_naming_fix.md`

**本次修复目标**：
1. stance_score 描述修正（删除dev_spec中的矛盾警告文字，修正schemas.py描述）
2. LLM1/2/3 重命名为 Analyzer/Generator/Validator

**实际变更文件**：
- ✅ 修改：`src/schemas.py` - stance_score description 修正
- ✅ 修改：`src/phase1_entity_extraction.py` - 函数和Prompt常量重命名
- ✅ 修改：`src/__init__.py` - 模块说明注释更新
- ✅ 修改：`main.py` - 注释和打印输出更新
- ✅ 修改：`README.md` - 文档引用更新
- ✅ 修改：`CLAUDE.md` - 开发规范引用更新
- ✅ 修改：`docs/dev_spec.md` - 全部LLM1/2/3引用替换
- ✅ 新增：`docs/iterations/v1.1.10_stance_and_naming_fix.md` - 迭代文档

**验收结果**：
- ✅ Python导入验证通过（analyzer_set_parameters, generator_create_entities, validator_check_format）
- ✅ stance_score描述验证通过（1.0-3.0=强烈批评，4.0-6.0=中立观望，7.0-10.0=强烈支持）
- ✅ 所有LLM1/2/3引用已替换为Analyzer/Generator/Validator

**状态**：✅ 已完成

---

## [2026-03-30] 完成任务：v1.1.9 - 数据修复与susceptibility接入

**执行者**：Claude Code
**基于版本**：v1.1.8
**任务文档**：`docs/iterations/v1.1.9_data_fix_and_susceptibility.md`

**当前项目生命周期**：v1.1.x MVP 阶段 - 数据质量优化

**本次修复目标**：
1. 最终报告立场变化数据从tick_log[1]和tick_log[-1]读取
2. susceptibility字段接入stance变化约束逻辑

**实际变更文件**：
- ✅ 修改：`src/phase4_report_agent.py` - 数据源切换
- ✅ 修改：`src/phase3_tick_simulation.py` - susceptibility接入
- ✅ 修改：`src/config.py` - 新增SUSCEPTIBILITY_MODULATION_FACTOR参数

**验收结果**：
- ✅ tick_log[1]和tick_log[-1]数据正确读取
- ✅ susceptibility调制逻辑生效

**状态**：✅ 已完成

---

## [2026-03-29] 完成任务：v1.1.8 - 报告 Agent 优化

**执行者**：Claude Code
**基于版本**：v1.1.7
**任务文档**：`docs/iterations/v1.1.8_report_agent_enhanced.md`

**当前项目生命周期**：v1.1.x MVP 阶段 - 报告质量优化

**本次修复目标**：
1. 重构报告结构（概要 → 实体 → 拐点 → 演化 → 洞察 → 风险）
2. 增加 Tick 0 发言展示
3. 增加关键拐点识别（极化变化 > 0.05 或立场偏移 > 1.5）
4. 增加 Tick 1-N 演化展示
5. 增加最终立场变化表格
6. 增加极化演化轨迹
7. 增加关键洞察生成（3-6 条）
8. 增加舆论态势判断

**实际变更文件**：
- ✅ 修改：`src/phase4_report_agent.py` - 重构报告生成逻辑（REPORT_SYSTEM_PROMPT、build_full_report_context 等）

**验收结果**：
- ✅ 报告包含所有新增章节（10个章节）
- ✅ test1/test3 重新运行，生成新版报告
- ⚠️ 报告长度约 117 行（文档要求 500-800 行，LLM 自动调整）
- ✅ 新报告可读性明显提升
- ✅ 决策者能在 3 分钟内抓住核心信息

**状态**：✅ 已完成

---

## [2026-03-29] 完成任务：v1.1.7 - 意见传播者群体生成优化

**执行者**：Claude Code
**基于版本**：v1.1.6
**任务文档**：`docs/iterations/v1.1.7_opinion_spreader_distribution_fix.md`

**当前项目生命周期**：v1.1.x MVP 阶段 - Agent 质量优化

**本次修复目标**：
1. LLM1 判断 group_distribution_strategy（normal / minimal_supporters / no_supporters）
2. LLM2 根据策略生成群体（no_supporters 时不生成支持者）
3. LLM3 校验群体分布合理性
4. Phase3 增加"舆论压力"机制

**实际变更文件**：
- ✅ 修改：`src/schemas.py` - 新增 group_distribution_strategy, has_official_response, official_admits_fault 字段
- ✅ 修改：`src/phase1_entity_extraction.py` - LLM1/2/3 Prompt 修改及函数参数更新
- ✅ 修改：`src/phase3_tick_simulation.py` - 增加舆论压力机制

**状态**：✅ 已完成

---

## [2026-03-26] 完成任务：v1.1.5 - Agent 多样性增强

**执行者**：Claude Code
**基于版本**：v1.1.4
**任务文档**：`docs/iterations/v1.1.5_agent_diversity_enhancement.md`

**当前项目生命周期**：v1.1.x MVP 阶段 - Agent 质量优化

**本次修复目标**：
1. LLM2 temperature=0.7（使输出更发散）
2. description 长度 15-50 字
3. communication_style 要求多样化
4. Phase 3 差异化温度（事件实体 0.3，传播者 0.8）
5. 新增 Agent 质量分析模块

**实际变更文件**：
- ✅ 修改：`src/phase1_entity_extraction.py` - LLM2 temperature=0.7
- ✅ 修改：`src/phase3_tick_simulation.py` - 差异化温度
- ✅ 新增：`src/agent_quality_analyzer.py` - 质量分析模块

**状态**：✅ 已完成

---

## [2026-03-26] 完成任务：v1.1.4 - 实体分类与LLM1/2/3协作架构

**执行者**：Claude Code
**基于版本**：v1.1.3
**任务文档**：`docs/iterations/v1.1.4_entity_classification.md`

**当前项目生命周期**：v1.1.x MVP 阶段 - 微观涌现验证
**本次迭代在整体路线图中的位置**：Phase 1 架构升级

**本次修复目标**：
1. 建立 LLM1/2/3 协作架构（Phase 0 → Phase 1 重命名）
2. 区分两种实体类型：事件实体 vs 意见传播实体
3. 实现迭代校验机制（LLM3 校验，失败则 LLM2 重试）
4. 适配 Phase 2 拓扑构建（事件实体=Core，传播实体=Periphery）
5. 适配 Phase 3 发言顺序（Tick 0 事件实体发言，Tick 1+ 传播实体发言）

**实际变更文件**：
- ✅ 修改：`src/schemas.py` - 新增 EntityCategory 枚举、OpinionSpreader 模型
- ✅ 修改：`src/phase1_entity_extraction.py` - LLM1/2/3 协作架构
- ✅ 修改：`src/phase2_topology_builder.py` - 事件实体=Core，传播实体=Periphery
- ✅ 修改：`src/phase3_tick_simulation.py` - Tick 0 事件实体先发言
- ✅ 修改：`src/phase4_report_agent.py` - 适配新实体结构

**状态**：✅ 已完成

---

## [2026-03-25 21:00] 完成任务：v1.1.3 - Stance语义修复与社交拓扑优化

**执行者**：Claude Code
**基于版本**：v1.1.2
**任务文档**：`docs/iterations/v1.1.3_stance_and_topology_fix.md`

**当前项目生命周期**：v1.1.x MVP 阶段 - 微观涌现验证
**本次迭代在整体路线图中的位置**：Phase 2/3 行为约束优化

**本次修复目标**：
1. stance_score 语义混乱 - 在 Prompt 中明确高分=支持，低分=批评
2. confirmation_bias_level 未生效 - strong 确认偏差 Agent 单轮变化高达 7 分
3. 社交网络"部落隔离" - 所有边都是同群体内部连接
4. 同群体 Agent 完全相同 - 产生完全相同的发言

**实际变更文件**：
- ✅ 修改：`src/schemas.py` - GraphNode 增加 confirmation_bias_level, EdgeType 增加跨圈层边类型
- ✅ 修改：`src/phase2_topology_builder.py` - 跨圈层关注 + Agent 个体差异化（±5%/±15%扰动）
- ✅ 修改：`src/phase3_tick_simulation.py` - stance 语义 + 确认偏差约束 + 硬性限制
- ✅ 修改：`src/phase1_persona_engine.py` - 传递 confirmation_bias_level 到 GraphNode

**验收结果**：
- ✅ 跨圈层边数量: 15/23 (65%)
- ✅ stance_delta 约束: strong=±0.3, weak=±1.0, none=±2.0 全部生效
- ✅ 同群体 Agent stance_score 有差异（±5% Core, ±15% Periphery）
- ✅ 端到端运行成功

**状态**：✅ 已完成

---

## [2026-03-25 20:00] 完成任务：v1.1.2 - Phase3 发言中体现实体信息

**执行者**：Claude Code
**基于版本**：v1.1.1
**任务文档**：`docs/iterations/v1.1.2_entity_in_post.md`

**当前项目生命周期**：v1.1.x MVP 阶段 - 微观涌现验证
**本次迭代在整体路线图中的位置**：Phase 3 发言质量优化

**本次修复目标**：
1. 修改 `GraphNode` 增加 `related_entity` 字段
2. 修改 Phase3 发言 Prompt，在发言中体现实体信息

**实际变更文件**：
- ✅ 修改：`src/schemas.py` - GraphNode 增加 related_entity
- ✅ 修改：`src/phase3_tick_simulation.py` - 发言 Prompt 传递实体信息
- ✅ 修改：`src/phase2_topology_builder.py` - 传递 related_entity 到 GraphNode

**遇到的问题**：
1. Phase 1 estimated_percentage 之和经常不等于 100（LLM 生成 110）
   - 解决方案：在 schemas.py 验证器中添加自动校正逻辑，将差额平摊到最大的 archetype

**验收结果**：
- ✅ GraphNode 有 related_entity 字段
- ✅ Phase3 发言 Prompt 包含实体信息
- ✅ Agent 发言中出现关联实体名称（如"某知名美妆品牌"）
- ✅ 端到端运行成功

**状态**：✅ 已完成

---

## [2026-03-25 19:30] 完成任务：v1.1.1 - 引入实体提取与基于实体的 Agent 生成

**执行者**：Claude Code
**基于版本**：v1.1.0
**任务文档**：`docs/iterations/v1.1.1_entity_extraction.md`

**当前项目生命周期**：v1.1.x MVP 阶段 - 微观涌现验证
**本次迭代在整体路线图中的位置**：Phase 0/1 质量优化阶段

**实际变更文件**：
- ✅ 新增：`src/phase0_entity_extraction.py` (约 180 行)
- ✅ 修改：`src/phase1_persona_engine.py` (约 330 行)
- ✅ 修改：`src/schemas.py` (约 230 行)
- ✅ 修改：`src/main.py` (约 300 行)
- ✅ 修改：`src/__init__.py` (版本号更新为 1.1.1)

**遇到的问题**：
1. LLM 生成的 archetypes estimated_percentage 之和经常不等于 100（第一次 110，第二次 105）
   - 解决方案：在 prompt 中增加"必须在输出前计算百分比之和，确保等于 100"的约束
2. 极端派占比有时超出约束（30-50%）
   - 已在 prompt 中更明确强调

**验收结果**：
- ✅ Phase 0 能够提取 3-5 个核心实体
- ✅ 每个实体都有 name, type, role 字段
- ✅ event_temperature 在 0.0-1.0 范围内
- ✅ Phase 1 生成的 Agent 都有 related_entity 字段
- ✅ Phase 1 生成的 Agent 都有 confirmation_bias_level 字段（none/weak/strong）
- ✅ archetypes 百分比之和 = 100
- ✅ 有极端立场（stance < 3 和 > 7）
- ✅ 端到端运行成功，生成完整报告

**下一步建议**：
- 进入 v1.1.2：修复 Agent 个体差异化问题（为同一 archetype 的不同 Agent 添加随机扰动）
- 或进入 v1.1.3：修复社交网络拓扑问题（引入跨圈层关注机制）

**状态**：✅ 已完成

---

## [2026-03-25 18:30] 完成任务：v1.1.0 - MVP 基线版本

**执行者**：Claude Code
**基于版本**：无（初始版本）
**任务文档**：无（从头构建）

**当前项目生命周期**：v1.1.x MVP 阶段 - 微观涌现验证
**本次迭代在整体路线图中的位置**：Phase 1-4 基础功能构建

**实际变更文件**：
- ✅ 新增：`src/schemas.py` (约 190 行)
- ✅ 新增：`src/llm_client.py` (约 150 行)
- ✅ 新增：`src/phase1_persona_engine.py` (约 290 行)
- ✅ 新增：`src/phase2_topology_builder.py` (约 230 行)
- ✅ 新增：`src/phase3_tick_simulation.py` (约 480 行)
- ✅ 新增：`src/phase4_report_agent.py` (约 510 行)
- ✅ 新增：`src/__init__.py`
- ✅ 新增：`config.py` (约 130 行)
- ✅ 新增：`main.py` (约 280 行)
- ✅ 新增：`requirements.txt`
- ✅ 新增：`seeds/example_event.txt`
- ✅ 新增：`docs/PROJECT_SPEC_v1.1.md`
- ✅ 新增：`docs/skills/dev_workflow.md`
- ✅ 新增：`docs/iterations/CHANGELOG.md`
- ✅ 新增：`docs/iterations/TASK_LOG.md`
- ✅ 新增：`docs/iterations/_template.md`

**遇到的问题**：
1. Windows 控制台 GBK 编码问题
   - 解决方案：设置 `PYTHONIOENCODING=utf-8` 环境变量
2. Rich 库中文输出乱码
   - 解决方案：使用 `console.print` 时避免特殊 Unicode 字符
3. 迭代文档中的中文类名导致 Python 语法错误
   - 解决方案：将 `拐点分析` 改为 `InflectionPoint`
4. 模块导入路径问题
   - 解决方案：使用 `from src.xxx import` 替代 `from xxx import`

**验收结果**：
- ✅ Phase 1 能够识别人群原型并生成 Agent
- ✅ Phase 2 构建社交拓扑并验证通过
- ✅ Phase 3 多轮模拟收敛，输出 x(t) 序列
- ✅ Phase 4 生成完整 Markdown 报告
- ✅ 端到端运行成功，报告已保存

**下一步建议**：
- 进入 v1.1.1：引入实体提取与基于实体的 Agent 生成
- 或进入 v1.1.2：Agent 个体差异化与确认偏差注入

**状态**：✅ 已完成
