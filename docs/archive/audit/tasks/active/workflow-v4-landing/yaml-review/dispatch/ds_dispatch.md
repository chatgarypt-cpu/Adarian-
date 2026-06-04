# DS Agent Team Readonly Review — Workflow Compact YAML Machine-Readability

## 0. Hard Requirements

```yaml
task_id: v4.0-workflow-compact-yaml-machine-review-01
team_mode_required: true
mcp_required: true
readonly_review_only: true
file_modification_allowed: false
git_commit_allowed: false
```

## 1. Objective

审查 `docs/skills/workflow_v4.0/workflow_core/workflow_compact_v0.3.yaml` 是否适合作为 workflow v4.0 的机器友好全局 compact/operating index。

## 2. Review Material

```
docs/skills/workflow_v4.0/workflow_core/workflow_compact_v0.3.yaml
```

Hermes-PM 已完成基础检查：YAML 语法通过，19 顶层 key 全部存在，布尔值正确，但缺少 `schema_version` 和 `compatible_workflow_core_version`。

## 3. Background

v4.0 文件结构计划：

```
docs/skills/workflow_v4.0/
  workflow_core/
    workflow_core_v4.0_r2.md       # 完整权威源
    workflow_compact_v0.3.md       # 人读作战地图
    workflow_compact_v0.3.yaml     # 机器友好索引（本次审查对象）
  control_agent/
  pm_runtime/
  ds_team/
  codex/
```

设计原则：
- workflow_core.md 是唯一权威源
- compact.md 是人读作战地图
- compact.yaml 是机器友好索引，不是第二权威源
- 不给每个 agent 单独配 compact
- 每个 agent 只配自己的 specific_instruction/skills

## 4. Reviewer Agents

```
1. YAML Schema Reviewer — 语法、结构、字段类型
2. Machine Readability Reviewer — agent/runner/checker 自动读取适用性
3. Auto-Generation Reviewer — 是否适合自动生成和校验
4. Risk Reviewer — 是否会误导 agent、缺少关键字段
```

## 5. Review Questions

### 5.1 YAML 基础质量
1. 是否存在 tab、非法冒号、未转义字符、重复 key、缩进错误？
2. 是否存在 Markdown 注释或长文本导致 parser 风险？
3. 是否建议去掉文件头大段注释？

### 5.2 机器友好性
1. 字段是否适合 agent 自动读取？
2. 字段名是否足够稳定？
3. 是否有过多人类自然语言句子？
4. 哪些字段应改成 enum？哪些应改成 bool？哪些应改成 list[enum]？

### 5.3 自动生成/自动读取场景
从以下场景审查：
1. Control Agent 读取判断管线位置
2. Hermes/PM Runtime 读取生成 dispatch
3. relay_runner/checker 读取检查 task directory
4. DS Team 读取确认 review contract
5. Codex 读取确认执行边界
6. 自动 gate checker 读取判断 closeout/hold

### 5.4 是否需要拆分
是否应拆成 `workflow_compact_v0.3.yaml` + `workflow_compact.schema.json`？

### 5.5 字段逐项检查

对以下 19 个顶层字段逐一给出 verdict（keep/rename/split/simplify/remove）：
metadata, authority, global_principles, role_map, default_routes, task_levels, task_directory_policy, pm_runtime_state_model, dispatch_contract, receipt_contract, ds_review_contract, codex_execution_contract, commit_gate, closeout_gate, hold_conditions, standard_outputs, file_first_delivery, agent_asset_layout_recommendation, minimum_memory_lines

### 5.6 关键风险
1. 是否会误导 agent 把 YAML 当成权威源？
2. 是否缺少 schema_version/compatible_workflow_core_version？
3. 是否缺少 required/optional 字段标记？
4. 是否缺少 enum 定义区？
5. 是否缺少 path_aliases？
6. 是否缺少 output_contracts 的 machine validation 规则？
7. 是否缺少 task lifecycle 状态枚举？
8. 是否缺少 status transition 规则？

## 6. Expected Output

Report:
```
audit/tasks/active/workflow-v4-landing/yaml-review/ds/ds_yaml_machine_review.md
```

Receipt:
```
audit/tasks/active/workflow-v4-landing/yaml-review/ds/ds_receipt.yaml
```

Receipt must include:
```yaml
task_id: v4.0-workflow-compact-yaml-machine-review-01
team_mode_used:
mcp_used:
yaml_parse_status:
machine_readability_verdict:  # pass / pass_with_minor_patches / patch_required / hold / fail
schema_recommendation:
blockers:
major_findings:
minor_findings:
field_verdicts: {}  # per-field: keep/rename/split/simplify/remove
recommended_next_action:
```

## 7. Boundaries

**DO**: Read-only YAML review, MCP + team mode
**DO NOT**: Modify YAML, modify workflow_core, closeout, git commit
