# DS Team Codex Taskbook 预实现审查报告

> **审查类型**: pre_implementation_taskbook_review  
> **审查对象**: `pm_runtime_communication_substrate_mvp_codex_taskbook_v0.1.md`  
> **审查日期**: 2026-05-22  
> **审查团队**: DS Team (Claude Code) — 3 Agent Team Mode  
> **MCP 使用**: true  
> **上游合同**: Runtime Contract v0.1 (DS 审查 pass_with_known_issues)  
> **上游 YAML**: workflow_compact_v0.3.3.yaml  

---

## 0. 审查结论

```yaml
acceptance_verdict: patch_required
codex_readiness: needs_patch
```

**该任务书当前不能直接交给 Codex 执行。** 存在 9 项 P0 问题和 8 项 P1 问题，必须在 Owner 修补后方可进入 Codex dispatch。

核心问题集中在三个方面：
1. **文件边界不完整** — allowed_files 缺少包初始化文件，forbidden_files 缺少对 CLAUDE.md、.venv/、pyproject.toml、docs/dev_spec.md 等关键文件的保护
2. **Schema 全面缺失** — 几乎所有 runtime artifact（pre_action_check、registry_events、blocker_report、owner_decision_request/record、pm_runtime_summary）都没有字段级定义
3. **YAML 对齐偏差** — runtime_state 枚举缺少 9 个 YAML 定义值，receipt 字段与 YAML receipt_contract 严重不匹配

---

## 1. 审查方法

### 1.1 Agent Team 组成

| 角色 | 审查维度 | 状态 |
|------|---------|------|
| Scope-Boundary-Verification | allowed_files/forbidden_files 完整性 + Hard Boundaries 完备性 | 完成 |
| Executability-Assessment | 模块清晰度、状态模型对齐、参数合理性、Codex 可执行性 | 完成 |
| Contract-Alignment | Runtime Contract + YAML v0.3.3 合同对齐 | 完成 |

### 1.2 审查材料

| 文件 | 路径 | 状态 |
|------|------|------|
| 主审查对象 — Taskbook | `audit/workflow_v4.0/hermes pm context/pm_runtime_communication_substrate_mvp_codex_taskbook_v0.1.md` | 已读取 |
| 上游合同 — Runtime Contract | `audit/workflow_v4.0/hermes pm context/pm_runtime_communication_substrate_runtime_contract_v0.1.md` | 已读取 |
| 上游计划 — Bootstrap Plan | `audit/workflow_v4.0/hermes pm context/pm_runtime_communication_substrate_bootstrap_plan_v0.3.md` | 已读取 |
| YAML 对齐参考 | `docs/skills/workflow_v4.0/workflow_core/workflow_compact_v0.3.3.yaml` | 已读取 |

---

## 2. Scope 边界审查

### 2.1 allowed_files 完整性

**结论: 不完整**

缺少的关键文件:

| # | 缺失文件 | 理由 | 严重度 |
|---|---------|------|--------|
| 1 | `tools/pm_runtime/__init__.py` | `relay/` 作为 Python 包需要父包 `__init__.py`，Codex 必须创建但不在 allowlist | P0 |
| 2 | `tools/__init__.py` | 若 `tools/` 尚未作为包存在，Codex 可能需要创建或修改 | P1 |

### 2.2 forbidden_files 完整性

**结论: 不完整 — 存在严重遗漏**

缺少的关键禁止文件:

| # | 缺失文件 | 风险 | 严重度 |
|---|---------|------|--------|
| 1 | `CLAUDE.md` | Codex 可修改项目级指令和工作流权限规则 | P0 |
| 2 | `.venv/**` | Codex 可安装包、修改 Python 环境 | P0 |
| 3 | `pyproject.toml` | Codex 可添加依赖或修改构建配置 | P0 |
| 4 | `requirements.txt` / `requirements*.txt` | Codex 可添加依赖 | P0 |
| 5 | `docs/dev_spec.md` | 架构规范文件，Codex 不得修改 | P1 |
| 6 | `docs/workflow_changelog.md` | 工作流变更记录，Codex 不得修改 | P1 |
| 7 | `docs/iterations/*` (除 v0.1.0 外) | Codex 可能修改无关迭代文档 | P1 |
| 8 | `workflow_compact.yaml` | 仅在第 5 节散文中被禁止，不在 forbidden_files glob 中 | P1 |
| 9 | `workflow_compact_v0.3.3.yaml` | 同上，仅散文禁止，不在 glob 列表中 | P1 |
| 10 | `audit/tasks/active/*` (其他 task_domain) | Codex 可能写入兄弟任务目录 | P2 |
| 11 | `tools/**` (pm_runtime 外) | 现有 tools 未受保护 | P2 |
| 12 | 任务书自身文件 | `pm_runtime_communication_substrate_mvp_codex_taskbook_v0.1.md` | P2 |
| 13 | Runtime Contract 文件 | `pm_runtime_communication_substrate_runtime_contract_v0.1.md` | P2 |

### 2.3 Glob 模式风险

`audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/**` 存在过度匹配风险:

- 该 glob 允许 Codex 创建、修改、**删除** 该目录下所有文件
- 若该目录中已有 Hermes 或 Control Agent 放置的引导产物，Codex 可在不违反 allowed_files 的情况下破坏它们
- 第 14 节 Hard Boundary "不得删除 audit/tasks 既有内容" 仅为操作散文，不是文件级 glob 约束
- **建议**: 将 allowed glob 细化为具体子目录/文件类型，或增加显式的 preserve-existing-files 约束

### 2.4 Hard Boundaries（第 14 节）完备性

第 14 节覆盖了 9 条禁止项，但以下 Runtime Contract 和 YAML 定义的禁止项未被明确覆盖:

| 缺失项 | 来源 | 严重度 |
|--------|------|--------|
| `treating_sandbox_denied_as_success` | Contract §12.1 Codex Profile | P1 |
| `suppressing_stderr_or_stdout_evidence` | Contract §12.1 Codex Profile | P1 |
| `self_closeout` | YAML role_registry.codex.forbidden | P2 |
| `enter_next_version_without_approval` | YAML role_registry.codex.forbidden | P2 |
| `expand_scope` (显式) | YAML role_registry.codex.forbidden | P2 |
| Hermes 16 条禁止项 (仅提及计数，未枚举) | Contract §12.3 | P2 |

---

## 3. 可执行性审查

### 3.1 模块清晰度

| 模块 | 评估 | 说明 |
|------|------|------|
| `cli.py` | **模糊** | init/run/recover/summary 子命令零行为规范 — Codex 必须猜测每个命令的内部逻辑、产物和退出码 |
| `relay_runner.py` | **模糊** | 11 条职责仅为要点列表。缺少: health-based control 检测逻辑、状态转换阈值、与 executor subprocess 的通信协议、heartbeat/progress 写入确切实时点 |
| `extractors.py` | **较清晰** | 5 条职责具体，但 "提取 agent message" 未定义目标字段（JSONL 中的 text/content/message 字段？） |
| `recovery.py` | **模糊** | 未定义如何程序化检测可恢复 vs 不可恢复失败，如何区分 trivial vs non-trivial recovery |

### 3.2 状态模型对齐

**task_status: 匹配** — 8 个值完全一致（proposed, approved, running, completed, failed, hold, closed, archived）

**runtime_state: 不匹配**

| | 数量 |
|---|---|
| Taskbook | 21 个值 |
| YAML v0.3.3 | 30 个值 |
| 差异 | 9 个 YAML 值缺失 |

Taskbook 缺失的 9 个 YAML runtime_state:

```text
not_started, running, completed, failed, timeout,
partial_output_recovered, artifact_missing, environment_blocked, hold_required
```

其中 4 个（not_started, running, completed, failed）与 task_status 重复 — 这是个设计坏味道。另外 5 个（timeout, partial_output_recovered, artifact_missing, environment_blocked, hold_required）是 healthcare-based control 直接相关的运行状态，缺失将导致 Codex 不实现或无法应对这些场景。

### 3.3 Health-Based Control 参数评估

| 参数 | 值 | 评估 |
|------|-----|------|
| `heartbeat_interval_sec` | 30s | 合理 |
| `progress_check_interval_sec` | 120s | 合理 |
| **`no_heartbeat_timeout_sec`** | **180s** | **过紧 — P0 问题** |
| `no_progress_review_sec` | 600s | 合理 |
| `owner_review_after_sec` | 1800s | 合理 |
| `emergency_max_wall_time_sec` | null | v0.1 可接受 |

**`no_heartbeat_timeout_sec=180s` 严重问题分析**:

```text
Codex 启动基线: 120–136s
第一次 heartbeat (heartbeat_interval=30s): 在启动后 150–166s 才写入
距离 180s 超时: 仅剩 14–30s 余量
```

任何环境延迟、sandbox 初始化或慢 I/O 都会触发误报超时。**建议最低 240s，推荐 300s**，确保至少 2 个 heartbeat 周期在启动基线后完成。

### 3.4 Owner Decision Relay 8 事件完整性

**完整。** Taskbook 的 8 种事件与 Runtime Contract §13.2 和 YAML `enums.owner_decision_event_type` 完全一致:

```text
approval_required, sandbox_denied, permission_blocked, waiting_input,
scope_violation, unclear_policy, missing_receipt, recovery_requires_approval
```

但 YAML `owner_decision_option`（5 个选项）在 taskbook 中未被引用:

```text
approve_with_scope, reject, abort_task, request_safer_alternative, ask_for_more_context
```

### 3.5 Required Checks 可执行性

```bash
.venv/bin/python -m py_compile tools/pm_runtime/relay/cli.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/relay_runner.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/extractors.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/recovery.py
.venv/bin/python -c "from tools.pm_runtime.relay import cli; print('import OK')"
```

- py_compile 命令语法正确
- `.venv/bin/python` 是项目特定路径，Codex sandbox 中可能不存在
- 回退到裸 `python` 的方案未指定 Python 版本，系统 python 可能缺少项目依赖
- import 检查会触发 `tools/pm_runtime/__init__.py` 的加载 — 但该文件不在 allowed_files 中

### 3.6 模糊点汇总

1. `cli.py` 子命令零行为规范
2. relay_runner 与 executor subprocess 的通信协议未定义
3. 8 个 artifact 文件没有格式/模式定义
4. Codex exec 命令中的 `--add-dir <sandbox_path>` 占位符未解析为具体路径
5. Demo 在 "real executor" 和 "echo executor" 之间摇摆
6. `task_config.yaml` 模板只有键名没有值、默认值或枚举约束
7. 没有 Python 版本要求
8. 没有依赖项声明
9. 没有并发模型说明
10. 没有错误处理策略

---

## 4. 合同对齐审查

### 4.1 Runtime Artifact 覆盖

| Contract Artifact | Taskbook §7 | 状态 |
|-------------------|-------------|------|
| `dispatch/task_config.yaml` | 仅模板在 §6.5 | 部分 |
| `runtime/pre_action_check.yaml` | 有 | 覆盖 |
| `runtime/task_state.yaml` | 有 | 覆盖 |
| `runtime/registry_events.jsonl` | 有 | 覆盖 |
| `runtime/heartbeat.json` | 有 | 覆盖 |
| `runtime/progress.yaml` | 有 | 覆盖 |
| `runtime/blocker_report.md` | 有 | 覆盖 |
| `runtime/owner_decision_request.yaml` | 有 | 覆盖 |
| `runtime/owner_decision_record.yaml` | 有 | 覆盖 |
| `runtime/recovery_summary.md` | 有 | 覆盖 |
| **`runtime/abort_report.yaml`** | **缺失** | **P0** |
| `logs/stdout.log` | 有 | 覆盖 |
| `logs/stderr.log` | 有 | 覆盖 |
| `logs/raw_output.jsonl` | 有 | 覆盖 |
| `logs/stdout.partial.log` | 有 | 覆盖 |
| `logs/stderr.partial.log` | 有 | 覆盖 |
| **`logs/raw_output.partial.*`** | **缺失** | **P2** |
| `summary/pm_runtime_summary.md` | 有 | 覆盖 |

**合同要求 18 项，Taskbook 覆盖 16 项。缺少 2 项：`runtime/abort_report.yaml` (P0) 和 `logs/raw_output.partial.*` (P2)。**

### 4.2 Schema 定义覆盖

| Schema | Contract 定义 | Taskbook 状态 | 严重度 |
|--------|--------------|---------------|--------|
| pre_action_check.yaml | §7.2 — 20 个必填字段 | **零字段定义** | P0 |
| registry_events.jsonl | §10.2 — 13 个 JSON 字段 | **零字段定义** | P0 |
| blocker_report.md | §9.3 — 12 个必填字段 | **零字段定义** | P1 |
| owner_decision_request.yaml | §13.3 — 19 个必填字段 | **零字段定义** | P1 |
| owner_decision_record.yaml | §13.4 — 10 个必填字段 | **零字段定义** | P1 |
| pm_runtime_summary.md | §17 — 17 个必填节 | **零节定义** | P1 |
| task_config.yaml | §6 — 带子字段 | **只有顶层键名** | P1 |
| failure_classification | §16 — 14 种类型 | **未引用** | P0 |

### 4.3 Receipt 合同对齐

**Taskbook §12 vs YAML receipt_contract: 部分对齐**

Taskbook 中缺失的 YAML 必填字段:

```text
task_title, started_at, completed_at, elapsed_sec, status, verdict,
team_mode_used, mcp_used, input_files, output_files, modified_files, next_recommendation
```

Taskbook 新增了 YAML 中未定义的 Codex 特定字段:

```text
changed_files, test_results, receipt_path, handoff_path, commit_status,
forbidden_files_touched, runtime_contract_deviations
```

**建议**: 使用分层 receipt 模型 — 核心字段对齐 YAML，扩展字段作为 Codex 特定附录。

### 4.4 Recovery Contract 覆盖

**部分覆盖。**

Contract §15 定义了 3 种恢复类型（trivial_recovery, non_trivial_recovery, owner_approved_recovery）和边界规则。Taskbook §6.4 覆盖了恢复操作但从未使用这个 3 类型分类。缺少 `recovery_type` 字段将导致 recovery_summary 无法区分权限级别。

### 4.5 Failure Classification 覆盖

**缺失。**

Contract §16 定义了 14 种失败分类:

```text
agent_completed, agent_failed, permission_blocked, sandbox_denied,
partial_output, json_parse_failed, no_output, timeout_or_abort,
process_killed, environment_blocked, missing_receipt, missing_report,
artifact_path_missing, role_boundary_violation
```

每种分类需要 evidence、confidence、classified_by、requires_independent_review 字段。

**Taskbook 完全没有引用失败分类。** 这意味着 relay_runner 和 recovery 模块无法对失败进行分类和路由。

### 4.6 Rerun Model 覆盖

**缺失。**

Contract §14 要求 round-based rerun 模型，包含 `round_id`、`parent_round_id`、`rerun_reason`、`rerun_config_delta`。Taskbook 仅在 runtime_state 中提到了 `rerun_required`，没有定义 rerun 数据模型、registry event 或配置增量机制。

### 4.7 No-Closeout 一致性

**一致性: 通过。** 三个文档（Taskbook、Contract、YAML）在 no-closeout 边界上保持一致:
- Contract §2.5: PM Runtime does not own closeout
- YAML closeout_gate: owner_control_only: true
- Taskbook §14: Codex 不得声称 closeout

### 4.8 Bootstrap Plan Phase 3 对齐

**对齐。** Taskbook 的 MVP 范围（cli.py、relay_runner.py、extractors.py、recovery.py）与 Bootstrap Plan Phase 3 一致。路径 `tools/pm_runtime/relay/` vs Plan 中的 `pm_runtime/relay/` 差异在 Plan 中是举例性质的，不构成冲突。

---

## 5. 发现汇总

### P0 — 阻断性问题（9 项）

| # | 标题 | 类别 |
|---|------|------|
| P0-1 | **forbidden_files 严重不完整** — CLAUDE.md、.venv/**、pyproject.toml、requirements.txt 未受保护 | Scope |
| P0-2 | **allowed_files 不完整** — `tools/pm_runtime/__init__.py` 缺失，Codex 创建 relay 包时会被 import 检查阻塞 | Scope |
| P0-3 | **runtime_state 枚举偏差** — YAML 30 个值 vs taskbook 21 个值，缺失 9 个（timeout、partial_output_recovered、artifact_missing、environment_blocked、hold_required 等） | Contract |
| P0-4 | **artifact schema 全面缺失** — pre_action_check（20 字段）、registry_events（13 字段）零规范，Codex 将自创格式 | Contract |
| P0-5 | **`runtime/abort_report.yaml` 缺失** — Contract §9.4 强制要求 abort 时写入，taskbook artifact 列表未列出 | Contract |
| P0-6 | **failure classification 未引用** — Contract §16 的 14 种失败类型完全缺失，relay_runner/recovery 无法分类失败 | Contract |
| P0-7 | **`no_heartbeat_timeout_sec=180s` 过紧** — Codex 启动基线 120–136s，仅有 14–30s 余量，首次运行大概率误报超时 | Exec |
| P0-8 | **receipt schema 严重不匹配** — 缺少 11 个 YAML receipt_contract 必填字段（task_title、started_at、completed_at、elapsed_sec、status、verdict 等） | Contract |
| P0-9 | **cli.py 和 relay_runner.py 零行为规范** — 只有职责要点，无函数签名、状态机、输出格式 | Exec |

### P1 — 重要问题（8 项）

| # | 标题 | 类别 |
|---|------|------|
| P1-1 | **blocker_report 无字段 schema** — Contract §9.3 的 12 个必填字段未在 taskbook 中定义 | Contract |
| P1-2 | **owner_decision_request/record 无 schema** — Contract §13.3/§13.4 共 29 个字段未定义 | Contract |
| P1-3 | **pm_runtime_summary 无节定义** — Contract §17 的 17 个必填节未指定 | Contract |
| P1-4 | **task_config 模板字段不足** — 只有顶层键名，缺少 paths、runtime_control、scope、executor_options 的子字段 | Exec |
| P1-5 | **demo 范围模糊** — "real executor" vs "echo executor" 二选一未决定，sandbox 路径占位符 `--add-dir <sandbox_path>` 未解析 | Exec |
| P1-6 | **rerun model 缺失** — Contract §14 的 round_id、parent_round_id、rerun_reason 未纳入 taskbook | Contract |
| P1-7 | **docs/dev_spec.md 和 docs/workflow_changelog.md 未受保护** — 不在 forbidden_files 中 | Scope |
| P1-8 | **workflow_compact.yaml / workflow_compact_v0.3.3.yaml 仅操作散文禁止** — 不在 forbidden_files glob 中，Codex 只解析 glob 时将漏过 | Scope |

### P2 — 一般问题（7 项）

| # | 标题 |
|---|------|
| P2-1 | `audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/**` glob 过于宽松，允许删除既有文件 |
| P2-2 | `tools/**`（pm_runtime 子树之外）未被明确禁止 |
| P2-3 | `audit/tasks/active/*`（其他 task_domain）未被明确禁止 |
| P2-4 | 任务书文件和 Runtime Contract 文件自身不在 forbidden_files 中 |
| P2-5 | 第 14 节未覆盖 Contract §12.1 的 Codex Profile 禁止项: `treating_sandbox_denied_as_success`、`suppressing_stderr_or_stdout_evidence` |
| P2-6 | Hermes 16 条禁止项（Contract §12.3）仅提及计数，未枚举 |
| P2-7 | Recovery 未使用 Contract §15 的 3 类型分类（trivial/non_trivial/owner_approved） |

### P3 — 建议性问题（6 项）

| # | 标题 |
|---|------|
| P3-1 | §8.3 "可以实现简化逻辑" 表述模糊 — 何为可接受的简化？ |
| P3-2 | 未指定 Python 版本要求 |
| P3-3 | 未声明依赖项（PyYAML 等） |
| P3-4 | 无并发模型说明 — relay_runner 的 heartbeat 与 subprocess 如何共存？ |
| P3-5 | `task_config.yaml` 模板路径（`tools/pm_runtime/templates/`）与 dispatch 实际落盘路径不一致 |
| P3-6 | YAML `owner_decision_option` 5 个枚举值在 taskbook 中未引用 |

---

## 6. Codex 准备度评估

```yaml
codex_readiness:
  ready: false
  verdict: needs_patch
  blockers:
    - forbidden_files 需从 9 项扩展到 22+ 项
    - allowed_files 需补充 __init__.py
    - 所有 runtime artifact 需补充字段级 schema（至少 8 个文件）
    - no_heartbeat_timeout_sec 需从 180s 提高到 >=240s
    - receipt 需对齐 YAML receipt_contract 必填字段
    - 需纳入 failure classification 和 abort_report
    - cli.py 和 relay_runner.py 需补充行为规范
  estimated_patch_effort: M-level (预计 1-2 轮 Owner repair)
```

---

## 7. 建议修补方案

### 7.1 Owner 修补清单（推荐优先级）

**第 1 轮修补（P0 必修）:**

1. **扩展 forbidden_files §5** — 新增:
   ```text
   CLAUDE.md
   .venv/**
   pyproject.toml
   requirements*.txt
   docs/dev_spec.md
   docs/workflow_changelog.md
   docs/iterations/* (除 v0.1.0-pm-runtime-communication-substrate-mvp.md)
   workflow_compact.yaml
   workflow_compact_v0.3.3.yaml
   tools/** (除 tools/pm_runtime/relay/** 和 tools/pm_runtime/templates/**)
   audit/tasks/active/* (除 communication-substrate-mvp/**)
   audit/workflow_v4.0/hermes pm context/*
   ```

2. **补充 allowed_files §4** — 新增 `tools/pm_runtime/__init__.py`

3. **提高 `no_heartbeat_timeout_sec`** — 从 180s 到 300s

4. **在 taskbook 中嵌入 artifact schema** — 至少将以下 schema 作为附录加入:
   - `pre_action_check.yaml` 字段定义（Contract §7.2）
   - `registry_events.jsonl` 事件格式（Contract §10.2）
   - `blocker_report.md` 字段（Contract §9.3）
   - `owner_decision_request.yaml` 字段（Contract §13.3）
   - `owner_decision_record.yaml` 字段（Contract §13.4）
   - `pm_runtime_summary.md` 节模板（Contract §17）
   - `task_config.yaml` 完整模板（Contract §6）

5. **新增 `runtime/abort_report.yaml` 到 artifact 列表**

6. **引用 failure classification** — 将 Contract §16 的 14 种类型纳入 recovery.py 和 relay_runner.py 职责

7. **对齐 receipt 字段** — 分层模型：核心字段对齐 YAML，Codex 特定字段作为扩展

8. **补充 runtime_state 枚举** — 将 YAML 的 9 个额外值纳入 taskbook §8.1

9. **补充 cli.py 和 relay_runner.py 行为规范** — 至少定义每个 CLI 子命令的输入/输出/退出码，以及 relay_runner 的状态转换图

**第 2 轮修补（P1 推荐修）:**

10. 确定 demo 范围并解析 sandbox 路径
11. 加入 rerun model（round_id、parent_round_id）
12. 显式列出 Hermes 16 条禁止项或交叉引用 Contract §12.3
13. 将 Hard Boundaries 与 Contract Codex Profile 禁止项对齐

### 7.2 不推荐现在做的事

- 写 Python 代码框架 — taskbook 修补优先
- 在 taskbook 中加入 Python 实现细节 — 留给 Codex
- 开始 demo 实现 — sandbox 路径和范围必须先确定
- 写 operator skill — Phase 4 事项，等 MVP 落地

---

## 8. 过程问题

| # | 问题 | 严重度 |
|---|------|--------|
| 1 | MCP filesystem 和 Agent Team 已按要求使用 | — |
| 2 | 审查严格保持只读，未修改任何文件 | — |
| 3 | 上游 Contract 和 YAML 之间存在 runtime_state 枚举偏差（30 vs 21），taskbook 继承了 Contract 的版本但未对齐 YAML — 这是 Contract 审查时的已知问题，但 taskbook 起草时未处理 | P2 |
| 4 | 任务书自身标记 `status: owner_repair_required / not_ready_for_codex` — 该自我诊断正确但未枚举需要修复的具体内容 | P3 |

---

## 9. 下一步建议

```yaml
recommended_next_action:
  - action: owner_repair_taskbook
    description: Owner 根据本报告 P0/P1 发现修补 taskbook v0.1 → v0.2
    priority: immediate
  - action: ds_re-review_taskbook_v0.2
    description: DS Team 对修补后的 v0.2 做快速 re-review
    priority: after_repair
  - action: owner_approval
    description: Owner 审批修补后的 taskbook
    priority: after_re-review
  - action: hermes_copy_to_iterations
    description: Hermes 将批准的 taskbook 复制到 docs/iterations/
    priority: after_owner_approval
  - action: codex_dispatch
    description: 触发 Codex safety gate 执行实现
    priority: after_hermes_copy
```

当前状态: **HOLD — 等待 Owner 修补 taskbook**

---

## 10. 审查元数据

```yaml
review_id: ds-review-codex-taskbook-communication-substrate-mvp-20260522
review_date: 2026-05-22
executor: DS Team (Claude Code)
review_type: pre_implementation_taskbook_review
team_mode_used: true
team_composition:
  - Scope-Boundary-Verification
  - Executability-Assessment
  - Contract-Alignment
mcp_used: true
mcp_tools:
  - mcp__filesystem__read_text_file
readonly: true
file_modification: none
git_commit: none
input_files:
  - audit/workflow_v4.0/hermes pm context/pm_runtime_communication_substrate_mvp_codex_taskbook_v0.1.md
  - audit/workflow_v4.0/hermes pm context/pm_runtime_communication_substrate_runtime_contract_v0.1.md
  - audit/workflow_v4.0/hermes pm context/pm_runtime_communication_substrate_bootstrap_plan_v0.3.md
  - docs/skills/workflow_v4.0/workflow_core/workflow_compact_v0.3.3.yaml
target_report_path: audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/ds/ds_codex_taskbook_review.md
target_receipt_path: audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/ds/ds_receipt.yaml
```

---

## 附录 A：Hermes 补充发现（2026-05-22，审查结束后追加）

> ⚠️ 以下内容由 Hermes（PM Runtime）在 DS Team 审查完成后追加，非 DS Team 原始产出。
> 来源：将任务书 v0.1 与 workflow_core_v4.0_r2.md §6 §7 逐项对照。

### A.1 L0-L3 权限分级定义缺失（对照 R2 §6.6）

任务书 §5 和 §8.3 有 `runtime_allowed_level` 字段但只有标签名，缺少每级的详细规则。
relay_runner.py 和 recovery.py 需要这些规则来判断"能不能自己处理"还是"必须回 Owner"。

R2 §6.6 的完整定义：

| 级别 | 名称 | 允许 | 禁止 |
|------|------|------|------|
| L0 | 只读回收 | 读 dispatch/receipt/result，生成 summary | 启动新任务、重试执行、修改任务书、改变状态 |
| L1 | 状态修复 | 标记 stalled/incomplete/failed/hold，生成缺失原因说明、summary | 自动重跑、补写执行方 receipt、替 DS/Codex 生成验收结论、把 failed 改成 completed |
| L2 | 同权限重试 | 修复执行通道（terminal→runner）、同权限重新启动、要求补交 receipt | 不得改 task_id/目标/执行对象/读写权限/输出产物/failure_policy，不得绕过安全扫描 |
| L3 | 任务方案变更 | — | 凡涉及改目标/执行对象/读写范围/验收条件/forbidden files 的动作，一律 L3，必须回 Owner 重新批准 |

**建议**：在任务书 §8 新增一节，将上表纳入 runtime_control 字段规范。

### A.2 HOLD 后标准动作清单缺失（对照 R2 §7.5）

R2 §7.5 定义 HOLD 后 PM Runtime 必须执行 8 项动作。任务书 §6.4 recovery.py 有 recovery 职责描述，但未要求输出这些字段：

```text
1. 写入 result.yaml
2. 写入 pm_runtime_summary.md
3. 标明 failure_type（按 R2 §7.4 的 9 种分类）
4. 标明已有产物（路径列表）
5. 标明缺失产物（路径列表）
6. 标明是否触及 L3（触及则必须 Owner 重新批准）
7. 给出 recommended_next_action
8. 等待 Owner-Control 判断（不得自动继续）
```

**建议**：在任务书 §6.4 recovery.py 职责中追加"HOLD 后必须输出以上 8 项"，或新增 §8.5 HOLD 输出规范。

### A.3 备注

以上两项在 DS Team 审查时未被覆盖，原因是 DS 审查当时以 Runtime Contract v0.1 和 YAML v0.3.3 为主要对齐参考，未额外对照 R2 原文 §6 §7。建议在 DS re-review v0.2 时将 R2 原文纳入审查材料清单。
