# PM Runtime Communication Substrate Runtime Contract v0.1

> document_type: runtime_contract / implementation_boundary_contract  
> project: Adarian / 多智能体舆情推演系统 Workflow v4.0  
> contract_name: PM Runtime Communication Substrate Runtime Contract  
> version: v0.1  
> status: draft candidate / not repository-landed / pending focused DS review  
> created_at: 2026-05-22  
> author: ChatGPT Control Agent  
> based_on:
> - `pm_runtime_communication_substrate_bootstrap_plan_v0.3.md`
> - `pm_runtime_communication_substrate_v0.3_codex_decision_relay_patch_note.md`
> - `ds_substrate_plan_review.md`
> - `hermes_codex_workflow_verification_spike_summary.md`
> - `owner_decision_relay_test_summary.md`
> owner_control_required: true  

---

## 0. Contract Purpose

本文件定义 PM Runtime Communication Substrate v0.1 的最小运行契约。

它不是：

```text
代码实现
operator skill
角色卡
workflow_core
DS 审查报告
Codex 执行任务卡
```

它是：

```text
在写 Python MVP 之前必须锁定的 runtime contract。
```

本 contract 的目的：

1. 明确任务目录、状态、session、registry、artifact、recovery、decision relay 的最小契约；
2. 防止平台实现阶段出现权限漂移、证据污染、状态混乱；
3. 将 DS Team v0.2 审查的 P0/P1 findings 固化为实现前约束；
4. 将 Codex spike 和 Owner Decision Relay 测试结果纳入 executor contract；
5. 为后续 Python MVP 任务卡提供可执行边界。

---

## 1. Scope

### 1.1 In Scope

PM Runtime Communication Substrate v0.1 覆盖：

1. task creation；
2. task directory policy；
3. task session；
4. independent process / supervisor model；
5. pre-action check；
6. health-based runtime control；
7. heartbeat / progress / result；
8. stdout / stderr / raw output capture；
9. append-only registry；
10. task_status / runtime_state；
11. managed executor profiles；
12. Owner Decision Relay；
13. recovery / rerun / round model；
14. partial output preservation；
15. PM Runtime summary；
16. no-closeout boundary。

### 1.2 Out of Scope

v0.1 不做：

1. 全局 daemon；
2. Web dashboard；
3. 分布式队列；
4. 多机执行；
5. 自动 git commit；
6. 自动 closeout；
7. 自动修改 workflow_core；
8. 自动修改 DS verdict；
9. 自动批准 Codex landing；
10. 复杂数据库；
11. 长期权限管理 UI；
12. 生产级并发调度池。

---

## 2. Core Runtime Principles

### 2.1 Communication Substrate Is Platform, Not Skill

```text
Communication Substrate = 工程基座平台
Operator Skill = 平台使用说明
Role Card = 角色边界
Workflow Core = 治理原则
```

不得再把通讯层平台误写成一个 `SKILL.md`。

后续可写 operator skill，但只能说明如何使用平台，不得把 skill 当成平台能力本体。

### 2.2 Independent Process Is Required

长程 executor 不能通过 Hermes 普通短时调用直接管理。

必须采用：

```text
Hermes / PM Runtime
→ independent supervisor process
→ executor process/session
→ persistent task registry
→ heartbeat/progress/result files
```

原因：

1. Codex / Claude 首次启动可能超过普通 120s 工具调用；
2. 长程任务需要持续状态；
3. 用户中断或会话断开后需要恢复；
4. 同一 task 下需要避免反复 cold start；
5. stdout/stderr/receipt/report 必须持久化。

### 2.3 Health-Based Control, Not Hard Timeout-Based Control

固定 hard timeout 只能作为 emergency guard，不得作为主调度策略。

正确模式：

```text
monitor health
→ detect no heartbeat / no progress / waiting input / permission blocked
→ write blocker report
→ request Owner-Control decision
→ continue / rerun / recover / abort
```

### 2.4 Evidence Preservation First

任何失败、超时、恢复、重跑、阻塞，都不得覆盖原始证据。

必须保留：

1. 原始 stdout；
2. 原始 stderr；
3. raw output；
4. exit code；
5. failure classification；
6. recovery action；
7. Owner decision；
8. append-only registry event。

### 2.5 PM Runtime Does Not Own Closeout

Communication Substrate 可以：

```text
dispatch
monitor
recover
collect evidence
summarize
```

不能：

```text
final closeout
modify DS verdict
downgrade blocker
approve landing
change workflow authority
git commit
```

最终 gate 仍属于 Owner-Control。

---

## 3. Canonical Directory Policy

### 3.1 Active Task Directory

v0.1 采用两级目录：

```text
audit/tasks/active/<task_domain>/<short_task>/
```

示例：

```text
audit/tasks/active/pm-runtime-governance/codex-workflow-verification-spike/
audit/tasks/active/workflow-governance/ds-substrate-plan-review/
audit/tasks/active/source-code/v1-2-9-patch/
```

### 3.2 Required Subdirectories

每个 task 目录至少包含：

```text
dispatch/
runtime/
logs/
summary/
```

按 executor 可选：

```text
ds/
codex/
sandbox/
scripts/
artifacts/
```

推荐结构：

```text
audit/tasks/active/<task_domain>/<short_task>/
├── dispatch/
│   ├── dispatch.md
│   ├── system_prompt.md
│   └── task_config.yaml
├── runtime/
│   ├── pre_action_check.yaml
│   ├── task_state.yaml
│   ├── registry_events.jsonl
│   ├── heartbeat.json
│   ├── progress.yaml
│   ├── blocker_report.md
│   ├── owner_decision_request.yaml
│   ├── owner_decision_record.yaml
│   └── recovery_summary.md
├── logs/
│   ├── stdout.log
│   ├── stderr.log
│   ├── raw_output.jsonl
│   ├── stdout.partial.log
│   └── stderr.partial.log
├── ds/
├── codex/
├── sandbox/
└── summary/
    └── pm_runtime_summary.md
```

### 3.3 YAML Alignment Requirement

若 workflow compact YAML 当前采用：

```text
audit/tasks/active/<task_id>/
```

则后续 YAML patch 必须对齐为两级目录，或加入兼容别名。

Runtime Contract 采用：

```yaml
directory_policy_decision: two_level_domain_short_task
yaml_patch_required: true
```

---

## 4. Task Identity Model

### 4.1 Required Identifiers

每个 task 必须有：

```yaml
task_id: required
task_domain: required
short_task: required
session_id: required_if_launched
round_id: required_if_executor_launched
```

### 4.2 Field Definitions

| Field | Meaning |
|---|---|
| task_id | 全局任务标识，稳定不变 |
| task_domain | 任务域，如 pm-runtime-governance / workflow-governance / source-code |
| short_task | 人类可读短任务名，用于路径 |
| session_id | 一次 executor 会话标识 |
| round_id | 同一 task 下第几轮执行，支持 rerun |

### 4.3 Task ID Recommendation

推荐格式：

```text
<domain>-<task-name>-<YYYYMMDD>-<short-hash>
```

示例：

```text
pm-runtime-governance-codex-spike-20260522-a1b2
```

---

## 5. Status Model

### 5.1 Two-Level Status Model

v0.1 使用双层状态：

```text
task_status = workflow-level lifecycle
runtime_state = operational detail
```

原因：

1. 防止 platform 自造状态与 YAML / compact 冲突；
2. 保持 workflow-level 状态稳定；
3. 将运行细节隔离在 runtime_state。

### 5.2 task_status

`task_status` 应对齐 workflow compact / YAML 的正式枚举。

v0.1 建议值：

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

如果后续 YAML patch 定义不同正式枚举，以 Owner-Control 批准后的 YAML 为准。

### 5.3 runtime_state

`runtime_state` 用于描述运行细节：

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

### 5.4 Status Boundary

不得将：

```text
executor_completed
summary_written
recovered
receipt_received
```

误写为：

```text
closed
closeout
accepted
Owner-Control pass
```

---

## 6. Task Config Contract

每次启动 executor 前必须有 `dispatch/task_config.yaml`。

最低字段：

```yaml
task_id: required
task_domain: required
short_task: required
task_level: S | M | L | patch
executor_type: claude | ds_team | codex | hermes | external_agent
execution_mode: managed_relay_session | managed_codex_exec | manual_transport
owner_control_required: true

paths:
  task_dir: required
  dispatch_path: required
  system_prompt_path: optional
  runtime_dir: required
  logs_dir: required
  summary_path: required

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

scope:
  allowed_files: []
  forbidden_files: []
  allowed_dirs: []
  sandbox_dir: optional

executor_options:
  sandbox_mode: optional
  allowed_tools: []
  max_turns: optional
  extra_args: []
```

---

## 7. Pre-Action Check Contract

### 7.1 Required File

Before any key runtime action, write:

```text
runtime/pre_action_check.yaml
```

### 7.2 Required Fields

```yaml
task_id:
session_id:
round_id:
action_type: create_task | launch_executor | recover_task | classify_failure | produce_summary | request_owner_decision
intended_executor:
task_domain:
task_level:
artifact_expected: true | false
artifact_target_paths: []
role_boundary_checked: true
allowed_by_role: true | false | unclear
needs_ds_team: true | false | unclear
needs_owner_approval: true | false | unclear
mcp_or_tool_preflight_required: true | false
scope_checked: true | false
allowed_files: []
forbidden_files: []
result: pass | hold
hold_reason: optional
created_at:
```

### 7.3 HOLD Rule

If:

```yaml
result: hold
```

then executor must not launch.

### 7.4 Pre-Action Gate Minimum Checks

Must check:

1. Is PM Runtime allowed to do this action?
2. Is this lightweight scan, runtime operation, formal audit, or final gate?
3. Does this task require DS Team?
4. Is task_domain correct?
5. Are artifact paths defined?
6. Is Owner approval required?
7. Are allowed / forbidden boundaries defined?
8. Are tool / MCP / sandbox conditions sufficient?
9. Could output be misread as closeout?

---

## 8. Independent Process and Session Contract

### 8.1 Process Model

Runtime uses:

```text
supervisor process
→ executor process/session
```

Minimum tracked fields:

```yaml
supervisor_pid:
executor_pid:
process_group:
started_at:
last_heartbeat_at:
last_progress_at:
last_observed_output_at:
```

### 8.2 Session State

Each launched executor round must have:

```yaml
session_id:
round_id:
executor_type:
execution_mode:
runtime_state:
started_at:
last_observed_output_at:
ended_at:
```

### 8.3 No Ordinary Short Call for Long Tasks

Codex / Claude / DS long tasks must not be managed by a single Hermes ordinary tool call.

If executor startup baseline exceeds ordinary tool timeout, use independent process.

Codex observed baseline:

```yaml
executor_startup_baseline:
  codex_exec_sec: 120
```

Claude baseline:

```yaml
executor_startup_baseline:
  claude_exec_sec: TBD
```

---

## 9. Health-Based Runtime Control

### 9.1 Health Signals

Runtime must observe:

1. heartbeat timestamp；
2. progress timestamp；
3. stdout growth；
4. stderr growth；
5. raw output event count；
6. pid / process state；
7. report path existence；
8. receipt path existence；
9. owner decision request existence。

### 9.2 State Transitions

Examples:

```text
healthy_running
→ slow_but_progressing
→ suspected_blocked
→ waiting_input
→ owner_decision_required
→ continue / rerun_required / aborted
```

### 9.3 Blocker Report

When suspected blocked, write:

```text
runtime/blocker_report.md
```

Required fields:

```yaml
task_id:
session_id:
round_id:
runtime_state:
elapsed_seconds:
last_heartbeat_at:
last_progress_at:
stdout_growth:
stderr_tail:
suspected_blocker:
recommended_actions:
  - continue
  - attach
  - request_owner_decision
  - repair_permissions
  - recover_partial_output
  - abort
owner_control_required: true
```

### 9.4 Abort Rule

Abort is allowed when:

1. Owner explicitly approves；
2. process is clearly dead；
3. no heartbeat and pid not alive；
4. safety boundary violation occurs；
5. executor is waiting for impossible input；
6. emergency guard triggers and partial output is preserved。

Abort must write:

```text
runtime/abort_report.yaml
logs/stdout.partial.log
logs/stderr.partial.log
```

---

## 10. Append-Only Registry Contract

### 10.1 Required File

Runtime must write:

```text
runtime/registry_events.jsonl
```

### 10.2 Event Format

Each line is JSON:

```json
{
  "event_id": "required",
  "task_id": "required",
  "session_id": "optional",
  "round_id": "optional",
  "timestamp": "required",
  "actor": "hermes|runtime|owner|codex|ds|control|external",
  "event_type": "created|pre_action_checked|launched|heartbeat|progress|blocked|owner_decision_requested|owner_decision_recorded|recovered|rerun_started|summary_written|aborted",
  "from_task_status": "optional",
  "to_task_status": "optional",
  "from_runtime_state": "optional",
  "to_runtime_state": "optional",
  "reason": "required",
  "evidence_paths": []
}
```

### 10.3 Anti-Tamper Rule

Runtime may write cached current state to:

```text
runtime/task_state.yaml
```

But cached state does not replace append-only registry.

If cached state conflicts with registry events:

```text
HOLD_REGISTRY_CONFLICT
return_to: Owner-Control
```

### 10.4 No Silent Rewrite

No component may silently rewrite:

1. registry_events.jsonl；
2. raw stdout / stderr；
3. original failure result；
4. owner decision record。

---

## 11. Output Capture Contract

### 11.1 Required Logs

Every executor launch must capture:

```text
logs/stdout.log
logs/stderr.log
logs/raw_output.*
```

Format depends on executor:

| Executor | stdout format |
|---|---|
| Codex | JSONL |
| Claude / DS | JSON or text depending CLI |
| External | task-specific |

### 11.2 Partial Output Preservation

On timeout / abort / process killed / sandbox denied / permission blocked:

```text
logs/stdout.partial.log
logs/stderr.partial.log
logs/raw_output.partial.*
runtime/abort_or_timeout_report.yaml
```

must be written if any data exists.

### 11.3 No Evidence Suppression

stderr must be preserved even if exit code is 0.

Warnings, permission denials, reconnection logs, sandbox messages are runtime evidence.

---

## 12. Executor Profiles

### 12.1 Codex Profile

```yaml
executor_type: codex
supported_modes:
  - managed_codex_exec
launch_mode: independent_subprocess
stdout_format: jsonl
recommended_sandbox_modes:
  - read-only
  - workspace-write
required_flags:
  - --skip-git-repo-check
  - --ephemeral
  - --json
recommended_scope_control:
  - --add-dir for write tasks
required_captures:
  - stdout
  - stderr
  - exit_code
  - jsonl_events
required_receipt_fields:
  - executor
  - mode
  - changed_files
  - commands_run
  - test_results
  - exit_code
  - sandbox_mode
  - stdout_path
  - stderr_path
  - known_issues
forbidden:
  - final_closeout
  - auto_commit_without_explicit_owner_approval
  - touching_forbidden_files
  - treating_sandbox_denied_as_success
  - suppressing stderr_or_stdout_evidence
```

Observed baseline:

```yaml
codex_cli_available: true
codex_exec_available: true
approval_required_observed: false
managed_codex_exec_candidate: true
startup_overhead_sec: 120_to_136
```

### 12.2 Claude / DS Team Profile

```yaml
executor_type: claude_or_ds_team
supported_modes:
  - managed_relay_session
launch_mode: independent_subprocess
required_outputs:
  - report_path
  - receipt_path
  - acceptance_verdict_if_review
  - findings_if_review
  - process_issues
  - blockers
  - mcp_used
  - team_mode_used
forbidden:
  - final_closeout
  - modifying_files_in_read_only_review
  - downgrading_blockers
  - treating_scan_as_audit
  - ignoring_real_paths
```

### 12.3 Hermes / PM Runtime Profile

PM Runtime must inherit all existing PM Runtime instruction forbidden items.

Minimum forbidden set:

```text
1. final closeout
2. modify DS verdict
3. downgrade blocker
4. modify Codex diff
5. approve high-risk task
6. expand scope
7. modify allowed / forbidden boundaries
8. close safety checks
9. modify workflow_core
10. mark candidate as repository-landed
11. delete historical documents
12. modify business source code
13. git commit
14. treat summary as final gate
15. bypass Owner-Control
16. hide process issues
```

PM Runtime may do:

```text
dispatch
monitor
recover
summarize
task-local communication repair
```

---

## 13. Owner Decision Relay Contract

### 13.1 Purpose

Owner Decision Relay covers all decision-needed runtime events, not just approval prompts.

### 13.2 Covered Events

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

### 13.3 Request File

When decision is needed, write:

```text
runtime/owner_decision_request.yaml
```

Required fields:

```yaml
task_id:
session_id:
round_id:
request_id:
executor:
event_type:
requested_action:
affected_files: []
observed_result:
agent_message:
risk_level: low | medium | high | unknown
allowed_scope: []
forbidden_scope: []
available_options:
  - approve_with_scope
  - reject
  - abort_task
  - request_safer_alternative
  - ask_for_more_context
recommended_action:
owner_control_required: true
created_at:
```

### 13.4 Decision File

Owner decision must be recorded in:

```text
runtime/owner_decision_record.yaml
```

Required fields:

```yaml
task_id:
session_id:
round_id:
request_id:
owner_decision:
decision_source: owner_chat | owner_file | owner_ui | unknown
decision_time:
approved_scope: []
rejected_scope: []
notes:
next_runtime_action:
```

### 13.5 One-Shot Limitation

If executor is one-shot subprocess, not all options are live-supported.

| Decision | One-shot support | Handling |
|---|---|---|
| reject | supported | record and stop |
| abort_task | supported | terminate and record |
| ask_for_more_context | not live-supported | rerun_or_manual_required |
| approve_with_modified_scope | not live-supported | start new round |
| request_safer_alternative | rerun required | start new round |

---

## 14. Round-Based Rerun Contract

### 14.1 Purpose

A rerun is not a new task. It is a new round under the same task.

### 14.2 Required Fields

```yaml
task_id:
round_id:
parent_round_id:
session_id:
rerun_reason:
rerun_config_delta:
evidence_from_previous_round: []
owner_decision_record: optional
```

### 14.3 Required Registry Event

Every rerun must append:

```json
{
  "event_type": "rerun_started",
  "reason": "required",
  "evidence_paths": ["previous round evidence"]
}
```

### 14.4 Rerun Triggers

Allowed rerun triggers:

1. sandbox_denied and Owner approves safer alternative；
2. missing receipt and Owner requests structured receipt rerun；
3. output format invalid；
4. permission issue repaired；
5. scope reduced；
6. executor failed due to recoverable environment issue。

### 14.5 Rerun Boundaries

Rerun must not:

1. erase previous failure；
2. change task_id；
3. claim normal completion if recovered；
4. expand scope without Owner approval；
5. hide previous round logs。

---

## 15. Recovery Contract

### 15.1 Recovery Types

```text
trivial_recovery
non_trivial_recovery
owner_approved_recovery
```

### 15.2 Trivial Recovery

Examples:

1. parse already-existing stdout；
2. extract receipt from existing report；
3. regenerate summary from existing evidence。

Allowed without new Owner approval, but must be recorded.

### 15.3 Non-Trivial Recovery

Examples:

1. change sandbox scope；
2. rerun executor；
3. reconstruct receipt manually；
4. classify a failed task as recovered。

Requires Owner-Control approval.

### 15.4 Recovery Output

Write:

```text
runtime/recovery_summary.md
```

Must include:

```yaml
task_id:
session_id:
round_id:
recovery_type:
original_failure_paths: []
new_output_paths: []
evidence_preserved: true | false
owner_approval_required: true | false
owner_approval_record: optional
runtime_state: recovered
closeout_claimed: false
```

---

## 16. Failure Classification Contract

v0.1 uses a minimal classification set:

```text
agent_completed
agent_failed
permission_blocked
sandbox_denied
partial_output
json_parse_failed
no_output
timeout_or_abort
process_killed
environment_blocked
missing_receipt
missing_report
artifact_path_missing
role_boundary_violation
```

Each classification must include:

```yaml
classification:
evidence:
  - path:
  - excerpt_or_summary:
confidence: low | medium | high
classified_by: runtime | hermes | ds | owner-control
requires_independent_review: true | false
```

Role boundary violation must not be self-cleared by Hermes.

---

## 17. Summary Contract

PM Runtime must write:

```text
summary/pm_runtime_summary.md
```

Required sections:

1. task_id；
2. task_status；
3. runtime_state；
4. executor_type；
5. execution_mode；
6. dispatch_path；
7. report_paths；
8. receipt_paths；
9. stdout/stderr/raw output paths；
10. registry path；
11. owner decision requests / records；
12. recovery actions；
13. process issues；
14. blockers；
15. known issues；
16. next recommendation；
17. explicit statement: `PM Runtime summary is not closeout`.

---

## 18. YAML / Compact Compatibility

This contract requires later alignment with workflow compact YAML:

1. directory policy；
2. task_status enum；
3. runtime_state enum；
4. task_level enum；
5. executor_type enum；
6. hold codes；
7. receipt contract；
8. dispatch contract；
9. closeout gate definitions。

Until YAML is patched:

```text
HOLD_YAML_ALIGNMENT_PENDING
```

does not block drafting Python MVP task card, but must block repository landing.

---

## 19. Implementation Gate

Python MVP task card may be drafted only after Owner-Control accepts this contract direction.

Codex implementation may begin only after:

1. Runtime Contract v0.1 reviewed；
2. no P0 blocker；
3. allowed files defined；
4. forbidden files defined；
5. no workflow_core modification unless explicitly approved；
6. no business source modification；
7. no auto commit；
8. test plan defined；
9. receipt requirements defined。

---

## 20. Focused DS Review Request

### 20.1 Review Type

```text
focused_runtime_contract_review
```

### 20.2 Required Questions

DS Team should review:

1. Does this contract fully absorb the 7 P0 findings from v0.2 review?
2. Is pre-action gate sufficiently early and enforceable?
3. Is independent process + task session sufficiently specified?
4. Is health-based runtime control better than hard timeout?
5. Is append-only registry sufficient to reduce tampering risk?
6. Is recovery evidence preservation sufficient?
7. Is Codex managed executor profile consistent with spike evidence?
8. Is Owner Decision Relay correctly generalized beyond approval prompts?
9. Are one-shot subprocess limitations handled honestly?
10. Are Hermes forbidden items sufficiently embedded?
11. Are there any P0 blockers before Python MVP task card?

### 20.3 Expected Output

```yaml
review_type: focused_runtime_contract_review
acceptance_verdict: pass | pass_with_known_issues | patch_required | hold | fail
findings:
  P0: []
  P1: []
  P2: []
  P3: []
process_issues: []
blockers: []
recommended_next_action:
report_path: required
```

---

## 21. Final Boundary

This contract does not authorize implementation.

It authorizes only the next review step.

Final closeout remains with Owner-Control.
