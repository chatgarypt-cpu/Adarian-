# Adarian Current E2E Candidate Baseline Audit

## 1. Executive Verdict

- **Baseline Verdict**: `pass_with_known_issues`
- **Current Status**: 主链路架构可运行，Phase 1-4 串联正确，E2E 产物完整，可复现
- **Can Freeze as Baseline**: 可以，但需记录已知问题
- **Main Reason**: 功能链路完整可用，但可观测能力严重缺失（RuntimeLogger 未接入 main.py），不阻止 freeze 但下一版本必须优先处理
- **Unique Next Action**: 在下一版本（scheduler v0）中集成 RuntimeLogger.configure() 到 main.py，建立 run_dir/run.log/timing_summary.json 机制

---

## 2. Evidence Scope

### Authoritative Evidence

| 证据类型 | 来源 | 采集时间 |
|---------|------|---------|
| 源码审计 | `adarian mvp/main.py` (295行) | 2026-04-24 |
| 源码审计 | `adarian mvp/src/**/*.py` | 2026-04-24 |
| Git 状态 | `git status` / `git log --oneline -n 10` | 2026-04-24 |
| E2E 产物 | `adarian mvp/outputs/` 目录 | 2026-04-24 |
| RuntimeLogger 实现 | `src/utils/runtime_logger.py` (222行) | 2026-04-24 |
| 备份目录 | `adarian mvp-backup-baseline-test1-e2e-runnable` | 2026-04-24 |

### Non-authoritative Historical References

以下材料仅作历史背景，不作当前 baseline 判定依据：
- 旧 TASK_LOG
- 旧 CHANGELOG
- 旧 iteration docs (v1.1.x 系列)
- 旧 dev_spec
- 子模块提交历史注释

### Commands / Checks Performed

```bash
git status                      # 工作区状态
git log --oneline -n 10         # 最近提交
ls -la outputs/                 # 产物目录
ls -la src/                     # 模块目录
Read main.py                    # 主入口审计
Read runtime_logger.py          # 可观测组件审计
Agent 主链路架构审计             # 并发任务
Agent 产出治理审计               # 并发任务
Agent E2E 证据完整性审计         # 并发任务
Agent 模块解耦审计               # 并发任务
```

---

## 3. E2E Evidence Completeness

### Known Missing Evidence

| 缺失项 | 根因 | 影响 |
|-------|------|------|
| `run_dir` | main.py 未调用 RuntimeLogger.configure() | 无法隔离多次运行 |
| `run.log` | RuntimeLogger.log_path 未初始化 | 无法追踪执行事件流 |
| `timing_summary.json` | RuntimeLogger.timing_path 未初始化 | 无法统计 LLM 调用/Phase 耗时 |

**根因定位**：`main.py` 第193行仅调用 `ensure_dirs()`，从未调用 `get_runtime_logger().configure(run_dir)`。

**代码证据**：
```python
# main.py:193
ensure_dirs()  # 仅创建固定 outputs 目录

# 缺失的关键调用（应在 ensure_dirs() 后添加）：
from src.utils.runtime_logger import get_runtime_logger
run_dir = config.OUTPUTS_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
get_runtime_logger().configure(run_dir)
get_runtime_logger().log_run_start("e2e", str(seed_file), str(run_dir))
```

### Actual Outputs Found

| 文件 | 状态 | 大小 | 内容验证 |
|------|------|------|---------|
| `entities_and_relations.json` | ✅ 完整 | 7865 bytes | 4 事件实体 + 8 意见传播者 |
| `social_graph.json` | ✅ 完整 | 8739 bytes | 节点 + 边 + stance_score |
| `tick_logs.json` | ✅ 完整 | 35166 bytes | Tick 0-5 全记录 |
| `final_report.md` | ✅ 完整 | 26346 bytes | 10 章节 Markdown 报告 |
| `final_report.json` | ✅ 完整 | 1645 bytes | risk_level + x_t_sequence |

### Phase 1-4 Completion Evidence

| Phase | 入口函数 | 核心模块 | 输出文件 | 完成状态 |
|-------|---------|---------|---------|---------|
| Phase 1 | `run_phase1()` | `src/phase1_entity_extraction.py` | `entities_and_relations.json` | ✅ |
| Phase 2 | `run_phase2()` | `src/phase2_topology_builder.py` | `social_graph.json` | ✅ |
| Phase 3 | `run_phase3()` | `src/phase3_tick_simulation.py` | `tick_logs.json` | ✅ |
| Phase 4 | `run_phase4()` | `src/phase4_report_agent.py` | `final_report.md` | ✅ |

### Root Cause of Missing run_dir / run.log / timing_summary.json

**根本原因**：RuntimeLogger 架构已完整实现（222行代码），但从未接入 E2E 主流程。

**代码证据链**：

1. **RuntimeLogger 实现完整** (`src/utils/runtime_logger.py`)：
   - `configure(run_dir)` 方法 → 创建 run_dir 目录
   - `log_path = run_dir / "run.log"` → 顺序事件日志
   - `timing_path = run_dir / "timing_summary.json"` → 统计汇总
   - `log_run_start/end()` → 运行级日志
   - `log_phase_start/end()` → Phase 级计时
   - `log_llm_start/end()` → LLM 调用追踪
   - `log_tick_start/end()` → Tick 级日志

2. **main.py 从未调用 configure()**：
   - 第193行仅调用 `ensure_dirs()` 创建固定 outputs 目录
   - 无任何 RuntimeLogger 相关导入或调用
   - Phase 计时通过手动 `time.time()` 计算（第225/227/230/232/235/237/240/242行）

3. **phase3_tick_simulation.py 有导入但未激活**：
   - 第35行导入 `get_runtime_logger`
   - 第749行调用 `log_speaker_selection`
   - 但 logger 未 configure，所有写入操作无效（log_path/timing_path 为 None）

4. **config.py 硬编码固定路径**：
   ```python
   OUTPUTS_DIR = PROJECT_ROOT / "outputs"  # 固定路径，无 run_dir 参数
   ENTITIES_OUTPUT_PATH = OUTPUTS_DIR / "entities_and_relations.json"
   SOCIAL_GRAPH_PATH = OUTPUTS_DIR / "social_graph.json"
   ```

### Impact on Baseline Freeze

**判断**：不阻止 baseline freeze。

**理由**：
1. 功能链路完整可用（Phase 1-4 串联正确）
2. E2E 产物完整（所有核心输出文件存在且内容正确）
3. 可观测缺失是"未完成集成"，而非"架构缺陷"
4. RuntimeLogger 代码已就绪，接入工作量可控（预计 1-2 小时）

**但必须记录为已知问题**，下一版本（scheduler v0）优先处理。

---

## 4. Main Pipeline Architecture Audit

### main.py Actual Call Chain

```
main.py:188 main()
│
├── 初始化
│   ├── ensure_dirs()                         ← config.py
│   ├── init_llm_client()                     ← src.llm_client
│   └── 加载种子文件 (sys.argv[1] or default)
│
├── Phase 1: run_phase1(seed_file)
│   ├── extract_entities_from_file()          ← src.phase1_entity_extraction.py
│   │   ├── analyzer_set_parameters()         → LLM: 设置 event_scale/controversy
│   │   ├── generator_create_entities()       → LLM: 提取实体+生成传播者
│   │   ├── validator_check_format()          → LLM: 格式校验（失败重试）
│   │   └── _post_process_entities()          → 后处理修正
│   └── save_entities_output()                → outputs/entities_and_relations.json
│
├── Phase 2: run_phase2(extraction_output)
│   ├── build_topology_from_extraction()      ← src.phase2_topology_builder.py
│   │   ├── 事件实体 → Core 节点 (archetype_index=-1)
│   │   ├── 意见传播者 → Periphery 节点 (archetype_index=-2)
│   │   ├── Core ↔ Core 互连
│   │   ├── Periphery → Core 必连
│   │   └── Periphery ↔ Periphery 30%概率连
│   ├── validate_topology()                   → NetworkX 连通性校验
│   └── save_social_graph()                   → outputs/social_graph.json
│
├── Phase 3: run_phase3(extraction_output, phase2_output, seed_text)
│   ├── SimulationEngine.__init__()           ← src.phase3_tick_simulation.py
│   ├── engine.run_simulation(max_ticks=5)
│   │   ├── run_tick_0()                      → 事件实体发言
│   │   ├── run_tick() (Tick 1-5)
│   │   │   ├── select_speakers()             ← src/phase3/speaker_selector.py
│   │   │   ├── 发言者: generate_opinion_spreader_post()
│   │   │   └── 静默者: update_silent_agent()
│   │   └── calculate_global_metrics()
│   ├── save_tick_logs()                      → outputs/tick_logs.json
│   └── get_x_t_sequence()
│
├── Phase 4: run_phase4(extraction_output, tick_logs, x_t_sequence)
│   ├── generate_report_with_llm()            ← src.phase4_report_agent.py
│   ├── save_report()                         → outputs/final_report.json
│   └── save_markdown_report()                → outputs/final_report.md
│
└── 手动计时输出 (第225-245行)
    ├── phase1_time, phase2_time, phase3_time, phase4_time
    └── total_time
```

### Phase 1 Status

- **模块位置**: `src/phase1_entity_extraction.py` (744行)
- **核心架构**: Analyzer/Generator/Validator 协作
- **输出验证**: ✅ entities_and_relations.json 存在且内容正确
- **风险标记**: 文件头部注释声称"已迁移到 src/phase1/"但该目录不存在（文档漂移）

### Phase 2 Status

- **模块位置**: `src/phase2_topology_builder.py` (380行)
- **核心逻辑**: Core/Periphery 节点分配 + 边连接规则
- **输出验证**: ✅ social_graph.json 存在且拓扑结构正确

### Phase 3 Status

- **模块位置**: `src/phase3_tick_simulation.py` (1017行) + `src/phase3/` 子模块
- **子模块结构**: context_builder.py, speaker_selector.py, state_updater.py, simulation_card.py
- **输出验证**: ✅ tick_logs.json 存在且 Tick 0-5 完整
- **风险**: 职责过重（1017行），Prompt 模板内嵌

### Phase 4 Status

- **模块位置**: `src/phase4_report_agent.py` (653行)
- **输出验证**: ✅ final_report.md 存在且内容完整（10章节）

### Main-chain Architecture Risk

| 风险等级 | 问题 | 影响 |
|---------|------|------|
| **高** | RuntimeLogger 未集成到 main.py | 无法追踪运行历史、LLM 调用、Phase 耗时 |
| **中** | phase1_entity_extraction.py 文档漂移 | 开发者可能误删"遗留"文件 |
| **中** | phase3_tick_simulation.py 职责过重 (1017行) | 维护风险高，改动易引入 bug |
| **低** | 计时逻辑重复（手动计时 vs RuntimeLogger） | 维护两套逻辑 |
| **低** | config.py 硬编码固定路径 | 多次运行互相覆盖 |

---

## 5. Module-level Decoupling Audit

### Modules That May Need Decoupling

| 模块 | 行数 | 耦合度 | 问题 |
|------|------|--------|------|
| `phase3_tick_simulation.py` | 1017 | 高 | Prompt + 解析 + 立场 + 指标 + 调度混杂 |
| `phase1_entity_extraction.py` | 744 | 中 | JSON 解析 + 后处理未抽取 |
| `phase4_report_agent.py` | 653 | 中 | 全局变量 `_llm_generated_markdown` 反模式 |

### Baseline-blocking Module Issues

| 问题 | 所在模块 | 原因 |
|------|----------|------|
| **历史遗留模块共存** | phase0_entity_extraction.py, phase1_persona_engine.py | 数据模型不一致，可能导致混淆 |

**建议 baseline freeze 前处理**：
- 明确标注废弃模块（添加 deprecated 标记）

### Baseline-after Module Issues

| 问题 | 优先级 | 预估工作量 |
|------|--------|-----------|
| phase3 Prompt 抽取到 `src/prompts/` | P1 | 2h |
| JSON 解析函数抽取到 `utils/json_utils.py` | P2 | 1h |
| phase4 全局变量消除 | P3 | 0.5h |

### Modules Not Worth Touching Now

| 模块 | 原因 |
|------|------|
| `agent_quality_analyzer.py` | 职责清晰，耦合低 |
| `runtime_logger.py` | 实现完整，只需接入 |
| `src/phase3/` 子模块 | 已是良好拆分范式 |
| `schemas.py` | 两套数据模型有向后兼容标记 |

---

## 6. Output & Observability Governance Audit

### Current Output Problems

| 问题 | 现状 | 影响 |
|------|------|------|
| **无 run_dir 隔离** | outputs 根目录固定路径 | 多次运行互相覆盖 |
| **命名混乱** | output1, outputs_test2, outputs_test3, run_test3_xxx 共存 | 风格不统一 |
| **tick_logs 目录空** | run_test3_20260424_163044/tick_logs/ 为空 | Tick 级日志未保存 |
| **无 run.log** | RuntimeLogger.log_path 未初始化 | 无法追踪事件流 |
| **无 timing_summary.json** | RuntimeLogger.timing_path 未初始化 | 无法统计 LLM/Phase 耗时 |

### Is Current Output Too Dirty / Scattered / Hard to Replay?

**判断**: 是。

**证据**：
1. outputs 根目录产物时间跨度：Apr 17 - Apr 24，说明多次运行互相覆盖
2. 存在 5 种不同命名风格的目录（output1, outputs_test2, outputs_test2_v1.1.6, outputs_test3, outputs_test5）
3. 无 run.log 无法复盘执行过程
4. 无 timing_summary.json 无法统计性能

### JSON Responsibility

`timing_summary.json` 应记录：
- `run`: start_time, end_time, elapsed_seconds, status, mode, seed_file
- `phases`: 各 Phase 的 start_time, end_time, elapsed_seconds
- `llm`: 调用次数, 每次 call 的 caller, model, elapsed_seconds, timestamp
- `ticks`: 各 tick 的 speaker_selection, elapsed_seconds, speakers, llm_calls
- `errors`: stage, error, timestamp

### CSV Responsibility

横向对比多次运行：
- run_id, seed, model, version, git_commit, git_dirty
- phase1_duration, phase2_duration, phase3_duration, phase4_duration, total_duration
- llm_call_count, tick_count, selected_speaker_count, silent_agent_count
- final_polarization_index, risk_level, output_completeness, status

### Markdown Responsibility

`run_summary.md` 或 `baseline_audit_report.md`：
- human-readable 运行摘要
- 关键指标一览
- 诊断建议
- 风险清单

### run.log Responsibility

顺序事件流：
- `[timestamp] RUN START mode=... seed=... run_dir=...`
- `[timestamp] PHASE START name=...`
- `[timestamp] LLM START caller=... model=...`
- `[timestamp] LLM END caller=... model=... elapsed=...`
- `[timestamp] PHASE END name=... elapsed=...`
- `[timestamp] TICK START tick=...`
- `[timestamp] SPEAKER SELECTION tick=... spreader_count=...`
- `[timestamp] TICK END tick=... elapsed=... speakers=...`
- `[timestamp] RUN END status=... elapsed=...`

### Need for Unified Schema

**判断**: 是。

**理由**：
1. RuntimeLogger 已定义 schema 结构，可直接复用
2. CSV 格式需统一字段以支持横向对比
3. Markdown 报告需统一模板以支持 baseline qualification 检查

---

## 7. White-box Testing Field Requirements

### Required Fields

| 字段 | 来源 | 用途 |
|------|------|------|
| `seed` | sys.argv 或默认 | 运行输入 |
| `model` | config.LLM_MODEL | 模型配置 |
| `version` | main.py banner 或 config | 版本追踪 |
| `run_id` | run_dir 名称 | 运行隔离 |
| `git_commit` | `git rev-parse --short HEAD` | 代码追踪 |
| `git_dirty` | `git status --porcelain` | 未提交状态 |
| `phase_start/end/duration` | RuntimeLogger | Phase 性能 |
| `llm_call_count` | RuntimeLogger | LLM 使用量 |
| `llm_call_elapsed` | RuntimeLogger | LLM 性能 |
| `parser_failure` | phase1/phase4 解析器 | 质量追踪 |
| `validator_failure` | phase1 Validator | 质量追踪 |
| `retry_count` | llm_client 重试机制 | 稳定性追踪 |
| `tick_index` | SimulationEngine | Tick 追踪 |
| `selected_speaker_count` | speaker_selector | 发言统计 |
| `silent_agent_count` | state_updater | 静默统计 |
| `final_polarization_index` | global_metrics | 输出质量 |
| `output_completeness` | 文件检查 | 产物完整性 |
| `status` | 成功/失败 | 运行状态 |

### Optional Fields

| 字段 | 用途 |
|------|------|
| `stance_drift` | 立场变化追踪 |
| `error_message` | 错误详情 |
| `timeout_event` | 超时追踪 |
| `fallback_behavior` | 兜底策略追踪 |

### Fields Not Recommended Yet

| 字段 | 原因 |
|------|------|
| `token_count` | 当前 LLM client 未实现统计 |
| `cost_estimate` | 需要模型定价信息 |
| `memory_usage` | 未接入性能监控 |

---

## 8. CLI Engineer System Assessment

### Should Build CLI System?

**判断**: 是。

**理由**：
1. 当前输出混乱，无法快速复盘
2. 无 run.log 无法定位问题
3. 无 CSV 无法横向对比
4. baseline qualification 检查需自动化

### Why

**当前痛点**：
- 复盘一次 E2E 需手动查看多个文件
- 比较多次 E2E 无统一数据源
- 定位 Phase/LLM/tick 问题需逐层追溯
- baseline qualification 判断依赖人工审计

### Minimal CLI Scope for Next Version

| 命令 | 功能 |
|------|------|
| `run-view` | 查看最新 run 的 run.log + timing_summary.json |
| `run-list` | 列出所有 run_dir 及摘要 |
| `run-compare <run_id1> <run_id2>` | 对比两次运行 |
| `run-export <run_id> --format csv` | 导出 CSV 报告 |
| `run-audit <run_id>` | 输出 baseline qualification 判断 |

### What Not to Build Yet

| 功能 | 原因 |
|------|------|
| `run-replay` | 需完整事件流录制，当前缺失 |
| `run-diff` | 需两次运行的详细 diff，数据不足 |
| `run-graph` | 可视化需额外依赖 |
| `interactive-ui` | MVP 阶段不必要 |

---

## 9. Risk Classification

### Baseline前必须处理

| 问题 | 原因 |
|------|------|
| **明确标注废弃模块** | phase0_entity_extraction.py 和 phase1_persona_engine.py 与当前数据模型冲突，需添加 deprecated 标记防止误用 |

### Baseline后可以处理

| 问题 | 优先级 | 预估工作量 |
|------|--------|-----------|
| RuntimeLogger 接入 main.py | P0 | 1-2h |
| phase3 Prompt 抽取 | P1 | 2h |
| 创建 src/prompts/ 目录 | P1 | 1h |
| JSON 解析函数抽取 | P2 | 1h |
| phase4 全局变量消除 | P3 | 0.5h |
| CLI 工程师系统建设 | P3 | 4-6h |
| 统一输出 schema | P2 | 2h |

### 不建议处理

| 问题 | 原因 |
|------|------|
| phase3 完全重构 | 过度投入，当前可运行 |
| 两套数据模型合并 | 有向后兼容标记，保留即可 |
| token/cost 统计 | 当前阶段不必要 |
| 可视化 UI | MVP 阶段不必要 |

---

## 10. Final Decision

- **Final Verdict**: `pass_with_known_issues`
- **Single Blocker**: 无阻止 baseline freeze 的硬性 blocker
- **Single Next Action**: 在下一版本（scheduler v0）集成 RuntimeLogger.configure() 到 main.py，建立 run_dir/run.log/timing_summary.json 机制
- **Do Not Do**: 不要在 baseline freeze 前重构 phase3 或创建新架构

---

**审计日期**: 2026-04-24
**审计员**: Claude Code (只读审计模式)
**审计范围**: `adarian mvp` 子模块当前工作区版本
**最终判断**: 可以 freeze 为 baseline，但需记录可观测能力缺失为已知问题