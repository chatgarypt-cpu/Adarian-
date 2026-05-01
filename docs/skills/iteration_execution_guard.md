# Iteration Execution Guard

## Position

This file is the project-level gate for Adarian implementation work. It connects the Adarian workflow to the global Codex skill:

`$adarian-iteration-safety-gate`

`docs/skills/workflow_core.md` remains the workflow rule authority. If this file conflicts with `workflow_core.md`, follow `workflow_core.md`.

## When This Gate Is Required

Codex must execute this gate before any Adarian task involving:

- version iteration such as `vX.Y.Z`
- implementation, bug fix, refactor, or behavior change
- architecture, schema, prompt, parameter, pipeline, validation, test, or output-contract change
- multi-file modification
- large code block, patch, rewrite, or generated code suggestion from the user or another agent

No coding, patching, committing, branching, stashing, or destructive cleanup may happen before the Pre-Implementation Review is complete and the user confirms the next action.

## Required Context

Codex must read or inspect, when present:

- `docs/skills/workflow_core.md`
- this file
- current iteration document under `docs/iterations/`
- `docs/iterations/TASK_LOG.md`
- `docs/iterations/CHANGELOG.md`
- relevant source files under `src/`
- relevant tests under `tests/`
- `README.md`, `main.py`, `config.py`, and `.env.example` when relevant
- current git state

If the task references files, functions, classes, prompts, schemas, or commands that do not exist, Codex must report the mismatch instead of assuming the plan is correct.

## Required Git / Version Isolation Check

Codex must inspect and report:

```bash
git status --short
git branch --show-current
git log -1 --oneline
git tag --points-at HEAD
```

If the working tree is dirty during an architecture, schema, prompt, pipeline, output-contract, or multi-file change, Codex must return `NEEDS_VERSION_ISOLATION` unless the user has explicitly decided to continue in the dirty tree.

Codex must not create commits, branches, stashes, resets, checkouts, or cleanup actions without explicit user confirmation.

### Dirty Tree Response Protocol

If `git status --short` is non-empty before a new iteration, multi-file edit, or quality-gated implementation:

1. Stop before editing files.
2. Report the dirty entries exactly enough for the user to understand the blocking state.
3. Provide user-runnable git commands for the two safe paths:
   - commit the intended preparation / audit / documentation changes
   - stash the dirty work with untracked files included
4. Do not run the commit, stash, restore, reset, cleanup, or destructive commands yourself unless the user explicitly asks for that exact action.
5. Resume the implementation gate only after `git status --short` is empty, or after the user explicitly decides to continue in the dirty tree.

Recommended command templates:

```bash
git status --short
git diff --stat
git diff --cached --stat
```

For committing intentional preparation work, tailor the pathspecs and message to the observed dirty files:

```bash
git add <paths>
git status --short
git diff --cached --stat
git commit -m "<message>"
```

For temporary isolation:

```bash
git stash push -u -m "wip: <reason>"
git status --short
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
- `review_id`
- `scope`
- decision label
- plan summary and acceptance criteria
- source files actually inspected
- mismatches between the plan and current code
- external code suggestion review, when applicable
- version isolation check
- risk table covering correctness, regression, schema compatibility, security, privacy/secrets, compliance/safety, runtime stability, rollback, test coverage, and documentation drift
- recommended implementation path
- likely changed files
- files explicitly not to touch
- validation commands, using `python3` on macOS when `py` is unavailable
- `risks`
- `decision_needed`

Codex must not use this gate to take over MiniMax/Sub Agent responsibilities. In particular, Codex must not update `TASK_LOG.md`, `CHANGELOG.md`, or iteration document status unless the workflow authority explicitly assigns that work to Codex.

## Completion Rule

After the review, Codex must wait for user confirmation. Only then may Codex implement the approved path and later deliver an `attempt_id` that references the approved `review_id`.
