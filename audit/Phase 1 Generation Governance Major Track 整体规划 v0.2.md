# Phase 1 Generation Governance Major Track 整体规划 v0.2

## 0. 文档定位

* **文档类型**：长期路线规划 / DS 审计修订版
* **版本**：v0.2
* **适用范围**：Adarian MVP Phase 1 生成治理大版本
* **当前基线**：v1.2.3 closeout ready / pass_with_known_issues
* **当前状态**：R0 GO / R1 HOLD
* **修订依据**：DS Agent Team 对 v0.1 的 5 Agent 并行审计结论
* **下一步版本**：v1.2.4 - Phase 1 R1 Readiness Hardening

DS 审计结论为 `PASS_WITH_ISSUES`：路线方向正确、版本拆分粒度合理、防漂移规则到位，但 v1.2.8 / v1.2.9 存在回滚与 fallback 缺口；同时确认 v1.2.4 可立即执行。

---

# 1. 大版本总目标

本大版本的核心目标不是外部检索增强，而是 Phase 1 生成治理能力建设。

## 1.1 北极星目标

```text
把 Phase 1 从一次性 LLM 生成器，
升级为可解析、可编译、可校验、可定向修复、可回滚、可防漂移、可适配多模型的 Generation Governance Loop。
```

## 1.2 目标链路

```text
LLM raw output
  ↓
Parser
  ↓
Compiler / Canonicalizer
  ↓
Validator
  ↓
ValidationReport
  ↓
Targeted Repair Loop
  ↓
Pre-repair Snapshot / Rollback
  ↓
Re-validate
  ↓
Diff Reporter / Drift Guard
  ↓
Fallback Strategy
  ↓
Accepted EntityExtractionOutput
  ↓
Phase 2 / Phase 3 / Phase 4
```

## 1.3 核心收益

```text
1. 降低 Phase 1 因模型输出不稳定导致的失败率
2. 避免 Validator 把可修复问题升级为整段重生成
3. 让失败可定位、修复可约束、变更可 diff、异常可回滚
4. 为后续多模型 profiling / 并发 / 调度提供统一治理入口
5. 保持 EntityExtractionOutput 作为下游 canonical object
```

---

# 2. 明确不做的内容

本大版本不做外部信息增强。

明确不做：

```text
Web Search
RAG
MCP
外部态势感知
事实核验
source citation
报告引用链
外部数据库接入
自动 source ranking
```

允许保留：

```text
InputBundle placeholder
source_fragments: []
manual_notes: []
```

边界句：

```text
当前阶段只治理 LLM 输出不稳定性，不扩展外部信息获取能力。
```

---

# 3. v0.2 路线总览

根据 DS 审计建议，v0.2 对 v0.1 做三处关键调整：

```text
1. Multi-model Generation Profile 前移到 P/C/V Skeleton 之后、Repair Loop 之前。
2. Repair Loop 版本必须加入 pre_repair_snapshot 与 rollback policy。
3. Diff Guard 版本必须加入 fallback strategy，避免 forbidden_changes 后流水线死锁。
```

## 修订后版本路线

```text
v1.2.3：Phase 1 Output Contract Freeze
v1.2.4：Phase 1 R1 Readiness Hardening
v1.2.5：Source Tree Governance
v1.2.6：Schema Split Governance
v1.2.7：Parser / Compiler / Validator Skeleton
v1.2.8：Multi-model Generation Profile for P/C/V
v1.2.9：ValidationReport + Targeted Repair Loop + Rollback
v1.2.10：Diff Reporter + Drift Guard + Fallback
v1.2.11：InputBundle Placeholder
```

---

# 4. 各版本规划

---

## v1.2.3：Phase 1 Output Contract Freeze

### 状态

```text
closeout ready / pass_with_known_issues
R0：GO
R1：HOLD
```

### 已完成目标

冻结当前 Phase 1 对 Phase 2 / Phase 3 / Phase 4 / main.py 的真实输出契约。

### 已完成内容

```text
1. 明确 EntityExtractionOutput 顶层字段
2. 明确 event_entities[] 字段
3. 明确 opinion_spreaders[] 字段
4. 明确 relations[] 字段
5. 明确 Phase 2 / Phase 3 / Phase 4 / main.py 字段依赖
6. 标注 src/phase1/ 不存在的事实
7. 标注 TASK_LOG / CHANGELOG 中 src/phase1/ 历史漂移
8. 补充 EntityExtractionOutput vs legacy Archetype 双路径差异
9. 补充 OpinionSpreader @property 保护
10. 补充 group_distribution_strategy ghost field
11. 补充 simulation_card.py persona getattr 容错边界
```

### 关键结论

```text
EntityExtractionOutput 仍是当前 canonical object。
src/phase1/ 当前不存在。
R1 不得基于已拆分 phase1 包的假设设计接入点。
```

---

## v1.2.4：Phase 1 R1 Readiness Hardening

### 定位

R1 前置硬化，不进入 R1。

### 目标

清理 R1 前最后几个低风险阻塞点。

### 任务

```text
1. 修复 src/phase1_entity_extraction.py 文件头漂移注释
2. 给 main.py 的 run_phase2 / run_phase3 / run_phase4 补最小类型标注
3. 增加 tests/test_phase1_output_contract.py
```

### DS 审计修正

DS 建议 v1.2.4 补充 E2E smoke 验收。该建议采纳。

### 不做

```text
Parser
Compiler
Validator
Repair Loop
Diff Guard
源码树搬迁
Schema 拆分
外部检索
```

### 前置条件

```text
v1.2.3 closeout ready
contract hardening 已完成
R1 仍 HOLD
```

### 验收条件

```text
1. py_compile main.py src/phase1_entity_extraction.py 通过
2. tests/test_phase1_output_contract.py 通过
3. py main.py seeds/test1.txt smoke 通过
4. src/phase1_entity_extraction.py 只修改文件头注释
5. main.py 只增加类型标注，不改变行为
6. 未创建 src/phase1/
7. 未修改 Phase 2 / Phase 3 / Phase 4
8. 未修改 schema 结构
9. 未进入 R1
```

### Gate

```text
v1.2.4：GO
```

---

## v1.2.5：Source Tree Governance

### 定位

源码树治理，让每个 Phase 拥有独立目录和清晰模块命名。

### 目标

从“阶段写在文件名里”升级为“阶段即包”。

### 目标结构

```text
src/
  phase1/
    __init__.py
    extraction.py
    persona.py          # legacy / if file still exists and is in use

  phase2/
    __init__.py
    topology_builder.py

  phase3/
    __init__.py
    tick_simulation.py
    speaker_selector.py
    context_builder.py
    simulation_card.py
    state_updater.py

  phase4/
    __init__.py
    report_agent.py
```

### DS 审计修正

DS 指出 v0.1 的目标结构遗漏 4 个模块：

```text
phase0_entity_extraction.py
phase1_persona_engine.py
agent_quality_analyzer.py
llm_client.py
```

并指出 shim 策略不清晰。该问题采纳。

### 模块归属策略

```text
phase1_persona_engine.py：
- 若当前仍存在且仍可导入，迁移为 src/phase1/persona.py 或标注 legacy persona path。
- 不得自动接入主链。

phase0_entity_extraction.py：
- 标注 deprecated / legacy。
- 不进入新 phase1 主链。

agent_quality_analyzer.py：
- 暂留 src/ 根目录。
- 后续可独立考虑 src/analysis/，不纳入本轮 phase package。

llm_client.py：
- 暂留 src/ 根目录。
- 属于 infrastructure，不归入 phase1/2/3/4。
```

### Shim 策略

采用 **冷备用 shim**：

```text
main.py 改为直接走新 import。
旧入口文件保留为兼容转发层，服务历史脚本与外部调用。
```

旧入口保留：

```text
src/phase1_entity_extraction.py
src/phase2_topology_builder.py
src/phase3_tick_simulation.py
src/phase4_report_agent.py
```

### 不做

```text
不改业务逻辑
不改 schema
不新增 Parser / Compiler / Validator
不做 Repair Loop
不改变 main.py 主链语义
```

### 前置条件

```text
v1.2.4 pass
contract test 已存在
main.py 类型标注已补强
E2E smoke 已通过
```

### 验收条件

```text
1. main.py 走新 phase package import
2. 旧 shim import 继续可用
3. 新 phase package 可导入
4. phase1_persona_engine / phase0 / analyzer / llm_client 归属已明确
5. py_compile 通过
6. contract test 通过
7. smoke test 通过
8. 未改变业务逻辑
9. 未删除旧入口
```

### Gate

```text
v1.2.5：CONDITIONAL GO
条件：v1.2.4 通过 + 模块归属与 shim 策略冻结
```

---

## v1.2.6：Schema Split Governance

### 定位

schema 分层治理。

### 目标

将单体 `src/schemas.py` 拆为阶段化 schema 包。

### 目标结构

```text
src/schemas/
  __init__.py
  common.py
  phase1.py
  phase2.py
  phase3.py
  phase4.py
```

### DS 审计修正

DS 指出 `NodeRole` 被 Phase 1 / Phase 2 / Phase 3 共同使用，`common.py` 内容必须提前定义，否则会出现 Phase 1 反向 import Phase 2 的语义倒挂。该问题采纳。

### common.py 初始收纳范围

```text
NodeRole
EntityCategory
通用 BaseModel / shared enum（如存在）
跨阶段共享类型
```

`EdgeType` 是否进入 common.py，需要在 v1.2.6 Pre-Implementation Review 中确认。

### 兼容原则

```text
1. 先迁移，不改语义
2. 旧 src.schemas import 兼容
3. EntityExtractionOutput 仍是 Phase 1 canonical object
4. OpinionSpreader.C / stance_score / confirmation_bias_level @property 必须保留
5. 不改变字段结构
6. 不改变 validator 行为
```

### 不做

```text
不新增 Parser / Compiler / Validator
不改字段语义
不删除 legacy property
不改变 Phase 2 / Phase 3 / Phase 4 行为
```

### 前置条件

```text
v1.2.5 pass
phase package import 稳定
contract test 存在
common.py 收纳范围已冻结
```

### 验收条件

```text
1. schema import 全部通过
2. 旧 src.schemas import 继续可用
3. Phase 1 / Phase 2 / Phase 3 / Phase 4 类型可正常引用
4. common.py 不造成语义倒挂
5. contract test 通过
6. py_compile 通过
7. smoke test 通过
8. 业务主链不改变
```

### Gate

```text
v1.2.6：GO after v1.2.5
条件：common.py 收纳范围明确
```

---

## v1.2.7：Parser / Compiler / Validator Skeleton

### 定位

R1 正式入口。

### 目标

建立 Phase 1 generation governance 的最小三层骨架。

### 任务

```text
Parser：
- 从 LLM raw output 中提取结构化 payload
- 处理 markdown fence / 前后解释文本 / JSON candidate
- 失败时输出 ParseError

Compiler：
- 将 parsed payload 规范化
- 做字段别名归一
- 做默认值补齐
- 做 legacy 字段兼容
- 做派生属性保护
- 输出可构造 EntityExtractionOutput 的 canonical payload
- 失败时输出 CompileError

Validator：
- 进行确定性 contract validation
- 不依赖 LLM 作为最终质量门
- 失败时输出 ValidationReport draft
```

### DS 审计修正 1：失败模式必须定义

DS 指出 v0.1 完全缺少 Parser / Compiler / Validator 失败模式定义。该问题采纳。

### 失败模式定义

```text
Parser failed：
- hard fail
- 不进入 Compiler
- 写 ParseError artifact

Compiler failed：
- hard fail
- 不进入 Validator
- 写 CompileError artifact

Validator failed：
- v1.2.7 不进入 Repair Loop
- 输出 ValidationReport draft
- 不允许 LLM 自判通过
- 不允许 silent pass
```

### Degraded pass 策略

```text
v1.2.7 默认不允许 degraded pass。
```

原因：

```text
质量门刚建立时不能立刻允许绕行，否则 Validator 权威性不足。
```

如确实需要 fallback，只能在 v1.2.7 DS 审计后作为 known issue 处理，不作为默认路径。

### DS 审计修正 2：age_range 表述修正

DS 指出当前源码中并不存在代码级 `age_range` hard bucket 校验，只有 prompt 层格式示例；因此 v0.1 中“当前 Validator 写死 bucket”的表述不准确。该问题采纳。

### age_range 规则冻结

`age_range` 在 v1.2.7 前应作为规则文档冻结，而不是作为“当前代码 bug”处理。

规则：

```text
age_range 是 persona descriptor，不是 strict enum。
Validator 不应因为合理区间未命中固定 bucket 就 hard fail。
```

合理输出：

```text
23-35
30-40
45-55
60+
青年
中年
unknown
```

应拒绝：

```text
不可解析
年龄明显非法
min_age > max_age
跨度过大且无解释
与 persona 严重冲突
```

### rule_id 映射

DS 指出当前 prompt 中的 15 条校验规则可映射为代码级 rule_id。该建议采纳。

v1.2.7 应新增：

```text
R01-R18 → code-level rule_id mapping
```

### 不做

```text
不做 Repair Loop
不做 Diff Guard
不做外部检索
不做模型路由
不做自动 prompt optimization
```

### 前置条件

```text
v1.2.6 pass
schema split 稳定
contract test 通过
Source Tree Governance 完成
age_range 规则文档已冻结
```

### 验收条件

```text
1. Parser 能处理当前 LLM 输出
2. Parser 失败有 ParseError artifact
3. Compiler 不改变 EntityExtractionOutput 对外契约
4. Compiler 失败有 CompileError artifact
5. Validator 能输出 deterministic pass/fail
6. Validator 失败有 ValidationReport draft
7. 合理 age_range 不再被固定枚举误杀
8. R01-R18 已映射为 code-level rule_id
9. contract test 仍通过
10. 合法旧输出仍能进入 Phase 2
11. 质量门不依赖 LLM 自判
12. 不进入 Repair Loop
```

### Gate

```text
v1.2.7：CONDITIONAL GO
条件：失败模式定义 + age_range 规则冻结 + contract test 重申
```

---

## v1.2.8：Multi-model Generation Profile for P/C/V

### 定位

前移后的多模型 P/C/V 稳定性评估。

### 调整原因

DS 建议将 Multi-model Generation Profile 前移至 v1.2.7 与 Repair Loop 之间，避免 Repair Loop 设计过拟合当前模型。该建议采纳。

### 目标

比较不同模型在 Parser / Compiler / Validator 链路中的表现，为 Repair Loop 设计提供证据。

### 指标

```text
model_name
parse_fail_rate
compile_fail_rate
validate_fail_rate
avg_attempts
truncation_rate
known_failure_modes
```

注意：此时尚未进入 Repair Loop，因此 `repair_success_rate` 不作为 v1.2.8 必备指标。

### profile 数据允许使用范围

DS 指出 v0.1 只写了禁止项，没写允许项。该问题采纳。

允许用于：

```text
DS 审计
模型稳定性比较
Parser / Compiler / Validator 规则调整建议
prompt 约束微调建议
Repair Loop 设计参考
```

禁止用于：

```text
自动模型路由
多模型投票
SideRunner
默认主链切换
自动选择“最佳模型”
```

### 前置条件

```text
v1.2.7 pass
Parser / Compiler / Validator 可观测
各失败 artifact 可统计
```

### 验收条件

```text
1. 不同模型可生成 phase1_pcv_profile_summary
2. 可统计 parse / compile / validate 失败率
3. 可记录 truncation_rate
4. 可列出 known_failure_modes
5. profile 结果仅用于审计与设计参考
6. 不影响默认主链
7. 不引入调度策略
```

### Gate

```text
v1.2.8：GO after v1.2.7
```

---

## v1.2.9：ValidationReport + Targeted Repair Loop + Rollback

### 定位

自修复闭环，但必须带 rollback 安全网。

### 目标

失败不再整段重生成，而是结构化报错 + 定向修复 + 可回滚。

### DS 审计修正

DS 将 Repair Loop 无回滚机制、未保存 pre_repair_snapshot、最大 repair 次数未定义列为最严重缺口之一。该问题采纳。

### 核心链路

```text
Validator failed
  ↓
Save pre_repair_snapshot
  ↓
ValidationReport
  ↓
RepairPromptBuilder
  ↓
LLM targeted repair
  ↓
Parser / Compiler / Validator again
  ↓
If repair degrades or fails beyond threshold
  ↓
Rollback to pre_repair_snapshot
```

### ValidationReport 最小字段

```text
passed
stage
rule_id
severity
message
failed_fields
expected
actual
repair_hint
repair_scope
object_key
```

### failed_fields 定位规则

DS 指出数组索引在 repair 后可能位移，建议使用 name / group_name 做主键定位。该建议采纳。

规则：

```text
event_entities 使用 name 作为 object_key
opinion_spreaders 使用 group_name 作为 object_key
relations 使用 source + target + type 作为 object_key
```

### 最大 repair 尝试次数

```text
max_repair_attempts = 5
```

### rollback policy

必须保存：

```text
pre_repair_snapshot
repair_attempts
last_valid_object
final_repair_status
```

回滚触发：

```text
1. repair 后 Parser failed
2. repair 后 Compiler failed
3. repair 后 Validator failed 且失败严重度上升
4. repair 修改 scope 外字段
5. repair 尝试次数超过 max_repair_attempts
```

### 原则

```text
LLM 负责修复候选
代码负责最终验收
DS 负责审计
Control Agent 负责 gate
```

### 不做

```text
不做 Diff Guard
不做多模型自动路由
不接外部输入
不让 LLM 自称通过
```

### 前置条件

```text
v1.2.8 pass
P/C/V 跨模型 profile 已完成
Validation rule_id / failed_fields 足够准确
pre_repair_snapshot 格式已冻结
rollback policy 已冻结
```

### 验收条件

```text
1. 失败能定位到字段和 object_key
2. repair prompt 只围绕 failed_fields / repair_scope
3. 每次 repair 前保存 pre_repair_snapshot
4. max_repair_attempts = 5
5. repair 后必须重新通过 Parser / Compiler / Validator
6. repair 失败或退化时可 rollback
7. 失败必须显式终止或 pass_with_known_issues
8. LLM 不能绕过代码质量门
```

### Gate

```text
v1.2.9：HOLD until rollback/pre_repair_snapshot design is frozen
```

---

## v1.2.10：Diff Reporter + Drift Guard + Fallback

### 定位

防止 repair 越界漂移，并避免流水线死锁。

### 目标

每次 repair 后知道改了什么，拦截明显越界修改，并在 hard reject 后有 fallback。

### DS 审计修正

DS 将 Diff Guard 硬拒绝无退路列为 CRITICAL，指出 forbidden_changes → reject → ??? 会造成流水线死锁。该问题采纳。

### 任务

```text
1. old_object vs repaired_object diff
2. 输出 DiffReport
3. 检查 forbidden changes
4. forbidden_changes 非空时拒绝 repaired_object
5. fallback 到 pre_repair_snapshot 或 last_valid_object
6. 输出 explicit fail / pass_with_known_issues
```

### DiffReport 字段

```text
added
deleted
modified
field_type_changes
forbidden_changes
scope_creep_changes
diff_summary
fallback_action
```

### Drift guard 规则

DS 指出 v0.1 遗漏字段类型变化、group_name 重命名、scope creep、Analyzer 产物隐式修改、estimated_percentage 级联等场景。该问题采纳。

新增保护：

```text
1. 字段类型变化保护
2. group_name / name 主键重命名保护
3. scope creep 检测
4. Analyzer 产物保护：event_summary / event_type / event_scale / event_controversy
5. estimated_percentage 级联变化检测
6. persona 字段删除保护
7. @property 兼容行为保护
```

### fallback strategy

```text
forbidden_changes 非空：
  → 拒绝 repaired_object
  → 回退 pre_repair_snapshot
  → 写入 DiffReport
  → 输出 pass_with_known_issues 或 explicit fail
```

### 不做

```text
不做复杂策略引擎
不做人工 UI
不做多版本自动合并
```

### 前置条件

```text
v1.2.9 pass
Repair Loop 能稳定产生 repaired candidate
pre_repair_snapshot 可用
ValidationReport 能给出 repair_scope
```

### 验收条件

```text
1. 每次 repair 有 DiffReport
2. DiffReport 能列出 added / deleted / modified / field_type_changes
3. forbidden_changes 非空时拒绝 repaired_object
4. forbidden_changes 后有 fallback，不死锁
5. repair drift 被记录到 run artifact
6. 下游契约不被破坏
```

### Gate

```text
v1.2.10：HOLD until fallback strategy is frozen
```

---

## v1.2.11：InputBundle Placeholder

### 定位

未来外部输入接口位。

### 目标

只把本地 seed_text 包装成 InputBundle，不接外部检索。

### 允许

```text
seed_text → InputBundle
source_fragments: []
manual_notes: []
```

### 禁止

```text
Web Search
RAG chunks
MCP results
外部数据库
source ranking
事实核验
报告引用链
```

### DS 审计修正

DS 指出 `source_fragments` 约束目前只有文档约定，无代码级执行。该问题采纳。

### 代码级约束

v1.2.11 必须增加：

```text
source_fragments must be empty in current version
manual_notes must be empty unless explicitly enabled
external_input_enabled = false
```

可以通过：

```text
Pydantic validator
或 contract test
```

### 前置条件

```text
Phase 1 generation governance 主链稳定
Diff Guard + Fallback 已完成
```

### 验收条件

```text
1. 本地 seed 可包装为 InputBundle
2. 当前主链行为不变
3. source_fragments 为空也能运行
4. 代码级约束禁止非空 external source
5. 未来外部输入有接口位
6. 当前没有任何外部检索实现
```

### Gate

```text
v1.2.11：GO later
条件：source_fragments 代码级约束明确
```

---

# 5. 修订后版本准入表

| 版本      | 定位                        |           准入判断 | 关键条件                           |
| ------- | ------------------------- | -------------: | ------------------------------ |
| v1.2.3  | Contract Freeze           |            已完成 | closeout ready                 |
| v1.2.4  | R1 Hardening              |             GO | 补 E2E smoke                    |
| v1.2.5  | Source Tree Governance    | CONDITIONAL GO | 模块归属 + 冷备用 shim                |
| v1.2.6  | Schema Split Governance   |             GO | common.py 收纳范围冻结               |
| v1.2.7  | P/C/V Skeleton            | CONDITIONAL GO | 失败模式 + age_range 规则文档          |
| v1.2.8  | Multi-model P/C/V Profile |             GO | v1.2.7 后执行                     |
| v1.2.9  | Repair Loop + Rollback    |           HOLD | pre_repair_snapshot + rollback |
| v1.2.10 | Diff Guard + Fallback     |           HOLD | fallback strategy              |
| v1.2.11 | InputBundle Placeholder   |       GO later | source_fragments 代码约束          |

---

# 6. 大版本总验收条件

整个 Phase 1 Generation Governance Major Track 完成时，必须满足：

```text
1. Phase 1 输出不再裸奔进入下游
2. Parser / Compiler / Validator 职责清楚
3. Parser / Compiler / Validator 失败模式清楚
4. 合理 age_range 不再被固定枚举误杀
5. ValidationReport 能定位 failed_fields 与 object_key
6. Repair Loop 是定向修复，不是整段重抽
7. Repair 前有 pre_repair_snapshot
8. Repair 失败或退化可以 rollback
9. Repair 后有 DiffReport
10. Drift Guard 能阻止明显越界修改
11. Drift Guard hard reject 后有 fallback，不死锁
12. 多模型 P/C/V 表现可观测
13. InputBundle 只保留外部输入接口位，不接外部检索
14. source_fragments 非空有代码级禁止
15. EntityExtractionOutput 仍保持对 Phase 2/3/4 的 canonical object 地位
16. 旧入口 shim 可兼容
17. schema 分层后旧 import 不破坏
18. 质量门权威判断不依赖 LLM
```

一句话验收：

> **Phase 1 可以面对不同模型的不稳定输出，但下游仍然只看到稳定、可校验、可追踪、可回滚的 canonical object。**

---

# 7. 防漂移规则 v0.2

## 7.1 不允许提前接外部检索

```text
InputBundle 只做 placeholder。
source_fragments 当前必须为空。
```

## 7.2 不允许把 review finding 自动升级为新版本

review findings 先归入当前版本 remediation。只有形成独立主问题时才开新版本。

## 7.3 不允许在 Source Tree Governance 中顺手改业务逻辑

源码树治理只改 package / import / shim，不改行为。

## 7.4 不允许在 Schema Split 中改字段语义

Schema Split 只拆文件，不改字段。

## 7.5 不允许 Validator 变成格式洁癖

尤其是：

```text
age_range 不允许 strict bucket hard fail。
```

## 7.6 不允许 LLM 作为质量门最终裁判

```text
LLM 可以生成、修复、解释。
代码负责验收。
DS 负责审计。
Control Agent 负责 gate。
```

## 7.7 不允许 Repair Loop 无回滚

```text
没有 pre_repair_snapshot，不允许进入 Repair Loop。
```

## 7.8 不允许 Drift Guard 硬拒绝后无退路

```text
forbidden_changes 必须触发 fallback，而不是流水线死锁。
```

---

# 8. 每阶段进入前必须核对的事项

## 进入 v1.2.4 前

```text
1. v1.2.3 是否 closeout ready
2. contract 文档是否存在
3. R1 是否仍 HOLD
```

## 进入 v1.2.5 前

```text
1. v1.2.4 contract test 是否通过
2. main.py 类型标注是否不改变行为
3. src/phase1_entity_extraction.py 文件头是否不再误导
4. smoke test 是否通过
5. 模块归属策略是否冻结
6. shim 策略是否冻结为冷备用
```

## 进入 v1.2.6 前

```text
1. phase package 是否导入稳定
2. shim 是否可用
3. py_compile 是否通过
4. contract test 是否通过
5. common.py 收纳范围是否明确
```

## 进入 v1.2.7 前

```text
1. schema split 是否完成
2. 旧 src.schemas import 是否兼容
3. EntityExtractionOutput 是否仍是 canonical object
4. OpinionSpreader @property 是否完整
5. age_range 规则文档是否冻结
6. Parser / Compiler / Validator 失败模式是否冻结
7. R01-R18 rule_id mapping 是否可执行
```

## 进入 v1.2.8 前

```text
1. Parser 是否稳定
2. Compiler 是否能输出 canonical payload
3. Validator 是否能输出 deterministic pass/fail
4. 失败 artifact 是否可统计
```

## 进入 v1.2.9 前

```text
1. P/C/V 跨模型 profile 是否完成
2. ValidationReport 字段是否足够支持 repair prompt
3. pre_repair_snapshot 格式是否冻结
4. rollback policy 是否冻结
5. max_repair_attempts 是否确认
```

## 进入 v1.2.10 前

```text
1. Repair Loop 是否稳定
2. pre_repair_snapshot 是否可用
3. repair_scope 是否明确
4. forbidden fields 是否来自 contract
5. fallback strategy 是否冻结
```

## 进入 v1.2.11 前

```text
1. generation governance 主链是否稳定
2. InputBundle 是否只做本地 seed 包装
3. external_input_enabled 是否为 false
4. source_fragments 非空是否有代码级禁止
```

---

# 9. 当前推进建议

```text
1. v0.2 路线可以进入用户确认。
2. v1.2.4 可以立即执行。
3. v1.2.5 需要在执行前补模块归属与 shim 策略审计。
4. v1.2.9 / v1.2.10 当前仍 HOLD，不得提前实现。
```

