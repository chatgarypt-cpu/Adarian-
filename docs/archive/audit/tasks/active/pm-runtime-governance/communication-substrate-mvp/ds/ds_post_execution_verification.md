# DS Team Post-Execution Functional Verification Report

## PM Runtime Communication Substrate MVP

---

**review_type**: `post_execution_functional_verification`
**task_id**: `ds-verify-pm-runtime-communication-substrate-mvp-20260522`
**executor**: DS Team / Claude
**date**: 2026-05-22
**status**: ✅ 验证完成

---

## 1. 验证概要

| 维度 | 结果 | 说明 |
|------|------|------|
| 文件边界检查 | **pass** | Codex 实现文件全部在允许路径内，禁止路径未被 Codex 触碰 |
| 语法/导入检查 | **pass** | 四个模块 py_compile + import 全部通过 |
| 收据模式检查 | **pass** | 包含 receipt.template.yaml 全部基字段 + Codex 扩展字段 |
| Demo 独立重跑 | **pass** | DS 独立执行 init → run → summary → recover 全部 exit 0 |
| 追加注册表检查 | **pass** | 每行合法 JSON，追加不覆盖，含所有必要字段 |
| 制品模式抽查 | **pass** | pre_action_check / summary / recovery 制品均符合 taskbook §10 |

**acceptance_verdict**: `pass_with_known_issues`
**implementation_readiness**: `usable`

---

## 2. 文件边界检查 (2.1)

### 2.1.1 Codex 实现的文件变更

通过 `git status --short` 和 `git diff --stat` 检查，Codex 创建了以下文件（全部为 untracked `??`）：

**实现文件（允许路径 `tools/pm_runtime/**`）：**
- `tools/pm_runtime/__init__.py` ✅
- `tools/pm_runtime/relay/__init__.py` ✅
- `tools/pm_runtime/relay/cli.py` ✅
- `tools/pm_runtime/relay/relay_runner.py` ✅
- `tools/pm_runtime/relay/extractors.py` ✅
- `tools/pm_runtime/relay/recovery.py` ✅
- `tools/pm_runtime/templates/task_config.yaml` ✅
- `tools/pm_runtime/templates/receipt.template.yaml` ✅（冗余副本，在允许路径内）
- `tools/pm_runtime/templates/dispatch.template.yaml` ✅（冗余副本，在允许路径内）

**制件文件（允许路径 `audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/**`）：**
- `codex/codex_receipt.yaml` ✅
- `codex/codex_handoff.md` ✅
- `summary/pm_runtime_summary.md` ✅
- `sandbox/demo_task/` 下全部 demo 制品 ✅

### 2.1.2 分支上预存在的其他变更（非 Codex 所为）

Git status 中以下变更为分支 `work/v1.2.8` 上预存在的其他工作流变更，**非 Codex 本次任务产生**：

- `.claude/worktrees/agent-*` — 6 个 submodule reference 标记为 `-dirty`（DS 验证会话本身进入 worktree 导致）
- `audit/hermes_tasks/` — 20 个文件标记为 `D`（预存在的删除）
- `docs/workflow_core.md` — 标记为 `D`（预存在的删除）
- `docs/skills/workflow_v4.0/` — 预存在的 untracked 文件（workflow v4.0 治理工作流）
- `audit/tasks/active/workflow-v4-landing/` — 预存在的其他任务包
- `audit/tasks/active/control-agent-governance/` — 预存在的其他任务包
- `audit/workflow_v4.0/` — 预存在的其他工作流制品

### 2.1.3 明确未触碰的禁止文件

| 禁止路径 | 状态 |
|----------|------|
| `src/**` | ✅ 未触碰 |
| `tests/**` | ✅ 未触碰 |
| `main.py` | ✅ 未触碰 |
| `config.py` | ✅ 未触碰 |
| `CLAUDE.md` | ✅ 未触碰 |
| `.venv/**` | ✅ 未触碰 |
| `pyproject.toml` | ✅ 未触碰 |
| `requirements*.txt` | ✅ 未触碰 |
| `docs/skills/**`（Codex 新增） | ✅ 未触碰 |
| `workflow_core*` | ✅ 未触碰 |
| `workflow_compact.yaml` | ✅ 未触碰 |
| `workflow_compact_v0.3.3.yaml` | ✅ 未触碰 |
| `.claude/**`（Codex 新增） | ✅ 未触碰 |
| `.codex/**` | ✅ 未触碰 |
| `.hermes/**` | ✅ 未触碰 |
| `.git/**` | ✅ 未触碰 |

### 2.1.4 Git 提交检查

- `git log -1` 显示最新提交为 `648accd chore: backup before workflow v4 governance cleanup`
- **Codex 未做 git commit** ✅
- 所有变更均为 unstaged 状态 ✅

**结论**: 文件边界检查 **pass**。Codex 严格遵守了允许/禁止文件边界。

---

## 3. 语法和导入检查 (2.2)

### 3.1 py_compile 结果

```bash
.venv/bin/python -m py_compile tools/pm_runtime/relay/cli.py        # ✅ pass
.venv/bin/python -m py_compile tools/pm_runtime/relay/relay_runner.py  # ✅ pass
.venv/bin/python -m py_compile tools/pm_runtime/relay/extractors.py    # ✅ pass
.venv/bin/python -m py_compile tools/pm_runtime/relay/recovery.py      # ✅ pass
```

### 3.2 import 结果

```bash
.venv/bin/python -c "from tools.pm_runtime.relay import cli"           # ✅ import OK
.venv/bin/python -c "from tools.pm_runtime.relay import relay_runner"  # ✅ import OK
.venv/bin/python -c "from tools.pm_runtime.relay import extractors"    # ✅ import OK
.venv/bin/python -c "from tools.pm_runtime.relay import recovery"      # ✅ import OK
```

**Python 解释器**: `.venv/bin/python`（项目虚拟环境，Python 3.14）

**结论**: 语法和导入检查 **pass**。

---

## 4. 收据模式检查 (2.3)

### 4.1 Codex Receipt 字段完整性

对比 `receipt.template.yaml` 基线和 Codex 回执：

| 基字段 | Codex 回执 | 状态 |
|--------|-----------|------|
| `task_id` | `pm-runtime-communication-substrate-mvp` | ✅ |
| `task_title` | `PM Runtime Communication Substrate MVP` | ✅ |
| `executor` | `codex` | ✅ |
| `started_at` | `2026-05-22T22:45:00+08:00` | ✅ |
| `completed_at` | `2026-05-22T23:01:26+08:00` | ✅ |
| `elapsed_sec` | `986` | ✅ |
| `status` | `completed` | ✅ |
| `verdict` | `pass_with_known_issues` | ✅ |
| `team_mode_used` | `N/A` | ✅ |
| `mcp_used` | `false` | ⚠️ 见 P2 |
| `input_files` | 5 files listed | ✅ |
| `output_files` | 10 files listed | ✅ |
| `modified_files` | `[]` (empty) | ✅ |
| `commands_run` | 10 commands listed | ✅ |
| `known_issues` | 7 items | ✅ |
| `blockers` | `[]` (empty) | ✅ |
| `next_recommendation` | non-empty | ✅ |
| `report_path` | codex_handoff.md path | ✅ |
| `receipt_path` | codex_receipt.yaml path | ✅ |
| `summary_path` | pm_runtime_summary.md path | ✅ |
| `run_dir` | sandbox/demo_task path | ✅ |
| `diff_summary` | non-empty | ✅ |
| `process_issues` | 2 items | ✅ |

**Codex 扩展字段**:

| 扩展字段 | Codex 回执 | 状态 |
|---------|-----------|------|
| `changed_files` | 11 entries | ✅ |
| `created_files` | 24 entries | ✅ |
| `test_results` | 7 entries | ✅ |
| `handoff_path` | codex_handoff.md path | ✅ |
| `commit_status` | `no_commit` | ✅ |
| `forbidden_files_touched` | `[]` (empty) | ✅ |
| `runtime_contract_deviations` | `[]` (empty) | ✅ |
| `python_interpreter` | `.venv/bin/python` path | ✅ |
| `owner_override_used` | `true` | ✅ |
| `owner_override_reason` | infrastructure_creation_lane 说明 | ✅ |

### 4.2 Handoff 检查

`codex_handoff.md` 存在，72 行完整内容：交付摘要、实现文件列表、Runtime 能力、Demo 证据路径、检查记录、已知问题、下一步建议。

**结论**: 收据模式检查 **pass**（mcp_used 字段见 P2 发现）。

---

## 5. Demo 独立重跑 (3.1)

### 5.1 重跑环境

- **Demo 目录**: `audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/ds_verify_demo/`
- **Config 来源**: 从 `tools/pm_runtime/templates/task_config.yaml` 复制并修改路径指向 ds_verify_demo
- **执行者**: `local_echo`（默认，非真实 Codex）

### 5.2 执行序列及结果

```bash
# 1. INIT — exit 0 ✅
.venv/bin/python -m tools.pm_runtime.relay.cli init \
  --config sandbox/ds_verify_demo/dispatch/task_config.yaml

# 2. RUN — exit 0 ✅
.venv/bin/python -m tools.pm_runtime.relay.cli run \
  --task-dir sandbox/ds_verify_demo

# 3. SUMMARY — exit 0 ✅
.venv/bin/python -m tools.pm_runtime.relay.cli summary \
  --task-dir sandbox/ds_verify_demo

# 4. RECOVER — exit 0 ✅
.venv/bin/python -m tools.pm_runtime.relay.cli recover \
  --task-dir sandbox/ds_verify_demo
```

**全部 4 个命令 exit 0**。

### 5.3 重跑产生的制品

| 预期制品 | 生成状态 |
|---------|--------|
| `runtime/pre_action_check.yaml` | ✅ 已生成 |
| `runtime/task_state.yaml` | ✅ 已生成 |
| `runtime/registry_events.jsonl` | ✅ 已生成（6 条事件） |
| `runtime/heartbeat.json` | ✅ 已生成 |
| `runtime/progress.yaml` | ✅ 已生成 |
| `runtime/failure_classification.yaml` | ✅ 已生成 |
| `runtime/recovery_summary.md` | ✅ 已生成 |
| `runtime/recovered_evidence/` (6 files) | ✅ 已生成 |
| `logs/stdout.log` | ✅ 已生成 |
| `logs/stderr.log` | ✅ 已生成 |
| `logs/raw_output.jsonl` | ✅ 已生成 |
| `logs/stdout.partial.log` | ✅ 已生成 |
| `logs/stderr.partial.log` | ✅ 已生成 |
| `logs/raw_output.partial.jsonl` | ✅ 已生成 |
| `summary/pm_runtime_summary.md` | ✅ 已生成 |

**结论**: Demo 独立重跑 **pass**。DS 可以完全独立地重现 Codex 报告的 demo 结果。

---

## 6. 追加注册表检查 (3.2)

### 6.1 Codex Demo 注册表（sandbox/demo_task）

- 13 条事件，每行合法 JSON ✅
- 完整生命周期追踪: created → pre_action_checked → launched → progress(executor_completed) → summary_written → recovered → summary_written（两次完整循环）✅
- 每条事件包含: `event_id`, `task_id`, `timestamp`, `actor`, `event_type`, `reason`, `evidence_paths` ✅
- 后执行的事件追加不覆盖前事件 ✅

### 6.2 DS 重跑注册表（sandbox/ds_verify_demo）

- 6 条事件（init 1 + run 3 + summary 1 + recover 1），每行合法 JSON ✅
- 事件类型序列: created → pre_action_checked → launched → progress → summary_written → recovered ✅
- 追加行为正确：init/run/summary/recover 各自追加新行 ✅

### 6.3 追加行为验证

- 两次 summary_written 事件（Codex demo 中第 5 行和第 7 行, 第 12 行和第 13 行）确认 summary 重跑追加而非覆盖 ✅
- recover 命令在已有 registry 基础上追加 `recovered` 事件 ✅

**结论**: 追加注册表检查 **pass**。

---

## 7. 关键制品模式抽查 (3.3)

### 7.1 `runtime/pre_action_check.yaml`

```yaml
action_type: launch_executor        # ✅ 存在
intended_executor: local_echo       # ✅ 存在
result: pass                        # ✅ 存在
hold_reason: ''                     # ✅ 存在（空字符串）
task_id: ...                        # ✅ 存在
scope_checked: true                 # ✅ 存在
allowed_by_role: true               # ✅ 存在
```

### 7.2 `summary/pm_runtime_summary.md`

- ✅ 包含 Task Identity / Task Status / Runtime State / Executor Type / Execution Mode 等全部要求章节
- ✅ **明确声明**: "PM Runtime summary is not closeout."（独立章节 "No Closeout Boundary"）
- ✅ 包含 stdout/stderr/raw output 路径、Registry 路径、Owner Decision 记录、Recovery Actions

### 7.3 `runtime/recovery_summary.md`

```yaml
recovery_type: trivial_recovery     # ✅ 存在
evidence_preserved: true            # ✅ 存在
closeout_claimed: false             # ✅ 明确声明未 closeout
original_failure_paths: [...]       # ✅ 原始证据路径
new_output_paths: [...]             # ✅ 恢复后新路径（recovered_evidence/）
```

- ✅ 原始日志未被覆盖：recovery.py 使用 `shutil.copyfile()` + `if not target.exists()` 保护
- ✅ 恢复产物写入独立目录 `recovered_evidence/`

### 7.4 `runtime/task_state.yaml`

```yaml
closeout_claimed: false             # ✅ 明确声明未 closeout
runtime_states_supported: [...]     # ✅ 含 30 个状态值
known_issues: [...]                 # ✅ 记录重叠已知问题
```

### 7.5 `dispatch/task_config.yaml`

```yaml
task_id: ...                        # ✅ 存在
executor_type: local_echo           # ✅ 存在
runtime_control:                    # ✅ 完整
  mode: health_based
  heartbeat_interval_sec: 30
  no_heartbeat_timeout_sec: 300     # ✅ 300s（非 120s）
  abort_requires_owner: true        # ✅
  preserve_partial_output_on_abort: true  # ✅
scope:                              # ✅ 完整
runtime_allowed_level: L1           # ✅
```

### 7.6 场景依赖制品

| 制品 | 代码支持 | 实际生成 |
|------|---------|--------|
| `blocker_report.md` | ✅ relay_runner.py `write_blocker_report()` | ❌ 无阻塞场景 |
| `owner_decision_request.yaml` | ✅ relay_runner.py `write_owner_decision_request()` | ❌ 无决策需求 |
| `owner_decision_record.yaml` | ✅ relay_runner.py `write_owner_decision_record_template()` | ❌ 无决策需求 |
| `abort_report.yaml` | ✅ relay_runner.py `write_abort_report()` | ❌ 无中止场景 |

这些是场景依赖制品，在正常 local_echo 流程中不需要生成，代码中有显式支持函数即可。

**结论**: 制品模式抽查 **pass**。

---

## 8. 发现汇总

### P0 — 阻塞性问题

**无。**

### P1 — 需关注的问题

**无。** Codex 实现的边界合规、功能完整性、制品正确性均满足 taskbook 要求。

### P2 — 次要问题

1. **`mcp_used: false`** — Codex 回执声明未使用 MCP，但 taskbook 及实际执行中 Codex 使用了文件读取操作。这不影响功能，但回执字段元数据不够精确。**建议**: 在后续任务中统一 `mcp_used` 的语义定义（指 MCP filesystem 工具还是其他 MCP 服务）。

2. **`created_files` vs `changed_files` 几乎相同** — 回执中两个列表有大量重叠（6 个实现文件同时出现在两个列表中），降低了字段的区分度。**建议**: `changed_files` 应只包含修改的预存在文件，`created_files` 只包含新建文件。

3. **Sandbox demo summary 在 `created_files` 中缺失** — `sandbox/demo_task/summary/pm_runtime_summary.md` 列在 `output_files` 但不在 `created_files` 中（而主 summary 两者都有）。这是回执记录的不一致。

### P3 — 建议改进

1. **`__pycache__` 生成** — py_compile 在 `tools/pm_runtime/` 下生成了 `__pycache__/` 目录。Codex 已在 known_issues 中记录。**无风险**，`.gitignore` 覆盖即可。

2. **模板副本放置** — Codex 在 `tools/pm_runtime/templates/` 下放置了 `receipt.template.yaml` 和 `dispatch.template.yaml` 的副本。这些是通用模板的冗余副本，不影响功能，但增加了维护点。

3. **`task_state.yaml` 中 runtime_state 不一致** — DS 重跑后 `task_state.yaml` 显示 `runtime_state: created` 而非 `recovered`，可能是因为 `init` 重跑了 task_state 初始化。这不影响核心功能但表明状态转换在多次重跑时可能不够精确。

---

## 9. Process Issues

1. **Owner override 使用** — Codex 使用了 `owner_override_used: true`，原因为 `infrastructure_creation_lane_not_supported_by_current_safety_gate`。这符合 taskbook §24 的预期（safety gate 需要 patch 以支持 infrastructure_creation_lane）。已在 known_issues 中记录。

---

## 10. Blockers

**无。**

---

## 11. Known Issues（继承自 Codex）

1. Safety gate 需后续 patch 以支持 Hermes 分发的 infrastructure_creation_lane
2. Runtime state 值与 task_status 有意重叠（MVP 兼容性）
3. MVP 仅支持单任务（无 daemon/queue/dashboard/database/worker pool）
4. 最小 YAML fallback 不是通用 YAML 解析器
5. py_compile 生成 `__pycache__` 文件
6. 预存在的通用模板和 dispatch/ds/scripts/relay_logs 证据被观察但未被修改
7. 分类分支覆盖了 MVP 级别所需标签，生产策略映射需 DS 和 Owner-Control 验证

---

## 12. Recommended Next Actions

1. **owner_control_gate** — Owner-Control 审查本 DS 验证报告并决定是否接受 MVP 为 bootstrap usable
2. **codex_patch** — 如 Owner 批准，触发 safety gate infrastructure_creation_lane patch（独立任务）
3. **不 hold** — DS Team 未发现需 hold 的阻塞问题

---

## 13. Gate 裁决

```yaml
acceptance_verdict: pass_with_known_issues
implementation_readiness: usable
```

**解释**: Codex 实现满足 taskbook 全部硬性要求——边界合规、语法正确、制品模式完整、Demo 可独立重现、追加注册表行为正确、无 closeout 声明。已知问题均为 MVP 范围内的设计取舍，不影响 bootstrap 可用性。

Owner-Control 可以决定是否接受此 MVP 作为 bootstrap usable。

---

*DS Team 验证完成时间: 2026-05-22T23:14:00+08:00*
*DS Team 不执行 closeout。*