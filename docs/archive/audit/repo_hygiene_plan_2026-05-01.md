# Repo Hygiene Plan - 2026-05-01

## Purpose

Prepare the repository for Phase 1 R0 contract-freeze work by turning the current migrated Mac workspace into a cleaner, auditable, rollback-friendly baseline.

## Checkpoint

- Pre-hygiene checkpoint commit: `f9fae60 checkpoint: pre hygiene dirty tree before phase1 r0`
- Branch: `master`
- Status before hygiene: clean working tree

## Decisions

- Runtime artifacts policy: remove generated run outputs from active Git tracking.
- Checkpoint policy: create a checkpoint before any hygiene edits.
- Scope boundary: do not change Phase 1 / Phase 2 / Phase 3 / Phase 4 business logic.
- Evidence policy: keep lightweight audit evidence under `audit/evidence/`, not full generated run trees under `outputs/`.

## Implementation Plan

1. Back up this plan in `audit/`.
2. Add repository text normalization policy in `.gitattributes`.
3. Update `.gitignore` so future generated runtime artifacts do not enter Git.
4. Preserve lightweight evidence notes for selected successful runs:
   - Primary current Mac evidence: `outputs/runs/test5_20260429_022613/`
   - Historical Windows-path comparison evidence: `outputs/runs/test7_20260427_174326/`
5. Remove `outputs/` and `profiling/output/` from Git tracking with `git rm --cached`, while preserving files locally.
6. Verify:
   - `git status --short`
   - `git diff --check`
   - tracked artifact count under `outputs/` and `profiling/output/`
7. Commit hygiene changes separately after review.

## Risks And Controls

| Risk | Control |
|------|---------|
| Accidental loss of run artifacts | Use `git rm --cached` only; do not delete local files. |
| Evidence loss | Keep lightweight evidence metadata under `audit/evidence/`. |
| EOL churn | Add `.gitattributes`; do not run broad formatters. |
| Scope creep | Do not touch business logic during this hygiene pass. |
| Rollback uncertainty | Use checkpoint commit `f9fae60` as the return anchor. |

## Out Of Scope

- No Phase 1 Output Contract Freeze document yet.
- No Parser / Compiler / Validator implementation.
- No generated artifact deletion from disk.
- No push to remote.
