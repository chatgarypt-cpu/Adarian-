# PM Runtime Skill Review: Workflow Alignment and Anti-Drift Governance

> review_type: PM Runtime lightweight alignment scan (not DS Team audit)
> reviewed_versions: v0.1 → v0.1.1
> reviewed_files:
>   - docs/skills/workflow_v4.0/pm_runtime/SKILL/pm_runtime_workflow_alignment_antidrift_SKILL_v0.1.md （已删除）
>   - docs/skills/workflow_v4.0/pm_runtime/SKILL/pm_runtime_workflow_alignment_antidrift_SKILL_v0.1.1.md （当前）
> reviewed_at: 2026-05-22
> reviewer: Hermes / PM Runtime
> status: draft scan, not final verdict
> pm_runtime_instruction_version: v0.1.3
> task_domain_moved_from: control-agent-governance （错误路由记录）

---

## 0. Overall Assessment

### v0.1 初评

定位清晰、边界明确、结构完整。8 种 drift 类型覆盖面广，HOLD 条件和 DS 升级规则务实。
§4 No Hooks 决策正确。发现 12 项缺漏和待改进点。

### v0.1 → v0.1.1 变化

v0.1.1 修补了 12 项中的 **7 项完全修复** + **2 项部分改进**。同时新增了 Bootstrap Status（§0）、
Pre-Action Awareness（§6）、吸收今天事故的 Execution Drift 检查项（§7.7），方向正确。

剩余 2 项未修复 + 1 项新增发现（MCP 工具上下文缺口）。

---

## 1. v0.1 原始 Findings 的修补状态

### P0 — 已全部修复

| # | 问题 | v0.1.1 状态 | 说明 |
|---|------|-----------|------|
| P0-1 | 缺与 governance skill §6 联动 | ✅ 修复 | §3.4 明确关系 + §16 step 7 |
| P0-2 | 缺与 pm_runtime_instruction 关系声明 | ✅ 修复 | §3.1 + 冲突规则 = HOLD |
| P0-3 | DS dispatch 缺 task_id | ✅ 修复 | §12 已加 task_id + task_level |

### P1 — 全部有改进

| # | 问题 | v0.1.1 状态 | 剩余 gap |
|---|------|-----------|---------|
| P1-1 | 缺 YAML 消费规则引用 | ⚠️ 部分 | §3.3 说了 YAML 需要维护，但没引用 v0.1.3 §3.1 的 10 条具体消费规则 |
| P1-2 | YAML 维护设计缺失 | ⚠️ 改进中 | §3.3 从"静态快照"升级到"需持续维护"+5 条检查点。方向正确，缺具体触发条件 |
| P1-3 | 缺输出路径 | ✅ 修复 | §10 指定路径 + "必须输出为文件，不应只放聊天" |

### P2 — 一项修复，两项未修复

| # | 问题 | v0.1.1 状态 | 说明 |
|---|------|-----------|------|
| P2-1 | 触发条件太软 | ✅ 修复 | §8 新增强制触发（candidate→landed 前必须 scan） |
| P2-2 | 缺 Hermes 工具操作指引 | ❌ 未修复 | 全文仍然零条 search_files/read_file/skill_view 用法 |
| P2-3 | 缺 drift 检测操作方法 | ⚠️ 部分 | §7 加了检查清单（有"查什么"），但没"怎么查"（工具路径） |

### P3 — 一项修复，一项未修复

| # | 问题 | v0.1.1 状态 | 说明 |
|---|------|-----------|------|
| P3-1 | 缺版本兼容声明 | ❌ 未修复 | 仍无 compatible_workflow_core / requires_yaml_version |
| P3-2 | §16 漏对齐步骤 | ✅ 修复 | §16 step 7 |

### Summary

```
v0.1 共 12 项 findings
├── ✅ 完全修复: 7 项 (P0-1/2/3, P1-3, P2-1, P3-2)
├── ⚠️ 部分改进: 2 项 (P1-1, P1-2)
└── ❌ 未修复:   2 项 (P2-2, P3-1)
```

---

## 2. v0.1.1 新增发现

### P2-4（新增）：MCP 工具上下文缺口 — scan 范围与执行者能力 mismatch

**发现过程**：在执行审查过程中，发现 anti-drift skill §9 Checked Sources 列出了
`.claude/`、`.codex/`、`.hermes/` 作为扫描目标，但 Hermes 实际能读到的路径和 skill 设计
之间存在结构性缺口。

**实际情况**：

| 路径 | 项目内存在？ | Hermes (read_file) | DS Team (MCP filesystem) |
|------|------------|-------------------|--------------------------|
| `.claude/` | ✅ | ✅ 可读 | ✅ 已白名单（settings.local.json L12-16） |
| `.codex/` | ❌ 不存在 | ❌ | ❌（Codex 配置在 `~/.codex/`） |
| `.hermes/` | ❌ 不存在 | ❌ | ❌（Hermes 配置在 `~/.hermes/`） |

**问题**：
1. Hermes 的 `read_file` 能读 `.claude/`，但不能跨到 `~/.codex/` 或 `~/.hermes/`
2. `.codex/` 和项目级 `.hermes/` 不存在，Codex/Hermes 真实配置在 home 目录下
3. Hermes 在执行 scan 时没有做路径可达性自检，默认自己能读到所有
4. DS Team 有 MCP 工具能跨路径读，但不能被持续调用（需显式 dispatch）
5. 结果：Configuration Drift（§7.8）检查形同虚设——检查者读不到被检查对象

**影响**：这是结构性 mismatch。Anti-drift skill 的设计意图是扫真实配置，但执行者
（Hermes）缺 MCP 工具。如果用 DS Team 做 scan，成本高且不能持续；用 Hermes 做 scan，
覆盖不全。

**建议修复方向**：
1. 给 Hermes 配 MCP filesystem 服务器（`native-mcp` skill 支持，需在 config.yaml 加配置）
2. 在 skill 中加路径可达性自检规则：scan 前先区分 verified / not_visible / not_exists 三类路径
3. 明确 §7.8 Configuration Drift 的执行者分工：轻量 scan 由 Hermes 做（能读到的部分），
   完整 scan 由 DS Team 做（通过 MCP）

---

## 3. v0.1.1 新增亮点

| # | 新增内容 | 价值 |
|---|---------|------|
| §0 | Bootstrap Status + 过渡链路 | 承认 bootstrap 阶段，避免自锁；允许人工搬运旧工作流 |
| §5 | Bootstrap Transitional Mode | 7 条临时规则，明确当前阶段各角色的约束 |
| §6 | Pre-Action Awareness | 8 项自检清单，直接回应 pre-action Gate 缺失。标注 "awareness rule 不是 hook" |
| §7.2 #1/2 | Role Boundary Drift 检查 PM Runtime 越权 | 直接吸收今天事故 |
| §7.7 #1/2/5 | Execution Drift 检查越权/未落盘/domain 错 | 同上 |
| §7.4 #3/5 | Path Drift 检查 domain 错误/artifact 路径 | 同上 |

**v0.1.1 最大的进步**：从"只扫文档"扩展到了"文档+运行时行为"，§7.2 和 §7.7 的检查
项直接覆盖了本次的失败模式。迭代速度快，吸取教训彻底。

---

## 4. 剩余 Priority（v0.1.1 视角）

| 优先级 | 问题 | 理由 |
|--------|------|------|
| P1 | #1 YAML 消费规则引用不完整 | §3.3 有方向无落地，缺 10 条具体规则的引用 |
| P1 | #2 YAML 维护设计缺触发条件 | 缺"何时标记 yaml_outdated_candidate"的规则 |
| P2 | #3 缺 Hermes 工具操作指引 | 尤其 §9 需要 §9.1 工具方法 + §9.2 路径可达性自检 |
| P2 | #4 MCP 工具上下文缺口（新增） | scan 范围远超 Hermes 读取能力，需基础设施变更 |
| P2 | #5 drift 检测操作方法不完整 | §7 有 checklist 无 tool mapping |
| P3 | #6 缺版本兼容声明 | 长远维护 |

---

## 5. PM Runtime Process Note

本次审查为 PM Runtime lightweight scan，**不是 DS Team 正式审计**。
执行过程中发现 4 项系统层面失败，详见同目录 `system_failure_analysis_2026-05-22.md`。

process_issues:
  1. 角色越界 — PM Runtime 做了深度审查而非先提出 DS Team 委派选项
  2. 产物未落盘 — 首次输出直接放在聊天中，后补写
  3. 目录 domain 路由错误 — PM Runtime 任务错误放在 control-agent-governance/ 下
  4. MCP 工具上下文缺失 — 执行 scan 时未做路径可达性自检，默认自己全能读到

---

## 6. Recommended Next Action

待 Owner 决策：

**基础设施**：
- 是否给 Hermes 配 MCP filesystem 服务器？（解决 P2-4 工具缺口）

**Skill 修订**：
- 是否由 Owner 直接修补 v0.1.1 的剩余 6 项 gap？
- 还是委派 DS Team 做 repository-level alignment review 后再统修？

**Pre-action Gate**：
- 是否在 governance skill 或 PM Runtime instruction 中加入 pre-action 自检机制？
  （v0.1.1 §6 已写了 awareness 层面的清单，是否升级为更强约束？）

workflow_compact_yaml_used: false
yaml_sections_checked: []
pm_runtime_instruction_version: v0.1.3
owner_control_required: true
