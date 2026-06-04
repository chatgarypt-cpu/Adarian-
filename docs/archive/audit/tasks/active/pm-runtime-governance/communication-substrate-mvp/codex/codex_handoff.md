# Codex Handoff: PM Runtime Communication Substrate MVP

## Delivery
Implementation delivered for PM Runtime / Hermes / DS / Owner-Control review.

Codex did not claim closeout, did not commit, and did not patch the safety gate.

## Implemented Files
- tools/pm_runtime/__init__.py
- tools/pm_runtime/relay/__init__.py
- tools/pm_runtime/relay/cli.py
- tools/pm_runtime/relay/relay_runner.py
- tools/pm_runtime/relay/extractors.py
- tools/pm_runtime/relay/recovery.py
- tools/pm_runtime/templates/task_config.yaml

## Runtime Capabilities
- CLI commands: init, run, recover, summary.
- Task initialization with pre_action_check, task_state, and append-only registry event.
- Independent subprocess launch foundation.
- local_echo executor demo support.
- stdout, stderr, raw output, and partial output preservation.
- streaming stdout/stderr capture into full and partial logs.
- raw output JSONL stream events for process start, stdout/stderr chunks, and process completion.
- heartbeat and progress artifacts.
- failure classification records.
- owner_decision_request and owner_decision_record artifact writers.
- abort_report artifact writer.
- Codex JSONL parsing and receipt candidate extraction helpers.
- trivial recovery that preserves original evidence.
- PM Runtime summary generation with explicit no-closeout boundary.

## Demo Evidence
- demo_task: audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/demo_task
- stdout: audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/demo_task/logs/stdout.log
- stderr: audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/demo_task/logs/stderr.log
- raw_output: audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/demo_task/logs/raw_output.jsonl
- registry: audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/demo_task/runtime/registry_events.jsonl
- demo_summary: audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/demo_task/summary/pm_runtime_summary.md
- recovery_summary: audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/demo_task/runtime/recovery_summary.md

## Checks Run
- .venv/bin/python -m py_compile tools/pm_runtime/relay/cli.py
- .venv/bin/python -m py_compile tools/pm_runtime/relay/relay_runner.py
- .venv/bin/python -m py_compile tools/pm_runtime/relay/extractors.py
- .venv/bin/python -m py_compile tools/pm_runtime/relay/recovery.py
- .venv/bin/python -c "from tools.pm_runtime.relay import cli; print('import OK')"
- .venv/bin/python -m tools.pm_runtime.relay.cli init --config tools/pm_runtime/templates/task_config.yaml
- .venv/bin/python -m tools.pm_runtime.relay.cli run --task-dir audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/demo_task
- .venv/bin/python -m tools.pm_runtime.relay.cli summary --task-dir audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/demo_task
- .venv/bin/python -m tools.pm_runtime.relay.cli recover --task-dir audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/sandbox/demo_task
- sidecar read-only review completed; findings patched or recorded.

## Pre-existing Files Observed
- tools/pm_runtime/templates/dispatch.template.yaml was pre-existing and read only.
- tools/pm_runtime/templates/receipt.template.yaml was pre-existing and read only.
- audit task package dispatch/ds/scripts/relay_logs/runtime files observed before implementation were pre-existing governance evidence and were not modified by Codex in this task.
- .DS_Store files were pre-existing and not modified by Codex.

## Known Issues
- Current safety gate needs a later patch for Hermes-dispatched infrastructure_creation_lane support.
- The MVP deliberately does not implement concurrency, daemon mode, queueing, dashboard, database, or auto closeout.
- The fallback YAML parser/writer is intentionally minimal.
- Py_compile generated __pycache__ files under the allowed tools/pm_runtime package path.
- Missing receipt/report, partial output, JSON parse failure, environment block, artifact path missing, and role boundary classifications are implemented as MVP classification branches; DS should verify policy mapping before production use.

## Forbidden Files
- forbidden_files_touched: []

## Next Recommendation
Send this implementation to PM Runtime / Hermes / DS verification, then Owner-Control. Handle safety gate support for the infrastructure creation lane in a separate task.
