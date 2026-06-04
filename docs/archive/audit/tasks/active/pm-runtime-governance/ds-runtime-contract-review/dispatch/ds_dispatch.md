# DS Team Dispatch: PM Runtime Communication Substrate Runtime Contract v0.1 — Focused Review

## 0. Hard Requirements

```yaml
task_id: ds-review-pm-runtime-communication-substrate-runtime-contract-20260522
task_domain: pm-runtime-governance
task_level: M
mode: focused_runtime_contract_review
executor: DS Team / Claude
team_mode_required: true
mcp_required: true
readonly_review_only: true
file_modification_allowed: false
git_commit_allowed: false
owner_control_required: true
```

## 1. Objective

审查 `PM Runtime Communication Substrate Runtime Contract v0.1`。
该合同是 v0.3 plan 的 Phase 1 产物，定义了 Python MVP 实现前必须锁定的全部边界。

本合同是 focused review（不是 full architecture review）。v0.2 的架构审查已通过（patch_required → v0.3 已修复 7 P0），本次只验证：
1. P0 修复是否到位
2. Contract 是否足够具体到可以直接写 Codex 任务卡

## 2. Review Materials

Required reading:

```
1. pm_runtime_communication_substrate_runtime_contract_v0.1.md  ← 主审查对象
2. pm_runtime_communication_substrate_bootstrap_plan_v0.3.md     ← 上游 plan
3. ds_substrate_plan_review.md                                    ← v0.2 DS 审查（7 P0 来源）
4. hermes_codex_workflow_verification_spike_summary.md            ← Codex spike 证据
5. owner_decision_relay_test_summary.md                           ← Owner Decision Relay 证据
6. workflow_compact_v0.3.2.yaml                                   ← YAML 对齐参考
```

All paths are under `audit/workflow_v4.0/hermes pm context/` or `audit/tasks/active/pm-runtime-governance/`.

## 3. Context: What Has Happened

```
2026-05-22 timeline:
  上午 → Hermes 四连失败（角色越界/未落盘/domain错/MCP缺口）
  中午 → anti-drift skill v0.1 → v0.1.1 迭代
  下午 → Communication Substrate Bootstrap Plan v0.1 → v0.2 → v0.3
        DS Team 审查 v0.2: patch_required, 7 P0
        Control Agent 出 v0.3 修复全部 P0
        Codex spike 验证: managed_codex_exec candidate
        Owner Decision Relay 测试: 发现 one-shot subprocess 限制
  → 现在: Runtime Contract v0.1 待审查
```

## 4. Review Questions (§20.2)

1. Does this contract fully absorb the 7 P0 findings from v0.2 review?
2. Is pre-action gate (§7) sufficiently early and enforceable?
3. Is independent process + task session (§8) sufficiently specified?
4. Is health-based runtime control (§9) better than hard timeout?
5. Is append-only registry (§10) sufficient to reduce tampering risk?
6. Is recovery evidence preservation (§15) sufficient?
7. Is Codex managed executor profile (§12.1) consistent with spike evidence?
8. Is Owner Decision Relay (§13) correctly generalized beyond approval prompts?
9. Are one-shot subprocess limitations (§13.5) handled honestly?
10. Are Hermes forbidden items (§12.3) sufficiently embedded (16 items)?
11. Are there any P0 blockers before Python MVP task card?

## 5. Additional Context: Codex Task Card Format Decision

After this contract review passes, the next step is writing a Codex task card for Python MVP implementation.
Owner + Hermes have decided to use **Adarian iteration document format** (`docs/iterations/vX.Y.Z-<topic>.md`) for the Codex task card. Rationale:
- Codex's `adarian-iteration-safety-gate` skill recognizes this format and triggers safety gates automatically
- Reuses existing Codex dispatch workflow (allowed/forbidden files, scope freeze, self-check commands)
- The implementation scope is `pm_runtime/relay/`, NOT `src/` — this must be explicitly distinguished from business source iterations

Please note in your review: does the Runtime Contract provide enough specificity for an iteration document format task card? Or are there gaps between contract-level abstraction and Codex-actionable detail?

**Owner补充要求**：请 DS Team 在审查中额外判断并给出具体建议：
1. 后续 Codex 实现任务是否适合采用 Adarian 迭代任务书板式（`docs/iterations/vX.Y.Z-<topic>.md`）？
2. 若采用，请给出该迭代任务书的以下字段建议范围：
   - `allowed_files` — Codex 允许修改的文件列表
   - `forbidden_files` — Codex 禁止触碰的文件列表（必须包含 src/main.py/config.py/tests/）
   - `required_checks` — 实现后的自检命令（如 py_compile、import 检查等）
   - `receipt_fields` — Codex 必须回传的回执字段
3. 明确标注：该迭代属于 "PM Runtime substrate infrastructure"，不属于 "Adarian 业务源码迭代"。防止 Codex 安全门误判或放行。

## 6. Pipeline After This Review

```text
Runtime Contract v0.1
  → DS focused review (this dispatch)
  → Owner acceptance
  → Control Agent drafts iteration task doc (vX.Y.Z-communication-substrate-mvp)
  → Codex implementation (pm_runtime/relay/)
  → DS Team testing/verification
  → Bootstrap online
```

## 7. Expected Output

Write report:
```
audit/tasks/active/pm-runtime-governance/ds-runtime-contract-review/ds/ds_runtime_contract_review.md
```

Write receipt:
```
audit/tasks/active/pm-runtime-governance/ds-runtime-contract-review/ds/ds_receipt.yaml
```

Report must include:

```yaml
review_type: focused_runtime_contract_review
team_mode_used: true | false
mcp_used: true | false
acceptance_verdict: pass | pass_with_known_issues | patch_required | hold | fail
p0_repair_status:  # 逐一验证 7 P0 修复
  P0-1_yaml_directory:
  P0-2_pre_action_gate:
  P0-3_registry_status:
  P0-4_partial_output:
  P0-5_authority_vacuum:
  P0-6_anti_tamper:
  P0-7_evidence_fidelity:
findings:
  P0: []
  P1: []
  P2: []
  P3: []
task_card_readiness_assessment:  # 新增：合同是否足够具体到直接写迭代任务书
  sufficient: true | false | needs_clarification
  gaps: []
process_issues: []
blockers: []
recommended_next_action: []
report_path: required
receipt_path: required
```

## 8. Boundaries

**DO**:
- Focused contract review (not re-audit architecture)
- Verify P0 repairs against v0.2 DS findings
- Use MCP filesystem + Agent Team (2-3 reviewers)
- Assess task card readiness

**DO NOT**:
- Modify any file
- Re-audit the architecture from scratch
- Claim closeout
- Expand into Codex landing scope

## 9. Working Directory

```
/Users/gary/项目开发/AdarianMigration/adarian mvp
```
