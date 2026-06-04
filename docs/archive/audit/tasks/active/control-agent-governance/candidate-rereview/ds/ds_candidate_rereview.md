# DS Team 候选稿只读复审报告

## Control Agent Governance Assets — Candidate Re-review

---

**复审编号**: v4.0-control-agent-assets-candidate-rereview-01
**复审类型**: read_only_governance_asset_rereview
**复审日期**: 2026-05-21
**复审方**: DS Team（Agent Team Mode，4 reviewer subagents）
**Team Mode Used**: true
**MCP Used**: true

---

## 一、复审概要

### 1.1 复审范围

| # | 文件 | 版本 | 定位 |
|---|------|------|------|
| 1 | `control_agent_system_prompt_v4_kernel_v0_3_slim_candidate.md` | v4 Kernel v0.3 Slim Candidate | 系统提示词内核 |
| 2 | `workflow_core_compact_v4_0_R0_1_candidate.md` | v4.0 R0.1 Candidate | 作战地图 / 快速索引 |
| 3 | `control_agent_specific_instruction_v4_0_R0_3_candidate.md` | v4.0 R0.3 Candidate | Control Agent 岗位说明书 |

### 1.2 审查依据

上一轮 DS 审查（`ds_governance_assets_review.md`）verdict: `patch_required`。本次复审仅验证修复状态，不重新展开完整大审计。

### 1.3 Reviewer Agent Team

| # | Reviewer | 职责 | Verdict |
|---|----------|------|---------|
| 1 | Format Reviewer | 代码块闭合、结构完整性 | pass |
| 2 | System Prompt Slimming Reviewer | 验证瘦身效果 | patch_required |
| 3 | Hermes-first Reviewer | 验证编排规则完整性 | pass |
| 4 | Layering / Authority Reviewer | 验证三层分工清晰度 | patch_required |

### 1.4 总体结论

**Acceptance Verdict: `pass_with_minor_patches`**

上一轮发现的 2 个 critical 阻断性格式问题（代码块未闭合 TAM-003/004）已完全修复。4 个 high 级别 P1 修复项（Hermes-first 缺失 HF-001、S-Level 冲突 HF-002、自授权漏洞 HF-003、file-first 缺失 TAM-008/TAM-010）全部到位。system prompt 瘦身完成约 70%（从 12K-18K tokens 压缩至约 3,000-3,500 tokens）。

剩余问题均为 minor 级别：system prompt 中 §8 输出骨架和 §4 HOLD 模板待进一步下沉，role instruction 缺少冲突解决声明，跨文件仍存在 7 处措辞重复可进一步精简。这些问题不构成阻断，可在正式落盘前顺手修补。

---

## 二、P0 修复验证

### 2.1 代码块闭合（原 TAM-003/004）

**状态: ✅ 已修复**

role instruction 候选稿（R0.3）共 11 个代码块，全部成对闭合。原 §6.4 区域已重构：旧的 §6.4.2-§6.4.9 子节移除，当前 §6.3 Template/Asset Mode 下的 5 个 H4 子节（§6.3.1-§6.3.5）各自独立，代码块均正确闭合。§6.4 Execution Mode 仅为一段纯文本段落，无代码块。

无任何章节被吸入代码块，所有标题可被正常解析。

### 2.2 结构完整性

**状态: ✅ 全部通过**

- system prompt: H1 + 9 个 H2（§1-§9），无跳级
- compact: H1 + 12 个 H2（§0-§11），含正确闭合的 mermaid 流程图
- role instruction: H1 + 17 个 H2（§0-§16），§6 下 4 个 H3 + 5 个 H4，无跳级

三份文件均无格式错乱、无多余/缺失分隔线、无缩进不一致。

---

## 三、P1 修复验证

### 3.1 System Prompt 结构性瘦身

**状态: ⚠️ 部分完成（约 70%）**

**已完成的瘦身：**
- ✅ 删除 §5 角色边界（原 5 个子节）
- ✅ 删除 §7 推进模式详细定义（4 种模式）
- ✅ 删除 §10 Execution Lock 条件
- ✅ 删除 §11 任务等级判断（S/M/L/Patch Lane）
- ✅ 删除 §12 Template 模板结构（与 role instruction 完全重复）
- ✅ 删除 §14 Owner 传达职责
- ✅ 删除 §15 文档职责
- ✅ 删除 §16 输出风格
- ✅ 删除 §18 自检清单
- ✅ 权威源关系简化为简表

**仍需修补：**
- ⚠️ §8 输出骨架（~500 字符）仍完整保留了 3 套输出模板，属于应下沉到 role instruction 的内容
- ⚠️ §4 缺上下文处理 保留了完整 HOLD 输出模板（5 行固定格式），建议仅保留判断逻辑
- ⚠️ §2 仍残留一行信息来源清单（"只基于：ChatGPT 项目资料来源..."）

**Token 估算：**
- 候选稿字符数：约 4,200 字符
- 估计 token 数：约 3,000-3,500 tokens
- 目标范围：1,500-2,500 tokens
- 超出上限约 40-50%
- 完成上述修补后预计可降至 2,000-2,500 tokens

### 3.2 System Prompt 是否只保留运行内核和硬约束

**状态: ⚠️ 基本合格**

候选稿结尾明确声明"本 system prompt 只保留运行内核和硬约束"，并提供兜底指引指向详细规则由 workflow_core/compact/role instruction 承载。但 §8 输出骨架的存在使声明与实际内容存在张力——输出格式模板不属于运行内核。

### 3.3 Role Instruction Hermes-first（原 HF-001）

**状态: ✅ 已修复**

role instruction 新增完整的 §9 "Hermes / PM Runtime First"：
- 明确声明"外部审查、执行、验收、回收、长程任务或多 Agent 协作时，默认路径是："
- 完整描述 5 步默认路径
- 补齐 4 条绕过条件
- 补齐 Hermes dispatch 最小 13 字段
- 补齐禁止自授权条款

### 3.4 Role Instruction File-first（原 TAM-008/TAM-010）

**状态: ✅ 已修复**

role instruction 新增 §6.3.4 "File-first 大文本交付"，明确规定了 system prompt、role card、compact、模板、任务卡、dispatch、长 prompt、长报告等大文本默认生成可下载 MD/TXT 文件，聊天中只给摘要/链接/版本号。

compact 新增 §9 "大文本交付索引" 作为补充。

### 3.5 Compact Hermes-first（原 HF-004）

**状态: ✅ 已修复**

compact 新增独立的 §4 "Hermes-first 快速规则"：
- 明确的文本开头："外部审查、外部执行、验收、回收、长程任务、多 Agent 协作，默认先走："
- 完整的 5 步默认路径
- 完整的 4 条直达例外
- 附禁止自授权条款
- §11 最小记忆句也包含"外部任务默认先走 Hermes / PM Runtime 编排"

### 3.6 S-Level 与 Hermes-first 冲突（原 HF-002）

**状态: ✅ 已修复**

role instruction §8 和 compact §6 的 S-Level 规则已从原来的并列表述"优先 DS / Hermes"修改为层级表述：
> "如需外部审查或回收，优先由 Hermes 派发 DS Team；只有无需 receipt 回收的一次性轻量任务，才可直达。"

system prompt 的 bypass 条件 #2 与此一致："S-Level 一次性轻量转交，且不需要 receipt / summary 回收"。

### 3.7 自授权漏洞（原 HF-003）

**状态: ✅ 已修复**

- system prompt §6：旧的第 5 条绕过条件"当前任务卡允许直达执行方"已删除
- 绕过条件从 5 条精确缩减为 4 条
- 新增明确禁止条款："不得用'当前任务卡允许直达'作为自授权理由"
- 附加兜底声明："即使直达，也必须说明：这是直达模式，不代表 closeout，不替代 Owner-Control gate"
- role instruction §9 和 compact §4 均同步了同一禁止条款

---

## 四、三层分工验证

### 4.1 各层定位

| 层级 | 文件 | 定位 | 自我声明 | 评价 |
|------|------|------|---------|------|
| 运行内核 | system prompt | 运行内核 / 硬约束 | "本 system prompt 只保留运行内核和硬约束" | ✅ 定位正确，但 §8 输出骨架超出范围 |
| 作战地图 | compact | 作战地图 / 快速索引 | "不是第二个 workflow_core.md，不是第二权威源" | ✅ 定位最清晰 |
| 岗位说明书 | role instruction | Control Agent 岗位行为 | "workflow_core.md 管完整规则；compact 负责快速调动；本文件只管 Control Agent 行动" | ✅ 定位正确 |

### 4.2 权威关系一致性

| 规则 | system prompt | compact | role instruction |
|------|:---:|:---:|:---:|
| 权威链声明 | ✅ §2 | ✅ §0 | ✅ §0 |
| compact 与 workflow_core 冲突 → 以 workflow_core 为准 | ✅ §2 | ✅ §0 | ⚠️ 缺失 |
| 三者冲突 → HOLD，回 Owner-Control | ✅ §2 | ⚠️ 未显式声明三者冲突规则 | ⚠️ 缺失 |
| 当前 workflow_core 若是 draft 不得当作正式权威 | ✅ §2 | ✅ §0 | ✅ §0 |
| 自身 draft/candidate 状态标注 | ⚠️ 缺失 | ✅ 标题 + §0 | ✅ 标题 + §0 |

### 4.3 跨文件重复

| ID | 严重度 | 重复内容 | 涉及文件 |
|----|--------|---------|---------|
| DUP-001 | medium | Hermes-first 默认路径 + 4 条例外（措辞几乎一字不差） | SP §6 + Compact §4 + RI §9 |
| DUP-002 | medium | Gate 严禁误判 8 条清单 | SP §7 + RI §10 |
| DUP-003 | medium | 输出骨架 3 套模板 | SP §8 + Compact §8 + RI §14 |
| DUP-004 | medium | 最重要行为准则 / 最小记忆句 | SP §9 + Compact §11 + RI §16 |
| DUP-005 | low | HOLD 输出 5 字段格式 | SP §4 + Compact §7 |
| DUP-006 | low | 用户确认后交付规则 | SP §5 + RI §6.3.3 |
| DUP-007 | low | 任务等级速判 S/M/L/Patch | Compact §6 + RI §8 |

**说明**: DUP-007 属于合理的分层重复（compact 为速查，RI 为岗位行为）。DUP-001 至 DUP-004 建议在正式落盘前清理：system prompt 中的完整措辞可缩减为一句硬约束 + 指针。

---

## 五、Hermes-first 一致性矩阵（更新后）

| 规则 | system prompt | role instruction | compact |
|------|:---:|:---:|:---:|
| 默认路径定义 | 完整 (§6) | 完整 (§9) | 完整 (§4) |
| 绕过条件（4条） | 完整 (§6) | 完整 (§9) | 完整 (§4) |
| 编排最小输出字段（13字段） | 委托给 RI | 完整 (§9) | Hermes 回收字段 (§8) |
| 外部审查默认走 Hermes | 完整 (§6) | 完整 (§9) | 完整 (§4) |
| 外部执行默认走 Hermes | 完整 (§6) | 完整 (§9) | 完整 (§4) |
| 不得误判清单 | 完整 (§7, 8项) | 完整 (§10, 8项) | 完整 (§7+§10) |
| 禁止自授权 | 完整 (§6) | 完整 (§9) | 完整 (§4) |
| File-first 大文本交付 | 完整 (§5) | 完整 (§6.3.4) | 完整 (§9) |

**结论**: 上一轮矩阵中所有标记为"缺失"或"部分"的格子，本轮已全部补齐。三份候选稿在 Hermes-first 编排规则上已对齐。

---

## 六、残余发现

### 6.1 Blockers

**无阻断性 blocker**。所有 critical/high 级别问题已修复。

### 6.2 Remaining Findings

| ID | 严重度 | 类别 | 位置 | 问题 | 建议 |
|----|--------|------|------|------|------|
| RF-001 | medium | 瘦身未完成 | SP §8 | 输出骨架（3 套模板）应下沉到 role instruction | 删除 SP §8，在 RI §14 保留为唯一权威 |
| RF-002 | medium | 瘦身未完成 | SP §4 | HOLD 输出模板（5 字段）应下沉到 role instruction | 仅保留判断逻辑，模板下沉 |
| RF-003 | medium | 权威缺失 | RI §0 | 缺少冲突解决声明（"若与 workflow_core 冲突，以 workflow_core 为准"） | 在 RI §0 补齐 |
| RF-004 | medium | 权威缺失 | Compact §0 | 缺少三者冲突规则（"若 workflow_core/compact/RI 三者冲突，HOLD"） | 在 Compact §0 补齐 |
| RF-005 | low | 重复 | SP §6 + Compact §4 + RI §9 | Hermes-first 路径 + 4 条例外三份完全重复 | SP 缩减为硬约束 + 指针 |
| RF-006 | low | 重复 | SP §7 + RI §10 | Gate 严禁误判 8 条清单重复 | 保留 SP 为硬约束版，RI 引用 SP |
| RF-007 | low | 重复 | SP §9 + Compact §11 + RI §16 | 最重要行为准则三段几乎相同 | 保留 Compact §11 为唯一"最小记忆句" |
| RF-008 | low | 状态标注 | SP 正文 | system prompt 缺少对自身 draft/candidate 状态的标注 | 在 SP 开头增加状态行 |
| RF-009 | note | Token | SP 全文 | Token 仍超出推荐范围上限约 40% | 完成 RF-001/002/005/006 后可进入范围 |

---

## 七、过程问题

| ID | 问题 | 严重度 |
|----|------|--------|
| PRC-001 | 4 个 reviewer subagent 均成功启动并完成独立审查 | 正常 |
| PRC-002 | MCP filesystem 工具成功用于全部 3 个候选稿文件读取 | 正常 |
| PRC-003 | Layering/Authority Reviewer 返回内容被截断（DUP-007 描述不完整），但不影响核心判断 | note |

---

## 八、最终判定

### 8.1 Acceptance Verdict

**`pass_with_minor_patches`**

### 8.2 理由

1. **P0 阻断性问题已修复**：role instruction 代码块全部闭合，结构完整性通过
2. **P1 核心修复项全部到位**：Hermes-first（HF-001/004）、S-Level 冲突（HF-002）、自授权漏洞（HF-003）、file-first（TAM-008/TAM-010）均已修复
3. **System prompt 瘦身有实质进展**：从 12K-18K tokens 压缩至约 3,000-3,500 tokens（压缩比 ~75%）
4. **三层分工基本清晰**：各文件自我定位正确，权威链一致
5. **剩余问题为 minor 级别**：8 个残余发现均为 medium/low/note，不构成阻断，可在正式落盘前顺手修补

### 8.3 与上一轮对比

| 指标 | 上一轮 | 本轮 | 变化 |
|------|--------|------|------|
| Critical | 2 | 0 | ✅ 清零 |
| High | 4 | 0 | ✅ 清零 |
| Major | 3 | 4 (medium) | ⬇️ 降级 |
| Medium | 8 | 4 | ⬇️ 减半 |
| Low/Note | 16 | 5 | ⬇️ 大幅减少 |
| SP Token 估算 | 12K-18K | 3K-3.5K | ⬇️ ~75% |
| Verdict | patch_required | pass_with_minor_patches | ⬆️ 提升一级 |

### 8.4 建议修补清单（落盘前顺手完成）

1. **SP §8 输出骨架** → 下沉到 RI §14（可节省 ~400 tokens）
2. **SP §4 HOLD 输出模板** → 仅保留判断逻辑，5 字段模板下沉到 RI
3. **RI §0 补齐冲突解决声明**
4. **Compact §0 补齐三者冲突规则**
5. **SP 增加自身 draft/candidate 状态标注**
6. **SP 中 Hermes-first 路径缩减为一句话 + 指针**（去 DUP-001 重复）

完成以上 6 项修补后，预计 system prompt token 可降至 2,000-2,500 tokens，跨文件重复减少约 40%，即可记为 clean pass。

---

## 九、报告元数据

```yaml
task_id: v4.0-control-agent-assets-candidate-rereview-01
review_type: read_only_governance_asset_rereview
team_mode_used: true
mcp_used: true
reviewers:
  - Format Reviewer
  - System Prompt Slimming Reviewer
  - Hermes-first Reviewer
  - Layering / Authority Reviewer
reviewed_files:
  - control_agent_system_prompt_v4_kernel_v0_3_slim_candidate.md
  - workflow_core_compact_v4_0_R0_1_candidate.md
  - control_agent_specific_instruction_v4_0_R0_3_candidate.md
total_findings: 9
critical: 0
high: 0
medium: 4
low: 4
note: 1
acceptance_verdict: pass_with_minor_patches
report_path: audit/tasks/active/control-agent-governance/candidate-rereview/ds/ds_candidate_rereview.md
receipt_path: audit/tasks/active/control-agent-governance/candidate-rereview/ds/ds_receipt.yaml
```

---

**复审完成。不执行 closeout，不修改任何文件，交由 Owner-Control 判断下一步。**
