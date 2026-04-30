# Repo Hygiene Closeout - 2026-05-01

## Status

Completed pending commit. File-level hygiene policy and audit evidence records were created, and generated runtime artifacts were removed from active Git tracking while remaining on disk.

## Baseline

- Pre-hygiene checkpoint: `f9fae60 checkpoint: pre hygiene dirty tree before phase1 r0`
- Branch: `master`
- Starting working tree after checkpoint: clean

## Completed

- Added plan backup:
  - `audit/repo_hygiene_plan_2026-05-01.md`
- Updated generated artifact ignore policy:
  - `.gitignore`
  - ignores `outputs/`
  - ignores `profiling/output/`
- Added text normalization policy:
  - `.gitattributes`
  - includes `*.jsonl text eol=lf` for profiling logs
- Added lightweight evidence directory:
  - `audit/evidence/README.md`
- Added current macOS-path run evidence:
  - `audit/evidence/run_test5_20260429_022613.md`
- Added historical Windows-path comparison run evidence:
  - `audit/evidence/run_test7_20260427_174326.md`

## Read-Only Inventory Findings

- Tracked generated artifact files before de-tracking: `166`
- Physical artifact files present under generated roots: `168`
- Extra ignored local files:
  - `outputs/.DS_Store`
  - `outputs/runs/.DS_Store`
- Tracked artifact roots:
  - `113` under `outputs/`
  - `53` under `profiling/output/`
- Runtime artifact categories:
  - `outputs/runs/*`
  - legacy `outputs/output*` and `outputs/test7`
  - `profiling/output/runs_archive/*`
  - `profiling/output/_to_be_deleted`

## De-Tracking Result

The generated artifact roots were removed from Git tracking with:

```bash
git rm --cached -r outputs profiling/output
```

Verification:

```bash
git ls-files outputs profiling/output | wc -l
git status --short
git diff --check
```

- `git ls-files outputs profiling/output | wc -l` returns `0`
- generated artifacts remain on disk
- `outputs/` and `profiling/output/` no longer reappear as Git changes

## Current Validation

- `.gitignore` correctly matches generated output examples when checked with `--no-index`.
- `git diff --check` currently reports no whitespace errors.
- `git ls-files outputs profiling/output | wc -l` returns `0`.

## Next Step

Stage hygiene files and de-tracking changes, then commit:

```bash
git add .gitignore .gitattributes audit/repo_hygiene_plan_2026-05-01.md audit/repo_hygiene_closeout_2026-05-01.md audit/evidence
git commit -m "chore: isolate generated runtime artifacts"
```

Keep EOL renormalization as a separate future commit if needed.
