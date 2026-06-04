# PM Runtime Skill: Workflow Alignment and Anti-Drift Governance v0.1.1

> file_target: `pm_runtime/skills/workflow_asset_governance/SKILL.md`  
> recommended_title: `PM Runtime Skill: Workflow Alignment and Anti-Drift Governance`  
> version: v0.1.1  
> status: bootstrap candidate / not repository-landed / pending formal DS-Codex alignment review  
> created_at: 2026-05-22  
> owner_control_required: true  
> execution_mode: Bootstrap Transitional Mode  
> hooks: deferred  

---

## 0. Bootstrap Status

当前 workflow_v4.0 仍处于 **bootstrap setup phase**。

这意味着：

1. DS Team / Codex 的正式 role instruction 尚未完整落位；
2. PM Runtime / Hermes 的子 skill 体系仍在搭建；
3. 当前 skill 是候选治理资产，不是 repository-landed workflow authority；
4. 当前阶段可以继续使用旧工作流进行人工搬运；
5. 本 skill 暂时只用于统一口径、防止漂移、辅助后续审查，不用于自动化执行。

本阶段不强行要求完整 A 线流程闭环。

允许的过渡链路：

```text
Control Agent 起草
→ Owner 快速判断方向
→ Hermes lightweight scan / runtime feedback
→ Control Agent 修订
→ 暂存为 candidate
→ DS / Codex role files 落位后再做正式 alignment review
→ Codex first landing
→ Owner-Control closeout
```

---

## 1. Core Purpose

本 skill 的核心不是“以 core 为尊”，也不是让 PM Runtime 变成 workflow 宪法警察。

本 skill 的核心是：

```text
防止 workflow_core、compact、YAML、agent instruction、真实 agent skill/config 文件之间发生口径漂移。
```

同时，本 skill 允许在 DS Team 核查和 Owner 批准下，反向识别：

```text
workflow_core 本身已经落后、冲突、不完整或不适应当前工作流演进。
```

因此：

```text
core = 当前治理基准 / current governance baseline
core ≠ 永恒真理
core ≠ 不可挑战的绝对权威
```

---

## 2. Scope

本 skill 只处理 **workflow alignment / anti-drift** 问题。

它关注：

1. 各 agent 角色边界是否漂移；
2. closeout / gate / audit / receipt / report 等术语是否漂移；
3. workflow_core、compact、YAML、role instruction、skill 文件之间是否冲突；
4. `.claude/`、`.codex/`、`.hermes/` 下真实配置是否与当前口径一致；
5. 新能力是否已经在局部 skill 中出现，但尚未被 core 吸收；
6. core 是否已经落后于实际 workflow 设计；
7. 当前是否需要 DS Team 做 repository-level read-only review。

本 skill 不负责：

1. 直接修改任何 workflow asset；
2. 直接修改 `.claude/`、`.codex/`、`.hermes/`；
3. 直接修复 core；
4. 直接批准 landing；
5. 直接 closeout；
6. 替 DS Team 做正式 audit；
7. 替 Codex 做落盘；
8. 创建 runtime.py、hook runner、relay contract 或自动化 schema。

---

## 3. Relationship to Existing Workflow Assets

### 3.1 Relationship to `pm_runtime_instruction_v0.1.3.md`

本 skill 是 PM Runtime / Hermes 的子 skill 候选模块，用于补充 PM Runtime 在 workflow alignment / anti-drift 方面的轻量扫描能力。

若本 skill 与 `pm_runtime_instruction_v0.1.3.md` 冲突：

```text
HOLD_PM_RUNTIME_SKILL_CONFLICT
return_to: Owner-Control
```

PM Runtime 不得自行选择优先级。

### 3.2 Relationship to workflow_core

workflow_core 是当前治理基准，但不是不可挑战的永恒权威。

若发现冲突，应区分：

```text
A. 子 agent / skill 漂移
B. core outdated / incomplete
C. compact / YAML mismatch
D. path / status mismatch
E. insufficient evidence
```

PM Runtime 只能标记疑似问题，不得自行裁决谁对谁错。

### 3.3 Relationship to compact / YAML

compact 和 YAML 是运行索引 / checklist source，不是 workflow authority。

本 skill 应检查它们是否：

1. 与当前 workflow_core 口径一致；
2. 与实际 role instruction / skill 文件一致；
3. 没有把自己写成 authority；
4. 没有保留过期枚举、状态、任务等级或 HOLD 条件；
5. 需要随实践演进更新。

YAML 不应被视为静态快照，而应被视为需要持续维护的机器友好索引。

### 3.4 Relationship to existing governance skill

如果仓库中已经存在 adarian-workflow-governance skill 或类似 governance skill，本 skill 应被视为其 anti-drift / alignment 部分的候选扩展，而不是默认替代。

在正式 landing 前，必须完成一次对齐判断：

```text
merge / replace / split responsibility / keep as bootstrap candidate
```

---

## 4. No Hooks in v0.1.1

本版本不写 hook。

原因：

1. core 尚未修复完；
2. DS Team / Codex role files 尚未完整落位；
3. PM Runtime 子模块仍在配置中；
4. 当前规则尚未经过正式 repository-level review；
5. 现在写 hook 会过早固化未成熟规则；
6. 当前阶段需要先全局对齐，再局部自动化。

明确禁止在本版本新增：

```text
runtime.py
hook runner
relay_contract_v0.1.yaml
relay_runner_config_schema.yaml
自动扫描脚本
自动拦截器
```

未来是否加入 hook，应等以下条件满足后再判断：

1. workflow_core 修复完成；
2. PM Runtime 子 skill 基本落位；
3. DS Team / Codex role instruction 落位；
4. router 稳定；
5. 经过一次 formal alignment review；
6. Owner-Control 批准进入自动化设计。

---

## 5. Bootstrap Transitional Mode

在 DS Team / Codex 正式文件未落位前，允许继续使用旧工作流进行人工搬运。

临时规则：

1. Control Agent 继续负责判断、起草、修订、gate；
2. Owner 可以人工搬运 prompt / 文件 / report；
3. Hermes 只能做 lightweight scan / runtime feedback；
4. Hermes 不得把 lightweight scan 声称为 DS Team audit；
5. DS Team 需要人工触发时，由 Control Agent 给出窄边界 prompt；
6. Codex 需要人工触发时，由 Control Agent 给出窄边界 prompt；
7. 所有候选资产必须标注 pending formal DS-Codex alignment review。

---

## 6. Pre-Action Awareness

本 skill 不实现 pre-action gate，但必须显式提醒 PM Runtime：

在执行任何 Adarian workflow 相关动作前，先做最小自检：

```text
1. 这个任务属于哪个执行者？
2. PM Runtime 是否被允许直接做？
3. 这是 lightweight scan、runtime feedback，还是正式 audit？
4. 是否需要 DS Team？
5. 是否会产生 artifact？
6. artifact 是否需要落盘路径？
7. 若创建任务目录，domain 是否正确？
8. 输出是否会被误读为 final verdict / closeout？
```

若任一问题无法回答：

```text
HOLD_PRE_ACTION_UNCLEAR
return_to: Owner-Control
```

注意：这只是 awareness rule，不是 hook，不是自动化 gate。

---

## 7. Drift Types

### 7.1 Authority Drift

检查是否出现：

1. Hermes / PM Runtime 自称可以 closeout；
2. DS Team 自称可以 final gate；
3. Codex 自称可以批准版本完成；
4. compact / YAML 被写成 workflow authority；
5. candidate 被误标为 repository-landed。

### 7.2 Role Boundary Drift

检查是否出现：

1. PM Runtime 替 DS Team 做正式 audit；
2. DS Team 扩展 scope；
3. Codex 修改 forbidden files；
4. Control Agent 假装本地执行；
5. Owner 被迫承担流水线人工审计。

### 7.3 Status Drift

检查是否混用：

```text
draft
candidate
patched candidate
loaded
repository-landed
accepted
closeout
```

重点防止：

```text
文档正文完成 ≠ 已落盘
Hermes completed ≠ closeout
DS pass ≠ closeout
Codex delivered ≠ closeout
project memory updated ≠ repository file updated
```

### 7.4 Path Drift

检查：

1. 文档声称路径是否真实存在；
2. 任务目录 domain 是否正确；
3. PM Runtime 产物是否误放到 Control Agent domain；
4. `.claude/`、`.codex/`、`.hermes/` 真实配置路径是否与文档描述一致；
5. report / receipt / summary 是否有真实路径。

### 7.5 Capability Drift

检查：

1. 某个 agent 是否获得 core 未定义的新能力；
2. 该能力是合理演进还是越权；
3. 是否需要被提升为 core revision candidate；
4. 是否需要 Owner-Control 批准吸收。

### 7.6 Terminology Drift

检查术语是否混用：

```text
audit
scan
review
triage
verification
acceptance
receipt
report
summary
closeout
landing
loaded
```

### 7.7 Execution Drift

检查实际执行是否偏离角色边界：

1. Hermes 是否在该委派时直接审查；
2. Hermes 是否输出 artifact 但未落盘；
3. DS 是否未按 team mode / MCP 要求执行；
4. Codex 是否扩大 allowed files；
5. 是否出现无 task_id 的 dispatch；
6. 是否出现无 receipt 的完成声明。

### 7.8 Configuration Drift

检查真实配置文件是否口径一致：

```text
.claude/
.codex/
.hermes/
```

重点检查：

1. SKILL.md；
2. system prompt / role instruction；
3. agent-specific instruction；
4. workflow compact / YAML reference；
5. task routing rule；
6. closeout / gate / audit / receipt 权限描述。

---

## 8. When to Use This Skill

PM Runtime 可在以下场景进行 lightweight scan：

1. 新增或修改 workflow_core / compact / YAML；
2. 新增或修改 PM Runtime 子 skill；
3. 新增或修改 Control / DS / Codex / Hermes role instruction；
4. 发现 agent 行为与当前口径不一致；
5. 准备将 candidate 资产送入正式 review；
6. 准备让 Hermes / DS / Codex 加载新配置；
7. Owner 怀疑 core 落后或子 agent 漂移；
8. 出现 task directory routing 错误；
9. 出现 artifact 未落盘；
10. 出现越权审查、越权 closeout 或错误 verdict。

强制触发：

```text
每次准备把 bootstrap candidate 升级为 repository-landed candidate 前，必须至少做一次 alignment scan 或 DS review。
```

---

## 9. Checked Sources

轻量扫描的推荐对象：

```text
workflow_core.md
workflow_core_compact.md
workflow_compact_v*.yaml
control_agent_specific_instruction_*.md
pm_runtime_instruction_*.md
pm_runtime/skills/**/SKILL.md
.claude/**/SKILL.md
.codex/**/SKILL.md
.hermes/**/SKILL.md
docs/iterations/**
audit/tasks/**
```

如果真实路径不可见：

```text
do_not_guess
mark_as: path_not_verified
```

---

## 10. Lightweight Scan Output

PM Runtime lightweight scan 必须输出为文件，不应只放聊天。

推荐路径：

```text
audit/tasks/active/pm-runtime-governance/<short-task>/summary/<scan_name>_YYYY-MM-DD.md
```

最低字段：

```yaml
review_type: pm_runtime_lightweight_alignment_scan
task_id: <required>
reviewed_assets:
  - path: <path>
    status: verified | not_visible | not_checked
workflow_compact_yaml_used: true | false
yaml_sections_checked: []
suspected_drift:
  - type: authority | role_boundary | status | path | capability | terminology | execution | configuration
    evidence: <brief evidence>
    severity: P0 | P1 | P2 | P3
core_revision_candidate:
  exists: true | false
  reason: <why>
recommended_next_action:
  - hold
  - ds_repository_level_review
  - control_agent_revision
  - owner_decision
limitations:
  - <what could not be verified>
owner_control_required: true
```

---

## 11. DS Review Escalation

PM Runtime 必须建议触发 DS Team repository-level read-only review，当出现：

1. authority / closeout / final gate 冲突；
2. PM Runtime 是否越权不清；
3. DS / Codex / Hermes 真实配置与文档口径不一致；
4. core 可能落后但证据不足；
5. YAML 与 markdown workflow 资产冲突；
6. 真实路径不可见；
7. bootstrap candidate 准备进入正式 landing；
8. Hermes lightweight scan 发现 P0/P1 问题。

DS Team review 必须检查真实配置，不得只看文档候选稿。

推荐 DS review scope：

```text
.claude/
.codex/
.hermes/
pm_runtime/skills/
workflow_core*
workflow_compact*
workflow_compact_v*.yaml
agent-specific instructions
```

DS Team 可能结论：

```text
sub_agent_drift
core_outdated_or_incomplete
compact_yaml_mismatch
path_mismatch
status_mismatch
execution_behavior_drift
insufficient_evidence_hold
```

---

## 12. DS Dispatch Skeleton

当触发 DS Team 时，dispatch 必须包含 task_id。

```markdown
# DS Team Dispatch: Repository-Level Workflow Alignment Review

task_id: ds-workflow-alignment-review-<YYYYMMDD>-<slug>
task_level: M
mode: read_only_repository_level_review
team_mode_required: true
mcp_required: true

## Objective

Review workflow alignment and anti-drift consistency across core workflow documents, compact/YAML assets, agent role instructions, and actual agent skill/config files.

## Required Scope

- workflow_core*
- workflow_compact*
- workflow_compact_v*.yaml
- control_agent_specific_instruction*
- pm_runtime_instruction*
- pm_runtime/skills/**
- .claude/**
- .codex/**
- .hermes/**

## Key Questions

1. Are any sub-agent instructions drifting from the current governance baseline?
2. Is workflow_core outdated, incomplete, or inconsistent with validated practice?
3. Are compact and YAML being treated correctly as indexes/checklists rather than authorities?
4. Are DS Team, Codex, Hermes, and Control Agent boundaries consistent?
5. Are status terms such as candidate, loaded, landed, accepted, and closeout used consistently?
6. Are task directory domains and artifact path requirements clear?
7. Are there signs of runtime behavior drift from available logs/reports?

## Forbidden Actions

- Do not modify files.
- Do not make final closeout.
- Do not downgrade blockers.
- Do not assume missing paths do not exist.
- Do not treat this dispatch as permission to expand scope.

## Required Output

- Chinese Markdown report file.
- acceptance_verdict: pass | pass_with_known_issues | patch_required | hold | fail
- findings by severity.
- process_issues.
- blockers.
- core_revision_candidates.
- sub_agent_drift_candidates.
- report_path.
```

---

## 13. Core Revision Candidate Rule

PM Runtime may identify a suspected core revision candidate, but cannot approve it.

Valid core revision candidate examples:

1. PM Runtime skill has validated a useful capability not reflected in core;
2. core still describes an old process contradicted by current accepted workflow;
3. core blocks bootstrap setup in a way that causes self-lock;
4. core misses a newly confirmed role boundary;
5. core conflicts with actual project-level operating practice confirmed by Owner.

Invalid examples:

1. Hermes wants more authority;
2. Codex wants fewer constraints;
3. DS Team wants to bypass Owner-Control;
4. A one-off convenience workaround;
5. a behavior that lacks evidence.

All core revision candidates require:

```text
DS review
Owner-Control decision
explicit patch or revision plan
```

---

## 14. HOLD Conditions

PM Runtime must HOLD when:

1. suspected closeout authority conflict exists;
2. PM Runtime is asked to do DS-level audit;
3. dispatch lacks task_id;
4. artifact has no output path;
5. task directory domain is unclear;
6. true config paths are not visible;
7. core / compact / YAML / role instruction conflict cannot be classified;
8. bootstrap candidate is being treated as repository-landed;
9. Hermes lightweight scan is being treated as DS audit;
10. Owner approval is required but missing.

Recommended HOLD codes:

```text
HOLD_AUTHORITY_CONFLICT
HOLD_PM_RUNTIME_ROLE_BOUNDARY
HOLD_PATH_NOT_VERIFIED
HOLD_TASK_DOMAIN_UNCLEAR
HOLD_ARTIFACT_PATH_MISSING
HOLD_BOOTSTRAP_ASSET_NOT_READY
HOLD_CORE_REVISION_REQUIRES_OWNER
HOLD_DS_REVIEW_REQUIRED
```

---

## 15. Acceptance Criteria for This Skill

This skill is acceptable as a bootstrap candidate only if:

1. It does not define executable hooks;
2. It does not authorize PM Runtime to closeout;
3. It does not treat core as immutable truth;
4. It allows core outdated candidates to be raised with evidence;
5. It requires DS review for repository-level alignment;
6. It requires real configuration paths to be checked;
7. It distinguishes Hermes lightweight scan from DS Team audit;
8. It requires artifact output paths;
9. It requires task_id in DS dispatch;
10. It declares bootstrap candidate status clearly.

---

## 16. Next-Step Roadmap

Recommended order:

```text
1. Use this v0.1.1 as bootstrap candidate.
2. Continue manually搬运旧工作流，避免新系统自锁。
3. Rewrite / refine anti-drift skill only after Owner review.
4. Draft DS Team instruction candidate.
5. Draft Codex instruction candidate.
6. Complete PM Runtime sub-skill set.
7. Align with existing governance skill §6.
8. Run DS Team repository-level alignment review.
9. Prepare Codex first landing dispatch.
10. Owner-Control closeout.
```

---

## 17. Final Boundary

This skill helps the workflow system notice drift.

It does not decide the final truth.

Final authority remains:

```text
Owner-Control gate
with DS evidence
and Codex execution receipts
when the formal lane is ready.
```
