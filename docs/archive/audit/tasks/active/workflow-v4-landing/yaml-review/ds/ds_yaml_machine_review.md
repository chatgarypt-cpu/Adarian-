# DS Team — Workflow Compact YAML 机器可读性审查报告

**审查日期**: 2026-05-21  
**审查ID**: `v4.0-workflow-compact-yaml-machine-review-01`  
**审查模式**: Agent Team（4 审查者并行）  
**MCP 使用**: 是（filesystem MCP 读取 YAML）  

---

## 1. 总体裁定

| 维度 | 评定 | 得分 |
|------|------|------|
| YAML 语法质量 | pass_with_minor_issues | 85/100 |
| 机器可读性 | patch_required | 48/100 |
| 自动生成可行性 | pass_with_minor_patches | medium |
| 风险评估 | patch_required | — |
| **综合裁定** | **patch_required** | — |

**结论**: YAML 文件结构良好、语法正确，但存在 4 个 blocker 级别缺陷和多个 major 级别问题，在作为 workflow v4.0 的机器友好全局索引投入生产使用前必须修补。

---

## 2. 各审查者发现汇总

### 2.1 YAML Schema Reviewer — 语法与结构

**裁定**: `pass_with_minor_issues` (85/100)

**语法问题**: 无
- 未发现 tab 字符、非法冒号、未转义字符、重复 key、缩进错误
- 2 空格缩进全文一致
- 无 YAML 解析陷阱（无裸 `yes`/`no`/`on`/`off`，字符串版本号如 `v0.3` 安全）

**类型一致性问题（3 项，严重度 medium）**:

| 字段 | 位置 | 问题 |
|------|------|------|
| `pm_runtime_required` | s_level/m_level/l_level/patch_lane | 混用 `'optional'`(string)、`'conditional'`(string)、`true`(bool)。严格 schema 验证器将拒绝此混用 |
| `ds_pre_audit_required` | s_level/m_level/l_level | 混用 `'optional'`(string)、`'conditional'`(string)、`true`(bool) |
| `ds_post_execution_review_required` | m_level/l_level | 混用 `'conditional'`(string)、`true`(bool) |

**文件头注释建议**: `trim` — 5 行注释块中的 `document_type`、`scope`、`purpose` 应移入 metadata mapping 作为正式字段，注释块精简为 1 行。

---

### 2.2 Machine Readability Reviewer — 机器可读性

**裁定**: `patch_required`

**自描述评分**: 48/100

**关键问题**:

1. **自然语言负担高**: `hold_conditions` 中 18 条为蛇形命名散文片段，非机器可处理标识符；`receipt_contract.hard_rules` 为完整散文句，简单 checker 无法解析
2. **枚举机会**: 21 个字段/子字段应转换为 enum 类型（含 `metadata.status`、`acceptance_verdict_values`、`hold_conditions`、`closeout_gate.valid_decisions` 等）
3. **布尔机会**: `task_levels.*.pm_runtime_required` 当前用字符串 `'optional'`/`'conditional'` 而非布尔值
4. **类型稳定性**: `codex_may_commit` 在 c0 中为字符串 `'false_until_confirmed'`，在 c1 中为布尔 `true`
5. **缩写未定义**: `ds`、`pm`、`s/m/l`、`codex`、`Hermes` 在文件中均无定义
6. **`standard_outputs` 无类型约束**: 输出模板缺少字段类型、required/optional 标记、验证规则

**字段名质量**: acceptable — snake_case 一致，但部分命名过长（`agent_asset_layout_recommendation`）

**枚举转换建议** (主要):
- `metadata.status` → `enum: [candidate, active, deprecated]`
- `task_levels.*.pm_runtime_required` → `enum: [required, optional, conditional]`
- `ds_review_contract.acceptance_verdict_values` → 已为列表，需集中注册
- `hold_conditions` → 结构化为 `[{code, description, severity, detection_rule}]`
- `receipt_contract.verdict` → `enum: [pass, pass_with_known_issues, fail, hold]`

---

### 2.3 Auto-Generation Reviewer — 自动生成场景

**裁定**: `pass_with_minor_patches`  
**自动生成可行性**: `medium`  
**拆分建议**: `split_schema`

**6 场景评分**:

| 场景 | 评分 | 说明 |
|------|------|------|
| Control Agent | needs_minor_patch | task_levels 缺少结构化分类标准（如文件数阈值），default_handling 为自然语言字符串 |
| Hermes/PM Runtime | **ready** | dispatch_contract 16 个 required_fields 完整，可直接代码生成 dispatch.yaml |
| relay_runner/checker | **ready** | task_directory_policy 提供规范路径和 3 级 layout specs，可确定性验证目录结构 |
| DS Team | needs_major_patch | ds_review_contract 严重缺失：无 5 阶段 DS Verify 流程、无 hard/soft target acceptance 逻辑、无 diff-baseline 规则 |
| Codex | needs_minor_patch | codex_safety_gate 和 git_safety_gate 仅名称引用但从未定义实际检查内容 |
| Auto Gate Checker | needs_minor_patch | hold_conditions 缺少严重级别分层和分类标签，required_checkpoints 缺验证谓词 |

**拆分建议详述**:
- `dispatch_contract` / `receipt_contract` / `ds_review_contract.acceptance_verdict_values` 为类 schema 契约 → 抽取为 `workflow_contracts_v0.1.schema.json`
- `role_map` / `gates` / `hold_conditions` / `global_principles` 等为规则/参考数据 → 保留在 `workflow_compact_v0.4.yaml`
- 拆分后 validator 可自动检查 dispatch.yaml 是否符合 JSON Schema，agent 读取 compact YAML 获取行为规则

---

### 2.4 Risk Reviewer — 风险审查

**裁定**: `patch_required`  
**权威混淆风险**: `high`  
**Agent 误导风险**: `medium`

**Blocker 级别风险 (4 项)**:

| # | 风险 | 缓解方案 |
|---|------|----------|
| 1 | **缺少 `schema_version`** — YAML 格式演化不可追踪 | 在 metadata 中增加 `schema_version: "1.0"`（与 asset version 区分） |
| 2 | **缺少 `compatible_workflow_core_version`** — 无法验证 YAML 与 workflow_core.md 的一致性 | 在 metadata 中增加 `compatible_workflow_core_version: "v4.0_r2"` |
| 3 | **`dispatch_contract.status` 无有效值定义** — agent 无法验证此字段 | 增加 `task_status_values` 枚举和 `task_lifecycle` 状态转换规则 |
| 4 | **缺少显式任务生命周期状态机** — pm_runtime_state_model 仅覆盖持久化，未定义状态及转换 | 增加 `task_lifecycle` 顶级 key |

**Major 级别风险 (3 项)**:

| # | 风险 | 缓解方案 |
|---|------|----------|
| 5 | **权威混淆** — YAML 声明自身非权威但使用强制性语言（forbidden/required/hard_rules），agent 必然将其视为事实权威 | 增加 machine-verifiable hash/checksum 链接到对应 workflow_core 版本，或提升为 derived-authority |
| 6 | **无集中枚举注册表** — acceptance_verdict_values (7 值) 和 closeout valid_decisions (5 值) 分散且部分重叠但语义不同 | 增加顶级 `enums` 区段，所有 enum 在此定义一次，其他部分按名称引用 |
| 7 | **receipt_contract.hard_rules 为自然语言** — PM Runtime agent 无法程序化验证 | 增加 `validation_schema` 子区段，使用 JSON Schema 或结构化断言 |

**Minor 级别风险 (2 项)**:

| # | 风险 |
|---|------|
| 8 | `required/optional` 标记仅在 dispatch_contract 和 receipt_contract 中存在，其他区段缺失 |
| 9 | 缺少 `path_aliases` — 模板路径嵌入字符串字面量，多站点修改困难 |

**缺失字段汇总 (9 项)**:
1. `schema_version` (metadata 内)
2. `compatible_workflow_core_version` (metadata 内)
3. `task_lifecycle` (顶级状态机)
4. `enums` (顶级集中枚举注册表)
5. `input_contract` (每个角色的输入规范)
6. `error_recovery_policy` (升级路径、重试规则、超时行为)
7. `path_aliases` (符号路径名注册表)
8. `receipt_contract.validation_schema` (机器可验证规则)
9. `dispatch_contract.status_values` (status 字段有效值枚举)

---

## 3. 19 顶层字段逐项裁定

| # | 字段 | 裁定 | 理由 |
|---|------|------|------|
| 1 | `metadata` | **keep** | 需增加 `schema_version` 和 `compatible_workflow_core_version` |
| 2 | `authority` | **keep** | 需增加版本 hash/checksum 以降低权威混淆风险 |
| 3 | `global_principles` | **keep** | 可考虑结构化 `{id, description}` 对替代裸字符串 |
| 4 | `role_map` | **rename** → `role_definitions` | 当前名称 risk agent 将其视为自身指令集；新增 header disclaimer |
| 5 | `default_routes` | **keep** | — |
| 6 | `task_levels` | **keep** | 必须统一 `pm_runtime_required` 等字段的类型（全部 string 或分离 required/bool + conditions） |
| 7 | `task_directory_policy` | **keep** | Layout specs 可直接用于确定性目录验证 |
| 8 | `pm_runtime_state_model` | **keep** | `state_rule` 需从散文句改为结构化映射 |
| 9 | `dispatch_contract` | **keep** | 最完整的区段之一；需增加 `status_values` enum |
| 10 | `receipt_contract` | **keep** | 需增加 `validation_schema` 替代自然语言 hard_rules |
| 11 | `ds_review_contract` | **keep** | 严重不足 — 需增加 DS Verify 5 阶段流程、acceptance 逻辑、diff-baseline 规则 |
| 12 | `codex_execution_contract` | **keep** | 需定义 `codex_safety_gate` 和 `git_safety_gate` 的具体检查内容 |
| 13 | `commit_gate` | **keep** | — |
| 14 | `closeout_gate` | **keep** | — |
| 15 | `hold_conditions` | **keep** | 需结构化为 `[{code, description, severity, detection_rule}]`，补充缺失条件 |
| 16 | `standard_outputs` | **keep** | 需增加字段类型和 required/optional 标记 |
| 17 | `file_first_delivery` | **keep** | — |
| 18 | `agent_asset_layout_recommendation` | **rename** → `asset_layout_recommendation` | `agent_` 前缀暗示这是给 agent 的指令而非文档布局约定 |
| 19 | `minimum_memory_lines` | **rename** → `design_constraints` | `memory_lines` 命名 risk agent 将这些作为系统 prompt 注入 |

---

## 4. 建议下一步

1. **立即修补 (blocker)**: 添加 `schema_version`、`compatible_workflow_core_version`、`task_lifecycle`、status 枚举
2. **优先修补 (major)**: 创建集中 `enums` 区段、添加 version hash/checksum、重构 `receipt_contract.hard_rules` 为结构化验证规则、大幅补充 `ds_review_contract`
3. **建议修补 (minor)**: 统一 `task_levels` 类型、结构化 `hold_conditions`、增加 `path_aliases`、重命名 3 个问题字段
4. **架构决策**: 是否拆分为 `compact.yaml` + `contracts.schema.json`
5. **不建议**此时拆分为多文件 — 先完成上述修补，v0.4 再评估拆分

---

*审查由 DS Agent Team 完成：YAML Schema Reviewer + Machine Readability Reviewer + Auto-Generation Reviewer + Risk Reviewer*
