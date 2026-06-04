# DS Team Dispatch: PM Runtime Substrate v0.1.1 Real Relay Verification

task_id: ds-verify-pm-runtime-substrate-v0.1.1-20260523
task_domain: pm-runtime-governance
task_level: M
mode: real_relay_verification
executor: DS Team / Claude
team_mode_required: true
mcp_required: true
owner_control_required: true

## 0. Objective

Codex has delivered v0.1.1 patch. Hermes has smoke-verified: py_compile all pass, import OK, local_echo demo pass, shell_command demo pass, heartbeat_history.jsonl records seq 1-10 across four states.

Now DS Team must run a **real relay** — not a demo rerun — with a real executor (Codex or Claude) through the substrate.

Goal: confirm the substrate works end-to-end for a non-trivial task, not just a local echo.

## 1. What Changed in v0.1.1

| v0.1 (old) | v0.1.1 (new) |
|---|---|
| Fake heartbeat (one-shot at end) | Real heartbeat during execution → `runtime/heartbeat_history.jsonl` + `runtime/heartbeat.json` |
| No streaming stdout/stderr | Streaming `logs/stdout.log` and `logs/stderr.log` while subprocess runs |
| No shell_command executor | `shell_command` / `managed_subprocess` executor foundation |
| No Hermes compat | `runtime/relay_heartbeat.txt`, `runtime/relay_progress.md`, `runtime/result.json` |
| Config path fragile | Clear errors for missing config, directory-as-config, etc. |

## 2. Required Inputs

Key implementation files:
```
tools/pm_runtime/relay/cli.py
tools/pm_runtime/relay/relay_runner.py
tools/pm_runtime/relay/extractors.py
tools/pm_runtime/relay/recovery.py
tools/pm_runtime/templates/task_config.yaml
```

Codex delivery artifacts:
```
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/codex/codex_receipt_v0_1_1.yaml
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/codex/codex_handoff_v0_1_1.md
```

Existing demos (for reference, do not modify):
```
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/v0_1_1_patch_demo/
```

## 3. Must Check: Real Relay Test

### 3.1 Prepare a Real Task Config

Create a new task config under:
```
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/ds_real_relay_test/dispatch/task_config.yaml
```

Use `shell_command` executor type. Pick a non-trivial command that takes at least 5-10 seconds to complete so heartbeat can be observed. Suggestion: a Python script or a multi-step shell pipeline.

### 3.2 Run the Full Relay Sequence

```bash
.venv/bin/python -m tools.pm_runtime.relay.cli init --config <path_to_task_config>
.venv/bin/python -m tools.pm_runtime.relay.cli run --task-dir <task_dir>
.venv/bin/python -m tools.pm_runtime.relay.cli summary --task-dir <task_dir>
.venv/bin/python -m tools.pm_runtime.relay.cli recover --task-dir <task_dir>
```

### 3.3 Verify Heartbeat

Inspect `runtime/heartbeat_history.jsonl`:
- Multiple heartbeat entries (not just one)
- Timestamps increasing monotonically
- runtime_state transitions observed (at minimum: running → executor_completed)
- Each entry has task_id, timestamp, runtime_pid, executor_pid, heartbeat_seq

Inspect `runtime/heartbeat.json`:
- Contains the final heartbeat state

### 3.4 Verify Streaming Logs

Inspect `logs/stdout.log` and `logs/stderr.log`:
- Contain actual executor output (not empty)
- Content matches what the executed command would produce

### 3.5 Verify Hermes Compat Files

Inspect:
- `runtime/relay_heartbeat.txt` — mirrors final heartbeat
- `runtime/relay_progress.md` — contains progress information
- `runtime/result.json` — contains task result

Confirm these files exist and have plausible content.

## 4. Should Check: v0.1.1-Specific Items

### 4.1 Config Path Robustness

Test that the CLI gives clear errors for:
- Missing config file
- Directory path where file expected
- No config found

(Do not test these against existing demo configs — use intentionally wrong paths.)

### 4.2 Recovery Does Not Destroy Evidence

Run `recover`, then verify:
- `heartbeat_history.jsonl` still has original entries (appended, not overwritten)
- `logs/stdout.log` still has original content
- Recovery summary mentions original execution details

## 5. Must Check: Boundary Compliance

### 5.1 File Boundary

Run:
```bash
git -C "<repo_path>" status --short
```

Verify no forbidden files were touched:
```
src/**
tests/**
main.py
config.py
CLAUDE.md
.venv/**
pyproject.toml
docs/skills/**
workflow_compact.yaml
workflow_compact_v0.3.3.yaml
.claude/**
.codex/**
.hermes/**
```

### 5.2 Syntax and Import

```bash
.venv/bin/python -m py_compile tools/pm_runtime/relay/cli.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/relay_runner.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/extractors.py
.venv/bin/python -m py_compile tools/pm_runtime/relay/recovery.py
.venv/bin/python -c "from tools.pm_runtime.relay import cli; print('import OK')"
```

## 6. Do Not Do

- Do not modify Codex delivery files
- Do not modify the existing demos in sandbox/v0_1_1_patch_demo/
- Do not commit anything
- Do not claim closeout
- Do not modify workflow authority files
- Do not perform full code review — this is functional verification only

## 7. Required Output

Write a Chinese Markdown verification report to:
```
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/ds/ds_relay_verification_v0_1_1.md
```

Required fields:
```yaml
review_type: real_relay_verification
team_mode_used: true | false
mcp_used: true | false
acceptance_verdict: pass | pass_with_known_issues | patch_required | hold | fail
implementation_readiness: usable | needs_patch | hold
heartbeat_verification:
  history_jsonl_exists: true | false
  multiple_entries: true | false
  timestamps_monotonic: true | false
  states_observed: [list]
streaming_verification:
  stdout_content_valid: true | false
  stderr_content_valid: true | false
hermes_compat_check:
  relay_heartbeat_txt: pass | fail
  relay_progress_md: pass | fail
  result_json: pass | fail
file_boundary_check:
  forbidden_files_touched: []
  unexpected_files: []
syntax_import_check: pass | fail
config_path_robustness: pass | partial | not_tested
recovery_preserves_evidence: pass | fail | not_tested
findings:
  P0: []
  P1: []
  P2: []
  P3: []
blockers: []
known_issues: []
recommended_next_action:
  - owner_acceptance
  - patch_required
  - hold
report_path: required
```

Also write a receipt YAML:
```
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/ds/ds_relay_verification_receipt_v0_1_1.yaml
```

## 8. Gate Meaning

If DS returns:
```yaml
acceptance_verdict: pass | pass_with_known_issues
implementation_readiness: usable
```

Then the substrate is ready for Owner acceptance → bootstrap online.

DS Team does not closeout. Owner-Control is the final gate.
