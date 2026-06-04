# DS Team Dispatch: PM Runtime Communication Substrate MVP Post-Execution Verification

task_id: ds-verify-pm-runtime-communication-substrate-mvp-20260522
task_domain: pm-runtime-governance
task_level: M
mode: post_execution_functional_verification
executor: DS Team / Claude
team_mode_required: true
mcp_required: true
owner_control_required: true

## 0. Objective

Verify the Codex-delivered PM Runtime Communication Substrate MVP.

This is not a full code review and not a performance test.

The goal is to confirm:

1. Codex stayed within allowed/forbidden boundaries;
2. the delivered modules compile and import;
3. receipt/handoff schema is complete;
4. DS can independently rerun the demo;
5. append-only registry behavior is plausible;
6. key runtime artifacts conform to the taskbook / Runtime Contract requirements.

## 1. Required Inputs

Please inspect the current repository state and task artifacts.

Key expected implementation paths:

```text
tools/pm_runtime/__init__.py
tools/pm_runtime/relay/__init__.py
tools/pm_runtime/relay/cli.py
tools/pm_runtime/relay/relay_runner.py
tools/pm_runtime/relay/extractors.py
tools/pm_runtime/relay/recovery.py
tools/pm_runtime/templates/task_config.yaml
```

Key task output paths:

```text
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/
```

Key reference files:

```text
docs/iterations/v0.1.0-pm-runtime-communication-substrate-mvp.md
receipt.template.yaml
dispatch.template.yaml
workflow_compact.yaml
```

## 2. Must Check: Hard Facts

### 2.1 File Boundary Check

Run or inspect:

```bash
git status --short
git diff --stat
```

Verify:

* created / modified files are only under allowed paths;
* no forbidden files were touched;
* no dependency files changed;
* no workflow authority files changed;
* no business source files changed;
* no git commit was made.

Explicitly check that these were not modified:

```text
src/**
tests/**
main.py
config.py
CLAUDE.md
.venv/**
pyproject.toml
requirements*.txt
docs/skills/**
workflow_core*
workflow_compact.yaml
workflow_compact_v0.3.3.yaml
.claude/**
.codex/**
.hermes/**
.git/**
```

### 2.2 Syntax and Import Check

Run:

```bash
.venv/bin/python -m py_compile tools/pm_runtime/relay/cli.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/relay_runner.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/extractors.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/recovery.py
.venv/bin/python -c "from tools.pm_runtime.relay import cli; print('import OK')"
```

If `.venv/bin/python` is unavailable, use `python` and report the interpreter path.

### 2.3 Receipt Schema Check

Inspect:

```text
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/codex/codex_receipt.yaml
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/codex/codex_handoff.md
```

Verify receipt includes base fields from `receipt.template.yaml` plus Codex extensions:

```yaml
task_id:
task_title:
executor:
started_at:
completed_at:
elapsed_sec:
status:
verdict:
input_files:
output_files:
modified_files:
created_files:
commands_run:
test_results:
known_issues:
blockers:
next_recommendation:
receipt_path:
handoff_path:
summary_path:
diff_summary:
commit_status:
forbidden_files_touched:
runtime_contract_deviations:
owner_override_used:
owner_override_reason:
python_interpreter:
```

## 3. Should Check: Functional Verification

### 3.1 Independent Demo Rerun

Do not trust Codex's self-reported demo alone.

Independently rerun the minimal demo sequence:

```bash
python -m tools.pm_runtime.relay.cli init --config <demo_task_config>
python -m tools.pm_runtime.relay.cli run --task-dir <demo_task_dir>
python -m tools.pm_runtime.relay.cli summary --task-dir <demo_task_dir>
python -m tools.pm_runtime.relay.cli recover --task-dir <demo_task_dir>
```

Use a safe demo directory under:

```text
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/ds_verify_demo/
```

Do not write outside the current task directory.

Verify that DS rerun produces or updates:

```text
runtime/pre_action_check.yaml
runtime/task_state.yaml
runtime/registry_events.jsonl
logs/stdout.log
logs/stderr.log
logs/raw_output.jsonl
summary/pm_runtime_summary.md
runtime/recovery_summary.md
```

### 3.2 Append-Only Registry Check

Inspect `runtime/registry_events.jsonl`.

Verify:

* each event is one JSON line;
* rerun / summary / recovery appends new lines rather than overwriting;
* timestamps exist;
* task_id / event_type / actor / reason / evidence_paths are present where expected.

### 3.3 Key Artifact Schema Spot Check

Spot-check these artifacts against taskbook §10:

```text
runtime/pre_action_check.yaml
runtime/task_state.yaml
runtime/blocker_report.md if present
runtime/owner_decision_request.yaml if present
runtime/owner_decision_record.yaml if present
runtime/abort_report.yaml if present
runtime/recovery_summary.md
summary/pm_runtime_summary.md
```

Verify especially:

* `pre_action_check.yaml` has action_type / intended_executor / result / hold_reason;
* `pm_runtime_summary.md` explicitly states it is not closeout;
* recovery does not overwrite original evidence;
* sandbox_denied / permission_blocked are not treated as success.

## 4. Do Not Do

Do not perform:

* full line-by-line Python code review;
* performance testing;
* large refactor suggestions;
* workflow_core modification;
* safety gate modification;
* dependency installation;
* git commit;
* closeout.

## 5. Required Output

Write a Chinese Markdown verification report.

Required fields:

```yaml
review_type: post_execution_functional_verification
team_mode_used: true | false
mcp_used: true | false
scope_compliance: pass | issue
acceptance_verdict: pass | pass_with_known_issues | patch_required | hold | fail
implementation_readiness: usable | needs_patch | hold
file_boundary_check:
  forbidden_files_touched: []
  unexpected_files: []
syntax_import_check:
  status: pass | fail | not_run
demo_rerun:
  status: pass | fail | partial | not_run
receipt_schema_check:
  status: pass | issue
append_only_check:
  status: pass | issue | not_run
artifact_schema_spot_check:
  status: pass | issue | partial
findings:
  P0: []
  P1: []
  P2: []
  P3: []
process_issues: []
blockers: []
known_issues: []
recommended_next_action:
  - owner_control_gate
  - codex_patch
  - hold
report_path: required
receipt_path: required
```

## 6. Gate Meaning

If DS returns:

```yaml
acceptance_verdict: pass | pass_with_known_issues
implementation_readiness: usable
```

then Owner-Control may decide whether to accept this MVP as bootstrap usable.

DS Team does not closeout.
