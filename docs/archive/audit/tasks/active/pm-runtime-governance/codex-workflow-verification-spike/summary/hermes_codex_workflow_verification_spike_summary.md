# Hermes Codex Workflow Verification Spike — Summary

> task_id: hermes-codex-workflow-verification-spike-20260522
> task_domain: pm-runtime-governance
> task_level: S
> mode: lightweight_runtime_spike
> executor: Hermes / PM Runtime
> status: completed
> created_at: 2026-05-22

---

## 1. Key Findings

| metric | value |
|--------|-------|
| codex_cli_available | **true** — /Applications/Codex.app/Contents/Resources/codex, v0.131.0-alpha.9 |
| codex_exec_available | **true** — `codex exec` subcommand with full options |
| readonly_noninteractive_result | **pass** — exit=0, correct response, no human confirmation |
| workspace_write_result | **pass** — exit=0, file created correctly, no human confirmation |
| approval_required_observed | **false** — no approval prompts in any of 3 tests |
| stdout_capturable | **true** — JSONL format, parseable via json.loads per line |
| stderr_capturable | **true** — all stderr output captured (39 bytes each: "Reading additional input from stdin...") |
| exit_code_capturable | **true** — exit_code=0 for all 3 tests |
| receipt_feasible | **true** — Codex correctly output structured YAML with all required fields |

## 2. Test Results

### 2.1 Read-Only (4.2)

- **Duration**: ~121s (includes 5 reconnection attempts during startup)
- **Sandbox mode**: read-only
- **Output format**: JSONL with item.completed/agent_message
- **Behavior**: Executed `rg --files` shell command, correctly identified CLAUDE.md exists, README does not
- **No confirmation triggers**

Raw logs:
- stdout: `logs/codex_readonly_stdout.log` (11KB, 10 JSONL lines)
- stderr: `logs/codex_readonly_stderr.log` (39 bytes)
- result: `runtime/codex_readonly_result.yaml`

### 2.2 Sandbox Write (4.3)

- **Duration**: ~136s
- **Sandbox mode**: workspace-write + --add-dir sandbox/
- **Behavior**: Created `sandbox/codex_probe.txt` with exact content "codex_probe_ok"
- **Did NOT touch any files outside sandbox**
- **No confirmation triggers**

Raw logs:
- stdout: `logs/codex_write_stdout.log` (3KB, 16 JSONL lines)
- stderr: `logs/codex_write_stderr.log` (39 bytes)
- result: `runtime/codex_write_result.yaml`

### 2.3 Receipt Feasibility (4.4)

- **Duration**: ~121s
- **Sandbox mode**: read-only
- **Behavior**: Output structured YAML with all 11 required fields correctly populated
- **No extra text, no markdown wrapping beyond the YAML block**

Raw logs:
- stdout: `logs/codex_receipt_stdout.log`
- stderr: `logs/codex_receipt_stderr.log` (39 bytes)
- result: `runtime/codex_receipt_feasibility.yaml`

## 3. Operational Observations

### 3.1 Startup Overhead

Each `codex exec` invocation takes ~120-136s for these simple tasks. Startup includes:
- 5 reconnection attempts (known behavior, noted in adarian-workflow-governance §8.4.1)
- Model initialization
- Context loading

This overhead is amortized for long tasks (DS Team reviews take 900-1500s) but dominates S-Level tasks.

### 3.2 JSONL Output Format

The `--json` flag produces JSONL (one JSON object per line). Key event types:
- `thread.started` — thread ID
- `turn.started` — turn start
- `error` — reconnection/infrastructure messages
- `item.started` / `item.completed` — command execution and agent messages
- `turn.completed` — usage stats

Agent response is in `item.completed` with `item.type == "agent_message"` and `item.text` containing the response.

### 3.3 No Human Confirmation

All three tests ran without triggering any approval/confirmation prompts. This is due to:
- `--sandbox read-only` and `--sandbox workspace-write` modes
- `--ephemeral` flag
- `--skip-git-repo-check` flag
- Project trusted in `~/.codex/config.toml` (`trust_level = "trusted"`)

### 3.4 sandbox Enforcement

The workspace-write test with `--add-dir` successfully constrained writes to the sandbox directory. Codex did not attempt to write to any other location.

## 4. Commands Reference

```bash
# Read-only
codex exec --sandbox read-only --skip-git-repo-check --ephemeral --json "prompt"

# Workspace-write with sandbox dir
codex exec --sandbox workspace-write --skip-git-repo-check --ephemeral --add-dir <sandbox_path> --json "prompt"

# Structured output
codex exec --sandbox read-only --skip-git-repo-check --ephemeral --json "prompt"
```

## 5. Compatibility with Communication Substrate

| requirement | status | notes |
|-------------|--------|-------|
| CLI available | ✅ | codex exec, full option set |
| Non-interactive | ✅ | No confirmations with correct flags |
| Read-only tasks | ✅ | sandbox read-only works |
| Controlled writes | ✅ | --add-dir constrains write scope |
| Structured receipts | ✅ | Can output YAML with specified fields |
| stdout capture | ✅ | JSONL parseable |
| stderr capture | ✅ | Low noise (39 bytes) |
| exit code capture | ✅ | 0 on success |
| Subprocess compatible | ✅ | Works with subprocess.Popen(start_new_session=True) |
| Startup overhead | ⚠️ | ~120s per invocation, significant for S-Level tasks |

## 6. Recommended Execution Mode

```yaml
recommended_execution_mode:
  - managed_codex_exec
```

Rationale:
- Codex supports non-interactive exec mode with sandbox controls
- No human approval needed with correct configuration
- Output is structured and capturable
- Works with independent subprocess launch
- Startup overhead is acceptable for M-Level and above tasks
- For S-Level tasks, the 120s startup overhead should be factored into timeout planning

## 7. Remaining Unknowns

1. **Long-task behavior**: Max turns? Memory usage over time? Tested only with S-Level prompts.
2. **Concurrent Codex processes**: Can multiple `codex exec` run simultaneously?
3. **Permission escalation**: What happens with workspace-write without --add-dir constraints?
4. **adarian-iteration-safety-gate skill**: The governance skill mentions `~/.codex/skills/adarian-iteration-safety-gate/` — not verified in this spike.
5. **Codex MCP integration**: `codex mcp` subcommand exists but not tested.

## 8. Process Issues

None. All three tests completed successfully.

## 9. Blockers

None for PM Runtime v0.1 Communication Substrate integration.

## 10. Next Recommendation

Codex appears feasible as a managed executor under the Communication Substrate model with `--sandbox workspace-write --add-dir` constraints. The v0.2 plan should include a note that Codex integration requires:

1. Standardized `codex exec` command templates per task type
2. Sandbox directory policy (per-task sandbox under task dir)
3. JSONL output parsing in relay_runner.py or extractors.py
4. Startup overhead allowance in timeout calculations (baseline +120s for Codex vs Claude)

This spike does not authorize Codex landing. Owner-Control decision required before Phase 2 implementation.

---

workflow_compact_yaml_used: false
pm_runtime_instruction_version: v0.1.3
owner_control_required: true
