# Workflow Core v4.0 R2 审查与落盘执行计划（修正版）

> 文档类型：Workflow Governance Review & Landing Execution Plan  
> 适用项目：Adarian MVP / 多智能体舆情推演系统  
> 当前对象：`workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md`  
> 目标落盘路径：`docs/skills/workflow_core.md`  
> 当前阶段：R2 freeze / readonly review / landing execution planning  
> 生成日期：2026-05-19  
> 版本说明：本版修正上一版中“C线复盘审查”的理解偏差；C线改为“落盘执行方案审查”。  
> Control Agent 判断：R2 未发现结构性漂移，但不得跳过 DS 只读审查直接 Codex 落盘。  

---

## 0. Executive Decision

当前不进入 Codex 落盘。

当前先走三条只读审查线：

```text
A线：R2 Structural Review
  审 R2 文档本身是否可以作为 workflow_core.md v4.0 落盘候选。

B线：Workflow Rollout Readiness Review
  审 v4.0 作为一套新工作流，应该如何上线和启用。

C线：Landing Execution Plan Review
  审第一批具体怎么落盘，哪些文件先改、谁执行、谁验收、哪些禁止动。
```

一句话分工：

```text
A线看“文档能不能落”。
B线看“制度怎么上线”。
C线看“第一批具体怎么落盘”。
```

推荐执行方式：

```text
Hermes PM Runtime 创建 3 个 readonly task；
A线必须开 DS Agent Team；
B线可由 Workflow Landing Reviewer 或 DS Team 执行；
C线建议由 DS Team 的另一个 subagent 执行，或单独再开一个 DS Team。
```

当前核心判断：

```text
1. R2 文档本身未见结构性漂移。
2. R2 仍需 DS Team 做只读验收。
3. v4.0 不只是 workflow_core.md 落盘，还涉及 Control Agent / Hermes / DS / Codex 指令同步。
4. Owner 的判断是正确的：Control Agent 口径应优先对齐。
5. 不应让 Codex 一次性改完整套 workflow 生态。
6. 第一批 Codex landing 必须小步：只落核心权威文件，不顺手改一堆派生文件。
```

---

## 1. 当前文件与目标

### 1.1 输入文件

```text
workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
```

可参考：

```text
workflow_core_v4_full_draft_2026-05-19.md
workflow_core_v4.0_full_draft_consistency_repaired_2026-05-19.md
docs/skills/workflow_core.md
docs/iterations/TASK_LOG.md
docs/iterations/CHANGELOG.md
```

### 1.2 目标落盘路径

```text
docs/skills/workflow_core.md
```

### 1.3 当前不允许动作

```text
1. 不允许 Codex 直接落盘。
2. 不允许 Hermes 自动覆盖 workflow_core.md。
3. 不允许 DS Team 修改文件。
4. 不允许自动生成 compact.yaml 并视为权威。
5. 不允许把 DS pass 当成最终 closeout。
6. 不允许把 Hermes completed 当成最终 closeout。
7. 不允许一次性修改 Control Agent / DS / Codex / Hermes 全部指令文件。
8. 不允许把 landing plan 审查变成源码改造任务。
```

---

## 2. 三线审查设计

## 2.1 A线：R2 Structural Review

### 目标

确认 R2 文档是否具备进入 Codex landing 的基础条件。

### 执行方

```text
DS Team
```

要求：

```text
team_mode_required = true
mcp_required = true
readonly_review_only = true
```

### 重点审查

```text
1. §0–§16 是否完整。
2. 是否仍有重复章节 / 拼接残留。
3. DS Verify / DS Accept 是否仍作为旧流程节点残留。
4. audit/hermes_tasks 是否仍被当作 canonical path。
5. owner_approval.md 是否仍被当作默认文件。
6. HOLD / FAIL 是否和 repairable_hold / blocking_hold 冲突。
7. Patch Loop / Patch Lane / Closeout 边界是否一致。
8. workflow_core.md / compact.md / compact.yaml / Agent-specific instructions 权威关系是否清楚。
```

### 输出

```text
audit/tasks/active/v4.0-workflow-r2-ds-review-01/ds/ds_review_report_workflow_core_v4_r2_2026-05-19.md
audit/tasks/active/v4.0-workflow-r2-ds-review-01/ds/ds_receipt.yaml
```

### Verdict

```text
PASS_TO_CODEX_LANDING
PASS_WITH_MINOR_NOTES
HOLD_FOR_REPAIR
FAIL_STRUCTURAL_CONFLICT
```

---

## 2.2 B线：Workflow Rollout Readiness Review

### 目标

审查 v4.0 作为一套新工作流，如何从“文档草案”变成“实际可运行的协作制度”。

### 执行方

```text
Workflow Landing Reviewer
```

也可由 DS Team 另起一组 reviewer 执行。

### 重点审查

```text
1. Control Agent 是否应先对齐 v4.0 口径。
2. workflow_core.md 何时覆盖。
3. compact.md 何时生成。
4. compact.yaml 何时生成。
5. Hermes dispatch template 何时更新。
6. DS Team instruction 何时更新。
7. Codex instruction 何时更新。
8. Hook / Skill / checklist 何时更新。
9. 哪些自动化不能在第一轮启用。
10. 最小安全上线顺序是什么。
```

### 输出

```text
audit/tasks/active/v4.0-workflow-rollout-readiness-01/summary/workflow_rollout_readiness_report_2026-05-19.md
audit/tasks/active/v4.0-workflow-rollout-readiness-01/runtime/result.yaml
```

### Verdict

```text
READY_FOR_STAGED_ROLLOUT
READY_AFTER_CONTROL_AGENT_PATCH
HOLD_FOR_MISSING_RUNTIME_TEMPLATES
HOLD_FOR_WORKFLOW_REDESIGN
```

---

## 2.3 C线：Landing Execution Plan Review

### 目标

审查第一批具体怎么落盘。

这不是复盘任务，也不是重新设计 v4.0。

C线要回答：

```text
当 A线确认 R2 可落，B线确认可分阶段上线后，
第一批 Codex 到底应该改哪些文件？
哪些文件不能动？
执行顺序是什么？
验收证据是什么？
谁来验收？
哪些动作必须 HOLD 回 Owner-Control？
```

### 执行方

推荐：

```text
DS Team 的另一个 subagent / Landing Execution Reviewer
```

备选：

```text
单独再开一个 DS Team
```

不要让 A线 DS 主控顺手完成 C线，除非明确拆分 reviewer 角色。

### 重点审查

```text
1. 第一批是否只覆盖 docs/skills/workflow_core.md。
2. 是否需要先产出 Control Agent v4.0 instruction patch 草案。
3. Control Agent patch 应该是落盘前置条件，还是落盘后第一补丁。
4. compact.md 是否应作为第二批产物，而不是第一批。
5. compact.yaml 是否必须等 compact.md 稳定后机器生成。
6. Hermes dispatch template 是否应在 workflow_core.md 落盘后再改。
7. DS / Codex agent-specific instructions 是否应最后同步。
8. Codex 首次 landing 的 allowed files / forbidden files 是什么。
9. TASK_LOG / CHANGELOG 是否本轮要改。
10. 是否需要 smoke test，还是只需要文档路径 / 引用 / Markdown 检查。
11. 首次 landing 是否需要 git commit，还是先 no-commit handoff。
12. 哪些情况下必须 HOLD 回 Owner-Control。
```

### C线必须输出一个“第一批落盘任务边界”

格式：

```yaml
first_landing_batch:
  executor: Codex
  allowed_files:
    - docs/skills/workflow_core.md
  forbidden_files:
    - docs/skills/workflow_core_compact.md
    - docs/skills/workflow_core_compact.yaml
    - any agent-specific instruction files
    - TASK_LOG.md unless explicitly authorized
    - CHANGELOG.md unless explicitly authorized
    - source code
  required_checks:
    - markdown fence balance
    - section count §0-§16
    - no old canonical path
    - no owner_approval.md default
    - no DS Verify / DS Accept as separate nodes
    - path reference check
  commit_mode: no_commit_until_owner_confirmed
```

### 输出

```text
audit/tasks/active/v4.0-workflow-landing-execution-review-01/summary/workflow_landing_execution_plan_review_2026-05-19.md
audit/tasks/active/v4.0-workflow-landing-execution-review-01/runtime/result.yaml
```

### Verdict

```text
LANDING_PLAN_READY
LANDING_PLAN_READY_WITH_CONDITIONS
HOLD_FOR_BOUNDARY_CLARIFICATION
HOLD_FOR_EXECUTION_RISK
```

---

## 3. 推荐最小安全落地顺序

### 3.1 三线审查前

```text
Step 0：冻结 R2，不再人工散修。
Step 1：Hermes 创建 A / B / C 三个 readonly task。
Step 2：Owner 批准 Hermes 派发三个 readonly task。
```

### 3.2 三线审查中

```text
Step 3：A线 DS Team 审 R2 文档质量。
Step 4：B线 Landing Reviewer 审 v4.0 上线顺序。
Step 5：C线 Landing Execution Reviewer 审第一批落盘边界。
```

### 3.3 三线审查后

```text
Step 6：Hermes 回收三线报告、receipt、result、summary。
Step 7：Control Agent 汇总三份报告，做 landing gate。
Step 8：如 A线 PASS 且 B/C 不阻塞，Owner-Control 批准 Codex first landing。
```

### 3.4 第一批落盘

推荐第一批只做：

```text
docs/skills/workflow_core.md
```

暂不做：

```text
workflow_core_compact.md
workflow_core_compact.yaml
Control Agent instruction files
DS instruction files
Codex instruction files
Hermes template files
TASK_LOG / CHANGELOG 大段同步
source code
```

第一批 Codex 任务应是：

```text
只覆盖 workflow_core.md；
运行文档 sanity check；
生成 codex_receipt.yaml / codex_handoff.md；
不 commit，等待 Owner-Control 判断。
```

### 3.5 第二批与后续

```text
第二批：Control Agent v4.0 instruction patch
第三批：workflow_core_compact.md
第四批：workflow_core_compact.yaml
第五批：Hermes dispatch template
第六批：DS Team instruction
第七批：Codex instruction
第八批：Hook / Skill / checklist
第九批：TASK_LOG / CHANGELOG closeout record
```

注：

```text
如果 B线或 C线判断 Control Agent patch 必须在 workflow_core.md 落盘前完成，
则应先生成 Control Agent patch 草案，但仍不应让 Codex 一次性改全套文件。
```

---

## 4. 为什么 Control Agent 要优先对齐

Owner 的判断成立。

原因：

```text
如果 Control Agent 仍按 v3 口径推进，
它会继续生成旧式 DS Verify / DS Accept prompt、
旧式 Codex prompt、
旧式 TASK_LOG / CHANGELOG 记录方式、
旧式人工传话流程。
```

因此，Control Agent 对齐优先级高于 compact / yaml / agent-specific 指令全面改造。

但需要区分：

```text
Control Agent 口径先对齐
≠
立刻让 Codex 修改所有 Control Agent 相关文件
```

更稳的路径：

```text
1. 先由 B/C 线确认 Control Agent patch 是否必须前置。
2. Control Agent 输出 v4.0 instruction patch 草案。
3. Owner 确认。
4. 再进入正式落盘。
```

---

## 5. Hermes 总控 Dispatch Prompt

以下内容可直接交给 Hermes。

```markdown
# Hermes PM Runtime Dispatch Plan - workflow_core.md v4.0 R2 Review & Landing Execution Planning

## 0. Runtime Role

You are Hermes PM Runtime for the Adarian MVP / 多智能体舆情推演系统 workflow governance upgrade.

Your role is task dispatch, status tracking, receipt collection, and summary generation.

You are not the final gatekeeper.

You must not modify source code, workflow_core.md, iteration documents, or any project files unless explicitly authorized by Owner-Control.

## 1. Current Context

The current candidate workflow document is:

```text
workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
```

Target canonical landing path after approval:

```text
docs/skills/workflow_core.md
```

Current status:

```text
R2 consistency-repaired draft
not yet DS-reviewed
not yet approved for Codex landing
```

## 2. Create Three Readonly Tasks

Create and dispatch three readonly tasks after Owner approval.

---

### Task A - DS Team R2 Structural Readonly Review

```yaml
task_id: v4.0-workflow-r2-ds-review-01
task_title: Workflow Core v4.0 R2 DS Team Readonly Review
executor: DS Team
task_type: readonly_review
team_mode_required: true
mcp_required: true
file_modification_allowed: false
git_commit_allowed: false
runtime_allowed_level: L2
status: proposed
canonical_task_dir: audit/tasks/active/v4.0-workflow-r2-ds-review-01/
```

Expected report:

```text
audit/tasks/active/v4.0-workflow-r2-ds-review-01/ds/ds_review_report_workflow_core_v4_r2_2026-05-19.md
```

Expected receipt:

```text
audit/tasks/active/v4.0-workflow-r2-ds-review-01/ds/ds_receipt.yaml
```

Verdict options:

```text
PASS_TO_CODEX_LANDING
PASS_WITH_MINOR_NOTES
HOLD_FOR_REPAIR
FAIL_STRUCTURAL_CONFLICT
```

---

### Task B - Workflow Rollout Readiness Review

```yaml
task_id: v4.0-workflow-rollout-readiness-01
task_title: Workflow Core v4.0 Rollout Readiness Review
executor: Workflow Landing Reviewer
task_type: readonly_review
team_mode_required: false
mcp_required: true
file_modification_allowed: false
git_commit_allowed: false
runtime_allowed_level: L2
status: proposed
canonical_task_dir: audit/tasks/active/v4.0-workflow-rollout-readiness-01/
```

Expected report:

```text
audit/tasks/active/v4.0-workflow-rollout-readiness-01/summary/workflow_rollout_readiness_report_2026-05-19.md
```

Expected result:

```text
audit/tasks/active/v4.0-workflow-rollout-readiness-01/runtime/result.yaml
```

Verdict options:

```text
READY_FOR_STAGED_ROLLOUT
READY_AFTER_CONTROL_AGENT_PATCH
HOLD_FOR_MISSING_RUNTIME_TEMPLATES
HOLD_FOR_WORKFLOW_REDESIGN
```

---

### Task C - Landing Execution Plan Review

```yaml
task_id: v4.0-workflow-landing-execution-review-01
task_title: Workflow Core v4.0 Landing Execution Plan Review
executor: Landing Execution Reviewer
task_type: readonly_review
team_mode_required: false
mcp_required: true
file_modification_allowed: false
git_commit_allowed: false
runtime_allowed_level: L2
status: proposed
canonical_task_dir: audit/tasks/active/v4.0-workflow-landing-execution-review-01/
```

Recommended executor options:

```text
Option 1: DS Team subagent / Landing Execution Reviewer
Option 2: separate DS Team
```

Expected report:

```text
audit/tasks/active/v4.0-workflow-landing-execution-review-01/summary/workflow_landing_execution_plan_review_2026-05-19.md
```

Expected result:

```text
audit/tasks/active/v4.0-workflow-landing-execution-review-01/runtime/result.yaml
```

Verdict options:

```text
LANDING_PLAN_READY
LANDING_PLAN_READY_WITH_CONDITIONS
HOLD_FOR_BOUNDARY_CLARIFICATION
HOLD_FOR_EXECUTION_RISK
```

## 3. Hermes Constraints

Hermes must:

```text
1. Create task directories under audit/tasks/active/<task_id>/.
2. Generate dispatch.md for each task.
3. Record approval.yaml only if Owner approval is explicitly provided.
4. Dispatch only approved tasks.
5. Track result.yaml.
6. Collect receipts and reports.
7. Produce pm_runtime_summary.md for each task.
8. Return only summary, report path, receipt path, and blocker status to Owner-Control.
```

Hermes must not:

```text
1. Modify workflow_core.md.
2. Modify docs/skills/workflow_core.md.
3. Modify Control Agent / DS / Codex instruction files.
4. Start Codex landing.
5. Delete or archive files.
6. Git commit.
7. Treat DS pass as final closeout.
8. Treat Hermes completed as final closeout.
```

## 4. Stop Conditions

Stop and return HOLD if:

```text
1. R2 file cannot be found.
2. MCP / file read is unavailable for required tasks.
3. DS Team cannot use team mode for Task A.
4. Task directories cannot be created.
5. Dispatch / receipt / result paths mismatch.
6. Any task attempts to modify files.
7. Any task attempts to start Codex landing.
8. Any task recommends bypassing Owner-Control.
```

## 5. Final Hermes Output to Owner-Control

Return:

```yaml
hermes_summary:
  task_a_status:
  task_a_verdict:
  task_a_report_path:
  task_a_receipt_path:
  task_b_status:
  task_b_verdict:
  task_b_report_path:
  task_b_result_path:
  task_c_status:
  task_c_verdict:
  task_c_report_path:
  task_c_result_path:
  blockers:
  process_issues:
  recommended_next_action:
```

Do not produce final closeout.
```

---

## 6. Task A：DS Team R2 只读审查 Prompt

```markdown
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

```text
STOP_REASON: team_mode_not_available
```

If MCP / file reading cannot be used, stop immediately:

```text
STOP_REASON: mcp_not_available_or_file_unreadable
```

Do not replace DS Agent Team review with single-agent skim review.

## 1. Input File

Review:

```text
workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
```

Optional references:

```text
workflow_core_v4_full_draft_2026-05-19.md
workflow_core_v4.0_full_draft_consistency_repaired_2026-05-19.md
docs/skills/workflow_core.md
```

## 2. Objective

Determine whether R2 is ready for Codex landing to:

```text
docs/skills/workflow_core.md
```

## 3. Required Reviewer Agents

Start at least:

```text
1. Structure Reviewer
2. Workflow Semantics Reviewer
3. Path & Artifact Governance Reviewer
4. HOLD / Patch Lane Reviewer
5. Landing Risk Reviewer
```

## 4. Required Checks

Check:

```text
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

```text
repairable_hold
blocking_hold
Patch Loop
Patch Lane
Owner-Control hold
```

## 6. Verdict Options

Use only one:

```text
PASS_TO_CODEX_LANDING
PASS_WITH_MINOR_NOTES
HOLD_FOR_REPAIR
FAIL_STRUCTURAL_CONFLICT
```

## 7. Output

Write report:

```text
audit/tasks/active/v4.0-workflow-r2-ds-review-01/ds/ds_review_report_workflow_core_v4_r2_2026-05-19.md
```

Write receipt:

```text
audit/tasks/active/v4.0-workflow-r2-ds-review-01/ds/ds_receipt.yaml
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
```

---

## 7. Task B：Workflow Rollout Readiness Prompt

```markdown
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

```text
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

```text
workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
```

References:

```text
docs/skills/workflow_core.md
docs/iterations/TASK_LOG.md
docs/iterations/CHANGELOG.md
```

## 3. Required Analysis

Cover:

```text
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

```text
audit/tasks/active/v4.0-workflow-rollout-readiness-01/summary/workflow_rollout_readiness_report_2026-05-19.md
```

Write result:

```text
audit/tasks/active/v4.0-workflow-rollout-readiness-01/runtime/result.yaml
```

## 5. Verdict Options

Use one:

```text
READY_FOR_STAGED_ROLLOUT
READY_AFTER_CONTROL_AGENT_PATCH
HOLD_FOR_MISSING_RUNTIME_TEMPLATES
HOLD_FOR_WORKFLOW_REDESIGN
```

Do not modify files.
Do not start Codex.
Do not closeout.
```

---

## 8. Task C：Landing Execution Plan Review Prompt

```markdown
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

```text
Option A: another DS Team subagent / Landing Execution Reviewer
Option B: a separate DS Team
```

Do not assign this to the same reviewer who is responsible for R2 structural acceptance unless roles are clearly separated.

## 2. Objective

Review the concrete landing execution plan.

This task answers:

```text
What exactly should be modified in the first Codex landing batch?
What should not be modified?
What should be the execution order?
What evidence is required before Owner-Control closeout?
```

This task does not judge whether R2 is structurally valid. That is Task A.

This task does not redesign the whole workflow rollout. That is Task B.

## 3. Inputs

Primary:

```text
workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
```

Optional references:

```text
docs/skills/workflow_core.md
docs/iterations/TASK_LOG.md
docs/iterations/CHANGELOG.md
current repository tree
```

## 4. Required Questions

Answer:

```text
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

```text
audit/tasks/active/v4.0-workflow-landing-execution-review-01/summary/workflow_landing_execution_plan_review_2026-05-19.md
```

Write result:

```text
audit/tasks/active/v4.0-workflow-landing-execution-review-01/runtime/result.yaml
```

## 8. Verdict Options

Use one:

```text
LANDING_PLAN_READY
LANDING_PLAN_READY_WITH_CONDITIONS
HOLD_FOR_BOUNDARY_CLARIFICATION
HOLD_FOR_EXECUTION_RISK
```

Do not modify files.
Do not start Codex.
Do not recommend direct bypass of Owner-Control.
Do not perform final gate.
```

---

## 9. 三线报告回来后的 Control Agent Gate

Control Agent 收到三份报告后，做一次合并判断。

### 9.1 允许进入 Codex First Landing 的条件

```text
1. A线 verdict = PASS_TO_CODEX_LANDING 或 PASS_WITH_MINOR_NOTES。
2. B线 verdict = READY_FOR_STAGED_ROLLOUT 或 READY_AFTER_CONTROL_AGENT_PATCH。
3. C线 verdict = LANDING_PLAN_READY 或 LANDING_PLAN_READY_WITH_CONDITIONS。
4. 没有 hard blocker。
5. Owner 明确确认进入 first landing。
```

### 9.2 如果 B线认为 Control Agent 必须先 patch

则下一步不是 Codex 覆盖 workflow_core.md，而是：

```text
Control Agent v4.0 instruction patch 草案
```

之后再决定是否进入：

```text
Codex first landing workflow_core.md
```

### 9.3 如果 C线认为 first landing 边界不清

则：

```text
不落盘；
由 Control Agent 明确 allowed / forbidden files；
重新发 C线复核或 Owner 直接确认。
```

### 9.4 如果 A线 HOLD

则：

```text
不落盘；
由 Control Agent 修 R2；
生成 R3；
再审。
```

---

## 10. 当前欠缺清单

当前最明显欠缺：

```text
1. Control Agent v4.0 instruction patch
2. Hermes dispatch template
3. DS Post-Execution Review 模板
4. Codex receipt / handoff 模板
5. approval.yaml 模板
6. result.yaml 模板
7. pm_runtime_summary.md 模板
8. workflow_core_compact.md
9. workflow_core_compact.yaml
10. Agent-specific instructions 权威关系说明
11. path audit checklist
12. 首次启用 v4.0 closeout checklist
13. landing execution checklist
14. 长文档重构 sanity check 脚本或流程
```

---

## 11. 最终建议

当前最稳推进方式：

```text
不要直接让 Codex 落盘。
先让 Hermes 派发 A / B / C 三个只读审查任务。
A线审 R2 是否可落盘。
B线审 v4.0 如何上线。
C线审第一批具体怎么落盘。
三线结果回来后，由 Control Agent 做 landing gate。
```

推荐下一步：

```text
Owner 批准 Hermes 创建并派发三个 readonly review task。
```
