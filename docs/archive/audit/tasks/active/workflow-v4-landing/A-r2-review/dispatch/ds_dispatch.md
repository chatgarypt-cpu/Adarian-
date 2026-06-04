# DS Agent Team Readonly Review - workflow_core.md v4.0 R2

## 0. Hard Requirements

```yaml
task_id: v4.0-workflow-r2-ds-review-01
team_mode_required: true
mcp_required: true
readonly_review_only: true
file_modification_allowed: false
git_commit_allowed: false
```

If team mode cannot be started, stop immediately:

```
STOP_REASON: team_mode_not_available
```

If MCP / file reading cannot be used, stop immediately:

```
STOP_REASON: mcp_not_available_or_file_unreadable
```

Do not replace DS Agent Team review with single-agent skim review.

## 1. Input File

Review:

```
audit/workflow_v4.0/workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
```

Optional references:

```
audit/workflow_v4.0/workflow_core_v4_full_draft_2026-05-19.md
audit/workflow_v4.0/workflow_core_v4.0_full_draft_consistency_repaired_2026-05-19.md
docs/skills/workflow_core.md
```

## 2. Objective

Determine whether R2 is ready for Codex landing to:

```
docs/skills/workflow_core.md
```

## 3. Required Reviewer Agents

Start at least:

```
1. Structure Reviewer
2. Workflow Semantics Reviewer
3. Path & Artifact Governance Reviewer
4. HOLD / Patch Lane Reviewer
5. Landing Risk Reviewer
```

## 4. Required Checks

Check:

```
1. §0–§16 each appears exactly once.
2. No duplicated top-level chapters.
3. No duplicated §3.4 / §3.5 blocks.
4. No stale duplicated §4 redline list.
5. No stitching residue before §11.
6. No empty code fences.
7. Markdown fences are balanced.
8. DS Verify / DS Accept are not restored as two separate workflow phases.
9. DS Post-Execution Review is the execution-after-review authority.
10. audit/tasks/active/<task_id>/ is canonical path.
11. audit/hermes_tasks and audit/pm_runtime_tasks are only legacy / transitional paths.
12. owner_approval.md is not a default required file.
13. task/approval.yaml is the default approval record.
14. PM Runtime cannot approve high-risk tasks.
15. PM Runtime cannot closeout.
16. DS Team cannot final gate.
17. Codex cannot self-closeout or self-expand scope.
18. repairable_hold / blocking_hold are consistent with Patch Loop.
19. Patch Loop and Patch Lane are clearly separated.
20. workflow_core.md / compact.md / compact.yaml / Agent-specific instructions authority relationship is clear.
21. No over-engineering or file explosion risk blocks landing.
```

## 5. Special Attention

Pay special attention to remaining `HOLD / FAIL` wording.

Determine whether it is limited to DS Pre-Audit verdict, or whether it conflicts with:

```
repairable_hold
blocking_hold
Patch Loop
Patch Lane
Owner-Control hold
```

## 6. Verdict Options

Use only one:

```
PASS_TO_CODEX_LANDING
PASS_WITH_MINOR_NOTES
HOLD_FOR_REPAIR
FAIL_STRUCTURAL_CONFLICT
```

## 7. Output

Write report:

```
audit/tasks/active/workflow-v4-landing/A-r2-review/ds/ds_review_report_workflow_core_v4_r2_2026-05-19.md
```

Write receipt:

```
audit/tasks/active/workflow-v4-landing/A-r2-review/ds/ds_receipt.yaml
```

Return summary only:

```yaml
verdict:
blockers:
known_issues:
process_issues:
can_enter_codex_landing:
report_path:
receipt_path:
team_mode_used:
mcp_used:
reviewer_agents:
```

Final landing decision belongs to Owner-Control.
