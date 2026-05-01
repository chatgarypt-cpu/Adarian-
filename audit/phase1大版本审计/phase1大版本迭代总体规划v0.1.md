# Phase 1 Generation Governance Major Track 整体规划 v0.1

## 0. 文档定位

* **文档类型**：长期路线规划 / Pre-Implementation Review Draft
* **适用范围**：Adarian MVP Phase 1 生成治理大版本
* **当前基线**：v1.2.3 closeout ready / pass_with_known_issues
* **当前状态**：R0 GO / R1 HOLD
* **下一步版本**：v1.2.4 - Phase 1 R1 Readiness Hardening
* **核心目标**：将 Phase 1 从“一次性 LLM 生成器”升级为“可解析、可编译、可校验、可定向修复、可防漂移、可适配多模型”的生成治理层

v1.2.3 已确认：`EntityExtractionOutput` 是当前 Phase 1 对下游的 canonical object；`entities_and_relations.json` 是运行产物与审计证据，不是主链唯一数据通道。当前主链通过 `run_phase1() → extraction_output → run_phase2/3/4` 的内存对象传递。

---

# 1. 大版本总目标

本大版本的目标不是外部检索增强，而是 Phase 1 生成治理能力建设。

## 1.1 目标链路

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
Re-validate
  ↓
Diff Reporter / Drift Guard
  ↓
Accepted EntityExtractionOutput
  ↓
Phase 2 / Phase 3 / Phase 4
```

## 1.2 核心收益

```text
1. 降低 Phase 1 因模型输出不稳定导致的失败率
2. 避免 Validator 把可修复的小问题升级为整段重生成
3. 为后续多模型 profiling / 并发 / 调度提供统一治理入口
4. 降低不同模型字段风格差异对下游 Phase 2/3/4 的冲击
5. 让失败可定位、修复可约束、变更可 diff、结果可审计
```

---

# 2. 明确不做的内容

本大版本不以外部输入增强为主目标。

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
未来外部输入接口位
```

也就是说：

> 当前阶段只治理 LLM 输出不稳定性，不扩展外部信息获取能力。

---

# 3. 总版本路线

```text
v1.2.3：Phase 1 Output Contract Freeze
v1.2.4：Phase 1 R1 Readiness Hardening
v1.2.5：Source Tree Governance
v1.2.6：Schema Split Governance
v1.2.7：Parser / Compiler / Validator Skeleton
v1.2.8：ValidationReport + Targeted Repair Loop
v1.2.9：Diff Reporter + Drift Guard
v1.2.10：Multi-model Generation Profile
v1.2.11：InputBundle Placeholder
```

---

# 4. 各版本规划

## v1.2.3：Phase 1 Output Contract Freeze

### 状态

```text
closeout ready / pass_with_known_issues
R0：GO
R1：HOLD
```

### 目标

冻结当前 Phase 1 对 Phase 2 / Phase 3 / Phase 4 / main.py 的真实输出契约。

### 已完成内容

```text
1. 明确 EntityExtractionOutput 顶层字段
2. 明确 event_entities[] 字段
3. 明确 opinion_spreaders[] 字段
4. 明确 relations[] 字段
5. 明确 Phase 2/3/4/main.py 字段依赖
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
2. Phase 1 output contract test 通过
3. src/phase1_entity_extraction.py 只修改文件头注释
4. main.py 只增加类型标注，不改变行为
5. 未创建 src/phase1/
6. 未修改 Phase 2 / Phase 3 / Phase 4
7. 未修改 schema 结构
8. 未进入 R1
```

---

## v1.2.5：Source Tree Governance

### 定位

源码树治理，让每个 Phase 拥有独立目录和清晰模块命名。

### 目标

从“阶段写在文件名里”升级为“阶段即包”。

当前 dev_spec 已明确主链为 Phase 1 → Phase 2 → Phase 3 → Phase 4，并且当前运行证据边界是 `outputs/runs/<run_id>/`。
但源码仍存在阶段主模块散落在 `src/` 根目录的问题。

### 目标结构

```text
src/
  phase1/
    __init__.py
    extraction.py

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

### 旧入口保留 shim

```text
src/phase1_entity_extraction.py
src/phase2_topology_builder.py
src/phase3_tick_simulation.py
src/phase4_report_agent.py
```

这些旧入口不删除，只作为兼容转发层。

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
```

### 验收条件

```text
1. 旧 import 继续可用
2. 新 phase package 可导入
3. main.py 运行路径不变
4. py_compile 通过
5. contract test 通过
6. 未改变业务逻辑
7. 未删除旧入口
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

### 兼容原则

```text
1. 先迁移，不改语义
2. 旧 import 兼容
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
不改变 Phase 2/3/4 行为
```

### 前置条件

```text
v1.2.5 pass
phase package import 稳定
contract test 存在
```

### 验收条件

```text
1. schema import 全部通过
2. 旧 src.schemas import 继续可用
3. Phase 1 / Phase 2 / Phase 3 / Phase 4 类型可正常引用
4. contract test 通过
5. py_compile 通过
6. 业务主链不改变
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

Compiler：
- 将 parsed payload 规范化
- 做字段别名归一
- 做默认值补齐
- 做 legacy 字段兼容
- 做派生属性保护
- 输出可构造 EntityExtractionOutput 的 canonical payload

Validator：
- 进行确定性 contract validation
- 不依赖 LLM 作为最终质量门
```

### age_range 规则修正

当前已确认一个关键 validator 风险：

```text
模型可能输出 23-35
但旧 Validator 因只接受 20-30 / 30-40 等写死 bucket 而打回
```

新规则：

```text
age_range 是 persona descriptor，不是 strict enum。
Validator 不应因为合理区间未命中固定 bucket 就 hard fail。
```

应接受：

```text
23-35
30-40
45-55
60+
青年
中年
unknown
```

拒绝：

```text
不可解析
年龄明显非法
min_age > max_age
跨度过大且无解释
与 persona 严重冲突
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
```

### 验收条件

```text
1. Parser 能处理当前 LLM 输出
2. Compiler 不改变 EntityExtractionOutput 对外契约
3. Validator 能输出 deterministic pass/fail
4. 合理 age_range 不再被固定枚举误杀
5. 合法旧输出仍能进入 Phase 2
6. 质量门不依赖 LLM 自判
7. 不进入 Repair Loop
```

---

## v1.2.8：ValidationReport + Targeted Repair Loop

### 定位

自修复闭环。

### 目标

失败不再整段重生成，而是结构化报错 + 定向修复。

### 核心链路

```text
Validator failed
  ↓
ValidationReport
  ↓
RepairPromptBuilder
  ↓
LLM targeted repair
  ↓
Parser / Compiler / Validator again
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
不做多模型 profile
不接外部输入
不让 LLM 自称通过
```

### 前置条件

```text
v1.2.7 pass
Parser / Compiler / Validator 稳定
Validation rule_id / failed_fields 足够准确
```

### 验收条件

```text
1. 失败能定位到字段
2. repair prompt 只围绕 failed_fields
3. 最多尝试次数可控
4. repair 后必须重新通过 Parser / Compiler / Validator
5. 失败必须显式终止
6. LLM 不能绕过代码质量门
```

---

## v1.2.9：Diff Reporter + Drift Guard

### 定位

防止 repair 越界漂移。

### 目标

每次 repair 后知道改了什么，并拦截明显越界修改。

### 任务

```text
1. old_object vs repaired_object diff
2. 输出 DiffReport
3. 检查 forbidden changes
4. forbidden_changes 非空时拒绝进入下游
```

### 典型 drift guard 规则

```text
age_range 修复不允许改 event_summary
relation 修复不允许删除 persona
parse_error 修复不允许大面积重写业务字段
只修 failed_fields，不重写 whole object
```

### 不做

```text
不做复杂策略引擎
不做人工 UI
不做多版本自动合并
```

### 前置条件

```text
v1.2.8 pass
Repair Loop 能稳定产生 repaired candidate
ValidationReport 能给出 repair scope
```

### 验收条件

```text
1. 每次 repair 有 DiffReport
2. DiffReport 能列出 added / deleted / modified
3. forbidden_changes 非空时拒绝通过
4. repair drift 被记录到 run artifact
5. 下游契约不被破坏
```

---

## v1.2.10：Multi-model Generation Profile

### 定位

为后续并发和调度服务。

### 目标

比较不同模型在 Phase 1 generation governance 链路中的稳定性。

### 指标

```text
model_name
parse_fail_rate
compile_fail_rate
validate_fail_rate
repair_success_rate
avg_attempts
truncation_rate
known_failure_modes
```

### 不做

```text
不做自动模型路由
不做多模型投票
不做 SideRunner
不影响默认主链
```

### 前置条件

```text
v1.2.7-v1.2.9 稳定
Parser / Compiler / Validator / Repair / Drift Guard 可观测
```

### 验收条件

```text
1. 不同模型可生成 phase1_generation_summary
2. 能比较格式稳定性和 repair 能力
3. 不影响默认主链
4. 不引入调度策略
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

### 前置条件

```text
Phase 1 generation governance 主链稳定
```

### 验收条件

```text
1. 本地 seed 可包装为 InputBundle
2. 当前主链行为不变
3. source_fragments 为空也能运行
4. 未来外部输入有接口位
5. 当前没有任何外部检索实现
```

---

# 5. 大版本总验收条件

整个 Phase 1 Generation Governance Major Track 完成时，必须满足：

```text
1. Phase 1 输出不再裸奔进入下游
2. Parser / Compiler / Validator 职责清楚
3. 合理 age_range 不再被固定枚举误杀
4. ValidationReport 能定位失败字段
5. Repair Loop 是定向修复，不是整段重抽
6. Repair 后有 DiffReport
7. Drift Guard 能阻止明显越界修改
8. 多模型生成表现可观测
9. InputBundle 只保留外部输入接口位，不接外部检索
10. EntityExtractionOutput 仍保持对 Phase 2/3/4 的 canonical object 地位
11. 旧入口 shim 可兼容
12. schema 分层后旧 import 不破坏
13. 质量门权威判断不依赖 LLM
```

一句话验收：

> **Phase 1 可以面对不同模型的不稳定输出，但下游仍然只看到稳定、可校验、可追踪的 canonical object。**

---

# 6. 关键防漂移规则

## 6.1 不允许把外部检索提前塞入本大版本

```text
InputBundle 只做 placeholder。
source_fragments 只允许为空。
```

## 6.2 不允许把 review findings 自动升级为新版本

review findings 先归入当前版本 remediation，只有形成独立主问题时才开新版本。

## 6.3 不允许在 Source Tree Governance 中顺手改业务逻辑

源码树治理只改 import / package / shim，不改行为。

## 6.4 不允许在 Schema Split 中改字段语义

Schema Split 只拆文件，不改字段。

## 6.5 不允许 Validator 变成格式洁癖

尤其是：

```text
age_range 不允许继续 strict bucket hard fail。
```

## 6.6 不允许 LLM 作为质量门最终裁判

```text
LLM 可以生成、修复、解释。
代码负责验收。
DS 负责审计。
Control Agent 负责 gate。
```

---

# 7. 进入每个阶段前必须核对的事项

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
```

## 进入 v1.2.6 前

```text
1. phase package 是否导入稳定
2. shim 是否可用
3. py_compile 是否通过
4. contract test 是否通过
```

## 进入 v1.2.7 前

```text
1. schema split 是否完成
2. 旧 src.schemas import 是否兼容
3. EntityExtractionOutput 是否仍是 canonical object
4. OpinionSpreader @property 是否完整
5. age_range 当前 Validator 位置是否已定位
```

## 进入 v1.2.8 前

```text
1. Parser 是否稳定
2. Compiler 是否能输出 canonical payload
3. Validator rule_id / failed_fields 是否准确
4. ValidationReport 字段是否足够支持 repair prompt
```

## 进入 v1.2.9 前

```text
1. Repair Loop 是否稳定
2. repair scope 是否明确
3. forbidden fields 是否来自 contract
```

## 进入 v1.2.10 前

```text
1. parse / compile / validate / repair / diff 指标是否可记录
2. 默认主链是否稳定
```

## 进入 v1.2.11 前

```text
1. generation governance 主链是否稳定
2. InputBundle 是否只做本地 seed 包装
3. 外部检索是否明确禁止
```

---

# 8. 给 DS 的审计 Prompt

```text
你现在作为 DS / DeepSeek 审计 Agent，审计《Phase 1 Generation Governance Major Track 整体规划 v0.1》。

你的角色：
- 只做方案审计
- 不做最终路线拍板
- 不扩展新架构
- 不建议提前接 Web Search / RAG / MCP
- 不写代码

审计目标：
判断该路线是否满足：
1. 版本边界清晰
2. 每个版本只解决一个主问题
3. v1.2.3 contract 事实被正确继承
4. EntityExtractionOutput canonical object 地位未被破坏
5. src/phase1/ 不存在的历史漂移风险被正确处理
6. Source Tree Governance 与 Parser/Compiler/Validator 是否被合理拆分
7. Schema Split 是否被合理单独拆分
8. age_range 从 strict enum 改为 parseable range validation 是否合理
9. Repair Loop 是否建立在 Parser/Compiler/Validator 稳定之后
10. Diff Guard 是否放在 Repair Loop 之后
11. Multi-model Generation Profile 是否没有过早承担自动路由
12. InputBundle Placeholder 是否没有提前接外部检索
13. 整个路线是否存在过度设计、顺序错误、遗漏前置条件或验收条件不足

重点检查：
- 是否有版本过大
- 是否有任务跨阶段
- 是否有 review finding 被错误升级为独立版本
- 是否有文档治理与代码治理混杂不清
- 是否有 schema 拆分风险被低估
- 是否有 import shim 兼容风险
- 是否有质量门依赖 LLM 自判
- 是否有外部检索提前混入当前大版本

输出格式：
1. 总结论：PASS / PASS_WITH_ISSUES / FAIL
2. 最大风险点 TOP 5
3. 版本顺序是否合理
4. 每个版本是否存在范围过大
5. 缺失的前置条件
6. 缺失的验收条件
7. 是否建议调整版本顺序
8. 是否允许进入 v1.2.4
9. 是否允许在 v1.2.4 后进入 v1.2.5 Source Tree Governance
10. 最终建议

禁止：
- 不要建议接 RAG
- 不要建议接 MCP
- 不要建议接 Web Search
- 不要直接改 roadmap
- 不要给 Codex 执行代码 prompt
```

---

# 9. 当前建议结论

```text
整体路线可以进入 DS 审计。
v1.2.4 可以准备执行。
v1.2.5 之后是否先做 Source Tree Governance，需要 DS 对 import / shim 风险做一次重点审计。
```


