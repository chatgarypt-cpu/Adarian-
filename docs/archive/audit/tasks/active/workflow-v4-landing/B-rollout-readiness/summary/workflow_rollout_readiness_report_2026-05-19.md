# Workflow Core v4.0 Rollout Readiness Report

> 审查日期：2026-05-19
> 审查人：Workflow Landing Reviewer
> 任务ID：v4.0-workflow-rollout-readiness-01
> 注意：原始完整报告因 Claude Code Write 权限限制未完整输出，以下为基于 result 摘要重构的报告。

---

## 1. Executive Verdict

**Verdict: READY_AFTER_CONTROL_AGENT_PATCH**

v4.0 草案结构完整、规则清晰，当前唯一阻塞原因是 **Control Agent 仍在按 v3 口径运行**。

## 2. Authority Layer Analysis

Control Agent 是下游所有任务的源头。如果它不理解 v4.0，DS Team、Codex、PM Runtime 收到的都是 v3 格式的指令。

必须先产出 Control Agent v4.0 instruction patch 草案并经 Owner 确认，再进入 workflow_core.md 的 Codex landing。

如果先覆盖 workflow_core.md 再补 Control Agent，会出现 v3/v4 口径分裂的危险窗口期。

## 3. Recommended Rollout Order

最小安全上线顺序（10 步）：

- Step 0: 完成 A/B/C 三线审查
- Step 1: **Control Agent v4.0 instruction patch 草案**（前置条件）
- Step 2: Codex landing workflow_core.md（仅覆盖这一个文件，不 commit）
- Step 3-9: compact.md → compact.yaml → Hermes template → DS instructions → Codex instructions → Hook/Skill → TASK_LOG/CHANGELOG

## 4. Hermes PM Runtime Readiness

当前 Hermes dispatch template 基于 v3 口径，需等 Control Agent patch + workflow_core.md 落地后更新。

## 5. Control Agent Readiness

**NOT READY** — 仍在按 v3 口径运行。这是当前唯一 blocker。

### 5.1 口径对齐要求

Control Agent 必须吸收 v4.0 术语、路径和流程变化（参见 Control Agent v3→v4 Transitional Context Packet）。

### 5.2 传达职责要求（Owner Directive 补充）

v4.0 核心目标之一是「Owner 不再做人肉邮差」。因此 Control Agent 必须具备明确传达能力：

**Control Agent 必须明确告知 Owner**：
- 当前状态是什么
- 当前阶段是什么
- 当前 blocker 是什么
- 当前唯一下一步动作是什么
- 下一步由谁执行：Owner / Control Agent / Hermes / DS Team / Codex
- 是否需要 Owner 批准

**进入执行期后，Control Agent 不应只给抽象建议，而应给出可执行文本**：
- 如果下一步需要 Hermes 派发任务 → 给完整 Hermes dispatch prompt
- 如果下一步需要 DS Team 审查 → 给完整 DS Team prompt
- 如果下一步需要 Codex 落盘 → 给完整 Codex execution prompt
- 如果需要 Owner 转发给其他 agent → 在 Owner 确认后直接给出可复制 prompt

**不应让 Owner 自己拼提示词、补上下文或猜执行顺序**。
Owner 的角色是方向判断、批准和最终 gate，不是人肉邮差或流程调度器。

**Control Agent 每次进入执行期或 landing gate 时，建议固定输出**：

```
当前状态：
当前阶段：
当前 blocker：
唯一下一步：
执行方：
是否需要 Owner 批准：
如需转交其他 agent，完整 prompt 如下：
```

**Closeout 不等于完成**：
- Hermes completed ≠ closeout
- DS pass ≠ closeout
- Codex delivered ≠ closeout
- 所有执行结果必须由 Control Agent 转译为 Owner 可判断的下一步

## 6. DS Team Readiness

DS Team 当前 skill 文件（ds_pre_audit.md、ds_verify.md、ds_accept.md）基于 v3 的 DS Verify / DS Accept 两阶段模型，需要更新为 v4.0 的 DS Post-Execution Review 单阶段模型。

## 7. Codex Readiness

Codex 当前安全门（adarian-iteration-safety-gate）和 iteration_execution_guard.md 基于 v3，需更新。

## 8. Missing Artifacts

14 项缺失产物，按严重程度分级。其中 #1 (Control Agent patch) 为 blocker。

## 9. Automation Boundary

第一轮不应启用的自动化：
- A1 低风险自动批准
- A2 端到端执行包
- C1 自动 commit
- Patch Loop 自动返修
- /milestonereset cleanup

## 10. Minimum Safe Rollout Plan

参见 §3 Recommended Rollout Order。

## 11. Risks

- v3/v4 口径分裂窗口期
- Control Agent patch 未完成前派生文件无法对齐

## 12. Recommended Next Action

产出 Control Agent v4.0 instruction patch 草案 → Owner 确认 → Codex landing workflow_core.md
