# PM Runtime Communication Substrate MVP — Codex Implementation Taskbook v0.1

> document_type: implementation_taskbook / Codex execution candidate  
> project: Adarian / 多智能体舆情推演系统 Workflow v4.0  
> task_name: PM Runtime Communication Substrate MVP  
> version: v0.1.0  
> lane: pm_runtime_infrastructure  
> status: owner_repair_required / not_ready_for_codex / not_repository_landed  
> canonical_task_domain: pm-runtime-governance  
> canonical_task_path: `audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/`  
> safety_gate_trigger_path_after_owner_approval: `docs/iterations/v0.1.0-pm-runtime-communication-substrate-mvp.md`  
> owner_control_required: true  

---

## 0. Current Gate

当前任务书还不能直接交给 Codex。

必须先经过：

```text
Control Agent draft
→ Owner repair / Owner approval
→ Hermes copies approved taskbook to docs/iterations as safety-gate trigger
→ Codex executes
→ Hermes / PM Runtime collects receipt
→ DS Team verifies implementation
→ Owner-Control gate
```

本任务书的主文件应先保留在：

```text
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/dispatch/codex_taskbook.md
```

只有 Owner 明确批准后，Hermes 才能复制一份到：

```text
docs/iterations/v0.1.0-pm-runtime-communication-substrate-mvp.md
```

注意：复制到 `docs/iterations/` 的目的只是触发 Codex 现有 safety gate。  
`audit/tasks/...` 仍然是 canonical task package 和 evidence root。

---

## 1. Background

PM Runtime Communication Substrate 是 PM Runtime / Hermes 的通讯层工程基座，不是 skill。

它用于解决：

1. 长程任务如何以独立进程运行；
2. Codex / Claude / DS Team 任务如何统一登记；
3. 任务如何写 heartbeat / progress / result；
4. 用户中断、进程超时、sandbox 拦截后如何恢复；
5. stdout / stderr / raw output 如何保全；
6. Owner Decision Relay 如何记录；
7. PM Runtime 如何生成 summary 但不 claim closeout。

本次实现基于以下已审查/已确认资产：

```text
PM Runtime Communication Substrate Runtime Contract v0.1
PM Runtime Communication Substrate Bootstrap Plan v0.3
Codex Execution and Owner Decision Relay Patch Note
DS Team Runtime Contract Review: pass_with_known_issues
workflow_compact.yaml → workflow_compact_v0.3.3.yaml
```

---

## 2. Implementation Objective

让 Codex 在 `tools/pm_runtime/relay/` 下实现一个最小 Python MVP。

MVP 目标：

```text
可创建任务
可启动独立 executor 进程
可记录 pre-action check
可写 append-only registry
可捕获 stdout / stderr
可保留 partial output
可生成 blocker report / owner decision request
可生成 pm_runtime_summary
不 closeout
不改业务源码
```

---

## 3. Source Placement

本次通讯层源码放在：

```text
tools/pm_runtime/relay/
```

模板放在：

```text
tools/pm_runtime/templates/
```

不要放入：

```text
skills/
tests/
src/
docs/skills/workflow_v4.0/
```

说明：

```text
Communication Substrate = 工程基座 platform
Skill = 后续 operator manual
```

因此 runtime 平台源码不得放到 skills 目录中。

---

## 4. Allowed Files

Codex 只允许创建或修改：

```text
tools/pm_runtime/relay/__init__.py
tools/pm_runtime/relay/cli.py
tools/pm_runtime/relay/relay_runner.py
tools/pm_runtime/relay/extractors.py
tools/pm_runtime/relay/recovery.py
tools/pm_runtime/templates/task_config.yaml
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/**
docs/iterations/v0.1.0-pm-runtime-communication-substrate-mvp.md
```

`docs/iterations/...` 只能在 Owner approval 后由 Hermes 复制 approved taskbook 形成。Codex 不应自行创建新的 iteration doc，除非 dispatch 明确要求。

---

## 5. Forbidden Files

Codex 严禁触碰：

```text
src/**
main.py
config.py
tests/**
seeds/**
outputs/**
docs/skills/workflow_v4.0/**
docs/skills/workflow_core.md
workflow_core*
.claude/**
.codex/**
.hermes/**
.git/**
```

也禁止：

```text
删除历史文件
修改 DS verdict
修改 Runtime Contract
修改 workflow_compact.yaml symlink
修改 workflow_compact_v0.3.3.yaml
git commit
```

---

## 6. Required MVP Modules

### 6.1 `cli.py`

提供最小 CLI：

```bash
python -m tools.pm_runtime.relay.cli init --config <task_config.yaml>
python -m tools.pm_runtime.relay.cli run --task-dir <task_dir>
python -m tools.pm_runtime.relay.cli recover --task-dir <task_dir>
python -m tools.pm_runtime.relay.cli summary --task-dir <task_dir>
```

v0.1 不要求复杂参数解析，可用 `argparse`。

### 6.2 `relay_runner.py`

负责：

1. 读取 task_config；
2. 写 pre_action_check；
3. 启动 independent subprocess；
4. 记录 pid / process_group；
5. 写 heartbeat；
6. 捕获 stdout / stderr；
7. 写 raw output；
8. 按 health-based control 标记 runtime_state；
9. 保存 partial output；
10. 写 registry event；
11. 不做 closeout。

### 6.3 `extractors.py`

负责：

1. 解析 Codex JSONL；
2. 提取 agent message；
3. 提取 structured YAML receipt；
4. 处理非 JSONL / partial output；
5. 返回 extraction result，不修改原始日志。

### 6.4 `recovery.py`

负责：

1. 从已有 logs 中恢复 report / receipt；
2. 生成 recovery_summary；
3. 保留原始 evidence；
4. 标记 recovered / rerun_required；
5. 不覆盖原始失败文件；
6. 不修改 DS verdict。

### 6.5 `task_config.yaml`

提供模板字段：

```yaml
task_id:
task_domain:
short_task:
task_level:
executor_type:
execution_mode:
owner_control_required: true
paths:
runtime_control:
scope:
executor_options:
```

---

## 7. Required Runtime Artifacts

MVP 必须支持生成以下文件：

```text
runtime/pre_action_check.yaml
runtime/task_state.yaml
runtime/registry_events.jsonl
runtime/heartbeat.json
runtime/progress.yaml
runtime/blocker_report.md
runtime/owner_decision_request.yaml
runtime/owner_decision_record.yaml
runtime/recovery_summary.md
logs/stdout.log
logs/stderr.log
logs/raw_output.jsonl
logs/stdout.partial.log
logs/stderr.partial.log
summary/pm_runtime_summary.md
```

v0.1 中某些文件可以只在对应场景生成，但代码结构必须支持写入。

---

## 8. Runtime Semantics

### 8.1 Status Model

采用双层状态：

```text
task_status = workflow lifecycle
runtime_state = operational detail
```

`task_status` 建议值：

```text
proposed
approved
running
completed
failed
hold
closed
archived
```

`runtime_state` 至少支持：

```text
created
dispatch_ready
pre_action_checking
launching
healthy_running
slow_but_progressing
waiting_input
permission_blocked
sandbox_denied
suspected_blocked
missing_receipt
missing_report
partial_output
recovering
recovered
rerun_required
aborting
aborted
executor_completed
executor_failed
summary_written
```

### 8.2 Registry

`runtime/registry_events.jsonl` 必须是 append-only。  
不得重写已有事件。

### 8.3 Health-Based Control

不允许把 hard timeout 当主控。

必须使用：

```yaml
runtime_control:
  mode: health_based
  heartbeat_interval_sec: 30
  progress_check_interval_sec: 120
  no_heartbeat_timeout_sec: 180
  no_progress_review_sec: 600
  owner_review_after_sec: 1800
  emergency_max_wall_time_sec: null
  abort_requires_owner: true
  preserve_partial_output_on_abort: true
```

v0.1 可以实现简化逻辑，但字段和 summary 必须存在。

### 8.4 Owner Decision Relay

需要支持 decision-needed event：

```text
approval_required
sandbox_denied
permission_blocked
waiting_input
scope_violation
unclear_policy
missing_receipt
recovery_requires_approval
```

运行中双向交互若不可行，必须标记：

```text
rerun_required
```

不得假装已经 live-supported。

---

## 9. Codex Managed Executor Requirements

Codex 执行模式：

```text
managed_codex_exec
```

应支持记录：

```text
codex exec --sandbox read-only --skip-git-repo-check --ephemeral --json
codex exec --sandbox workspace-write --skip-git-repo-check --ephemeral --add-dir <sandbox_path> --json
```

注意：

1. Codex stdout 是 JSONL；
2. Codex 启动基线约 120–136 秒；
3. 不得用 120s 普通调用超时判断任务失败；
4. sandbox_denied 不是 success；
5. approval_required 未必出现，OS sandbox 可能直接拦截。

---

## 10. Required Checks

Codex 完成后必须运行：

```bash
.venv/bin/python -m py_compile tools/pm_runtime/relay/cli.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/relay_runner.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/extractors.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/recovery.py
.venv/bin/python -c "from tools.pm_runtime.relay import cli; print('import OK')"
```

如果 `.venv/bin/python` 不存在，可使用：

```bash
python -m py_compile ...
python -c "from tools.pm_runtime.relay import cli; print('import OK')"
```

但必须在 receipt 中说明 Python 解释器路径。

---

## 11. Minimal Demo Requirement

Codex 应创建一个只在当前任务目录下运行的 sandbox demo，验证：

1. init task；
2. run a tiny local command executor 或 echo executor；
3. stdout/stderr capture；
4. registry event append；
5. summary generation。

Demo 只允许写：

```text
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/**
```

如果 demo 不可做，需说明 blocker，不得扩大 scope。

---

## 12. Receipt Requirements

Codex 必须回传：

```yaml
executor: codex
task_id: pm-runtime-communication-substrate-mvp
changed_files: []
commands_run: []
test_results: []
diff_summary:
receipt_path:
handoff_path:
commit_status: no_commit
forbidden_files_touched: []
known_issues: []
blockers: []
runtime_contract_deviations: []
```

---

## 13. DS Verification Expectations

Codex 完成后，DS Team 应检查：

1. 是否只改 allowed_files；
2. 是否没有触碰 forbidden_files；
3. 是否实现独立进程 / session 基础；
4. pre_action_check 是否可生成；
5. registry_events 是否 append-only；
6. stdout/stderr 是否保留；
7. partial output 是否有接口；
8. owner_decision_request / record 是否有接口；
9. recovery 是否保留证据；
10. summary 是否明确 not closeout。

---

## 14. Hard Boundaries

Codex 不得：

1. 触碰业务源码；
2. 修改 workflow authority；
3. 修改 YAML symlink；
4. 修改 `.claude/.codex/.hermes`；
5. 提交 git commit；
6. 扩大实现成 daemon / dashboard / queue；
7. 删除 audit/tasks 既有内容；
8. 把 demo 写到业务目录；
9. 声称 closeout。

---

## 15. Owner Approval Before Iteration Trigger

This is mandatory:

```text
Do not copy this taskbook into docs/iterations until Owner has repaired and approved it.
```

Approval sequence:

```text
1. Draft stays in audit/tasks/.../dispatch/
2. Owner repairs / approves taskbook
3. Hermes copies approved taskbook to docs/iterations/
4. Codex safety gate may start
```

If this sequence is violated:

```text
HOLD_OWNER_APPROVAL_MISSING
```

---

## 16. Expected Next Step

After Owner approval:

Hermes should copy the approved taskbook to:

```text
docs/iterations/v0.1.0-pm-runtime-communication-substrate-mvp.md
```

and then dispatch Codex with this taskbook.

Until then:

```text
implementation_status: not_started
codex_dispatch_status: hold
```
