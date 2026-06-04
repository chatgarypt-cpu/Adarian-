# DS Team Dispatch: PM Runtime Communication Substrate Bootstrap Plan Review

## 0. Hard Requirements

```yaml
task_id: ds-review-pm-runtime-communication-substrate-plan-20260522
task_domain: pm-runtime-governance
task_level: M
mode: read_only_architecture_plan_review
executor: DS Team / Claude
team_mode_required: true
mcp_required: true
readonly_review_only: true
file_modification_allowed: false
git_commit_allowed: false
owner_control_required: true
```

## 1. Objective

审查 `PM Runtime Communication Substrate Bootstrap Plan v0.2`。
该计划提出 **Communication Substrate First** 路线：
先建设 PM Runtime 通讯层工程基座平台（Python），再逐步补齐治理层（gate/MCP/skills/workflow_core）。

核心主张：通讯层是 engineering substrate，不是 skill。

## 2. Review Materials

Required reading:

```
1. dispatch/pm_runtime_communication_substrate_bootstrap_plan_v0.2.md  ← 主审查对象
2. audit/tasks/active/control-agent-governance/pm_runtime_relay_context_packet_2026-05-21.md  ← 当前 relay_runner 实际情况
3. audit/tasks/active/pm-runtime-governance/pm-runtime-skill-review/summary/system_failure_analysis_2026-05-22.md  ← Hermes 系统失败分析
4. audit/tasks/active/pm-runtime-governance/pm-runtime-skill-review/summary/pm_runtime_skill_review_v0.1_2026-05-22.md  ← anti-drift skill 审查报告
5. docs/skills/workflow_v4.0/workflow_core/workflow_compact_v0.3.2.yaml  ← 当前 YAML 状态
6. docs/skills/workflow_v4.0/pm_runtime/pm_runtime_instruction_v0.1.3.md  ← PM Runtime 当前角色定义
```

## 3. Context: Why This Plan Exists

2026-05-22，Hermes 在执行 PM Runtime lightweight scan 过程中连续发生 4 项系统失败（详见文件 #3）：
1. 角色越界 — Hermes 替 DS Team 做了深度审查
2. 产物未落盘 — 长文输出直接丢聊天
3. 目录 domain 路由错误 — PM Runtime 任务放在了 Control Agent 域下
4. MCP 工具上下文缺失 — Hermes 缺少文件系统 MCP 工具

四项失败的共同根因：**有规范但无 pre-action Gate 约束执行**。

当前 relay_runner.py 是任务内脚手架，存在 13 项已知缺口（硬编码、无 registry、无恢复能力等）。

v0.2 计划主张：与其继续修补 workflow_core/anti-drift/gate 文档，不如先建设通讯层工程基座，
用真实任务运转暴露问题后再制度化。

## 4. Review Questions（必须逐一回答）

请 DS Team 重点审查：

1. v0.2 是否正确修复了 v0.1 "把通讯层误写成 skill" 的关键错误？
2. Communication Substrate 作为工程基座平台，是否是当前 bootstrap 阶段的正确主线？
3. Python MVP 是否比 Go MVP 更适合当前阶段？
4. task registry / recovery / stdout-stderr capture 是否为 v0.1 必需能力？是否有遗漏？
5. 是否应继续保留任务内 relay_runner 复制模式作为过渡？
6. 是否存在过早平台化、过度工程化？
7. 是否遗漏 Codex / Claude / DS / Hermes 的关键 executor profile？
8. 是否需要更早引入 MCP / settings.local.json preflight？
9. 是否充分防止 Hermes 通过平台建设自我扩权？
10. 下一步应先写 Runtime Contract、Python MVP 任务卡，还是先写三张角色卡？
11. 是否存在 P0 blocker？

Additional cross-check（结合输入文件 #3 和 #4）：
12. v0.2 的架构是否能阻止 2026-05-22 四连失败的重现？
13. v0.2 与 anti-drift skill v0.1.1 的关系是否清晰（先后顺序？谁等谁？）

## 5. Expected Output

Write report:
```
audit/tasks/active/pm-runtime-governance/ds-substrate-plan-review/ds/ds_substrate_plan_review.md
```

Write receipt:
```
audit/tasks/active/pm-runtime-governance/ds-substrate-plan-review/ds/ds_receipt.yaml
```

Report must include:

```yaml
review_type: read_only_architecture_plan_review
team_mode_used: true | false
mcp_used: true | false
scope_compliance: pass | issue
acceptance_verdict: pass | pass_with_known_issues | patch_required | hold | fail
findings:
  P0: []
  P1: []
  P2: []
  P3: []
process_issues: []
blockers: []
four_failures_prevention_assessment:  # 新增：评估 v0.2 对四项失败的防御效果
  role_boundary_violation:
  artifact_path_missing:
  task_domain_routing_error:
  mcp_tool_context_gap:
anti_drift_skill_relationship_assessment:  # 新增：v0.2 与 anti-drift v0.1.1 的先后关系
recommended_next_action: []
report_path: <required>
receipt_path: <required>
```

## 6. Boundaries

**DO**:
- Read-only architecture plan review
- Use MCP filesystem tools to read all 6 input files
- Use Agent Team (minimum 3 reviewers: Architecture / Execution Feasibility / Safety-Boundary)
- If MCP or team mode unavailable: HALT and report in process_issues
- If any input file not found: mark as path_not_verified, do not skip

**DO NOT**:
- Modify any file
- Write code
- Update workflow_core
- Claim closeout
- Expand into Codex landing scope
- Treat missing files as nonexistent

## 7. Working Directory

```
/Users/gary/项目开发/AdarianMigration/adarian mvp
```
