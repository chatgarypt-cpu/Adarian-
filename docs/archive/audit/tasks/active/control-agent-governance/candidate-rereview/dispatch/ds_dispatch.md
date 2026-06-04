# DS Agent Team Readonly Re-review — Control Agent Governance Assets Candidate Review

## 0. Hard Requirements

```yaml
task_id: v4.0-control-agent-assets-candidate-rereview-01
team_mode_required: true
mcp_required: true
readonly_review_only: true
file_modification_allowed: false
git_commit_allowed: false
```

## 1. Objective

对以下三份修复后候选稿做轻量只读复审，验证上一轮审查发现的问题是否已修复。

## 2. Review Materials

```
audit/workflow_v4.0/control agent context/adarian_control_agent_governance_assets_candidates_2026_05_21/control_agent_system_prompt_v4_kernel_v0_3_slim_candidate.md
audit/workflow_v4.0/control agent context/adarian_control_agent_governance_assets_candidates_2026_05_21/workflow_core_compact_v4_0_R0_1_candidate.md
audit/workflow_v4.0/control agent context/adarian_control_agent_governance_assets_candidates_2026_05_21/control_agent_specific_instruction_v4_0_R0_3_candidate.md
```

Reference: previous DS review at `audit/tasks/active/control-agent-governance/assets-review/ds/ds_governance_assets_review.md`

## 3. Background

上一轮 DS 审查 verdict: `patch_required`。关键问题包括：
- system prompt 过度膨胀（84% 冗余，12K-18K tokens）
- role instruction §6.4 代码块未闭合
- role instruction 缺少 Hermes-first
- compact 缺少 Hermes-first 文本规则
- role instruction 缺少 file-first 大文本交付
- system prompt 存在"当前任务卡允许直达"自授权漏洞
- 派生资产需标注 candidate

三份候选稿为修复后版本，本次只做复审，不重新展开完整大审计。

## 4. Reviewer Agents

```
1. Format Reviewer — 检查代码块闭合、结构完整性
2. System Prompt Slimming Reviewer — 验证瘦身效果
3. Hermes-first Reviewer — 验证编排规则完整性
4. Layering / Authority Reviewer — 验证三层分工清晰度
```

## 5. Review Focus (仅复审以下事项)

### P0 修复验证
- role instruction Template / Asset Mode 代码块是否已闭合

### P1 修复验证
- system prompt 是否完成结构性瘦身
- system prompt 是否只保留运行内核和硬约束
- role instruction 是否补齐 Hermes-first
- role instruction 是否补齐 file-first 大文本交付
- compact 是否补齐 Hermes-first 快速规则
- S-Level 与 Hermes-first 是否不再冲突
- "当前任务卡允许直达"自授权漏洞是否已删除

### 三层分工
- system prompt = 运行内核 / 硬约束
- compact = 作战地图 / 快速索引
- role instruction = Control Agent 岗位说明书

### 残余 blocker 检查
- 是否存在无法加载、无法复制、结构错乱、权威关系冲突、重复过多、明显过长

## 6. Expected Output

Write report:
```
audit/tasks/active/control-agent-governance/candidate-rereview/ds/ds_candidate_rereview.md
```

Write receipt:
```
audit/tasks/active/control-agent-governance/candidate-rereview/ds/ds_receipt.yaml
```

Report must include:
```yaml
task_id: v4.0-control-agent-assets-candidate-rereview-01
review_type: read_only_governance_asset_rereview
team_mode_used:
mcp_used:
reviewed_files: [...]
p0_status:
p1_status:
system_prompt_slimming_verdict:
hermes_first_alignment:
file_first_alignment:
layering_alignment:
remaining_findings:
blockers:
process_issues:
acceptance_verdict:  # pass / pass_with_minor_patches / patch_required / hold / fail
report_path:
receipt_path:
```

## 7. Boundaries

**DO**: Read-only re-review, MCP + team mode, verify fixes
**DO NOT**: Modify files, call Codex, closeout, git commit
