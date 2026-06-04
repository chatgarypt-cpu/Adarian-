# DS Team Dispatch: Codex Taskbook v0.1 — Pre-Implementation Review

## 0. Hard Requirements

```yaml
task_id: ds-review-codex-taskbook-communication-substrate-mvp-20260522
task_domain: pm-runtime-governance
task_level: M
mode: pre_implementation_taskbook_review
executor: DS Team / Claude
team_mode_required: true
mcp_required: true
readonly_review_only: true
file_modification_allowed: false
git_commit_allowed: false
owner_control_required: true
```

## 1. Objective

审查 Control Agent 起草的 Codex 实现任务书 (`pm_runtime_communication_substrate_mvp_codex_taskbook_v0.1.md`)。

该任务书将直接交给 Codex 执行——如果任务书有漏洞或边界不清，Codex 可能越界。本次审查的目的是：在 Codex 动手之前，确认任务书足够安全、明确、可执行。

## 2. Review Materials

Required reading:

```
1. pm_runtime_communication_substrate_mvp_codex_taskbook_v0.1.md   ← 主审查对象
2. pm_runtime_communication_substrate_runtime_contract_v0.1.md      ← 上游合同（已 DS 审查通过）
3. pm_runtime_communication_substrate_bootstrap_plan_v0.3.md         ← 上游 plan
4. workflow_compact_v0.3.3.yaml                                      ← YAML 对齐参考
```

All paths under `audit/workflow_v4.0/hermes pm context/` or `docs/skills/workflow_v4.0/workflow_core/`.

## 3. Context

```
2026-05-22 当前状态:
  ✅ Runtime Contract v0.1 — DS 审查 pass_with_known_issues
  ✅ YAML v0.3.3 — bootstrap 对齐完成
  ✅ Owner 已审批 Contract 和 YAML
  → 现在: Codex 任务书 v0.1 待 DS 审查
  → 之后: Owner 审批 → Hermes 复制到 docs/iterations/ → Codex 执行
```

## 4. Review Questions

1. **Scope 边界是否足够严格？** allowed_files 和 forbidden_files 是否覆盖了所有可能被 Codex 误触的文件？
2. **MVP 模块定义是否清晰？** cli.py / relay_runner.py / extractors.py / recovery.py 的职责描述是否足够具体到可以直接写代码？
3. **Runtime Artifacts 是否完整？** 13 种 artifact 是否覆盖了 Communication Substrate Contract 的要求？
4. **双层状态模型是否正确？** task_status 和 runtime_state 的值是否与 workflow_compact_v0.3.3.yaml 对齐？
5. **Health-Based Control 参数是否合理？** heartbeat_interval / progress_check_interval / no_heartbeat_timeout 等值是否可用？
6. **Owner Decision Relay 8 种事件是否完整？** 是否遗漏了实际会触发的场景？
7. **Hard Boundaries（第14节）是否足够？** 9 条禁止项是否能防止 Codex 越界？
8. **Required Checks（第10节）是否可执行？** py_compile 和 import 检查命令是否正确？
9. **是否需要补充或修改任何内容？** 有没有缺失的关键约束？
10. **该任务书是否可以直接交给 Codex 执行？** 如果不能，具体缺什么？

## 5. Expected Output

Write report:
```
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/ds/ds_codex_taskbook_review.md
```

Write receipt:
```
audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/ds/ds_receipt.yaml
```

Report must include:

```yaml
review_type: pre_implementation_taskbook_review
team_mode_used: true | false
mcp_used: true | false
acceptance_verdict: pass | pass_with_known_issues | patch_required | hold | fail
findings:
  P0: []
  P1: []
  P2: []
  P3: []
codex_readiness:
  ready: true | false | needs_patch
  gaps: []
scope_boundary_assessment:
  allowed_files_complete: true | false
  forbidden_files_complete: true | false
  missing_from_allowed: []
  missing_from_forbidden: []
runtime_artifact_coverage:
  contract_artifacts: N  # how many contract-required
  taskbook_artifacts: N  # how many taskbook covers
  gaps: []
process_issues: []
blockers: []
recommended_next_action: []
report_path: required
receipt_path: required
```

## 6. Boundaries

**DO**:
- Review taskbook for completeness / safety / executability
- Use MCP filesystem + Agent Team (2-3 reviewers)
- Compare against Runtime Contract and YAML for alignment
- Report in Chinese Markdown

**DO NOT**:
- Modify any file
- Claim closeout
- Re-audit the Runtime Contract (already passed)
- Write code or suggest implementation details beyond taskbook review

## 7. Working Directory

```
/Users/gary/项目开发/AdarianMigration/adarian mvp
```
