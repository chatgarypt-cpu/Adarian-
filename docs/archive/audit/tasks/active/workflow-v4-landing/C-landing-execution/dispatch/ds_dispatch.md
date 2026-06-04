# Landing Execution Plan Review - workflow_core.md v4.0

## 0. Task Metadata

```yaml
task_id: v4.0-workflow-landing-execution-review-01
task_title: Workflow Core v4.0 Landing Execution Plan Review
executor: Landing Execution Reviewer
task_type: readonly_review
mcp_required: true
file_modification_allowed: false
git_commit_allowed: false
```

## 1. Executor Recommendation

This task can be executed by either:

```
Option A: another DS Team subagent / Landing Execution Reviewer
Option B: a separate DS Team
```

Do not assign this to the same reviewer who is responsible for R2 structural acceptance unless roles are clearly separated.

## 2. Objective

Review the concrete landing execution plan.

This task answers:

```
What exactly should be modified in the first Codex landing batch?
What should not be modified?
What should be the execution order?
What evidence is required before Owner-Control closeout?
```

This task does not judge whether R2 is structurally valid. That is Task A.

This task does not redesign the whole workflow rollout. That is Task B.

## 3. Inputs

Primary:

```
audit/workflow_v4.0/workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
```

Optional references:

```
docs/skills/workflow_core.md
docs/iterations/TASK_LOG.md
docs/iterations/CHANGELOG.md
current repository tree
```

## 4. Required Questions

Answer:

```
1. Should the first landing batch only modify docs/skills/workflow_core.md?
2. Should Control Agent v4.0 instruction patch be required before first landing?
3. Should compact.md be generated in the first batch or later?
4. Should compact.yaml be generated manually or by machine after compact.md?
5. Should Hermes dispatch template be updated before or after workflow_core.md landing?
6. Should DS / Codex agent-specific instructions be updated before or after workflow_core.md landing?
7. Should TASK_LOG / CHANGELOG be changed in the first batch?
8. Should there be a smoke test?
9. What static checks are required?
10. Should Codex commit automatically?
11. What are the allowed files?
12. What are the forbidden files?
13. What are the stop conditions?
14. What evidence should Codex return?
15. Who performs post-landing review?
```

## 5. Required Output: First Landing Batch Boundary

You must output this section:

```yaml
first_landing_batch:
  executor: Codex
  purpose:
  allowed_files:
  forbidden_files:
  required_commands:
  required_static_checks:
  required_receipts:
  post_landing_review:
  commit_mode:
  stop_conditions:
```

Recommended default:

```yaml
first_landing_batch:
  executor: Codex
  purpose: "Land reviewed workflow_core v4.0 full authority document only."
  allowed_files:
    - docs/skills/workflow_core.md
  forbidden_files:
    - docs/skills/workflow_core_compact.md
    - docs/skills/workflow_core_compact.yaml
    - any Control Agent instruction files
    - any DS Team instruction files
    - any Codex instruction files
    - any Hermes / PM Runtime template files
    - docs/iterations/TASK_LOG.md unless explicitly authorized
    - docs/iterations/CHANGELOG.md unless explicitly authorized
    - source code
  required_static_checks:
    - "§0–§16 each appears exactly once"
    - "Markdown code fences are balanced"
    - "No empty code fences"
    - "No audit/hermes_tasks as canonical path"
    - "No owner_approval.md as default approval file"
    - "No DS Verify / DS Accept as separate nodes"
    - "docs/skills/workflow_core.md remains sole authority"
  required_receipts:
    - codex_receipt.yaml
    - codex_handoff.md
  post_landing_review:
    - DS readonly post-landing path/reference review
  commit_mode: no_commit_until_owner_confirmed
```

## 6. Required Report Structure

```markdown
# Workflow Core v4.0 Landing Execution Plan Review

## 1. Executive Verdict

## 2. First Landing Batch Boundary

## 3. Allowed Files

## 4. Forbidden Files

## 5. Execution Order

## 6. Required Checks

## 7. Required Evidence

## 8. Commit Policy

## 9. Post-Landing Review

## 10. Stop Conditions

## 11. Risks

## 12. Final Recommendation
```

## 7. Output

Write report:

```
audit/tasks/active/workflow-v4-landing/C-landing-execution/summary/workflow_landing_execution_plan_review_2026-05-19.md
```

Write result:

```
audit/tasks/active/workflow-v4-landing/C-landing-execution/runtime/result.yaml
```

## 8. Verdict Options

Use one:

```
LANDING_PLAN_READY
LANDING_PLAN_READY_WITH_CONDITIONS
HOLD_FOR_BOUNDARY_CLARIFICATION
HOLD_FOR_EXECUTION_RISK
```

Do not modify files.
Do not start Codex.
Do not recommend direct bypass of Owner-Control.
Do not perform final gate.
