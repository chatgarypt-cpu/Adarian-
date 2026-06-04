# Iteration Execution Guard

## Position

This file is the project-level execution gate for Codex in Adarian.

`docs/skills/workflow_core.md` is the primary workflow authority. If this file conflicts with `workflow_core.md`, follow `workflow_core.md`.

This guard connects the v3 workflow to the global Codex skill:

```text
$adarian-iteration-safety-gate
```

`review_id` is a Codex safety-gate trace id. It is not one of the four v3 workflow event ids, and it does not replace `audit_id`, `attempt_id`, or `acceptance_id`.

## When This Gate Is Required

Codex must execute this gate before any Adarian task involving:

- version iteration such as `vX.Y.Z`
- implementation, bug fix, refactor, or behavior change
- architecture, schema, prompt, parameter, pipeline, validation, test, or output-contract change
- multi-file modification
- workflow, skill, hook, or execution-policy changes
- large code block, patch, rewrite, or generated code suggestion from another agent

No coding, patching, committing, branching, stashing, cleanup, or destructive action may happen before the Pre-Implementation Review is complete and the user confirms the next action, unless the user has explicitly authorized a bounded documentation/configuration landing task.

## Required Context

Codex must read or inspect, when present and relevant:

- `docs/skills/workflow_core.md`
- this file
- `docs/skills/main_agent_delivery.md`
- current iteration document under `docs/iterations/`
- DS Pre-Audit Report, when the task provides an `audit_id`
- `docs/iterations/TASK_LOG.md`
- `docs/iterations/CHANGELOG.md`
- relevant source files under `src/`
- relevant tests under `tests/`
- `README.md`, `main.py`, `config.py`, and `.env.example` when relevant
- current git state

If the task references files, functions, classes, prompts, schemas, reports, hooks, or commands that do not exist, Codex must report the mismatch instead of assuming the plan is correct.

## Required Git / Version Isolation Check

Codex must inspect and report:

```bash
git status --short --untracked-files=all
git status --porcelain=v1 -- src tests main.py config.py scripts profiling seeds
git status --porcelain=v1 -- docs audit
git branch --show-current
git log -1 --oneline
git tag --points-at HEAD
```

For implementation attempts, Codex must distinguish source execution dirty state from documentation/audit dirty state.

Default source execution pathspec:

```text
src tests main.py config.py scripts profiling seeds
```

If source execution dirty state is non-empty, Codex must return `SOURCE_DIRTY_BLOCKER` / `NEEDS_VERSION_ISOLATION` unless the user or Control Agent explicitly decides to continue.

Dirty entries under `docs/` or `audit/` must be reported and classified, but do not automatically block source implementation unless they affect the current iteration authority, audit evidence, `base_commit`, allowed scope, or acceptance record.

A task prompt or Control Agent gate may override the pathspec for a specific iteration.

Codex must not create commits, branches, stashes, resets, checkouts, restores, or cleanup actions without explicit user confirmation.

### Dirty Tree Response Protocol

Before a new iteration, multi-file edit, or quality-gated implementation, Codex must report the full dirty tree and then apply the source execution gate:

1. Run and report `git status --short --untracked-files=all`.
2. Run the source execution pathspec check:
   ```bash
   git status --porcelain=v1 -- src tests main.py config.py scripts profiling seeds
   ```
3. If the source execution check is non-empty, stop before editing files and report `SOURCE_DIRTY_BLOCKER`.
4. Run and report the documentation/audit classification check:
   ```bash
   git status --porcelain=v1 -- docs audit
   ```
5. If only `docs/` or `audit/` are dirty, report `DOC_DIRTY_ALLOWED_OR_NEEDS_CLASSIFICATION` and continue only when those entries do not affect the current iteration authority, audit evidence, `base_commit`, allowed scope, or acceptance record.
6. Provide user-runnable git commands for the two safe paths when isolation is needed:
   - commit the intended preparation / audit / documentation changes
   - stash the dirty work with untracked files included
7. Do not run commit, stash, restore, reset, cleanup, or destructive commands yourself unless the user explicitly asks for that exact action.
8. Resume only after the source execution pathspec is clean, or after the user / Control Agent explicitly decides to continue with the reported source dirty entries.

Recommended command templates:

```bash
git status --short --untracked-files=all
git status --porcelain=v1 -- src tests main.py config.py scripts profiling seeds
git status --porcelain=v1 -- docs audit
git diff --stat
git diff --cached --stat
```

For committing intentional preparation work, tailor the pathspecs and message to the observed dirty files:

```bash
git add <paths>
git status --short --untracked-files=all
git diff --cached --stat
git commit -m "<message>"
```

For temporary isolation:

```bash
git stash push -u -m "wip: <reason>"
git status --short --untracked-files=all
```

## Required Decision Labels

The review must return exactly one:

- `GO`
- `GO_WITH_ADJUSTMENTS`
- `NEEDS_CLARIFICATION`
- `NEEDS_VERSION_ISOLATION`
- `NO_GO`

## Required Review Output

Codex must output a `Pre-Implementation Review` containing:

- `task_id`
- `audit_id` when provided, otherwise `N/A`
- `review_id` for the Codex safety gate
- `scope`
- decision label
- plan summary and acceptance criteria
- source files actually inspected
- mismatches between the plan and current repository state
- external suggestion review, when applicable
- version isolation check
- risk table covering correctness, regression, schema compatibility, security, privacy/secrets, compliance/safety, runtime stability, rollback, test coverage, and documentation drift
- recommended implementation path
- likely changed files
- files explicitly not to touch
- validation commands, using `python3` on macOS when `py` is unavailable
- risks
- `decision_needed`

## Codex Boundary

Codex may:

- implement the bounded scope approved by the user / Control Agent
- run self-check level commands declared by the iteration document or task prompt
- report actual modified files, tests, artifact checks, and known issues
- provide `attempt_id` in every delivery

Codex must not:

- perform DS Pre-Audit, DS Verify, or DS Accept as the authority of record
- update `TASK_LOG.md`, `CHANGELOG.md`, or iteration document status unless the workflow authority explicitly assigns that work to Codex
- declare final closeout
- expand scope into the next version
- modify forbidden files

## Completion Rule

After the review, Codex must wait for user confirmation. Only then may Codex implement the approved path and later deliver an `attempt_id`.
