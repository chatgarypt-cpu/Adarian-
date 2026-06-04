# Codex Handoff: PM Runtime Substrate v0.1.1 Patch

## Delivery
Implementation delivered for PM Runtime / Hermes / DS / Owner-Control review.

Codex did not claim closeout, did not commit, did not patch safety gate, and did not modify Hermes source/config.

## Diagnosis
```yaml
diagnosis:
  fake_heartbeat_confirmed: true
  real_executor_missing_confirmed: partial
  hermes_integration_missing_confirmed: true
  task_config_path_issue_confirmed: true
  state_machine_jump_confirmed: true
```

Evidence: v0.1.0 demo worked, but heartbeat was not continuously recorded for long-running executors, shell_command was not explicitly modeled/proven, Hermes legacy relay artifacts were absent, and config path failure cases needed clearer errors.

## Patched Behavior
- `relay_runner.py` now refreshes canonical `runtime/heartbeat.json` during managed subprocess execution.
- Each heartbeat is also appended to `runtime/heartbeat_history.jsonl` for post-run verification.
- stdout/stderr are streamed into full and partial logs while the subprocess runs.
- `shell_command` / `managed_subprocess` is supported as the v0.1.1 real executor foundation.
- `codex` / `claude` command-template modes are minimally supported through configured args.
- Hermes compatibility aliases are written under `runtime/`: `relay_heartbeat.txt`, `relay_progress.md`, and `result.json`.
- Config handling rejects missing config files, directory-as-config, directory-as-dispatch-path, missing recorded config, and multiple YAML dispatch candidates with clear errors.

## Demo
Demo root:
`audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/v0_1_1_patch_demo/`

Local echo demo:
```bash
.venv/bin/python -m tools.pm_runtime.relay.cli init --config audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/v0_1_1_patch_demo/local_echo/dispatch/task_config.yaml
.venv/bin/python -m tools.pm_runtime.relay.cli run --task-dir audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/v0_1_1_patch_demo/local_echo
.venv/bin/python -m tools.pm_runtime.relay.cli summary --task-dir audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/v0_1_1_patch_demo/local_echo
.venv/bin/python -m tools.pm_runtime.relay.cli recover --task-dir audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/v0_1_1_patch_demo/local_echo
```

Managed subprocess demo:
```bash
.venv/bin/python -m tools.pm_runtime.relay.cli init --config audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/v0_1_1_patch_demo/shell_command/dispatch/task_config.yaml
.venv/bin/python -m tools.pm_runtime.relay.cli run --task-dir audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/v0_1_1_patch_demo/shell_command
.venv/bin/python -m tools.pm_runtime.relay.cli summary --task-dir audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/v0_1_1_patch_demo/shell_command
.venv/bin/python -m tools.pm_runtime.relay.cli recover --task-dir audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/v0_1_1_patch_demo/shell_command
```

Heartbeat evidence:
- `shell_command/runtime/heartbeat_history.jsonl` shows seq 1 through 10 across `running`, `healthy_running`, `slow_but_progressing`, and `executor_completed`.
- `shell_command/runtime/heartbeat.json` contains the final heartbeat.
- `shell_command/runtime/relay_heartbeat.txt` mirrors the final heartbeat as `legacy_compat`.

## Hermes Candidate Status
The substrate is now suitable for Hermes real-relay candidate testing under the current task directory.

Remaining limitation: legacy compat aliases are under `runtime/`, not old `relay_logs/`, because `relay_logs/**` was not in the v0.1.1 allowed write scope. If Hermes still requires `relay_logs/`, that needs separate Owner-approved scope expansion or Hermes-side adaptation.

## Validation
- `.venv/bin/python -m py_compile tools/pm_runtime/relay/cli.py`: pass
- `.venv/bin/python -m py_compile tools/pm_runtime/relay/relay_runner.py`: pass
- `.venv/bin/python -m py_compile tools/pm_runtime/relay/extractors.py`: pass
- `.venv/bin/python -m py_compile tools/pm_runtime/relay/recovery.py`: pass
- `.venv/bin/python -c "from tools.pm_runtime.relay import cli; print('import OK')"`: pass
- local_echo demo: pass
- managed_subprocess demo: pass

## Boundary
- forbidden_files_touched: []
- commit_status: no_commit
- closeout_claimed: false

