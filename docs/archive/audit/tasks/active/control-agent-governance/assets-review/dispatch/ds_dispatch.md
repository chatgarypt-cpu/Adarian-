# DS Agent Team Readonly Review — Control Agent Governance Assets Consistency & System Prompt Slimming

## 0. Hard Requirements

```yaml
task_id: v4.0-control-agent-governance-assets-ds-review-01
team_mode_required: true
mcp_required: true
readonly_review_only: true
file_modification_allowed: false
git_commit_allowed: false
```

If team mode cannot be started, stop immediately: `STOP_REASON: team_mode_not_available`

If MCP / file reading cannot be used, stop immediately: `STOP_REASON: mcp_not_available_or_file_unreadable`

Do not replace DS Agent Team review with single-agent skim review.

## 1. Objective

判断以下四类资产之间是否职责清晰、边界一致、权威关系正确，并重点评估 system prompt 是否过度膨胀、是否需要瘦身。

## 2. Review Materials

```
audit/workflow_v4.0/control agent context/workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
audit/workflow_v4.0/control agent context/workflow_core_compact_v4_0_R0.md
audit/workflow_v4.0/control agent context/control_agent_specific_instruction_v_4_r_0.2.md
audit/workflow_v4.0/control agent context/control_agent_system_prompt_v4_kernel_v0_2_1.md
```

如任一文件不可读取，必须 HOLD，并说明缺失文件、影响和补齐方式。

## 3. Background

已知事实：

- workflow_core v4.0 R2 仍是 draft / consistency-repaired snapshot，不是最终落盘版
- workflow_core_compact_v4_0_R0.md 已补齐，定位是人读运行小抄 / 作战地图，不是第二权威源
- control_agent_specific_instruction_v_4_r_0.2.md 已补入 Template / Asset Mode，但可能存在格式和内容结构问题
- control_agent_system_prompt_v4_kernel_v0_2_1.md 已补入自动启用 Control Agent 模式、compact-first、用户确认后全量交付、Hermes/PM Runtime first、大文本默认文件交付
- Owner 当前判断：v0.2.1 system prompt 很可能过度设计，超过 8k tokens，很多内容应下沉到 compact 或 Control Agent-specific instruction

同时吸收以下审查意见：

1. System prompt 不应成为 workflow_core 的压缩版
2. System prompt 只应保留底座命令和硬约束
3. workflow_core.md 管完整权威流程
4. workflow_core_compact.md 管快速索引、角色坐标、管线地图、红线清单、输出骨架
5. Control Agent-specific instruction 管网页端 Control Agent 的岗位行为细则
6. system prompt 必须能自动启用 Control Agent 模式，但不应重复展开全部角色职责
7. system prompt 必须写入 Hermes / PM Runtime first，避免 Control Agent 直接跳 DS / Codex
8. 用户确认后要给完整可复制内容，但大文本默认应以文件交付，不应只塞聊天超长代码块
9. 当前 system prompt v0.2.1 很可能过长，应审查哪些段落应保留、哪些应下沉、哪些应删除

## 4. Required Reviewer Agents

至少分为以下 5 个 reviewer：

```
1. Authority Alignment Reviewer
   — 审查 workflow_core / compact / role instruction / system prompt 的权威关系

2. System Prompt Minimalism Reviewer
   — 审查 system prompt 是否过长、是否重复 workflow_core 或角色卡

3. Control Agent Behavior Reviewer
   — 审查 system prompt 是否足以驱动 Control Agent 正常工作

4. Hermes-first Workflow Reviewer
   — 审查是否正确体现 PM Runtime / Hermes first 编排逻辑

5. Template / Asset Mode Reviewer
   — 审查模板化作业、确认后交付、大文本文件交付规则是否放在正确层级
```

DS 主控只做汇总、冲突消解和最终 verdict，不应替代各 reviewer 独立审查。

## 5. Required Review Questions

### 5.1 权威源关系

1. workflow_core.md、workflow_core_compact.md、Control Agent-specific instruction、system prompt 的权威关系是否清楚？
2. compact 是否被正确定位为作战地图，而不是第二权威源？
3. Control Agent-specific instruction 是否被正确定位为岗位说明书，而不是 workflow_core 替代品？
4. system prompt 是否误把 draft workflow_core 当作已正式落盘权威源？

### 5.2 System Prompt 是否过度设计

1. control_agent_system_prompt_v4_kernel_v0_2_1.md 是否明显过长？
2. 哪些段落应保留在 system prompt？
3. 哪些段落应下沉到 workflow_core_compact.md？
4. 哪些段落应下沉到 Control Agent-specific instruction？
5. 哪些段落应删除或合并？
6. 是否可以压缩到更适合作为 ChatGPT 系统提示词的长度？

### 5.3 System Prompt 必须保留的硬约束

请判断 system prompt 是否至少应保留以下内容：

1. ChatGPT 网页端 Control Agent 身份
2. 不是本地 runtime / Codex / Hermes / DS / shell
3. 自动启用 Control Agent 模式
4. compact-first 检索
5. workflow_core 是最终权威
6. 缺上下文不猜测，HOLD
7. Hermes / PM Runtime first for external work
8. 用户确认后给完整交付
9. 大文本默认文件交付
10. 最终 gate 不交给 Hermes / DS / Codex

请判断这些是否足够，是否还有必须保留项。

### 5.4 Compact 与角色卡承接关系

1. workflow_core_compact_v4_0_R0.md 是否足以承担「快速启动索引」职责？
2. control_agent_specific_instruction_v_4_r_0.2.md 是否足以承接 system prompt 中过重的行为细则？
3. Template / Asset Mode 应主要放在 role instruction，还是 system prompt 也需要保留最小触发规则？
4. Hermes-first 规则应在 system prompt、compact、role instruction 中如何分层？

### 5.5 格式与结构问题

1. control_agent_specific_instruction_v_4_r_0.2.md 中 Template / Asset Mode 代码块是否有未闭合或结构吞并问题
2. system prompt v0.2.1 是否因为长代码块影响复制和加载
3. 是否需要拆成四层结构：system prompt kernel / Control Agent role instruction / compact / workflow_core

### 5.6 Hermes-first 逻辑

1. system prompt v0.2.1 是否已经修复「直接跳 DS / Codex」的问题？
2. 是否还存在让 Control Agent 绕过 Hermes 的歧义？
3. 是否需要把「外部审查 / 执行 / 回收默认走 Hermes」写得更短、更硬？
4. 哪些细则应移到 compact 或 role instruction？

## 6. Expected Output

DS Team 应输出中文 Markdown 审查报告，并提供真实文件路径。

报告至少包含：

```yaml
task_id: v4.0-control-agent-governance-assets-ds-review-01
review_type: read_only_governance_asset_review
team_mode_used: true / false
mcp_used: true / false

reviewed_files:
  - workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
  - workflow_core_compact_v4_0_R0.md
  - control_agent_specific_instruction_v_4_r_0.2.md
  - control_agent_system_prompt_v4_kernel_v0_2_1.md

authority_alignment:
compact_alignment:
role_card_alignment:
system_prompt_readiness:
system_prompt_slimming_assessment:
hermes_first_alignment:
template_asset_mode_alignment:
format_issues:

findings:
  - id:
    severity: blocker / major / minor / note
    location:
    issue:
    recommendation:

recommended_layering:
  system_prompt_should_keep:
  move_to_compact:
  move_to_control_agent_role_card:
  move_to_workflow_core:
  delete_or_merge:

recommended_system_prompt_target:
  target_length:
  required_sections:
  optional_sections_to_remove:

process_issues:
blockers:
known_issues:
acceptance_verdict:
report_path:
```

`acceptance_verdict` 取值：`pass` / `pass_with_minor_patches` / `patch_required` / `hold` / `fail`

## 7. Output Files

Write report:
```
audit/tasks/active/control-agent-governance/assets-review/ds/ds_governance_assets_review.md
```

Write receipt:
```
audit/tasks/active/control-agent-governance/assets-review/ds/ds_receipt.yaml
```

## 8. Boundaries

**DO**:
- Read-only review of all 4 assets
- Use MCP filesystem tools
- Use multi-reviewer subagents (5+)
- Report authority conflicts, system prompt bloat, layering issues
- Output structured findings with specific locations and recommendations

**DO NOT**:
- Modify any file
- Make governance judgments beyond review scope
- Call Codex
- Start Codex landing
- Auto-promote findings to tasks
- Perform final closeout
