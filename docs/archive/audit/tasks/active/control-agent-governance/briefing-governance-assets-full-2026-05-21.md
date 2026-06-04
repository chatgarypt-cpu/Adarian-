# Control Agent Briefing — workflow_core v4.0 Governance Assets 全量审查汇总

> 文档类型：ControlContextPacket / Owner-Control 过渡期简报
> 目标读者：Control Agent（ChatGPT 网页端）
> 生成方：Hermes-PM
> 日期：2026-05-21
> 状态：transitional / 不替代 workflow_core.md

---

## 0. 本文件是什么

汇总以下全部审查和补充，供 Control Agent 一次性了解当前 v4.0 治理资产的全貌：

1. R2 三线审查（A/B/C）结论
2. Control Agent Governance Assets 两轮 DS 审查（33+6 项发现）
3. 候选稿 vs R2 总纲领交叉分析（1 处矛盾 + 10 项 R2 缺失）
4. Owner Directive：PM Runtime 通讯修复边界
5. Owner Directive：Control Agent / Hermes PM 传达职责
6. 命名规范变更（两级目录）
7. 当前所有资产文件路径索引

---

## 1. R2 三线审查结论（2026-05-19）

| 线 | verdict | 关键发现 |
|---|---------|---------|
| A线 — R2 结构审查 | PASS_WITH_MINOR_NOTES | 1 个格式缺陷（§10→§11 缺 `---`），21/21 必检通过 |
| B线 — 上线准备度 | READY_AFTER_CONTROL_AGENT_PATCH | Control Agent 必须先对齐 v4.0，14 项缺失产物 |
| C线 — 落盘执行计划 | LANDING_PLAN_READY_WITH_CONDITIONS | 第一批仅覆盖 workflow_core.md，23 forbidden files，C0 commit |

---

## 2. Control Agent Governance Assets 第一轮 DS 审查（2026-05-21）

**审查对象**：
- `workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md`
- `workflow_core_compact_v4_0_R0.md`
- `control_agent_specific_instruction_v_4_r_0.2.md`
- `control_agent_system_prompt_v4_kernel_v0_2_1.md`

**Verdict: `patch_required`** — 33 项发现（2 critical, 4 high, 3 major, 8 medium）

### Critical 发现（2 项，已修复）

| ID | 问题 | 位置 |
|----|------|------|
| TAM-003 | 代码块未闭合 | role instruction §6.4 L367 |
| TAM-004 | 结构吸入，§6.4.2-§6.4.9 全部被吞入代码块 | role instruction §6.4 L390-581 |

### High 发现（4 项，已修复）

| ID | 问题 |
|----|------|
| TAM-007 | system prompt §12 与 role instruction §6.4.5 完全重复 |
| TAM-008 | role instruction 缺少 file-first 大文本交付规则 |
| HF-001 | role instruction 缺少 Hermes-first 定义 |
| HF-002 | S-Level 与 Hermes-first 冲突（"优先 DS / Hermes"并列无层级） |

### System Prompt 膨胀评估

- 当前：12K-18K tokens → 建议：1.5K-2.5K tokens
- 84% 内容与其他资产重复
- 19 个章节中：4 个保留、9 个下沉到 role card、4 个下沉到 compact、2 个删除

---

## 3. Control Agent Governance Assets 第二轮复审（2026-05-21）

**审查对象**（修复后候选稿）：
- `control_agent_system_prompt_v4_kernel_v0_3_slim_candidate.md`（178行）
- `workflow_core_compact_v4_0_R0_1_candidate.md`（210行）
- `control_agent_specific_instruction_v4_0_R0_3_candidate.md`（302行）

**Verdict: `pass_with_minor_patches`**（较上轮提升一级）

### 修复确认

| 审查维度 | 状态 |
|---------|------|
| P0 格式修复 | ✅ 代码块已闭合 |
| System Prompt 瘦身 | ⚠️ 6 项 minor 待收尾 |
| Hermes-first 补齐 | ✅ 三份资产均有完整规则 |
| S-Level 冲突 | ✅ 已修复 |
| 自授权漏洞 | ✅ 已删除 |
| File-first 交付 | ✅ 已补齐 |
| 三层分工 | ✅ 清晰 |

### 剩余 minor（6 项，不阻塞）

- SP §4 HOLD 输出模板待下沉到 role instruction
- SP §8 输出骨架待下沉
- Compact §0 缺少三者冲突规则显式声明
- 跨文件 7 处措辞重复可进一步精简
- 版本号体系待统一
- 自检清单跨文件待统一为 19 项版

---

## 4. 候选稿 vs R2 总纲领交叉分析

### 矛盾：1 处

**S-Level 路由规则**：
- R2 §8.2：`"S-Level：优先 DS / Hermes 做只读回收"` — 并列，无层级
- 候选人：`"S-Level 如需外部审查或回收，优先由 Hermes 派发 DS Team"` — 明确 Hermes→DS 层级

→ 候选人已修复，R2 需同步。

### R2 缺失内容：10 项

| # | 缺失项 | 重要性 |
|---|--------|--------|
| 1 | Hermes-first 显式默认声明 | **high** |
| 2 | "不得用当前任务卡自授权"反模式 | **high** |
| 3 | File-first 大文本交付规则 | **high** |
| 4 | 三者冲突解决（workflow_core / compact / role instruction） | medium |
| 5 | Draft 治理资产处理规则 | medium |
| 6 | Agent 系统位置总表 | medium |
| 7 | 场景触发器 | low |
| 8 | 标准交付物格式速查 | low |
| 9 | Closeout 反模式紧凑清单 | low |
| 10 | Owner 传达固定模板 | low |

前三项建议补入 R2。其余是 compact/role instruction 层面的操作细则。

---

## 5. Owner Directive：PM Runtime 通讯修复边界（2026-05-19）

Hermes-PM 可在 `audit/tasks/active/<task>/` 下执行 task-local repair：

**允许**：修 relay_runner、JSON 提取、heartbeat/progress/result、重提取已完成 agent 输出、补写 runtime_note/process_issue、生成 pm_runtime_summary、重试通讯通道

**禁止**：改 src/、tests/、main.py、config.py、workflow_core.md、迭代文档、contracts、git commit

**硬规则**：
1. 修通讯不修源码
2. 修 relay 不修业务逻辑
3. 回收报告不修改结论
4. 标记 process_issue 不降级 blocker
5. 越界立即 HOLD 回 Owner-Control
6. 所有 repair 必须在 pm_runtime_summary 披露

---

## 6. Owner Directive：Control Agent / Hermes PM 传达职责（2026-05-19）

### Control Agent 必须明确告知 Owner
- 当前状态、当前阶段、当前 blocker、唯一下一步、执行方、是否需要批准

### Control Agent 必须输出可执行文本
- Hermes dispatch prompt / DS Team prompt / Codex execution prompt，不抽象建议

### 固定输出模板
```
当前状态：
当前阶段：
当前 blocker：
唯一下一步：
执行方：
是否需要 Owner 批准：
完整 prompt：
```

### Hermes PM 固定汇报
```
当前运行状态：
已完成任务：
阻塞任务：
产物路径：
是否需要 Owner 决策：
推荐唯一下一步：
```

### Closeout 不等于完成
Hermes completed ≠ closeout / DS pass ≠ closeout / Codex delivered ≠ closeout
所有执行结果必须由 Control Agent 转译为 Owner 可判断的下一步。

---

## 7. 命名规范变更

任务目录从扁平改为两级结构：

```
之前：audit/tasks/active/v4.0-workflow-r2-ds-review-01/
之后：audit/tasks/active/workflow-v4-landing/A-r2-review/

模式：audit/tasks/active/<domain>/<short-task>/
```

当前 domain：`control-agent-governance/`
- `assets-review/` — 第一轮 DS 审查
- `candidate-rereview/` — 第二轮复审

---

## 8. 当前所有资产文件路径索引

### 权威源

| 文件 | 路径 |
|------|------|
| v3 现行权威 | `docs/skills/workflow_core.md` |
| v4.0 R2 草案 | `audit/workflow_v4.0/control agent context/workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md` |
| v4.0 执行计划 | `audit/workflow_v4.0/workflow_core_v4_r2_review_and_landing_execution_plan_revised_2026-05-19.md` |

### 候选稿（待 Owner 确认后落盘）

| 文件 | 路径 |
|------|------|
| System Prompt v0.3 slim | `audit/workflow_v4.0/control agent context/adarian_control_agent_governance_assets_candidates_2026_05_21/control_agent_system_prompt_v4_kernel_v0_3_slim_candidate.md` |
| Compact R0.1 | `.../workflow_core_compact_v4_0_R0_1_candidate.md` |
| Role Instruction R0.3 | `.../control_agent_specific_instruction_v4_0_R0_3_candidate.md` |

### 三线审查产物

| 线 | 报告 | 回执 |
|---|------|------|
| A线 | `audit/tasks/active/workflow-v4-landing/A-r2-review/ds/ds_review_report_workflow_core_v4_r2_2026-05-19.md` | `.../ds/ds_receipt.yaml` |
| B线 | `.../B-rollout-readiness/summary/workflow_rollout_readiness_report_2026-05-19.md` | `.../runtime/result.yaml` |
| C线 | `.../C-landing-execution/summary/workflow_landing_execution_plan_review_2026-05-19.md` | `.../runtime/result.yaml` |

### Governance Assets 审查产物

| 轮次 | 报告 | 回执 |
|------|------|------|
| 第一轮 | `audit/tasks/active/control-agent-governance/assets-review/ds/ds_governance_assets_review.md` | `.../ds/ds_receipt.yaml` |
| 第二轮 | `audit/tasks/active/control-agent-governance/candidate-rereview/ds/ds_candidate_rereview.md` | `.../ds/ds_receipt.yaml` |

### 上下文包

| 文件 | 路径 |
|------|------|
| Control Agent v3→v4 过渡上下文包 | `audit/tasks/active/workflow-v4-landing/control-context-packet/summary/control_agent_v3_to_v4_context_packet_2026-05-19.md` |
| 本文件 | `audit/tasks/active/control-agent-governance/briefing-governance-assets-full-2026-05-21.md` |

### PM Runtime 摘要

| 文件 | 路径 |
|------|------|
| workflow-v4-landing 执行摘要 | `audit/tasks/active/workflow-v4-landing/pm_runtime_summary.md` |

---

## 9. 当前状态与推荐下一步

### 当前状态
- R2 草案：A线 PASS_WITH_MINOR_NOTES，可进入 Codex landing
- 三份候选稿：第二轮复审 PASS_WITH_MINOR_PATCHES，6 项 minor 不阻塞
- B线 blocker：Control Agent 必须先对齐 v4.0（当前通过本简报和上下文包完成）

### 推荐路径
1. Owner-Control 确认三份候选稿
2. 修复 6 项 minor → clean pass
3. R2 草案补入 3 项 high 缺失 → 更新 R2
4. Owner 批准 Codex first landing（仅 `docs/skills/workflow_core.md`）
5. 候选稿转为正式 → 落盘到对应路径
