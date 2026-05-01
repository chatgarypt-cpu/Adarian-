# 迭代路线规格书：Phase 1 Generation Governance Long-term Roadmap Spec v0.1

## 📍 版本信息

* **文档类型**：长期路线图 / 内部审计规格书
* **文档版本**：v0.1
* **适用范围**：Adarian MVP Phase 1 生成模块长期治理
* **基于版本**：v1.2.x 当前功能基线
* **目标阶段**：production
* **状态**：待内部审计
* **核心定位**：将 Phase 1 从“LLM 单次生成模块”升级为“可适配多模型、多输入源、可校验、可修复、可审计的生成治理层”

---

## 0. 核心结论

本路线图批准以下长期方向：

```text
Phase 1 不再被定义为一个 Prompt + JSON Parser，
而应逐步升级为 Phase 1 Generation Governance Layer。
```

该治理层的长期目标是：

```text
多输入源可接入
多模型可适配
生成结果可编译
结构错误可定位
失败输出可修复
修复过程可 diff
下游输入可稳定
运行证据可审计
```

但执行原则必须收口：

```text
长期允许模块化设计；
短期只允许最小闭环落地；
每次迭代只解决一个治理层问题；
不得一次性重写 Phase 1。
```

---

# 1. 背景与问题定义

## 1.1 当前 Phase 1 的定位风险

当前 Phase 1 主要承担：

```text
seed text
  ↓
LLM generation
  ↓
JSON parse / validator
  ↓
entities_and_relations.json
  ↓
Phase 2 / Phase 3 / Phase 4
```

该路径当前可以运行，但存在长期风险：

```text
1. LLM 输出格式不稳定
2. Parser 容错压力持续上升
3. Validator 只能判断结果是否合格，不能形成结构化错误资产
4. Retry 更接近重新抽奖，而不是定向修复
5. 下游依赖 Phase 1 输出结构，一旦字段漂移会放大为系统级故障
6. 未来如果接入 RAG / MCP / Web Search / 外部材料，Phase 1 会成为输入污染入口
7. 不同模型的输出风格、JSON 合规能力、截断概率、repair 能力不同，缺少统一适配层
```

---

## 1.2 本路线图要解决的问题

本路线图不是为了解决单次 JSON 解析失败，而是为了解决：

```text
Phase 1 如何长期承接不稳定生成、不稳定模型、不稳定输入源，
同时保证下游 Phase 2/3/4 的输入稳定。
```

---

## 1.3 本路线图不解决的问题

以下内容不纳入本路线图早期实现：

```text
1. 不立即接入 Web Search
2. 不立即接入 MCP
3. 不立即接入 RAG
4. 不立即切换 YAML 为主格式
5. 不重写 Phase 2 / Phase 3 / Phase 4
6. 不重写整体业务 schema
7. 不引入新的模拟范式
8. 不做多模型自动路由
9. 不做 agent 对话机制重构
10. 不做报告生成范式重构
```

---

# 2. 战略目标

## 2.1 长期目标

Phase 1 长期演化为：

```text
Input Adapter
  ↓
LLM Generator
  ↓
Parser
  ↓
Compiler
  ↓
Canonical Intermediate Object
  ↓
Validator
  ↓
ValidationReport
  ↓
Repair Loop
  ↓
Diff Reporter
  ↓
Diff Guard
  ↓
Canonical Phase 1 Output
  ↓
Downstream Phases
```

---

## 2.2 成功标准

长期成功标准：

```text
1. 换模型时，不需要重写 Phase 1 主流程
2. 接外部输入时，不直接污染业务对象
3. LLM 输出失败时，系统能定位失败类型
4. Repair 不再是整段重写，而是局部定向修复
5. 每次 repair 都能知道改了什么
6. 下游 Phase 2/3/4 只消费 canonical output
7. 每次失败、修复、diff、最终接纳都有日志证据
```

---

## 2.3 失败标准

出现以下情况视为路线图执行失败：

```text
1. 一次性重写 Phase 1
2. YAML 替代 JSON 成为主目标
3. 为了 repair loop 改坏 Phase 2/3/4 契约
4. 让 LLM 承担确定性 Validator 职责
5. 引入外部检索但没有 source boundary
6. repair 后无法知道改了哪些字段
7. 新增模块没有 run_dir 证据
8. 长期架构设计导致当前主链不可运行
```

---

# 3. 架构变更说明

## 3.1 当前结构问题

当前 Phase 1 存在职责混合：

```text
LLM 负责生成
Parser 负责救火
Validator 负责兜底
Retry 负责重新尝试
下游直接依赖最终 JSON
```

问题在于：

```text
1. 生成、解析、校验、修复、审计没有清晰边界
2. 错误没有结构化沉淀
3. repair 不是工程闭环，而是再次生成
4. 模型差异没有被抽象
5. 外部输入未来缺少安全入口
```

---

## 3.2 目标结构

目标模块划分：

```text
Module A：Input Adapter Layer
- 负责把 seed / 外部材料 / RAG 片段 / 人工补充材料包装成统一 InputBundle

Module B：Generation Layer
- 负责调用 LLM 生成候选结构
- 不直接决定结果能否进入下游

Module C：Parser Layer
- 负责从 raw_text 提取 JSON/YAML/dict
- 输出 ParseResult / ParseError

Module D：Compiler Layer
- 负责把松散 dict 编译为 canonical object
- 做字段归一、类型归一、枚举归一、引用预处理

Module E：Validator Layer
- 负责确定性校验
- 输出 ValidationReport

Module F：Repair Loop Layer
- 负责根据 ValidationReport 构造定向修复 prompt
- 不允许无边界重写

Module G：Diff Reporter / Diff Guard
- 负责比较 repair 前后对象
- 防止修复漂移

Module H：Model Adapter / Model Profile
- 负责记录不同模型在 Phase 1 的失败模式和稳定性指标

Module I：Run Evidence Layer
- 负责把 parse / compile / validate / repair / diff 证据写入 run_dir
```

---

## 3.3 本路线图涉及层级

* [x] Entity Extractor
* [x] Group Planner
* [x] Persona Writer
* [x] Assembler / Rules Engine
* [ ] Phase 2
* [ ] Phase 3
* [ ] Phase 4
* [x] Runtime Logging
* [x] Run Artifact Governance
* [x] Whitebox Observability

明确边界：

```text
本路线图只治理 Phase 1 输入与输出稳定性。
不得改变 Phase 2/3/4 的业务语义。
```

---

# 4. 长期数据流设计

## 4.1 旧流程

```text
seed.txt
  ↓
Phase 1 Prompt
  ↓
LLM raw output
  ↓
JSON parse
  ↓
Validator
  ↓
失败则重试
  ↓
entities_and_relations.json
  ↓
Phase 2
```

---

## 4.2 目标流程

```text
Raw Inputs
  ↓
InputAdapter
  ↓
InputBundle
  ↓
Phase1Generator
  ↓
RawGenerationCandidate
  ↓
Parser
  ↓
ParsedPayload
  ↓
Compiler
  ↓
CanonicalPhase1Object
  ↓
Validator
  ↓
ValidationReport
  ↓
Repair Loop if failed
  ↓
Diff Reporter
  ↓
Diff Guard
  ↓
AcceptedPhase1Output
  ↓
entities_and_relations.json
  ↓
Phase 2 / Phase 3 / Phase 4
```

---

## 4.3 兼容性说明

* [ ] 完全兼容
* [x] 部分变更
* [ ] 不兼容

说明：

```text
1. 对下游保持兼容：entities_and_relations.json 顶层契约不得破坏
2. 对 Phase 1 内部允许新增治理层
3. 对 run_dir 允许新增 generation governance 证据文件
4. 对旧字段只允许保留或补强，不允许删除
5. 对模型输出格式允许增强，但最终输出必须 compile 回 canonical object
```

---

# 5. Roadmap 分阶段规格

---

# R0：Phase 1 Output Contract Freeze

## 阶段目标

冻结当前 Phase 1 对下游的输出契约。

## 核心问题

```text
在没有确认下游真实依赖字段前，任何 Compiler / Intermediate Object / Repair Loop 都缺少锚点。
```

## 本阶段只做

```text
1. 审计 Phase 2 / Phase 3 / Phase 4 实际读取 Phase 1 的字段
2. 标记 required / optional / legacy / deprecated 字段
3. 标记禁止破坏字段
4. 标记未来可迁移到 intermediate object 的字段
5. 输出 Phase 1 Output Contract 文档
```

## 本阶段不做

```text
1. 不改代码
2. 不新增 Parser
3. 不新增 Compiler
4. 不新增 YAML
5. 不新增 Repair Loop
```

## 产物

```text
docs/iterations/phase1-output-contract-freeze.md
```

## 验收标准

```text
1. 明确 Phase 1 当前输出字段全集
2. 明确下游真实依赖字段
3. 明确当前不可删除字段
4. 明确可选字段与未来迁移字段
5. 审计结论可作为后续 Compiler 设计依据
```

## Gate

```text
没有 R0，不允许进入 R1。
```

---

# R1：Parser + Compiler + Validator Skeleton

## 阶段目标

建立最小 generation governance skeleton。

## 本阶段只做

```text
1. 新增 Parser
2. 新增轻量 Compiler
3. 新增确定性 Validator
4. 新增结构化 ValidationReport
5. 主流程仍输出旧 entities_and_relations.json
```

## 推荐新增文件

```text
src/phase1/generation_guard/__init__.py
src/phase1/generation_guard/parser.py
src/phase1/generation_guard/compiler.py
src/phase1/generation_guard/validator.py
src/phase1/generation_guard/reports.py
```

## Parser 责任

```text
raw_text → parsed_payload
```

检查：

```text
1. 是否为空
2. 是否存在 markdown fence
3. 是否存在解释性前后缀
4. 是否 JSON 可解析
5. 是否疑似截断
```

## Compiler 责任

```text
parsed_payload → canonical_phase1_object
```

只做：

```text
1. 字段别名归一
2. group_id 归一
3. stance / actor_type / relation_type 枚举归一
4. list / dict 类型归一
5. 下游 required 字段补齐检查
```

不做：

```text
1. 不做业务质量判断
2. 不做事实核验
3. 不做外部检索
4. 不改变下游 schema
```

## Validator 责任

第一版只做确定性检查：

```text
1. event_entities 非空
2. opinion_spreaders 非空
3. group_id 唯一
4. relation from/to 引用存在
5. required fields 存在
6. enum 合法
7. 数值范围合法
8. can_speak 字段存在
9. 疑似截断检测
```

## 本阶段不做

```text
1. 不做 Repair Loop
2. 不做 Diff Guard
3. 不做 YAML 主入口
4. 不做外部输入
5. 不改 Phase 2/3/4
```

## 验收标准

```text
1. parse 失败有 ParseError
2. compile 失败有 CompileError
3. validate 失败有 ValidationReport
4. ValidationReport 包含 failed_fields / rule_id / severity / repair_hint
5. 合法输出仍能进入 Phase 2
6. py main.py seeds/test7.txt 通过
```

## Gate

```text
R1 通过后，才允许进入 R2。
```

---

# R2：Targeted Repair Loop

## 阶段目标

把失败后的“重新生成”升级为“定向修复”。

## 本阶段只做

```text
1. RepairPromptBuilder
2. previous_output + ValidationReport 驱动 repair
3. 最多尝试次数控制
4. repair 结果重新进入 Parser / Compiler / Validator
```

## 推荐新增文件

```text
src/phase1/generation_guard/repair.py
```

## Repair 输入

```text
1. original_task
2. previous_output
3. ValidationReport
4. failed_fields
5. repair_hint
6. forbidden_change_scope
```

## Repair 输出

```text
repaired_raw_output
```

## Repair 约束

```text
1. 不允许无关字段重写
2. 不允许删除已通过字段
3. 不允许改变 event_frame，除非 failed_fields 指向 event_frame
4. 不允许改变 group_id，除非引用错误要求修复
5. 不允许改变下游契约字段名称
```

## 本阶段不做

```text
1. 不做 DiffGuard
2. 不做 YAML
3. 不做多模型路由
4. 不做外部输入
```

## 验收标准

```text
1. validate failed 后进入 repair，而不是直接 full regenerate
2. repair prompt 能定位 failed_fields
3. repair 后重新 parse / compile / validate
4. 最多尝试次数可控
5. repair 全失败时显式终止，不伪装成功
```

## Gate

```text
R2 通过后，才允许进入 R3。
```

---

# R3：Diff Reporter + Minimal Diff Guard

## 阶段目标

防止 repair loop 引入结构漂移。

## 本阶段只做

```text
1. 计算 repair 前后 object diff
2. 输出 DiffReport
3. 拦截明显越界修改
```

## 推荐新增文件

```text
src/phase1/generation_guard/diff.py
src/phase1/generation_guard/diff_guard.py
```

## DiffReport 字段

```text
added
deleted
modified
forbidden_changes
diff_summary
```

## Minimal Diff Guard 规则

```text
1. 如果 failed_fields 只在 relations：
   - 不允许修改 event_summary
   - 不允许删除 opinion_spreaders
   - 不允许删除 event_entities

2. 如果 failed_fields 只在 opinion_spreaders：
   - 不允许修改 event_summary
   - 不允许删除 event_entities

3. 如果 failed_fields 是 parse_error：
   - 只允许格式修复
   - 不允许大面积业务字段变化

4. 如果 repair 后 required fields 减少：
   - 直接拒绝
```

## 本阶段不做

```text
1. 不做复杂策略引擎
2. 不做人工 UI
3. 不做多版本合并
4. 不做业务事实判断
```

## 验收标准

```text
1. 每次 repair 后生成 DiffReport
2. DiffReport 写入 run_dir
3. forbidden_changes 非空时拒绝进入下游
4. repair drift 能被显式记录
```

## Gate

```text
R3 通过后，才允许进入 R4。
```

---

# R4：Model Adapter + Phase1 Generation Profile

## 阶段目标

让 Phase 1 具备多模型测试的可观测能力。

## 本阶段只做

```text
1. 记录不同模型在 Phase 1 的生成表现
2. 输出 phase1_generation_summary.json
3. 建立 model failure mode registry
```

## 推荐新增文件

```text
src/phase1/generation_guard/model_adapter.py
src/phase1/generation_guard/model_profile.py
```

## 指标字段

```text
model_name
attempt_count
parse_fail_count
compile_fail_count
validate_fail_count
repair_success_count
repair_fail_count
truncation_count
avg_attempts
final_acceptance_rate
known_failure_modes
```

## 本阶段不做

```text
1. 不做自动模型选择
2. 不做多模型投票
3. 不做 SideRunner
4. 不做调度策略
```

## 验收标准

```text
1. 不同模型运行 Phase 1 后能生成对比摘要
2. summary 不影响主链运行
3. 默认模型路径保持不变
4. 模型失败模式进入 run_dir 证据
```

## Gate

```text
R4 通过后，才允许进入 R5。
```

---

# R5：InputBundle + Input Adapter Skeleton

## 阶段目标

为未来外部数据源接入预留稳定入口。

## 本阶段只做

```text
1. 定义 InputBundle
2. 定义 SourceFragment
3. 定义 SourceMetadata
4. 当前 seed.txt 通过 InputAdapter 包装
5. Phase 1 Generator 从 InputBundle 读取内容
```

## 推荐新增文件

```text
src/phase1/input_adapter.py
src/phase1/input_models.py
```

## InputBundle 建议字段

```text
seed_text
source_fragments
manual_notes
source_metadata
input_mode
created_at
```

## SourceFragment 建议字段

```text
source_id
source_type
content
title
timestamp
reliability_hint
retrieval_method
```

## 本阶段不做

```text
1. 不联网
2. 不接 MCP
3. 不接 RAG
4. 不做 source ranking
5. 不做事实核验
6. 不把 source_basis 传入最终报告
```

## 验收标准

```text
1. seed.txt 能被包装为 InputBundle
2. 当前主链运行结果不发生结构性变化
3. Phase 1 generator 不再直接依赖裸 seed 字符串
4. 未来外部 source 可作为 SourceFragment 接入
```

## Gate

```text
R5 通过后，才允许进入 R6。
```

---

# R6：External Retrieval Readiness Review

## 阶段目标

在接入 Web / RAG / MCP 之前完成安全与责任边界审计。

## 本阶段只做审计，不做实现。

## 审计问题

```text
1. 外部输入是否会污染 seed facts？
2. 是否需要区分 user-provided facts 与 retrieved facts？
3. 是否需要 source credibility 字段？
4. 是否需要 fact_usage trace？
5. source_basis 是否需要进入 Phase 3？
6. source_basis 是否需要进入 Phase 4？
7. 政府决策报告是否允许引用未核验外部材料？
8. 外部材料失败时是否允许 fallback 到 seed-only？
```

## 本阶段不做

```text
1. 不接 MCP
2. 不接 Web Search
3. 不接 RAG
4. 不接数据库
5. 不改报告格式
```

## 验收标准

```text
1. 输出 External Retrieval Readiness Review
2. 明确允许接入的数据源类型
3. 明确禁止接入的数据源类型
4. 明确 source trace 责任边界
5. 明确失败 fallback 策略
```

---

# 6. 字段职责迁移

## 6.1 从 LLM 移除，改为代码处理

```text
parse_status
compile_status
validation_status
rule_id
failed_fields
repair_hint
diff_report
forbidden_changes
attempt_count
truncation_detected
model_failure_mode
```

原因：

```text
这些字段属于系统治理、校验、审计职责，必须由代码层生成。
```

---

## 6.2 保留在 LLM

```text
event_summary
event_entities 初稿
opinion_spreaders 初稿
relations 初稿
persona 表达层内容
group narrative
event controversy interpretation
```

原因：

```text
这些字段仍属于语义生成与社会解释任务。
```

---

## 6.3 延后生成

```text
source_basis
fact_usage_trace
retrieval_confidence
external_source_ranking
semantic_delta_reason
influence_trace
multi-model arbitration result
RAG citation chain
```

原因：

```text
这些字段依赖外部输入治理或后续可解释性链路，不应在早期 generation governance 中提前实现。
```

---

# 7. 文件变更长期清单

## 7.1 允许新增目录

```text
src/phase1/generation_guard/
```

## 7.2 长期允许新增文件

```text
src/phase1/generation_guard/__init__.py
src/phase1/generation_guard/parser.py
src/phase1/generation_guard/compiler.py
src/phase1/generation_guard/validator.py
src/phase1/generation_guard/reports.py
src/phase1/generation_guard/repair.py
src/phase1/generation_guard/diff.py
src/phase1/generation_guard/diff_guard.py
src/phase1/generation_guard/model_adapter.py
src/phase1/generation_guard/model_profile.py
src/phase1/input_adapter.py
src/phase1/input_models.py
```

## 7.3 允许修改文件

```text
src/phase1_entity_extraction.py
src/phase1/orchestrator.py
src/phase1/rules_engine.py
src/schemas.py
main.py（仅限 run_dir 证据路径传递）
src/utils/runtime_logger.py（仅限新增 summary 记录）
docs/iterations/CHANGELOG.md
docs/iterations/TASK_LOG.md
docs/dev_spec.md
```

## 7.4 明确禁止早期修改

```text
src/phase2_topology_builder.py
src/phase3_tick_simulation.py
src/phase3/speaker_selector.py
src/phase3/context_builder.py
src/phase3/state_updater.py
src/phase4_report_agent.py
profiling/
CLI
MCP / Web Search / RAG 相关模块
```

---

# 8. Run Artifact 证据要求

每次 Phase 1 generation governance 生效后，run_dir 至少允许新增：

```text
phase1_generation_summary.json
phase1_validation_report.json
phase1_repair_attempts.json
phase1_diff_report.json
```

最低要求：

```text
1. parse / compile / validate / repair 状态可追踪
2. 失败原因可定位
3. 修复次数可统计
4. repair 前后 diff 可审计
5. 最终 accepted object 可回放
```

---

# 9. 验收标准

## 9.1 模块级验收

* [ ] Parser 是否只负责解析，不承担业务判断
* [ ] Compiler 是否只做规范化和对象编译
* [ ] Validator 是否为确定性代码规则
* [ ] Repair Loop 是否基于 ValidationReport
* [ ] Diff Guard 是否能拦截明显越界
* [ ] Model Profile 是否只做观测，不做路由
* [ ] Input Adapter 是否只做包装，不做事实判断

---

## 9.2 行为验收

必须运行：

```bash
py main.py seeds/test7.txt
```

最低通过标准：

```text
1. 退出码为 0
2. run_dir 正常生成
3. entities_and_relations.json 正常生成
4. social_graph.json 正常生成
5. tick_logs.json 正常生成
6. final_report.md 正常生成
7. 新增 governance 证据文件正常生成
8. 旧字段未删除
9. Phase 2/3/4 行为不发生结构性破坏
```

---

## 9.3 回归验收

必须验证：

```bash
py -m py_compile src/phase1_entity_extraction.py
py -m py_compile src/phase1/orchestrator.py
```

如新增 generation_guard：

```bash
py -m py_compile src/phase1/generation_guard/parser.py
py -m py_compile src/phase1/generation_guard/compiler.py
py -m py_compile src/phase1/generation_guard/validator.py
```

---

# 10. 实现约束

```text
1. 不允许跳过 Pre-Implementation Review
2. 不允许一次性实现 R1-R6
3. 不允许为了长期架构破坏当前主链
4. 不允许让 LLM 生成 ValidationReport 的权威字段
5. 不允许把 YAML 作为早期主目标
6. 不允许提前接入外部检索
7. 不允许修改 Phase 2/3/4 契约
8. 不允许删除旧字段
9. 不允许用 prompt 修复结构问题
10. 不允许新增未声明的架构层
```

---

# 11. 内部审计判断

## 11.1 合规项

```text
1. 该路线图符合最小收口原则
2. 该路线图保留长期模块化能力
3. 该路线图没有立即引入外部检索风险
4. 该路线图没有破坏 Phase 2/3/4
5. 该路线图将 LLM 不稳定性隔离在治理层内
6. 该路线图支持未来多模型评测
```

## 11.2 风险项

```text
1. 如果 R0 不做，后续 Compiler 会缺少契约锚点
2. 如果 R1-R3 合并过大，容易形成 Phase 1 重构事故
3. 如果过早接 YAML，会转移问题焦点
4. 如果过早接 RAG，会污染 seed-only baseline
5. 如果 DiffGuard 不做，Repair Loop 可能引入新漂移
```

## 11.3 审计结论

```text
通过长期方向。
不批准一次性完整实现。
批准按 R0 → R1 → R2 → R3 → R4 → R5 → R6 单路径推进。
```

---

# 12. 唯一下一步动作

```text
先执行 R0：Phase 1 Output Contract Freeze。
```

R0 完成前，不允许进入 Parser / Compiler / Repair Loop 实现。

---

# 13. 给 Codex / 内部审计 Agent 的完整执行 Prompt

```text
你现在接手 Adarian MVP 的 Phase 1 Generation Governance 长期路线审计任务。

当前目标不是实现代码，而是完成 R0：Phase 1 Output Contract Freeze。

任务背景：
Adarian 当前 Phase 1 负责从 seed text 生成 entities_and_relations.json，并供 Phase 2 / Phase 3 / Phase 4 使用。后续计划将 Phase 1 从“LLM 单次生成 + JSON Parser + Validator”升级为“Parser-Compiler-Validator-Repair-DiffGuard”的生成治理层。但在任何实现前，必须先冻结当前 Phase 1 输出契约，避免后续重构破坏下游。

你的唯一任务：
审计当前源码中 Phase 2 / Phase 3 / Phase 4 实际读取 Phase 1 输出的哪些字段，并形成 Phase 1 Output Contract Freeze 文档。

必须完成：
1. 搜索并阅读以下相关文件：
   - src/phase1_entity_extraction.py
   - src/phase1/orchestrator.py
   - src/phase1/rules_engine.py
   - src/schemas.py
   - src/phase2_topology_builder.py
   - src/phase3_tick_simulation.py
   - src/phase4_report_agent.py
   - main.py

2. 输出字段分级：
   - required_fields：下游实际依赖，不能删除
   - optional_fields：当前存在但下游非强依赖
   - legacy_fields：为兼容保留
   - candidate_intermediate_fields：未来可迁移到 intermediate object
   - forbidden_to_change_fields：短期禁止变更字段

3. 明确 Phase 1 当前输出对象：
   - event_summary
   - event_scale
   - event_controversy
   - event_type
   - event_entities
   - opinion_spreaders
   - relations
   - I / P / C / stance_score / susceptibility
   - can_speak / original_statement 等相关字段

4. 审计下游使用方式：
   - Phase 2 使用哪些字段建图
   - Phase 3 使用哪些字段进行 tick simulation / speaker behavior
   - Phase 4 使用哪些字段生成 final_report
   - main.py 如何传递 Phase 1 输出

5. 输出文档：
   - docs/iterations/phase1-output-contract-freeze.md

文档结构必须包含：
- 版本信息
- 当前 Phase 1 输出结构
- 下游字段依赖表
- required / optional / legacy / forbidden 字段分级
- 未来 Compiler 输入输出边界建议
- 不允许变更清单
- 后续 R1 Parser-Compiler-Validator 的准入条件
- 验收标准

严格约束：
- 不修改任何业务代码
- 不新增 Parser
- 不新增 Compiler
- 不新增 Repair Loop
- 不新增 YAML 支持
- 不接外部检索
- 不修改 Phase 2 / Phase 3 / Phase 4
- 本轮只做只读审计与文档输出

验收标准：
- 能明确回答 Phase 1 哪些字段是下游必须依赖
- 能明确回答哪些字段未来可以进入 intermediate object
- 能明确回答哪些字段短期绝对不能动
- 文档可作为后续 R1 实现 Parser / Compiler / Validator 的依据

输出时请附带：
- 实际审计文件列表
- 字段依赖表
- 风险判断
- 是否允许进入 R1 的结论
```

---

# 14. 最终收口判断

```text
当前不进入实现。
当前只进入 R0 契约冻结。
```

这是最稳路径。先把 Phase 1 的真实契约钉死，再谈 Compiler、Repair Loop 和 Diff Guard。
