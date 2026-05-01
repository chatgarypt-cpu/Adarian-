# Phase 1 Output Contract Freeze v1.2.3

## 📍 版本信息

- **文档类型**：Phase 1 Output Contract Freeze
- **契约版本**：v1.2.3
- **任务 ID**：task-phase1-output-contract-freeze-r0
- **Review ID**：review-phase1-output-contract-freeze-01 / review-phase1-output-contract-freeze-02
- **基于提交**：`b13dd57 chore: isolate generated runtime artifacts`
- **状态**：R0 / contract freeze / documentation only
- **DS 审计结论**：`PASS_WITH_FINDINGS`
- **结论**：R0: GO，R1: HOLD

---

# 1. 契约冻结目标

本文件用于冻结当前 Phase 1 对下游 Phase 2 / Phase 3 / Phase 4 / `main.py` 的真实输出契约。

本文件不是 Parser / Compiler / Validator / Repair Loop 的实现文档。本文件是后续 R1 的准入依据。

后续任何 Phase 1 工程化改造，不得破坏本文档中冻结的 `required_fields`、`forbidden_to_change_fields` 和 `EntityExtractionOutput` canonical object 地位。

---

# 2. 当前 Phase 1 实际结构

## 2.1 当前主模块

当前 Phase 1 主模块仍是：

```text
src/phase1_entity_extraction.py
```

## 2.2 当前不存在的历史规划模块

当前仓库中不存在：

```text
src/phase1/orchestrator.py
src/phase1/rules_engine.py
```

因此，后续 R1 不得基于 `src/phase1/` 已经存在的假设进行接入设计。

## 2.3 文档漂移说明

`src/phase1_entity_extraction.py` 文件头声称：

```text
v1.1.14+ 已迁移到 src/phase1/
```

但当前仓库没有 `src/phase1/`。

该问题属于文档漂移证据。本轮只记录，不修复。

---

# 3. 当前 Phase 1 输出结构

## 3.1 EntityExtractionOutput 顶层字段

- `event_summary`
- `event_scale`
- `event_controversy`
- `event_type`
- `event_entities`
- `opinion_spreaders`
- `relations`

## 3.2 event_entities[] 字段

- `name`
- `type`
- `role`
- `entity_category`
- `can_speak`
- `original_statement`
- `can_speak_reason`

## 3.3 opinion_spreaders[] 字段

- `group_name`
- `related_event_entity`
- `description`
- `I`
- `P`
- `susceptibility`
- `estimated_percentage`
- `communication_style`
- `entity_category`
- `persona_name`
- `age_range`
- `occupation`
- `personality`
- `motivation`
- `typical_phrases`

## 3.4 relations[] 字段

- `source`
- `target`
- `type`

## 3.5 派生属性说明

以下字段当前不是 LLM 必填输出字段，也不是落盘 JSON 中必须由模型直接生成的字段：

- `C`
- `stance_score`
- `confirmation_bias_level`

`C`：

```text
C = P * (I / 10)
```

属于 IPC 语义中的派生值。

`stance_score`：

`stance_score` 由 `I / P` 映射得到，用于兼容 Phase 2 / Phase 3 / Phase 4 的立场表达。

`confirmation_bias_level`：

`confirmation_bias_level` 由 `I` 推导得到，用于兼容展示和部分模拟语义。

`OpinionSpreader.C` / `OpinionSpreader.stance_score` / `OpinionSpreader.confirmation_bias_level` 当前均为 `@property`，不是 `EntityExtractionOutput` 的落盘 JSON 字段。

保护优先级：

1. `stance_score`：Phase 2 / Phase 4 直接读取，属于高优先级兼容属性。
2. `confirmation_bias_level`：Phase 2 / Phase 4 直接读取，Phase 3 也经 GraphNode 消费，属于高优先级兼容属性。
3. `C`：当前已定义，但未发现明确下游消费，保护优先级低于 `stance_score` / `confirmation_bias_level`。

约束：后续 Compiler 设计不得把 `C` / `stance_score` / `confirmation_bias_level` 误判为 `EntityExtractionOutput.opinion_spreaders[]` 的 LLM 必填输出字段。

## 3.6 EntityExtractionOutput vs Archetype 双路径差异

本契约冻结的是当前主链 `EntityExtractionOutput` 路径：

```text
Phase 1 EntityExtractionOutput
  → Phase 2 GraphNode
  → Phase 3 / Phase 4
```

在该路径中，`OpinionSpreader.stance_score` / `confirmation_bias_level` 是由 `I / P` 或 `I` 推导出的 `@property`。

仓库中仍保留 legacy `Archetype` 路径：

```text
src/phase1_persona_engine.py
  → Archetype
```

该 legacy 路径中的 `Archetype.stance_score` / `Archetype.confirmation_bias_level` 是模型字段，并且历史 prompt 曾要求 LLM 直接输出。不得把本契约对 `OpinionSpreader` 派生属性的约束外推到 `Archetype` 路径；若后续清理 legacy 路径，必须单独审计。

---

# 4. 下游字段依赖表

## 4.1 Phase 2 字段依赖

入口：

```text
src/phase2_topology_builder.py
build_topology_from_extraction(extraction_output)
```

真实依赖：

- `extraction_output.event_entities`
- `extraction_output.opinion_spreaders`

`event_entities` 依赖字段：

- `name`

用途：

1. 生成 Core 节点 `group_name` / `related_entity`。
2. 建立 entity map。
3. 支撑 `opinion_spreaders[].related_event_entity` 的引用匹配。

`opinion_spreaders` 依赖字段：

- `group_name`
- `related_event_entity`
- `I`
- `P`
- `susceptibility`
- `persona_name`
- `age_range`
- `occupation`
- `personality`
- `motivation`
- `typical_phrases`

用途：

1. `group_name` 用于生成 Periphery 节点。
2. `related_event_entity` 用于建立 Periphery → Core 关注边。
3. `I / P` 通过 `stance_score` 派生属性进入 GraphNode。
4. `susceptibility` 进入 GraphNode 并影响后续模拟。
5. `persona_*` 字段进入 GraphNode，影响 Phase 3 发言上下文。

Phase 2 当前不直接使用：

- `event_summary`
- `event_scale`
- `event_controversy`
- `event_type`
- `relations`
- `event_entities[].can_speak`
- `event_entities[].original_statement`
- `opinion_spreaders[].estimated_percentage`
- `opinion_spreaders[].communication_style`
- `opinion_spreaders[].description`

Phase 2 风险说明：

`opinion_spreaders[].related_event_entity` 必须能匹配 `event_entities[].name`。否则 Periphery → Core 的关注边会缺失。

## 4.2 Phase 3 字段依赖

入口：

```text
src/phase3_tick_simulation.py
SimulationEngine(extraction_output, phase2_output, seed_text)
```

真实依赖：

- `event_summary`
- `event_entities`
- `opinion_spreaders`
- `group_distribution_strategy`（ghost field）

`event_entities` 依赖字段：

- `name`
- `type`
- `role`
- `can_speak`
- `original_statement`
- `can_speak_reason`

用途：

1. `name / type / role` 用于 Tick 0 事件实体记录。
2. `can_speak` 用于决定事件实体是否允许发言。
3. `original_statement` 优先作为 Tick 0 原始发言。
4. `can_speak_reason` 用作白盒观测字段来源。

Tick 0 控制语义：

```text
can_speak = true
  → 事件实体可进入发言逻辑

can_speak = false
  → 事件实体应被记录为 blocked / 不可发言
```

该语义在 R1 前不得改变。

`opinion_spreaders` 依赖字段：

- `group_name`

用途：建立 spreader map。

其他 persona / stance 字段主要由 Phase 2 转入 GraphNode，再由 Phase 3 消费。

间接强依赖包括：

- `I`
- `P`
- `susceptibility`
- `persona_name`
- `age_range`
- `occupation`
- `personality`
- `motivation`
- `typical_phrases`

说明：`confirmation_bias_level` / `stance_score` / `susceptibility` 等模拟字段主要来自 GraphNode。GraphNode 又由 Phase 2 基于 Phase 1 的 `I / P / susceptibility / persona_*` 构建。因此 `I / P / susceptibility / persona_*` 属于间接强依赖，不得改断。

`group_distribution_strategy` ghost field：

- Phase 3 当前通过 `getattr(extraction_output, "group_distribution_strategy", "normal")` 读取。
- 该字段不在 `EntityExtractionOutput` schema 中，不属于固定输出字段。
- 若 R1 清理或重建输出对象，不得误以为该字段是 schema required field；同时也不得忽略它会静默回退为 `"normal"` 并改变模拟分支。

`simulation_card.py` persona 容错边界：

- `simulation_card.py` 对 `persona_name` / `age_range` / `occupation` / `personality` / `motivation` / `typical_phrases` 等字段使用 `getattr(..., default)` 容错。
- 这意味着 Phase 3 构建 simulation card 时不会因单个 persona 字段缺失立即崩溃。
- 该容错只降低运行时崩溃风险，不代表 persona 字段可删除或改名；字段缺失会降低 Phase 3 发言上下文质量。

## 4.3 Phase 4 字段依赖

入口：

```text
src/phase4_report_agent.py
generate_report_with_llm(...)
save_markdown_report(...)
```

真实依赖：

- `event_summary`
- `event_type`
- `event_scale`
- `event_controversy`
- `event_entities`
- `opinion_spreaders`

`event_entities` 依赖字段：

- `name`
- `type`
- `role`
- `can_speak`
- `original_statement`
- `can_speak_reason`

用途：

1. 支撑报告中的事件主体说明。
2. 支撑发言可用性说明。
3. 支撑白盒解释与风险描述。

`opinion_spreaders` 依赖字段：

- `group_name`
- `related_event_entity`
- `estimated_percentage`
- `I`
- `P`

派生展示字段：

- `stance_score`
- `confirmation_bias_level`

用途：

1. `group_name` 用于报告中的群体命名。
2. `related_event_entity` 用于展示群体与事件实体的关系。
3. `estimated_percentage` 用于报告中的占比展示。
4. `I / P` 通过 `stance_score` 派生属性用于立场展示。
5. `confirmation_bias_level` 派生属性用于展示。

Phase 4 当前不明显直接依赖：

- `relations`
- `persona_name`
- `age_range`
- `occupation`
- `personality`
- `motivation`
- `typical_phrases`

但必须强调：这些 persona 字段会被 Phase 2 透传到 GraphNode，并间接影响 Phase 3 发言生成上下文，因此不能删除或改名。

## 4.4 main.py 字段传递方式

当前主链传递方式：

```text
run_phase1()
  → extraction_output

run_phase2(extraction_output)
  → phase2_output

run_phase3(extraction_output, phase2_output, seed_text)
  → tick_logs

run_phase4(extraction_output, phase2_output, tick_logs, x_t_sequence)
  → final_report
```

结论：`main.py` 使用内存对象 `EntityExtractionOutput` 传递 Phase 1 输出。`entities_and_relations.json` 是运行产物与审计证据，不是主链唯一数据通道。

---

# 5. 字段分级

## 5.1 required_fields

短期不可删除，否则会破坏当前主链或核心报告。

- `event_summary`
- `event_scale`
- `event_controversy`
- `event_type`
- `event_entities`
- `event_entities[].name`
- `event_entities[].type`
- `event_entities[].role`
- `event_entities[].can_speak`
- `event_entities[].original_statement`
- `opinion_spreaders`
- `opinion_spreaders[].group_name`
- `opinion_spreaders[].related_event_entity`
- `opinion_spreaders[].I`
- `opinion_spreaders[].P`
- `opinion_spreaders[].susceptibility`
- `opinion_spreaders[].persona_name`
- `opinion_spreaders[].age_range`
- `opinion_spreaders[].occupation`
- `opinion_spreaders[].personality`
- `opinion_spreaders[].motivation`
- `opinion_spreaders[].typical_phrases`

## 5.2 optional_fields

当前存在，但部分下游非强依赖，或主要用于展示 / 审计。

- `relations`
- `event_entities[].can_speak_reason`
- `event_entities[].entity_category`
- `opinion_spreaders[].description`
- `opinion_spreaders[].estimated_percentage`
- `opinion_spreaders[].communication_style`
- `opinion_spreaders[].entity_category`

说明：

- `can_speak_reason` 当前对白盒观测和报告说明有价值。虽然可列为 optional，但建议保留并补强。
- `estimated_percentage` 当前主要被 Phase 4 展示使用。不直接驱动 Phase 2 / Phase 3 主模拟，但仍属于报告契约字段，R1 前不得删除。
- `entity_category` 有默认值，是输出语义边界的一部分。可默认，不可反向改义。

## 5.3 legacy_fields

当前没有作为 JSON 落盘字段，但存在兼容属性或历史语义。

- `stance_score`
- `confirmation_bias_level`
- `C`
- `group_distribution_strategy`

说明：

- `stance_score`：由 `I / P` 派生，用于兼容 Phase 2 / Phase 3 / Phase 4。
- `confirmation_bias_level`：由 `I` 派生，用于兼容展示。
- `C`：由 `P * (I / 10)` 派生，属于 IPC 语义；当前无明确下游消费，保护优先级低于 `stance_score` / `confirmation_bias_level`。
- `group_distribution_strategy`：Phase 3 使用 `getattr(..., "normal")` 兼容读取。当前不属于 `EntityExtractionOutput` 固定输出字段。

## 5.4 candidate_intermediate_fields

适合后续迁移到 intermediate object 或 Compiler 内部结构。

- Parser 原始 payload
- Analyzer 输出：`event_summary` / `event_scale` / `event_controversy` / `event_type`
- 传播者规划字段：`I` / `P` / `susceptibility` / `estimated_percentage`
- persona 表达字段：`persona_name` / `age_range` / `occupation` / `personality` / `motivation` / `typical_phrases` / `communication_style`
- 派生字段：`C` / `stance_score` / `confirmation_bias_level`
- 修复 / 校验证据：validator errors / repair attempts / diff report

## 5.5 forbidden_to_change_fields

R1 前短期禁止变更。

顶层字段名与基本类型：

- `event_summary`
- `event_scale`
- `event_controversy`
- `event_type`
- `event_entities`
- `opinion_spreaders`
- `relations`

引用关系：

- `event_entities[].name`
- `opinion_spreaders[].related_event_entity`

立场语义：

- `I`
- `P`
- `stance_score` 派生行为
- `OpinionSpreader.stance_score` @property 方法签名
- `OpinionSpreader.confirmation_bias_level` @property 方法签名
- `OpinionSpreader.C` @property 方法签名（低优先级保护；当前无明确下游消费）

Tick 0 发言控制语义：

- `can_speak`
- `original_statement`

Canonical object：

- `EntityExtractionOutput`

具体约束：

1. 不得删除或重命名顶层字段。
2. 不得改变 `event_entities[].name` 与 `opinion_spreaders[].related_event_entity` 的引用关系。
3. 不得改变 `I / P` 的取值语义。
4. 不得改变 `stance_score` 的兼容派生行为。
5. 不得删除或重命名 `OpinionSpreader.stance_score` / `confirmation_bias_level` @property。
6. 不得把 legacy `Archetype.stance_score` / `confirmation_bias_level` 与 `OpinionSpreader` 派生属性混为同一契约路径。
7. 不得改变 `can_speak` 对 Tick 0 speaker behavior 的控制语义。
8. 不得改变 `original_statement` 优先作为 Tick 0 原始发言的语义。
9. 不得替换 `EntityExtractionOutput` 作为 Phase 1 对下游 canonical object 的地位。

---

# 6. 主要风险

## 6.1 文档漂移风险：高

路线图引用了当前不存在的文件：

- `src/phase1/orchestrator.py`
- `src/phase1/rules_engine.py`

后续 R1 若基于该假设设计接入点，会直接偏离当前源码事实。

## 6.2 文件头漂移风险：高

`src/phase1_entity_extraction.py` 自称已迁移到 `src/phase1/`，但当前目标目录不存在。

该问题会误导后续执行 Agent 判断 Phase 1 当前结构。

## 6.3 契约误判风险：中

以下字段是派生属性，不应被要求 LLM 直接输出：

- `C`
- `stance_score`
- `confirmation_bias_level`

如果 R1 把这些字段误判为 LLM 必填输出，会增加 prompt 负担并制造 parser / validator 误报。

补充：该结论仅适用于 `EntityExtractionOutput.opinion_spreaders[]` 的 `OpinionSpreader` 路径。legacy `Archetype` 路径中的同名字段属于模型字段，不能被本契约自动改写。

## 6.4 间接依赖漏判风险：中

persona 字段对 Phase 4 不一定直接使用，但会经 Phase 2 进入 GraphNode，间接影响 Phase 3 发言生成。

因此以下字段不能删除或改名：

- `persona_name`
- `age_range`
- `occupation`
- `personality`
- `motivation`
- `typical_phrases`

## 6.5 R1 事故风险：中

如果不先完成 R0，Parser / Compiler 很容易改变：

- 字段名
- 字段来源
- 派生语义
- 引用关系
- canonical object

从而破坏 Phase 2 / Phase 3 / Phase 4。

## 6.6 测试边界风险：中

当前 tests 主要覆盖 JSON parser，缺少针对 Phase 1 output contract 的契约测试。

后续 R1 若进入实现，应补充 contract-level tests。

## 6.7 历史记录漂移风险：高

`TASK_LOG.md` / `CHANGELOG.md` 中存在声称 `src/phase1/orchestrator.py`、`src/phase1/rules_engine.py`、`src/phase1/__init__.py` 已创建或修改的历史记录。

v1.2.3 review findings 已将这些记录标注为历史漂移。后续 R1 不得把这些历史记录作为当前源码事实依据。

---

# 7. R1 准入条件

只有满足以下条件，才允许进入 R1：Parser + Compiler + Validator Skeleton。

1. `docs/contracts/phase1-output-contract-freeze-v1.2.3.md` 已完成。
2. 文档明确 required / optional / legacy / candidate_intermediate / forbidden 字段。
3. 文档明确 Phase 2 / Phase 3 / Phase 4 / `main.py` 的真实字段依赖。
4. 文档明确当前 `src/phase1/` 目录不存在。
5. R1 不得按已拆分架构接入。
6. 文档明确 `C` / `stance_score` / `confirmation_bias_level` 是派生属性。
7. R1 不得把 `C` / `stance_score` / `confirmation_bias_level` 作为 LLM 必填输出字段。
8. 文档明确 `EntityExtractionOutput` 与 legacy `Archetype` 双路径差异。
9. 文档明确 `OpinionSpreader.stance_score` / `confirmation_bias_level` @property 不得删除或重命名。
10. 文档明确 `group_distribution_strategy` 是 Phase 3 ghost field。
11. 文档明确 `simulation_card.py` 对 persona 字段有 `getattr` 容错，但该容错不构成删除字段的依据。
12. 文档明确 persona 字段不得删除或改名。
13. 文档明确 `EntityExtractionOutput` 仍是对下游的 canonical object。
14. 文档经用户或内部审计 Agent 确认。

---

# 8. R0 不允许变更清单

本次 R0 严格禁止：

- 不修改任何业务代码
- 不新增 Parser
- 不新增 Compiler
- 不新增 Validator
- 不新增 Repair Loop
- 不新增 YAML 支持
- 不接外部检索
- 不修改 Phase 2
- 不修改 Phase 3
- 不修改 Phase 4
- 不修改 `main.py`
- 不修改 `schemas.py`
- 不更新 `TASK_LOG.md` / `CHANGELOG.md`，除非用户明确授权

---

# 9. 后续 R1 设计提醒

R1 进入 Parser + Compiler + Validator Skeleton 时，必须遵守：

1. `EntityExtractionOutput` 仍是 Phase 1 对下游的 canonical object。
2. Compiler 只能服务于 canonical object 构建，不得替换下游契约。
3. Validator 只能做确定性结构校验，不得让 LLM 生成权威校验结果。
4. 派生字段由代码计算，不由 LLM 负责输出。
5. Parser / Compiler / Validator 不得改动 Phase 2 / Phase 3 / Phase 4。
6. R1 第一版不得接 YAML 主路径。
7. R1 第一版不得接外部检索。

---

# 10. 最终结论

- DS 审计结论：`PASS_WITH_FINDINGS`
- R0：GO
- R1：HOLD
- v1.2.3 review findings 已在本契约内完成文档 remediation
- R1 进入前必须确认本契约 hardening 已完成，并确认未基于 `src/phase1/` 历史漂移记录设计接入点
