# Workflow Compact YAML 综合审查报告

> 审查对象：`docs/skills/workflow_v4.0/workflow_core/workflow_compact_v0.3.yaml`
> 审查层级：Hermes-PM 预检 + DS Agent Team 深度审查
> 日期：2026-05-21

---

## 一、Hermes-PM 预检

### 1.1 基础解析

| 检查项 | 结果 |
|--------|------|
| YAML 语法 | ✅ `yaml.safe_load` 通过 |
| 必需 top-level key（9个） | ✅ 全部存在 |
| 期望字段（19个） | ✅ 全部存在 |
| 布尔值类型 | ✅ 全部 native bool（无 "true"/"false" 字符串） |
| 长文本（>200字符） | ⚠️ 1 处（`agent_asset_layout_recommendation.rule`，227字符，可接受） |
| schema_version | ❌ 缺失 |
| compatible_workflow_core_version | ❌ 缺失 |
| 文件规模 | 547 行 / 15,450 字符 |

### 1.2 类型预检

| 字段 | 类型 | 状态 |
|------|------|------|
| metadata | dict | ✅ |
| role_map | dict | ✅ |
| task_levels | dict | ✅ |
| closeout_gate | dict | ✅ |
| hold_conditions | list | ✅ |

---

## 二、DS Agent Team 深度审查

**审查模式**：Agent Team（4 reviewer）+ MCP
**审查耗时**：892s / 14 turns

### 2.1 总体裁定

| 维度 | 评定 | 得分 |
|------|------|------|
| YAML 语法质量 | pass_with_minor_issues | 85/100 |
| 机器可读性 | **patch_required** | 48/100 |
| 自动生成可行性 | pass_with_minor_patches | — |
| 风险评估 | patch_required | — |
| **综合裁定** | **patch_required** | — |

### 2.2 Blocker（4 项）

| # | Blocker | 说明 |
|---|---------|------|
| 1 | 缺 `schema_version` | YAML 格式演化不可追踪 |
| 2 | 缺 `compatible_workflow_core_version` | 无法验证 YAML 与 workflow_core.md 一致性 |
| 3 | 缺 `task_status_values` 枚举 | `dispatch_contract.status` 无有效值定义 |
| 4 | 缺 `task_lifecycle` 状态机 | PM Runtime 无法判定任务状态转换合法性 |

### 2.3 Major 发现（8 项）

| # | 问题 |
|---|------|
| 1 | **权威混淆风险** — YAML 声明非权威但使用强制性语言，agent 必然视为事实权威 |
| 2 | **无集中枚举注册表** — acceptance_verdict 和 closeout decisions 分散且语义重叠 |
| 3 | **receipt_contract.hard_rules 为自然语言** — 不可机器校验 |
| 4 | **ds_review_contract 严重单薄** — 缺 5 阶段 DS Verify 流程、acceptance 逻辑、diff-baseline 规则 |
| 5 | **task_levels 类型混用** — `pm_runtime_required` 混用 string/bool |
| 6 | **hold_conditions 为散文** — 18 条为蛇形命名片段，非结构化标识符 |
| 7 | **codex_safety_gate / git_safety_gate 仅名称引用** — 从未定义实际检查内容 |
| 8 | **自然语言负担高** — 多处 agent 行为规则为完整英语散文句 |

### 2.4 6 场景评分

| 场景 | 评分 |
|------|------|
| Control Agent 读取判断管线 | needs_minor_patch |
| Hermes/PM Runtime 生成 dispatch | **ready** |
| relay_runner/checker 检查目录 | **ready** |
| DS Team 确认 review contract | needs_major_patch |
| Codex 确认执行边界 | needs_minor_patch |
| Auto Gate Checker 判断 closeout | needs_minor_patch |

### 2.5 字段逐项裁定

| 裁定 | 数量 | 字段 |
|------|------|------|
| keep | 16 | metadata, authority, global_principles, default_routes, task_levels, task_directory_policy, pm_runtime_state_model, dispatch_contract, receipt_contract, ds_review_contract, codex_execution_contract, commit_gate, closeout_gate, hold_conditions, standard_outputs, file_first_delivery |
| rename | 3 | role_map → role_definitions, agent_asset_layout_recommendation → asset_layout_recommendation, minimum_memory_lines → design_constraints |

### 2.6 缺失字段总计（9 项）

1. `schema_version`
2. `compatible_workflow_core_version`
3. `task_lifecycle`（顶级状态机）
4. `enums`（顶级集中枚举注册表）
5. `input_contract`（每个角色的输入规范）
6. `error_recovery_policy`
7. `path_aliases`
8. `receipt_contract.validation_schema`
9. `dispatch_contract.status_values`

### 2.7 拆分建议

DS Team 建议：**暂不拆分**。先完成 blocker 修补，v0.4 再评估是否拆为 `compact.yaml` + `contracts.schema.json`。

---

## 三、综合判断

| 来源 | 裁定 |
|------|------|
| Hermes-PM 预检 | 语法通过，2 项缺失 |
| DS Team 审查 | patch_required（4 blocker + 8 major） |
| **综合** | **patch_required** |

Hermes 预检的 2 项缺失与 DS 的 4 个 blocker 中的前 2 项完全吻合。

---

## 四、推荐修复优先级

| 优先级 | 项目 |
|--------|------|
| P0 立即 | 补 schema_version、compatible_workflow_core_version、task_lifecycle、task_status_values |
| P1 优先 | 创建 enums 注册表、结构化 hold_conditions、重构 receipt_contract.hard_rules |
| P1 优先 | 大幅补充 ds_review_contract（5 阶段 DS Verify 流程） |
| P1 优先 | 定义 codex_safety_gate / git_safety_gate 实际内容 |
| P2 建议 | 统一 task_levels 类型、增加 path_aliases、重命名 3 个字段 |
| P3 架构 | v0.4 评估 YAML + JSON Schema 拆分 |

---

## 五、产出路径

| 文件 | 路径 |
|------|------|
| DS 审查报告 | `audit/tasks/active/workflow-v4-landing/yaml-review/ds/ds_yaml_machine_review.md` |
| DS receipt | `audit/tasks/active/workflow-v4-landing/yaml-review/ds/ds_receipt.yaml` |
| 本综合报告 | `audit/tasks/active/workflow-v4-landing/yaml-review/yaml_combined_review_2026-05-21.md` |
