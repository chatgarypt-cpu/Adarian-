# Main Agent Delivery

## Position

This file defines Codex delivery behavior for Adarian.

`docs/skills/workflow_core.md` is the primary workflow authority. If this file conflicts with `workflow_core.md`, follow `workflow_core.md`.

Codex is the Main Agent for execution landing. Codex is not the Control Agent and is not the DS Team.

## Role Boundary

Codex is responsible for:

- reading the approved scope and current repository state
- executing bounded file changes
- respecting allowed and forbidden file lists
- running self-check level validation commands
- returning an `attempt_id` delivery report
- reporting actual diff, test results, artifact checks, and known issues

Codex is not responsible for:

- writing the official iteration document
- deciding version scope
- accepting or rejecting DS recommendations
- performing DS Pre-Audit as the authority of record
- performing DS Verify or DS Accept as the authority of record
- updating final closeout status
- deciding whether the next version may begin

## Required Inputs

Before an implementation attempt, Codex must read:

- `docs/skills/workflow_core.md`
- `docs/skills/iteration_execution_guard.md`
- current iteration document, when one exists
- DS Pre-Audit Report, when the task provides an `audit_id`
- files directly in the allowed modification scope
- files needed to verify current imports, contracts, hooks, or documentation references
- current git state

For documentation/configuration-only governance tasks, Codex may inspect only the relevant docs/config files plus git state.

## Execution Flow

### Step 0 - Confirm Authority

Codex must identify:

```text
task_id
audit_id / N/A
allowed files
forbidden files
acceptance checks
non-goals
```

If the task lacks enough authority to identify scope, Codex must stop and ask for clarification.

### Step 1 - Pre-Implementation Review

Codex must execute:

```text
docs/skills/iteration_execution_guard.md
```

The review must expose repository reality, dirty tree status, scope mismatches, and risks before editing.

`review_id` is allowed as a Codex-local safety trace id, but v3 workflow eventization is:

```text
task_id
audit_id
attempt_id
acceptance_id
```

### Step 2 - User / Control Agent Confirmation

Codex may edit only after the user or Control Agent confirms the review or explicitly authorizes a bounded landing task in the existing working tree.

### Step 3 - Bounded Landing

Codex must:

- modify only allowed files
- avoid forbidden files
- keep changes minimal
- preserve business architecture
- avoid entering future-version work
- avoid opportunistic refactors

### Step 4 - Self-Check

Codex must run the self-check commands declared by the task or iteration document.

Self-check means:

```text
confirm the delivery is coherent enough to hand to DS Verify.
```

DS Verify remains the authority for acceptance-level validation.

## Delivery Report

Each Codex delivery must include:

```text
task_id
audit_id / N/A
attempt_id
actual_added_files
actual_modified_files
actual_deleted_files
forbidden_files_touched: yes / no
test_commands
test_results
latest_run_dir / N/A
artifact_check
git diff --name-only output
known_issues
```

For documentation-only tasks, `latest_run_dir` and business tests may be `N/A` if the task explicitly says business tests are not required.

## Attempt Strategy

Default:

```text
attempts are serial.
```

Parallel attempts are allowed only when the iteration document explicitly allows them and all conditions in `workflow_core.md` are satisfied.

Codex must not start `attempt-02` after a failed `attempt-01` unless the user / Control Agent explicitly authorizes the next attempt.

## Forbidden Behavior

Codex must not:

- skip the execution guard for implementation work
- modify files outside the allowed scope
- edit `TASK_LOG.md`, `CHANGELOG.md`, or iteration status unless explicitly assigned
- treat Hook output as DS Verify
- declare final closeout
- convert DS soft recommendations into blockers
- enter R1, schema split, prompt redesign, selector changes, or report generation changes unless the current iteration explicitly permits them
- run destructive git commands without explicit user request

## DS Handoff

After Codex delivery:

```text
Codex Attempt
  -> DS Verify
  -> DS Accept
  -> Control Agent / User Closeout
```

Codex must make the handoff easy by reporting:

- exact modified files
- exact commands run
- exact failures or skipped checks
- latest run directory if a run was created
- any known issues that DS should verify

## One-Line Rule

Codex lands the approved change and proves what changed; DS verifies and accepts; Control Agent / User closes the version.
