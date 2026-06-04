# Adarian Current E2E Candidate Baseline Audit

## 1. Executive Verdict

- **Baseline Verdict:** pass_with_known_issues
- **Current Status:** E2E 可跑通，Phase 1-4 产物齐全，所有源文件编译通过，tick 模拟数据完整，LLM 报告质量达标
- **Can Freeze as Baseline:** 可以，但必须以文档记录已知问题
- **Main Reason:** 缺失 run_dir / run.log / timing_summary.json 的根本原因是 RuntimeLogger 存在且功能完整但未接入 main.py 主调用链，属可观测能力回退而非数据产出失败
- **Unique Next Action:** 下一版本将 RuntimeLogger.configure(run_dir) 接入 main.py，补回运行目录隔离与结构化日志

## 2. Evidence Scope

### Authoritative Evidence

1. 当前工作区源码（12 个 .py 源文件，全部 py_compile 通过）
2. git status（已修改工作区，"retoreshitmountaion" 为最新 commit）
3. outputs/ 实际产物（含 root 级别和 run_test3_20260424_163044/ 两份）
4. py -3 命令行可复现结果

### Non-authoritative Historical References

以下材料经确认后仅作背景参考，不作为 baseline 判定依据：

- CLAUDE.md、README.md、docs/ 目录下旧迭代文档
- 旧 TASK_LOG、CHANGELOG
- profiling/ 目录历史数据

### Commands / Checks Performed

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 所有源文件编译 | `py -3 -m py_compile` × 12 文件 | 全部通过 |
| config 导入 | `py -3 -c "import config"` | 通过 |
| tick_logs 数据完整性 | JSON 解析 + 字段验证 | 6 个 tick (0-5)，所有条目完整 |
| entities 数据完整性 | JSON 解析 + 字段验证 | 4 事件实体 + 7 传播者，P 双向对立通过 |
| final_report.md 质量 | 直接读取 | 565 行，结构完整 |
| 输出文件对比 | root vs run_test3 文件大小比较 | 完全相同（重复写入） |
| Git 状态 | `git status --short` | 工作区修改 + 未跟踪目录 |
| Dead code 检测 | Grep × 3 次 | 确认 AGENT_POST_*_PROMPT 为死代码 |

## 3. E2E Evidence Completeness

### Known Missing Evidence

| 缺失项 | 路径 | 严重度 |
|--------|------|--------|
| run_dir | 不存在 | 中 |
| run.log | 不存在 | 中 |
| timing_summary.json | 不存在 | 中 |

### Actual Outputs Found

**Root outputs/：**
- entities_and_relations.json（7865 B）
- social_graph.json（8739 B）
- tick_logs.json（35166 B）
- final_report.json（1645 B）
- final_report.md（26346 B）

**run_test3_20260424_163044/：**
- entities_and_relations.json（7865 B，与 root 相同）
- social_graph.json（8739 B，与 root 相同）
- tick_logs.json（35166 B）
- tick_logs/ 目录（含 tick_0.json 到 tick_5.json）
- final_report.json（1645 B）
- final_report.md（26346 B，与 root 相同）
- seed_test3.txt（690 B，种子副本）

### Phase 1-4 Completion Evidence

| Phase | 产物 | 状态 | 证据 |
|-------|------|------|------|
| Phase 1 | entities_and_relations.json | 完整 | 4 事件实体（含 can_speak 标记）、7 意见传播者（含 I/P/susceptibility/persona 全套字段）、11 条关系、event_scale=0.85、event_controversy=0.88 |
| Phase 2 | social_graph.json | 完整 | 11 节点（4 Core + 7 Periphery）、边连通性通过 |
| Phase 3 | tick_logs.json + tick_logs/ | 完整 | 6 个 tick (0-5)，每 tick 含完整 AgentEntry（stance, comment, reasoning, change_reason）、GlobalMetrics（mean_stance, std_stance, polarization_index） |
| Phase 4 | final_report.md + final_report.json | 完整 | 565 行 Markdown，涵盖 10 个报告章节；JSON 含 emotion_trajectory、inflection_points、risk_level |

**数据质量验证：**
- Tick 0: 4 entries (4 active, 0 silent), mean=4.20, pol=0.35
- Tick 1: 7 entries (6 active, 1 silent), mean=4.31, pol=0.40
- Tick 2: 7 entries (6 active, 1 silent), mean=4.26, pol=0.42
- Tick 3: 7 entries (5 active, 2 silent), mean=4.26, pol=0.48
- Tick 4: 7 entries (5 active, 2 silent), mean=4.22, pol=0.49
- Tick 5: 7 entries (5 active, 2 silent), mean=4.32, pol=0.51

极化指数从 0.35 升至 0.51，变化连续无断层，active/silent 分布合理，无异常空结果或超时。

### Root Cause of Missing run_dir / run.log / timing_summary.json

**根因：RuntimeLogger 存在但未接入 main.py 主调用链。**

证据链：

1. `src/utils/runtime_logger.py`（223 行）定义了完整的 `RuntimeLogger` 类，包含 `configure(run_dir)` 方法——调用后会创建 `{run_dir}/run.log` 和 `{run_dir}/timing_summary.json`
2. `main.py` 全文无任何 `from src.utils.runtime_logger import ...` 语句——`RuntimeLogger` 从未被 main.py 导入或配置
3. `src/llm_client.py` 和 `src/phase3_tick_simulation.py` 中确实调用了 `get_runtime_logger()`，但由于 `configure()` 从未被调用，`self.log_path` 和 `self.timing_path` 均为 `None`，`_append_log()` 和 `_write_summary()` 的第一行检查 `if not self.log_path: return` 直接返回，所有日志写入均为空操作
4. `main.py` 无任何 `run_dir` 概念——所有 Phase 输出直接写入 config 定义的静态路径（`outputs/entities_and_relations.json`、`outputs/social_graph.json` 等），无运行目录隔离

**分类：runtime logger 未接入（属于可观测能力回退，非数据产出故障）。**

### Impact on Baseline Freeze

缺失 run.log 和 timing_summary.json **不阻止 baseline freeze**，因为：

- Phase 1-4 核心数据产物完整且质量达标
- LLM 调用通过 `_diag_log` 的 `print()` 输出仍可观察
- Phase 耗时在 console 输出中仍然可见
- 运行结果可通过 tick_logs.json 和 final_report.md 复盘

但此缺失会导致：无法回放单次运行的精确时间线、无法比较多次运行的 LLM 调用次数和耗时、无法结构化检索运行事件。

## 4. Main Pipeline Architecture Audit

### main.py Actual Call Chain

```
main()
  ├─ ensure_dirs()
  ├─ init_llm_client()
  ├─ run_phase1(seed_file)
  │    └─ extract_entities_from_file() → extract_entities_with_validation()
  │         ├─ analyzer_set_parameters()         [LLM call 1: Analyzer]
  │         ├─ generator_create_entities()        [LLM call 2: Generator, 重试最多 3 轮]
  │         ├─ validator_check_format()           [LLM call 3: Validator]
  │         └─ save_entities_output()
  ├─ run_phase2(extraction_output)
  │    └─ build_topology_from_extraction() → build_topology()
  │         ├─ validate_topology()
  │         └─ save_social_graph()
  ├─ run_phase3(extraction_output, phase2_output, seed_text)
  │    └─ SimulationEngine.run_simulation()
  │         ├─ run_tick_0()                       [LLM call: 事件实体发言]
  │         └─ for tick in 1..max_ticks:
  │              └─ run_tick(tick)
  │                   ├─ select_speakers()
  │                   ├─ generate_opinion_spreader_post()  [LLM call: 传播者发言]
  │                   │    └─ build_lightweight_context()
  │                   └─ update_silent_agent()
  │         └─ save_tick_logs()
  ├─ run_phase4(extraction_output, tick_logs, x_t_sequence)
  │    └─ generate_report_with_llm()              [LLM call: 报告生成]
  │         ├─ save_report()
  │         └─ save_markdown_report()
  └─ [console 输出计时摘要]
```

**调用链与源码一致，无结构漂移。**

### Phase 1 Status

- **稳定。** Analyzer → Generator → Validator 三阶段协作架构工作正常
- Generator 使用独立的 `LLMClient(temperature=0.7)` 而非全局单例，差异化温度设计合理
- `_post_process_entities()` 自动修正 can_speak 和 original_statement，防御性后处理有效
- 最大 3 轮重试，Validator 校验失败时有明确的反馈链路
- 遗留注释（line 21-22）指出的 `src/phase1/` 迁移未完成，但当前代码自包含、无外部依赖断裂

### Phase 2 Status

- **稳定。** 拓扑构建规则清晰：Core-Core 互关 + Periphery→Core 必须关注 + Periphery-Peripery 可选 30%
- `apply_individual_jitter()` 差异化扰动（Core ±5%, Periphery ±15%）正常工作
- `validate_topology()` 包含 4 项验收标准（角色检查、关注关系、连通性）
- 无 LLM 依赖，纯确定性算法

### Phase 3 Status

- **稳定但含死代码。** `SimulationEngine` 核心逻辑完整：
  - Tick 0：事件实体发言（含 can_speak 检查 + original_statement 优先）
  - Tick N：自适应 speaker selection + 意见传播者发言 + 静默 agent 漂移
  - `apply_stance_constraint()` 进行 susceptibility 调制的 stance 变化硬约束
  - `get_followed_comments()` v1.1.12 拓扑信息流修复（Tick 2+ 可见 peer 发言）
- **死代码问题：** `AGENT_POST_SYSTEM_PROMPT`（line 126-158）和 `AGENT_POST_USER_PROMPT`（line 160-178）未被使用——实际 prompt 由 `src/phase3/context_builder.py:build_lightweight_context()` 动态构造
- `EVENT_ENTITY_POST_SYSTEM_PROMPT`（line 92-122）仍在使用（Tick 0），非死代码

### Phase 4 Status

- **稳定。** LLM 报告生成 + fallback 机制 + Markdown 保存
- `_llm_generated_markdown` 模块级全局变量用于跨函数传递——不够优雅但功能正常
- `generate_fallback_report()` 兜底机制有效，当 LLM 报告过短时自动降级
- `parse_llm_report_response()` 依赖 `load_phase2_output()` 读取文件而非传入参数——耦合度偏高但功能可接受

### Main-chain Architecture Risk

- **无架构级 blocker。** 主链路 Phase 1→2→3→4 数据流清晰，各 Phase 接口明确
- **轻微风险点：**
  1. Phase 1 输出写入静态路径（config.ENTITIES_OUTPUT_PATH），后续 Phase 隐式依赖该路径而非显式传入——如果未来支持并行运行会冲突
  2. Phase 4 的 `parse_llm_report_response()` 内部调用 `load_phase2_output()` 读取文件而非使用已加载数据——多余的 I/O 和隐式依赖
  3. `_llm_generated_markdown` 模块级全局变量——函数纯度受损，但不影响正确性

## 5. Module-level Decoupling Audit

### Modules That May Need Decoupling

| 模块 | 位置 | 问题 |
|------|------|------|
| runtime_logger | src/utils/runtime_logger.py | 完整实现但未接入 main.py，所有日志写入为空操作 |
| context_builder | src/phase3/context_builder.py | 新的轻量 prompt 构造方式与 phase3_tick_simulation.py 中的旧 AGENT_POST_*_PROMPT 模板并存，后者为死代码 |
| phase1_entity_extraction | src/phase1_entity_extraction.py | 包含 `# LEGACY FILE — v1.1.14+ 已迁移到 src/phase1/` 注释但 src/phase1/ 目录不存在——迁移未完成 |

### Baseline-blocking Module Issues

**无。** 所有模块问题均为可观测性或代码清洁度问题，不阻止基线产出。

### Baseline-after Module Issues

1. **runtime_logger 接入 main.py**（下一版本必须处理）：在 `main()` 中创建 run_dir、调用 `logger.configure(run_dir)`、在 run_start/run_end 和每个 Phase start/end 处记录
2. **死代码清理**（下一版本建议处理）：移除 `phase3_tick_simulation.py` 中未使用的 `AGENT_POST_SYSTEM_PROMPT` 和 `AGENT_POST_USER_PROMPT`
3. **Phase 1 遗留迁移标记处理**（可延后）：确认 `src/phase1/` 迁移计划是否仍需执行

### Modules Not Worth Touching Now

1. `src/phase0_entity_extraction.py`：旧版本实体提取模块，未被 main.py 导入，保留作为历史参考
2. `src/agent_quality_analyzer.py`：Agent 质量分析工具，未被 main.py 导入，保留作为独立工具
3. `scripts/probes/` 目录下的 prompt probe 脚本：独立测试工具，不阻塞主线

## 6. Output & Observability Governance Audit

### Current Output Problems

| 问题 | 严重度 | 影响 |
|------|--------|------|
| 无运行目录隔离 | 高 | 每次运行覆盖 root outputs/，无法回放历史运行 |
| root outputs 与 run_test3 目录并存且内容相同 | 中 | 混淆权威数据源 |
| 历史输出目录堆积（output1, outputs_test2, outputs_test3 等 9+ 个目录） | 中 | 无法区分有效运行和测试残留 |
| tick_logs.json 与 tick_logs/ 目录数据重复 | 低 | 两份相同数据，维护负担 |
| 无 normal/benchmark 分区 | 中 | 无法区分正式运行和基准测试 |
| 旧路径兼容输出残留（如 outputs_test2 中的 .md 文档混入输出目录） | 低 | 非运行产物污染输出空间 |

### Is Current Output Too Dirty / Scattered / Hard to Replay?

**是。** 当前产出方式存在以下复盘困难：

- **难以回放一次 E2E：** 无 run.log 记录事件顺序，只能靠 tick_logs.json 反推
- **难以比较多次 E2E：** 无结构化 timing 数据，无运行元信息区分
- **难以定位 Phase/LLM/tick 层级问题：** 无分层日志，出错时只能从 console 输出回溯
- **多次运行互相污染：** 静态路径写入导致后续运行覆盖前次运行产物

**判定：产出治理已成为下一版本必须处理的问题。**

### JSON Responsibility

应记录的 JSON 字段：run_meta（run_id, seed, model, version, git_commit, start_time, end_time, status）、phase 状态（phase1/2/3/4 各阶段的 start/end/duration/status）、LLM 调用记录（caller, model, elapsed, timestamp, token_usage）、parser/validator/retry 事件（phase, attempt, error_type, passed）、tick 状态（tick_index, speaker_count, silent_count, polarization_index, mean_stance）、error/timeout/fallback 事件（stage, error_type, message, timestamp）

### CSV Responsibility

应记录的 CSV 字段：多次运行横向对比表，列包括 run_id, seed, model, version, git_commit, phase1_duration, phase2_duration, phase3_duration, phase4_duration, total_duration, llm_call_count, tick_count, final_polarization, final_mean_stance, risk_level, status

### Markdown Responsibility

应记录的 Markdown：baseline audit report（本次审计报告）、human-readable summary（每 run 一句话摘要 + 关键指标）、diagnosis（异常诊断报告）、risk list（关注事项列表）、next action（明确下一步动作）

### run.log Responsibility

应记录的顺序事件流：RUN START → PHASE 1 START → LLM CALL (Analyzer) → LLM END → LLM CALL (Generator) → LLM END → LLM CALL (Validator) → LLM END → PHASE 1 END → PHASE 2 START → PHASE 2 END → PHASE 3 START → TICK 0 START → TICK 0 END → TICK 1 START → SPEAKER SELECTION → LLM CALL → TICK 1 END → ... → PHASE 3 END → PHASE 4 START → LLM CALL (Report) → PHASE 4 END → RUN END → 所有 retry/exception/output_write 事件

### Need for Unified Schema

**需要但不宜过度设计。** 建议统一 JSON schema 包含上述字段，CSV 和 Markdown 各自从同一份 JSON 派生，避免维护多份不一致的数据提取逻辑。run.log 保持为文本流，与结构化 JSON 互补。

## 7. White-box Testing Field Requirements

### Required Fields

| 字段 | 说明 | 当前状态 |
|------|------|----------|
| seed | 种子文件名 | 仅在 console 输出 |
| model | LLM 模型名 | 仅在 console 输出 |
| version | 代码版本号 | 无记录 |
| run_id | 运行唯一标识 | 无记录 |
| git_commit | 当前 commit hash | 无记录 |
| git_dirty | 工作区是否干净 | 无记录 |
| phase1_duration | Phase 1 耗时 | 仅在 console 输出 |
| phase2_duration | Phase 2 耗时 | 仅在 console 输出 |
| phase3_duration | Phase 3 耗时 | 仅在 console 输出 |
| phase4_duration | Phase 4 耗时 | 仅在 console 输出 |
| total_duration | 总耗时 | 仅在 console 输出 |
| llm_call_count | LLM 总调用次数 | RuntimeLogger 内部计数但不持久化 |
| llm_per_call_elapsed | 每次 LLM 调用耗时 | RuntimeLogger 记录但不持久化 |
| parser_failure_count | JSON 解析失败次数 | 无记录 |
| validator_failure_count | Validator 校验失败次数 | 无记录 |
| retry_count | Phase 1 Generator 重试次数 | 无记录 |
| tick_count | tick 总数 | tick_logs.json 可计数 |
| tick_polarization | 每 tick 极化指数 | tick_logs.json 有 |
| tick_mean_stance | 每 tick 平均立场 | tick_logs.json 有 |
| selected_speaker_count | 每 tick 选中发言者数 | RuntimeLogger 记录但不持久化 |
| silent_agent_count | 每 tick 静默 agent 数 | tick_logs.json 可计数 |
| stance_drift_max | 最大立场漂移 | tick_logs.json 可计算 |
| global_metrics | 全局指标 | tick_logs.json 有 |
| output_completeness | 产出完整性标记 | 无记录 |
| error_count | 错误次数 | RuntimeLogger 记录但不持久化 |
| timeout_count | 超时次数 | 无记录 |
| final_e2e_status | E2E 状态（success/failure/partial） | 无记录 |

### Optional Fields

- token_usage（prompt_tokens, completion_tokens, total_tokens）：需 LLM provider 返回 usage 数据
- convergence_detection：当前收敛检测被注释掉（TODO），暂不需要
- memory_usage：非核心指标，可后续追加
- speaker_selection_ratio：已在 RuntimeLogger 中记录但不持久化

### Fields Not Recommended Yet

- 每个 agent 的完整 prompt 文本：过大，应放在 debug 模式
- 每轮 LLM 返回的原始 JSON：过大，应仅记录解析失败的情况
- 中间 stance 矩阵：可从 tick_logs.json 反推，无需重复存储
- ChromaDB 访问日志：非关键路径

## 8. CLI Engineer System Assessment

### Should Build CLI System?

**是，但仅限于最小范围。** 当前阶段不需要完整的 CLI 端工程师系统，但需要一个最小的命令行入口来替代手工检查 outputs/ 目录的工作流。

### Why

1. 当前复盘一次 E2E 需要手动打开 3-4 个 JSON/Markdown 文件
2. 比较两次运行结果需要手动 diff 文件
3. 无 run.log 时定位 LLM 错误只能看 console 回滚
4. 判断 baseline qualification 无自动化检查
5. 下一版本接入 RuntimeLogger 后需要工具读取结构化日志

### Minimal CLI Scope for Next Version

```
py -m adarian.cli run <seed>        # 运行 E2E（替代 py main.py seeds/test1.txt）
py -m adarian.cli log <run_id>      # 查看 run.log
py -m adarian.cli timing <run_id>   # 查看 timing_summary.json
py -m adarian.cli audit <run_id>    # 输出 baseline qualification check 结果
py -m adarian.cli compare <id1> <id2>  # 比较两次 E2E
```

只需 5 个命令，覆盖运行、日志查看、计时查看、基线检查、运行比较。

### What Not to Build Yet

- Web dashboard / GUI
- 实时 tick 可视化
- 历史运行数据库
- 自动化报警 / 阈值监控
- 多 seed batch 运行（先确保单 seed 可观测性）
- 分布式运行管理

## 9. Risk Classification

### Baseline前必须处理

**无。** 当前版本可以在记录已知问题的前提下 freeze 为 baseline。

### Baseline后可以处理

| 序号 | 事项 | 分类 | 优先级 |
|------|------|------|--------|
| 1 | RuntimeLogger 接入 main.py，创建 run_dir 隔离机制 | 可观测性修复 | P0 |
| 2 | 死代码清理：移除 phase3_tick_simulation.py 中未使用的 AGENT_POST_*_PROMPT | 代码清洁 | P1 |
| 3 | 输出目录治理：统一为 run_dir/{timestamp}_{seed}/ 结构，废弃静态路径写入 | 产出治理 | P1 |
| 4 | 历史输出目录清理：删除 output1, outputs_test2 等 9+ 个旧目录 | 产出治理 | P1 |
| 5 | 统一 JSON schema（run_meta + phases + llm_calls + ticks + errors） | 数据规范 | P1 |
| 6 | 白盒测试字段接入（至少覆盖 run_id, git_commit, llm_call_count, error_count） | 可观测性 | P2 |
| 7 | 最小 CLI 建设（run / log / timing / audit / compare） | 工程化 | P2 |
| 8 | Phase 4 parse_llm_report_response() 解耦：改为参数传入 phase2_output | 模块解耦 | P3 |
| 9 | Phase 1 遗留迁移标记处理（LEGACY FILE 注释） | 代码清洁 | P3 |
| 10 | tick_logs.json 与 tick_logs/ 目录去重 | 数据规范 | P3 |

### 不建议处理

| 序号 | 事项 | 原因 |
|------|------|------|
| 1 | 删除 phase0_entity_extraction.py / agent_quality_analyzer.py | 未被 main.py 导入，保留作为历史参考无副作用 |
| 2 | 清理 scripts/probes/ 目录 | 独立测试工具，不影响主线 |
| 3 | 重构 Phase 3 为重写架构 | 当前架构稳定，引入新架构会导致漂移 |
| 4 | 将 ChromaDB 接入 runtime logger | ChromaDB 目前未被主线使用（config 中有配置但 main.py 未初始化） |
| 5 | 引入 Pydantic 验证所有 LLM 输出 | 当前自由 JSON + 后处理模式足够，引入结构化输出会增加 prompt 复杂度 |
| 6 | 将 console 输出改为结构化 logging 框架 | 过度工程化，当前 print + Rich 足够观察 |

## 10. Final Decision

- **Final Verdict:** pass_with_known_issues — 当前版本具备 baseline freeze 资格，核心链路完整、产物齐全、编译通过
- **Single Blocker:** 无。缺失 run_dir / run.log / timing_summary.json 为运行时日志未接入所致，不阻止数据产出
- **Single Next Action:** 下一版本执行 RuntimeLogger 接入 main.py（创建 run_dir、配置 logger、在 run/phase 边界记录），补回可观测性
- **Do Not Do:** 不要在 baseline 前引入新架构、不要重构 Phase 3、不要建设完整 CLI 系统、不要删除历史遗留文件
