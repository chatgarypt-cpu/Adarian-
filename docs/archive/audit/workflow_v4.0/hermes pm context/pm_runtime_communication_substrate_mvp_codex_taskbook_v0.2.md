# PM Runtime Communication Substrate MVP — Codex Implementation Taskbook v0.2

> document_type: execution_taskbook / codex_implementation_contract  
> project: Adarian / 多智能体舆情推演系统 Workflow v4.0  
> task_name: PM Runtime Communication Substrate MVP  
> version: v0.2  
> supersedes: `pm_runtime_communication_substrate_mvp_codex_taskbook_v0.1.md`  
> lane: pm_runtime_infrastructure  
> status: owner_repair_candidate / not_ready_for_codex_until_owner_approval_and_ds_re_review  
> canonical_task_domain: pm-runtime-governance  
> canonical_task_path: `audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/`  
> canonical_dispatch_path: `audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/dispatch/codex_taskbook.md`  
> safety_gate_trigger_path_after_owner_approval: `docs/iterations/v0.1.0-pm-runtime-communication-substrate-mvp.md`  
> owner_control_required: true  

---

## 0. Current Gate

当前任务书仍处于 **Owner repair candidate**，不能直接交给 Codex。

必须走以下顺序：

```text
Control Agent draft v0.2
→ Owner review / repair / approval
→ DS Team quick re-review
→ Owner approval
→ Hermes copies approved taskbook to docs/iterations/ as Codex safety-gate trigger
→ Codex executes
→ Hermes / PM Runtime collects receipt / handoff
→ DS Team verifies implementation
→ Owner-Control gate
```

主任务包保留在：

```text
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/dispatch/codex_taskbook.md
```

只有 Owner 明确批准后，Hermes 才能复制一份到：

```text
docs/iterations/v0.1.0-pm-runtime-communication-substrate-mvp.md
```

复制到 `docs/iterations/` 的目的只是触发 Codex 现有 safety gate。  
`audit/tasks/...` 仍然是 canonical task package 和 evidence root。

若未经过 Owner approval 即复制或执行：

```text
HOLD_OWNER_APPROVAL_MISSING
```

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

本任务书基于以下上游资产：

```text
PM Runtime Communication Substrate Runtime Contract v0.1
PM Runtime Communication Substrate Bootstrap Plan v0.3
Codex Execution and Owner Decision Relay Patch Note
DS Team Runtime Contract Review: pass_with_known_issues
DS Team Codex Taskbook v0.1 Review: patch_required
workflow_compact.yaml → workflow_compact_v0.3.3.yaml
dispatch.template.yaml
receipt.template.yaml
workflow_core_v4.0_r2.md §6 / §7
```

---

## 2. R2 Generic Template Inheritance

### 2.1 Template Principle

本任务书继承 R2 的通用模板设计：

```text
dispatch.template.yaml = 通用任务分发基线
receipt.template.yaml = 通用任务回执基线
```

Communication Substrate MVP 只能在长程 runtime 行为需要时扩展字段，不应另起一套互不兼容的分发 / 回执格式。

### 2.2 Relationship

```text
R2 Generic Dispatch / Receipt Templates
  ↓ baseline
Runtime Contract v0.1
  ↓ long-running runtime extension
This Codex Taskbook v0.2
  ↓ concrete execution contract
Codex Implementation
```

### 2.3 Compatibility Rule

Codex implementation must produce artifacts that can be mapped back to:

```text
dispatch.template.yaml
receipt.template.yaml
```

If Runtime Contract and generic templates appear to conflict:

```text
HOLD_TEMPLATE_CONTRACT_CONFLICT
return_to: Owner-Control
```

Codex must not invent a third incompatible format.

---

## 3. Dispatch Compatibility Block

This taskbook maps to the generic `dispatch.template.yaml` baseline as follows:

```yaml
task_id: pm-runtime-communication-substrate-mvp
task_title: PM Runtime Communication Substrate MVP
task_type: codex_attempt
task_domain: pm-runtime-governance
lane: pm_runtime_infrastructure
owner: Owner-Control
executor: codex
status: proposed
created_at: owner_approved_time_required

goal:
  - Implement a minimal Python MVP for PM Runtime Communication Substrate under allowed paths.
  - Provide independent process / task session support.
  - Provide runtime artifact generation and evidence preservation.
  - Do not modify business source code or workflow authority.

scope:
  in_scope:
    - tools/pm_runtime/relay/**
    - tools/pm_runtime/templates/task_config.yaml
    - current canonical task package artifacts
  out_of_scope:
    - Adarian business runtime
    - Phase 1-4 simulation code
    - report generation logic
    - workflow authority files
    - global daemon/dashboard/distributed queue

allowed_actions:
  - create allowed Python package files
  - implement minimal CLI
  - implement relay runner MVP
  - implement Codex JSONL extraction
  - implement recovery helpers
  - implement task_config template
  - run py_compile and import checks
  - run sandbox demo under current task sandbox
  - produce receipt and handoff

forbidden_actions:
  - modify business source code
  - modify workflow authority
  - modify agent role instructions
  - modify YAML symlink or compact YAML
  - modify CLAUDE.md
  - modify dependency files
  - git commit
  - claim closeout
  - expand scope

allowed_read_paths:
  - audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/**
  - workflow_compact.yaml
  - dispatch.template.yaml
  - receipt.template.yaml
  - Runtime Contract v0.1 if present in task package
  - Bootstrap Plan v0.3 if present in task package

allowed_write_paths:
  - tools/pm_runtime/__init__.py
  - tools/pm_runtime/relay/**
  - tools/pm_runtime/templates/task_config.yaml
  - audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/runtime/**
  - audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/logs/**
  - audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/codex/**
  - audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/summary/**
  - audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/**

expected_outputs:
  - Python MVP files under tools/pm_runtime/relay/
  - task_config template
  - py_compile/import check results
  - sandbox demo artifacts
  - Codex receipt
  - handoff report

acceptance_criteria:
  - no forbidden files touched
  - all required checks run or blocker recorded
  - runtime artifacts schema supported
  - receipt aligns with generic receipt template plus Codex extension
  - PM Runtime summary states not closeout

failure_policy:
  on_blocker: hold_and_report
  on_scope_violation: stop_and_report
  on_forbidden_file_touch: fail_and_report
  on_missing_receipt: hold
```

---

## 4. Implementation Objective

Let Codex implement a minimal Python MVP under `tools/pm_runtime/relay/`.

MVP must support:

1. task initialization；
2. pre-action check；
3. independent subprocess launch；
4. append-only registry event writing；
5. stdout / stderr / raw output capture；
6. partial output preservation；
7. Codex JSONL extraction；
8. minimal failure classification；
9. Owner Decision Relay artifact generation；
10. recovery summary；
11. PM Runtime summary；
12. no-closeout boundary。

MVP must not implement:

1. global daemon；
2. dashboard；
3. distributed queue；
4. database；
5. auto approval；
6. auto closeout；
7. workflow_core modification；
8. business source modification。

---

## 5. Source Placement

Source code must be placed under:

```text
tools/pm_runtime/relay/
```

Templates must be placed under:

```text
tools/pm_runtime/templates/
```

Rationale:

```text
Communication Substrate = engineering platform
Skill = future operator manual
```

Therefore platform runtime source code must not be placed under `skills/`.

---

## 6. Allowed Files

Codex may create or modify only:

```text
tools/pm_runtime/__init__.py
tools/pm_runtime/relay/__init__.py
tools/pm_runtime/relay/cli.py
tools/pm_runtime/relay/relay_runner.py
tools/pm_runtime/relay/extractors.py
tools/pm_runtime/relay/recovery.py
tools/pm_runtime/templates/task_config.yaml

audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/runtime/**
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/logs/**
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/codex/**
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/summary/**
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/**
```

If `tools/__init__.py` is required for import in the current repository layout, Codex must not create it silently. It must report:

```text
HOLD_TOOLS_PARENT_PACKAGE_REQUIRED
```

and ask Owner-Control whether creating `tools/__init__.py` is allowed.

Reason: `tools/` may already contain unrelated assets and must not be turned into a Python package without approval.

---

## 7. Forbidden Files

Codex must not modify, create, delete, or rewrite:

```text
src/**
main.py
config.py
tests/**
seeds/**
outputs/**

CLAUDE.md
.venv/**
pyproject.toml
requirements.txt
requirements*.txt

docs/dev_spec.md
docs/workflow_changelog.md
docs/skills/**
docs/skills/workflow_v4.0/**
docs/skills/workflow_core.md
workflow_core*
workflow_compact.yaml
workflow_compact_v0.3.3.yaml

docs/iterations/**
!docs/iterations/v0.1.0-pm-runtime-communication-substrate-mvp.md

.claude/**
.codex/**
.hermes/**
.git/**

tools/**
!tools/pm_runtime/**
!tools/pm_runtime/relay/**
!tools/pm_runtime/templates/**

audit/tasks/active/**
!audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/**
```

Additional forbidden actions:

```text
delete existing files under audit/tasks unless explicitly created by Codex in this task
modify Runtime Contract
modify DS review reports
modify this taskbook unless explicitly instructed
modify generic dispatch/receipt templates
git commit
```

If glob semantics cannot express negative patterns in the executing tool, Codex must treat the most restrictive interpretation as binding and ask for clarification.

---

## 8. Required Modules and Behavior

### 8.1 `cli.py`

Minimum CLI:

```bash
python -m tools.pm_runtime.relay.cli init --config <task_config.yaml>
python -m tools.pm_runtime.relay.cli run --task-dir <task_dir>
python -m tools.pm_runtime.relay.cli recover --task-dir <task_dir>
python -m tools.pm_runtime.relay.cli summary --task-dir <task_dir>
```

#### `init`

Input:

```text
--config <task_config.yaml>
```

Behavior:

1. read YAML config；
2. validate required top-level fields；
3. create required runtime/logs/summary dirs under task_dir；
4. write `runtime/pre_action_check.yaml` with action_type=create_task；
5. write first append-only registry event；
6. write or update `runtime/task_state.yaml`；
7. exit 0 on success。

Outputs:

```text
runtime/pre_action_check.yaml
runtime/registry_events.jsonl
runtime/task_state.yaml
```

Exit codes:

```text
0 = success
2 = config_invalid
3 = scope_or_path_invalid
4 = hold_required
1 = unexpected_error
```

#### `run`

Input:

```text
--task-dir <task_dir>
```

Behavior:

1. read task_config from dispatch or runtime task_state；
2. write pre_action_check with action_type=launch_executor；
3. if hold, do not launch；
4. launch executor only if allowed；
5. write heartbeat/progress/log files；
6. capture stdout/stderr/raw output；
7. classify result；
8. write registry events；
9. generate blocker_report if blocked；
10. do not closeout。

Exit codes:

```text
0 = executor_completed_or_summary_written
5 = executor_failed
6 = blocked_or_owner_decision_required
7 = recovery_required
1 = unexpected_error
```

#### `recover`

Behavior:

1. inspect existing logs and runtime artifacts；
2. never overwrite original evidence；
3. attempt trivial recovery only；
4. write recovery_summary；
5. mark runtime_state=recovered or rerun_required；
6. do not modify verdict。

Exit codes:

```text
0 = trivial_recovery_completed
6 = owner_decision_required
7 = non_trivial_recovery_required
1 = unexpected_error
```

#### `summary`

Behavior:

1. read registry events；
2. read task_state；
3. read receipt/report/log paths；
4. produce `summary/pm_runtime_summary.md`；
5. explicitly state not closeout。

Exit codes:

```text
0 = summary_written
1 = unexpected_error
```

### 8.2 `relay_runner.py`

Must implement:

1. read `task_config.yaml`；
2. write pre_action_check before launch；
3. support independent subprocess launch；
4. record process metadata if available；
5. write heartbeat；
6. write progress；
7. capture stdout；
8. capture stderr；
9. capture raw output；
10. preserve partial output；
11. classify failure using §17；
12. emit owner decision request for decision-needed events；
13. write summary-supporting runtime artifacts；
14. never claim closeout。

Minimum state transition:

```text
created
→ pre_action_checking
→ launching
→ healthy_running
→ executor_completed | executor_failed | suspected_blocked | sandbox_denied | permission_blocked | missing_receipt | missing_report | timeout | hold_required
→ summary_written | rerun_required | recovered | aborted
```

### 8.3 `extractors.py`

Must implement functions with behavior equivalent to:

```python
parse_jsonl_events(path) -> list[dict]
extract_codex_agent_messages(events) -> list[str]
extract_yaml_blocks(text) -> list[str]
extract_receipt_candidate(text) -> dict | None
write_extraction_result(result, output_path) -> None
```

Codex JSONL parsing must handle:

1. one JSON object per line；
2. item.completed events；
3. agent_message text；
4. error events；
5. incomplete JSONL gracefully；
6. no mutation of source log file。

### 8.4 `recovery.py`

Must implement:

1. trivial recovery from existing logs；
2. recovery_summary writing；
3. evidence preservation；
4. distinction among:
   - trivial_recovery
   - non_trivial_recovery
   - owner_approved_recovery
5. rerun_required when recovery cannot be safely completed。

Must not:

1. overwrite original logs；
2. rewrite DS verdict；
3. mark failed as completed；
4. suppress failure evidence。

---

## 9. Required Runtime Artifacts

MVP must support generating:

```text
dispatch/task_config.yaml
runtime/pre_action_check.yaml
runtime/task_state.yaml
runtime/registry_events.jsonl
runtime/heartbeat.json
runtime/progress.yaml
runtime/blocker_report.md
runtime/owner_decision_request.yaml
runtime/owner_decision_record.yaml
runtime/recovery_summary.md
runtime/abort_report.yaml

logs/stdout.log
logs/stderr.log
logs/raw_output.jsonl
logs/stdout.partial.log
logs/stderr.partial.log
logs/raw_output.partial.jsonl

summary/pm_runtime_summary.md
```

Some files are scenario-dependent. However, the code must have explicit support for writing them.

---

## 10. Artifact Schemas

### 10.1 `runtime/pre_action_check.yaml`

Required fields:

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
hold_reason:
created_at:
```

### 10.2 `runtime/registry_events.jsonl`

Each line must be JSON with:

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

### 10.3 `runtime/blocker_report.md`

Required YAML frontmatter or equivalent table:

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

### 10.4 `runtime/owner_decision_request.yaml`

```yaml
task_id:
session_id:
round_id:
request_id:
executor:
event_type: approval_required | sandbox_denied | permission_blocked | waiting_input | scope_violation | unclear_policy | missing_receipt | recovery_requires_approval
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

### 10.5 `runtime/owner_decision_record.yaml`

```yaml
task_id:
session_id:
round_id:
request_id:
owner_decision: approve_with_scope | reject | abort_task | request_safer_alternative | ask_for_more_context
decision_source: owner_chat | owner_file | owner_ui | unknown
decision_time:
approved_scope: []
rejected_scope: []
notes:
next_runtime_action:
```

### 10.6 `runtime/abort_report.yaml`

```yaml
task_id:
session_id:
round_id:
abort_reason:
abort_requested_by:
abort_approved_by:
abort_time:
partial_output_preserved: true | false
stdout_partial_path:
stderr_partial_path:
raw_output_partial_path:
next_recommendation:
owner_control_required: true
```

### 10.7 `runtime/recovery_summary.md`

Required fields:

```yaml
task_id:
session_id:
round_id:
recovery_type: trivial_recovery | non_trivial_recovery | owner_approved_recovery
original_failure_paths: []
new_output_paths: []
evidence_preserved: true | false
owner_approval_required: true | false
owner_approval_record:
runtime_state: recovered | rerun_required
closeout_claimed: false
```

### 10.8 `dispatch/task_config.yaml`

Template must include:

```yaml
task_id:
task_domain:
short_task:
task_level: S | M | L | patch
executor_type: claude | ds_team | codex | hermes | external_agent | local_echo
execution_mode: managed_relay_session | managed_codex_exec | manual_transport | local_echo
owner_control_required: true

paths:
  task_dir:
  dispatch_path:
  system_prompt_path:
  runtime_dir:
  logs_dir:
  summary_path:

runtime_control:
  mode: health_based
  heartbeat_interval_sec: 30
  progress_check_interval_sec: 120
  no_heartbeat_timeout_sec: 300
  no_progress_review_sec: 600
  owner_review_after_sec: 1800
  emergency_max_wall_time_sec:
  abort_requires_owner: true
  preserve_partial_output_on_abort: true

scope:
  allowed_files: []
  forbidden_files: []
  allowed_dirs: []
  sandbox_dir:

executor_options:
  sandbox_mode:
  allowed_tools: []
  max_turns:
  extra_args: []
```

### 10.9 `summary/pm_runtime_summary.md`

Must contain sections:

1. Task identity；
2. Task status；
3. Runtime state；
4. Executor type；
5. Execution mode；
6. Dispatch path；
7. Report paths；
8. Receipt paths；
9. stdout / stderr / raw output paths；
10. Registry path；
11. Owner decision requests / records；
12. Recovery actions；
13. Process issues；
14. Blockers；
15. Known issues；
16. Next recommendation；
17. Explicit statement: `PM Runtime summary is not closeout`.

---

## 11. Status Model

### 11.1 task_status

Must support:

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

### 11.2 runtime_state

Must support YAML v0.3.3 runtime states, including at least:

```text
not_started
created
dispatch_ready
pre_action_checking
launching
running
healthy_running
slow_but_progressing
waiting_input
permission_blocked
sandbox_denied
suspected_blocked
missing_receipt
missing_report
partial_output
partial_output_recovered
recovering
recovered
rerun_required
aborting
aborted
executor_completed
executor_failed
completed
failed
timeout
artifact_missing
environment_blocked
hold_required
summary_written
```

### 11.3 Bad Smell Note

Some runtime_state values overlap with task_status, such as `running`, `completed`, `failed`.

Codex must not resolve this conflict by deleting states.

For v0.1 MVP:

```text
implement compatibility
record overlap as known_issue
do not redesign enum without Owner-Control
```

---

## 12. Runtime Control

Use:

```yaml
runtime_control:
  mode: health_based
  heartbeat_interval_sec: 30
  progress_check_interval_sec: 120
  no_heartbeat_timeout_sec: 300
  no_progress_review_sec: 600
  owner_review_after_sec: 1800
  emergency_max_wall_time_sec: null
  abort_requires_owner: true
  preserve_partial_output_on_abort: true
```

`no_heartbeat_timeout_sec` is set to **300s** to avoid false timeout during Codex startup, given observed Codex baseline of ~120–136s.

---

## 13. Failure Classification

MVP must include classification support for:

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

Each classification record must include:

```yaml
classification:
evidence:
  - path:
  - excerpt_or_summary:
confidence: low | medium | high
classified_by: runtime | hermes | ds | owner-control
requires_independent_review: true | false
```

`role_boundary_violation` must not be self-cleared by Hermes.

---

## 14. Recovery and Rerun Model

### 14.1 Recovery Types

```text
trivial_recovery
non_trivial_recovery
owner_approved_recovery
```

### 14.2 Rerun Model

Rerun is a new round under the same task, not a new task.

Required fields:

```yaml
task_id:
round_id:
parent_round_id:
session_id:
rerun_reason:
rerun_config_delta:
evidence_from_previous_round: []
owner_decision_record:
```

### 14.3 Rerun Registry Event

Every rerun must append:

```json
{
  "event_type": "rerun_started",
  "reason": "required",
  "evidence_paths": ["previous round evidence"]
}
```

---

## 15. R2 Runtime Permission Levels L0-L3

The implementation must respect R2 permission levels.

| Level | Name | Allowed | Forbidden |
|---|---|---|---|
| L0 | read-only recovery | read dispatch/receipt/result; generate summary | start new task; retry execution; modify taskbook; change status |
| L1 | status repair | mark stalled/incomplete/failed/hold; generate missing-reason report and summary | auto rerun; fabricate executor receipt; generate DS/Codex verdict; change failed to completed |
| L2 | same-permission retry | repair execution channel; restart with same permissions; request missing receipt | change task_id/goal/executor/read-write scope/output/failure_policy; bypass safety scan |
| L3 | task plan change | none by runtime | any change to goal/executor/read-write scope/acceptance criteria/forbidden files requires Owner re-approval |

Default runtime_allowed_level for MVP:

```yaml
runtime_allowed_level: L1
```

L2 retry requires explicit Owner-Control approval unless dispatch already grants it.

L3 always requires Owner-Control re-approval.

---

## 16. HOLD Output Requirements

When task enters HOLD, PM Runtime must output:

```text
1. result.yaml
2. pm_runtime_summary.md
3. failure_type
4. existing_artifacts: []
5. missing_artifacts: []
6. l3_touched: true | false
7. recommended_next_action
8. waiting_for_owner_control: true
```

PM Runtime must not automatically continue after HOLD.

---

## 17. Codex Managed Executor Requirements

Codex execution mode:

```text
managed_codex_exec
```

Supported patterns:

```bash
codex exec --sandbox read-only --skip-git-repo-check --ephemeral --json "<prompt>"
```

```bash
codex exec --sandbox workspace-write --skip-git-repo-check --ephemeral --add-dir <sandbox_path> --json "<prompt>"
```

Rules:

1. Codex stdout is JSONL；
2. Codex startup baseline is about 120–136s；
3. ordinary 120s tool timeout must not be treated as task failure；
4. sandbox_denied is not success；
5. approval_required may not appear because OS sandbox can deny directly；
6. no git commit；
7. no touching forbidden files；
8. no closeout claim。

---

## 18. Demo Scope

MVP demo must use **local_echo executor** by default, not real Codex.

Rationale:

```text
The MVP tests the substrate machinery, not Codex model behavior.
```

Demo must write only under:

```text
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/**
```

Demo should verify:

1. init；
2. run local_echo；
3. stdout/stderr capture；
4. registry append；
5. summary generation。

Real Codex integration can be tested after local substrate demo passes.

---

## 19. Required Checks

Codex must run:

```bash
.venv/bin/python -m py_compile tools/pm_runtime/relay/cli.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/relay_runner.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/extractors.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/recovery.py
.venv/bin/python -c "from tools.pm_runtime.relay import cli; print('import OK')"
```

If `.venv/bin/python` does not exist, use:

```bash
python -m py_compile ...
python -c "from tools.pm_runtime.relay import cli; print('import OK')"
```

and record Python interpreter path in receipt.

Python version requirement:

```text
Python >= 3.11 recommended
```

No new dependencies may be added.

If YAML parsing is needed and PyYAML is unavailable, implement minimal stdlib-compatible fallback or treat YAML writing as text serialization. Do not modify dependency files.

---

## 20. Layered Receipt Contract

Codex receipt must inherit `receipt.template.yaml`.

### 20.1 Base Required Fields

```yaml
task_id:
task_title:
executor:
started_at:
completed_at:
elapsed_sec:
status:
verdict:
team_mode_used:
mcp_used:
input_files: []
output_files: []
modified_files: []
commands_run: []
known_issues: []
blockers: []
next_recommendation:
report_path:
receipt_path:
summary_path:
run_dir:
diff_summary:
process_issues: []
```

### 20.2 Codex Extension Fields

```yaml
changed_files: []
test_results: []
handoff_path:
commit_status: no_commit | committed | unknown
forbidden_files_touched: []
runtime_contract_deviations: []
python_interpreter:
```

### 20.3 Verdict Values

Allowed:

```text
pass
pass_with_known_issues
patch_required
hold
fail
```

Codex must not write `closeout`.

---

## 21. Codex Receipt Requirements

Codex must produce:

```text
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/codex/codex_receipt.yaml
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/codex/codex_handoff.md
```

Receipt must include both base fields and Codex extension fields.

---

## 22. DS Verification Expectations

After Codex returns, DS Team should verify:

1. only allowed files changed；
2. forbidden files untouched；
3. package import works；
4. CLI commands exist；
5. pre_action_check schema generated；
6. registry_events append-only；
7. stdout/stderr preserved；
8. abort_report support present；
9. failure classification present；
10. owner_decision_request/record support present；
11. recovery summary preserves evidence；
12. receipt aligns with generic template；
13. PM Runtime summary states not closeout；
14. no git commit。

---

## 23. Hard Boundaries

Codex must not:

1. touch business source code；
2. modify workflow authority；
3. modify YAML symlink；
4. modify generic templates；
5. modify `.claude/.codex/.hermes`；
6. modify dependency files；
7. commit git；
8. expand implementation into daemon / dashboard / queue；
9. delete audit/tasks existing content；
10. write demo outside sandbox；
11. treat sandbox_denied as success；
12. suppress stdout/stderr evidence；
13. claim closeout；
14. enter next version without approval；
15. expand scope；
16. modify this taskbook。

---

## 24. Owner Approval Before Iteration Trigger

This remains mandatory:

```text
Do not copy this taskbook into docs/iterations until Owner has repaired and approved it.
```

Approval sequence:

```text
1. Draft stays in audit/tasks/.../dispatch/
2. Owner repairs / approves taskbook
3. DS Team quick re-review
4. Owner final approval
5. Hermes copies approved taskbook to docs/iterations/
6. Codex safety gate may start
```

If violated:

```text
HOLD_OWNER_APPROVAL_MISSING
```

---

## 25. DS Re-Review Request

Review type:

```text
pre_implementation_taskbook_re_review
```

DS Team should check:

1. Are all P0 findings from v0.1 review addressed?
2. Are allowed_files / forbidden_files complete?
3. Are R2 dispatch / receipt templates properly inherited?
4. Are runtime artifact schemas sufficient?
5. Is no_heartbeat_timeout_sec fixed to 300s?
6. Is failure classification included?
7. Is abort_report included?
8. Is receipt contract aligned with YAML receipt template?
9. Are cli.py / relay_runner.py behavior specs sufficient for Codex?
10. Are R2 L0-L3 and HOLD output rules included?
11. Is taskbook ready for Owner approval and Codex dispatch?

Expected DS verdict:

```yaml
acceptance_verdict: pass | pass_with_known_issues | patch_required | hold | fail
codex_readiness: ready | needs_patch | hold
report_path: required
```

---

## 26. Expected Next Step

If DS re-review returns pass / pass_with_known_issues:

```text
Owner final approval
→ Hermes copies approved taskbook to docs/iterations/v0.1.0-pm-runtime-communication-substrate-mvp.md
→ Codex dispatch
```

Until then:

```yaml
implementation_status: not_started
codex_dispatch_status: hold
```
