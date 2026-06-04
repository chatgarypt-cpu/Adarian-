# Workflow Rollout Readiness Review - workflow_core.md v4.0

## 0. Task Metadata

```yaml
task_id: v4.0-workflow-rollout-readiness-01
task_title: Workflow Core v4.0 Rollout Readiness Review
executor: Workflow Landing Reviewer
task_type: readonly_review
mcp_required: true
file_modification_allowed: false
git_commit_allowed: false
```

## 1. Objective

Review how workflow_core v4.0 should be operationalized after R2 is approved.

Answer:

```
1. What should be landed first?
2. Should Control Agent instructions be updated first?
3. When should docs/skills/workflow_core.md be overwritten?
4. When should workflow_core_compact.md be generated?
5. When should workflow_core_compact.yaml be generated?
6. When should DS / Codex / Hermes / Control Agent-specific instructions be updated?
7. What is missing before the workflow can actually run?
8. What should Hermes do vs. what should Codex do vs. what should Control Agent do?
9. What should not be automated yet?
10. What is the minimum safe rollout plan?
```

## 2. Inputs

Primary:

```
audit/workflow_v4.0/workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
```

References:

```
docs/skills/workflow_core.md
docs/iterations/TASK_LOG.md
docs/iterations/CHANGELOG.md
```

## 3. Required Analysis

Cover:

```
1. Authority layer
2. Rollout order
3. Hermes readiness
4. Control Agent readiness
5. DS Team readiness
6. Codex readiness
7. Missing artifacts
8. Automation boundary
9. Minimum safe rollout
```

## 4. Required Output

Write report:

```
audit/tasks/active/workflow-v4-landing/B-rollout-readiness/summary/workflow_rollout_readiness_report_2026-05-19.md
```

Write result:

```
audit/tasks/active/workflow-v4-landing/B-rollout-readiness/runtime/result.yaml
```

## 5. Verdict Options

Use one:

```
READY_FOR_STAGED_ROLLOUT
READY_AFTER_CONTROL_AGENT_PATCH
HOLD_FOR_MISSING_RUNTIME_TEMPLATES
HOLD_FOR_WORKFLOW_REDESIGN
```

## 6. Output Format

### Report (Chinese Markdown)

```markdown
# Workflow Core v4.0 Rollout Readiness Report

## 1. Executive Verdict

## 2. Authority Layer Analysis

## 3. Recommended Rollout Order

## 4. Hermes PM Runtime Readiness

## 5. Control Agent Readiness

## 6. DS Team Readiness

## 7. Codex Readiness

## 8. Missing Artifacts

## 9. Automation Boundary

## 10. Minimum Safe Rollout Plan

## 11. Risks

## 12. Recommended Next Action
```

### result.yaml

```yaml
task_id: v4.0-workflow-rollout-readiness-01
verdict:
blockers:
missing_artifacts:
automation_boundary:
minimum_safe_rollout_order: []
recommended_next_action:
report_path:
```

Do not modify files.
Do not start Codex.
Do not closeout.
