# DS Agent Team 审计结论：Phase 1 大版本迭代总体规划 v0.1

**审计日期**：2026-05-01
**审计方法**：5 Agent 并行审计，逐版本比对源码 + 版本间依赖链验证
**审计对象**：`audit/phase1大版本迭代总体规划v0.1.md`（v1.2.3 → v1.2.11，共 9 个版本）
**审计定位**：方案审计，不做路线拍板，不扩展架构，不写代码

---

## 总结论：PASS_WITH_ISSUES

路线方向正确，版本拆分粒度合理，防漂移规则到位。存在 **3 个 CRITICAL/HIGH 级别缺口**需在进入 v1.2.8 前解决，v1.2.4 可立即执行。

---

## 一、逐版本审计结论

### v1.2.3 → v1.2.4（硬化过渡）

| 审计项 | 结论 | 关键证据 |
|--------|------|---------|
| v1.2.3 11 项声明完成度 | ✅ 11/11 全部确认 | schemas.py:222-240 顶层字段、schemas.py:168-189 @property、phase3_tick_simulation.py:209 ghost field 等 |
| 文件头漂移修复 | ✅ 合理，风险极低 | `phase1_entity_extraction.py:21-22` 声称已迁移到不存在的 `src/phase1/` |
| main.py 类型标注 | ✅ 合理，4 个函数缺标注 | main.py:89/129/159 的 extraction_output 参数无类型 |
| contract test 创建 | ✅ 必要，当前 tests/ 只有 2 个文件 | 合同 6.6 明确指出的缺口 |
| closeout ready 确认 | ✅ | TASK_LOG.md:87、planning:111 |
| 对 v1.2.3 结论的破坏性 | 无 | 类型标注反而强化 canonical object 地位 |

**裁决**：✅ GO — v1.2.4 可立即执行。建议补充一条验收条件：`py main.py seeds/test1.txt` E2E 烟测通过。

---

### v1.2.5（Source Tree Governance）

| 审计项 | 结论 | 关键证据 |
|--------|------|---------|
| 目标结构遗漏 | ⚠️ 4 个模块未归位 | `phase0_entity_extraction.py`, `phase1_persona_engine.py`, `agent_quality_analyzer.py`, `llm_client.py` 未在目标结构中 |
| shim 策略 | ⚠️ 热路径 vs 冷备用未明确 | main.py 是继续走旧 import（shim 热路径）还是切新 import（shim 冷备用）？ |
| Phase 3 包已部分建成 | ⚠️ tick_simulation.py 搬迁需小心 | `src/phase3/` 已有 4 个文件，`phase3_tick_simulation.py` 仍在根目录 |
| 范围合理性 | ✅ 纯文件移动，不改逻辑 | 规划 :251-258 |

**裁决**：⚠️ CONDITIONAL GO — v1.2.4 完成后可进入，但需先确定：(a) 遗漏模块归属 (b) shim 策略 (c) persona_engine 是否归入 `src/phase1/`。

---

### v1.2.6（Schema Split Governance）

| 审计项 | 结论 | 关键证据 |
|--------|------|---------|
| schemas.py 规模 | 667 行 | `wc -l src/schemas.py` |
| 跨阶段类型引用 | ⚠️ NodeRole 被 Phase 1/2/3 共同使用 | `phase1_persona_engine.py:335`、`phase2_topology_builder.py:28`、`phase3_tick_simulation.py:32` |
| common.py 内容未定义 | ⚠️ NodeRole、EntityCategory 归属模糊 | 若放入 phase2.py → Phase 1 出现语义倒挂 `from schemas.phase2 import NodeRole` |
| 循环导入风险 | ✅ 无 | schema 文件间单向依赖 common.py |
| 与 v1.2.5 合并可行性 | ❌ 不建议合并 | v1.2.5 建包通道 → v1.2.6 在通道上重组 schema，跳过第一步归因成本翻倍 |

**裁决**：✅ GO（v1.2.5 通过后）。需先明确 common.py 收纳内容。

---

### v1.2.7（Parser / Compiler / Validator Skeleton）

| 审计项 | 结论 | 关键证据 |
|--------|------|---------|
| Parser 需求来源 | ✅ 已存在 5 级 JSON fallback | `phase1_entity_extraction.py:188-259` markdown fence + 内嵌引号 + 中文弯引号 |
| 当前 Validator 是 LLM | ⚠️ 非确定性校验 | `phase1_entity_extraction.py:692-740` — LLM 返回文本错误列表，无 rule_id/failed_fields |
| age_range 硬编码桶 | ❌ 不存在 | 当前无代码级 age_range 校验，只有 prompt 层面格式示例（:436,485）。下游全为透传字符串，零影响 |
| @property 保护 | ✅ 有效但静默 | `schemas.py:168-189` — @property 覆盖 LLM 输出值，不报错不警告 |
| 失败模式 | ❌ 完全缺失 | 规划未说明 Parser 失败怎么办、Compiler 失败怎么办、Validator 失败时能否 degraded pass |
| 15 条校验规则 → rule_id | ✅ 可完整映射 | `phase1_entity_extraction.py:466-511` R01-R18（3 条为不报错规则） |
| 版本体量 | ⚠️ 偏大 | 4 个组件（Parser+Compiler+Validator+age_range 修正），建议 age_range 规则文档独立冻结 |
| 依赖 v1.2.6 的硬性 | v1.2.5 硬依赖，v1.2.6 软依赖 | 跳过 v1.2.6 技术上可行（import 单体 schema），但 v1.2.6 后续执行时需改 import 路径 |

**裁决**：⚠️ CONDITIONAL GO（v1.2.6 通过后）。必须补充：(a) 各组件失败模式定义 (b) age_range 规则提前文档化 (c) 验收条件增加"contract test 仍通过"。

---

### v1.2.8（ValidationReport + Targeted Repair Loop）

| 审计项 | 结论 | 关键证据 |
|--------|------|---------|
| 当前重试是"整段重生成" | ✅ 规划判断准确 | `phase1_entity_extraction.py:763-810` — error_feedback 只是文本拼接，Generator 重新生成全部 JSON |
| 当前重试次数 | 3 层嵌套，最坏 27 次 LLM 调用 | API 层 3 × Pydantic 层 3 × 业务层 3 |
| 重试间无参数变化 | ✅ temperature 始终 0.7 | `phase1_entity_extraction.py:589` |
| ValidationReport 字段 | ✅ 基本足够 | passed/stage/rule_id/severity/message/failed_fields/expected/actual/repair_hint |
| failed_fields 索引脆弱性 | ⚠️ 数组索引在 repair 后可能位移 | 建议用 name/group_name 做主键定位 |
| **回滚机制** | ❌ **完全缺失** | 全文搜索 rollback/回滚：0 处提及 |
| pre_repair_snapshot | ❌ **未要求保存** | v1.2.9 需要 old_object 做 diff，但 v1.2.8 不产出 |
| 最大 repair 尝试次数 | ❌ 未定义 | 仅说"可控"，建议 5 次（定向修复代价远低于整段重生成） |

**裁决**：⛔ HOLD — 必须先解决回滚机制和 pre_repair_snapshot 保存。这是本审计发现的**最严重缺口**。

---

### v1.2.9（Diff Reporter + Drift Guard）

| 审计项 | 结论 | 关键证据 |
|--------|------|---------|
| 当前 diff 机制 | ❌ 不存在 | `src/agent_quality_analyzer.py:16` import difflib 但用于发言分析，无关 |
| Drift guard 规则 | ⚠️ 遗漏 5 个场景 | 字段类型变化、group_name 重命名、scope creep、Analyzer 产物隐式修改、estimated_percentage 级联 |
| 硬拒绝无退路 | ❌ **流水线死锁风险** | forbidden_changes → reject → ???，无 fallback |
| 依赖 v1.2.8 的稳定性 | ✅ 真实且关键 | repair_success_rate < 50% 时 Diff Guard 价值极低 |
| 与 v1.2.8 合并 | ❌ 不建议 | 各自解决独立问题，但存在数据契约缺口 |

**裁决**：⛔ HOLD（与 v1.2.8 联动）。必须补充：(a) 回退策略 (b) Analyzer 产物保护 (c) 字段类型保护。

---

### v1.2.10（Multi-model Generation Profile）

| 审计项 | 结论 | 关键证据 |
|--------|------|---------|
| 7 个指标可测量性 | ✅ 7/7 可测量，5 个依赖 v1.2.7-v1.2.8 | model_name 和 truncation_rate 已就绪（main.py:236、runtime_logger.py:115） |
| 多模型基础设施 | ✅ 已存在 | config.py:67-86（4 provider）、llm_client.py:53（兼容多 provider） |
| Profile 数据使用边界 | ❌ **重大遗漏** | 只说了"禁止"（路由/投票/SideRunner），没说"允许"（DS 审阅/推荐/调整 prompt） |
| 排在最后的代价 | ⚠️ v1.2.8 开发无跨模型数据 | Parser 设计可能暗含当前模型假设，Repair 策略可能过拟合 |
| 建议调整 | **前移至 v1.2.7 和 v1.2.8 之间** | 至少先评测 P/C/V 链路的跨模型表现 |

**裁决**：✅ GO 但建议前移。需补充 profile 数据允许使用的明确条款。

---

### v1.2.11（InputBundle Placeholder）

| 审计项 | 结论 | 关键证据 |
|--------|------|---------|
| seed_text 来源 | ✅ 仅本地文件 | 6 处引用均为本地文件读取，无外部检索 |
| 双重文件读取 | ⚠️ main.py:316 和 phase1_entity_extraction.py:840 各读一次 | InputBundle 可统一为一次读取 |
| source_fragments 约束 | ⚠️ 仅文档约定，无代码执行 | 建议增加 Pydantic validator 或合约测试 |
| 字段消费者未定义 | ⚠️ source_fragments/manual_notes 将来由谁消费？ | Parser? Compiler? 新预处理步骤？ |

**裁决**：✅ GO（主链稳定后）。需补充 source_fragments 约束的代码级执行。

---

## 二、跨版本风险汇总（TOP 10）

| 排名 | 严重度 | 风险描述 | 涉及版本 | 源码证据 |
|------|--------|---------|---------|---------|
| 1 | **CRITICAL** | Repair Loop 无回滚机制 — 修坏不可逆 | v1.2.8 | 规划 :511-518，全文 0 处提及 rollback/回滚 |
| 2 | **CRITICAL** | Diff Guard 硬拒绝无退路 — 流水线死锁 | v1.2.9 | 规划 :538，forbidden_changes 非空 → reject → ??? |
| 3 | **HIGH** | v1.2.7 各组件失败模式完全缺失 | v1.2.7 | 规划 :413-420 "不做"列表无失败行为定义 |
| 4 | **HIGH** | v1.2.8 不保存 pre_repair_snapshot → v1.2.9 无 old_object | v1.2.8→v1.2.9 | 数据契约缺口 |
| 5 | **HIGH** | v1.2.10 profile 数据使用边界未定义 | v1.2.10 | 只定义禁止，未定义允许 |
| 6 | **MEDIUM** | v1.2.5 目标结构遗漏 4 个模块 | v1.2.5 | persona_engine.py, phase0, analyzer, llm_client |
| 7 | **MEDIUM** | v1.2.7 体量偏大（4 组件） | v1.2.7 | Parser+Compiler+Validator+age_range |
| 8 | **MEDIUM** | v1.2.10 排在最后 → v1.2.8 开发无跨模型数据 | v1.2.10 | 位置规划 :98 |
| 9 | **LOW** | common.py 内容未定义（NodeRole 归属） | v1.2.6 | phase1_persona_engine.py:335 引用 Phase 2 类型 |
| 10 | **LOW** | source_fragments 约束无代码执行 | v1.2.11 | 仅文档约定 :708 |

---

## 三、版本间依赖链验证

```
v1.2.3 ──→ v1.2.4 ──→ v1.2.5 ──→ v1.2.6 ──→ v1.2.7 ──→ v1.2.8 ──→ v1.2.9 ──→ v1.2.10
  ✅          ✅         ✅         ✅         ⚠️         ❌         ❌          ⚠️
                                                      回滚缺失   数据契约   位置争议
                                                               缺口
                                                          
                                                          v1.2.11 ← 仅依赖"主链稳定"
                                                            ⚠️
                                                          约束无执行
```

| 依赖链 | 硬性 | 验证结果 |
|--------|------|---------|
| v1.2.3 → v1.2.4 | 硬依赖 | ✅ v1.2.4 三项任务完全基于 v1.2.3 冻结的契约 |
| v1.2.4 → v1.2.5 | 硬依赖 | ✅ contract test + 类型标注是 Source Tree 安全网 |
| v1.2.5 → v1.2.6 | 硬依赖 | ✅ 包导入通道必须先稳定，再在通道上拆 schema |
| v1.2.6 → v1.2.7 | 软依赖 | ⚠️ 技术上可跳过（import 单体 schema），但后续需改 import 路径 |
| v1.2.7 → v1.2.8 | 硬依赖 | ✅ "稳定"需量化标准，否则边界模糊 |
| v1.2.8 → v1.2.9 | 硬依赖 | ❌ 存在数据契约缺口（old_object） |
| v1.2.9 → v1.2.10 | 可并行 | ⚠️ 建议 v1.2.10 前移至 v1.2.7 后 |

---

## 四、准入判断汇总

| 版本 | 准入 | 条件 |
|------|------|------|
| v1.2.4 | ✅ GO | 立即执行。补充 E2E 烟测验收条件 |
| v1.2.5 | ⚠️ CONDITIONAL | v1.2.4 通过 + 确定遗漏模块归属 + 明确 shim 策略 |
| v1.2.6 | ✅ GO | v1.2.5 通过 + 明确 common.py 内容 |
| v1.2.7 | ⚠️ CONDITIONAL | v1.2.6 通过 + 补充失败模式 + age_range 规则提前冻结 + contract test 重申 |
| v1.2.8 | ⛔ HOLD | 必须先解决回滚机制 + pre_repair_snapshot + 量化"稳定"标准 |
| v1.2.9 | ⛔ HOLD | 与 v1.2.8 联动，增加回退策略 |
| v1.2.10 | ✅ GO（建议前移） | 补充 profile 使用边界 |
| v1.2.11 | ✅ GO | 主链稳定后 + 补充 source_fragments 代码约束 |

---

## 五、建议改动

### v1.2.4 执行前
1. 明确 contract test 的 3-5 条具体断言范围
2. 补充验收条件：E2E 烟测通过

### v1.2.5 执行前
3. 目标结构补全：phase1_persona_engine.py → `src/phase1/persona.py`、phase0 → 标注废弃、llm_client/analyzer → 保留根目录
4. 明确 shim 策略为"冷备用"（main.py 直接走新 import）
5. 补充验收条件：遗漏模块仍可正常 import

### v1.2.6 执行前
6. common.py 明确收纳 NodeRole、EntityCategory

### v1.2.7 执行前
7. **补充失败模式定义**（Parser 失败→终止? Compiler 失败→跳过? Validator 失败→degraded pass?）
8. age_range 规则修正独立文档冻结（不混入 v1.2.7 代码实现）
9. 验收条件增加"contract test 仍通过"
10. 将 15 条校验规则（R01-R18）映射为代码级 rule_id

### v1.2.8 执行前（最关键）
11. **增加 pre_repair_snapshot 保存机制**（为 v1.2.9 铺路）
12. **增加回退机制**（退化检测 + 回退到 pre_repair_snapshot + pass_with_known_issues）
13. 量化 v1.2.7 "稳定"标准（建议：Parser ≥ 95%, Compiler ≥ 98%, Validator 一致性 ≥ 99%）
14. 定义最大 repair 尝试次数（建议 5 次）

### v1.2.9 执行前
15. 增加回退策略（forbidden_changes → 回退 pre_repair_snapshot + pass_with_known_issues）
16. Drift guard 规则补充：Analyzer 产物保护、字段类型保护、scope creep 检测

### v1.2.10
17. 补充 profile 数据"允许"使用条款（DS 审阅/推荐/调整 prompt)
18. 建议前移至 v1.2.7 和 v1.2.8 之间

### v1.2.11
19. source_fragments 约束增加 Pydantic validator 或合约测试

---

## 六、全路线概览

| 版本 | 定位 | 范围 | 准入 | 关键风险 |
|------|------|------|------|---------|
| v1.2.3 | Contract Freeze | 文档 | ✅ 已完成 | — |
| v1.2.4 | R1 Hardening | 3 项低风险变更 | ✅ GO | — |
| v1.2.5 | Source Tree | 4 packages + 4 shims | ⚠️ | 遗漏 4 模块 |
| v1.2.6 | Schema Split | 1→6 文件 | ✅ | common.py 未定义 |
| v1.2.7 | P/C/V Skeleton | 3 组件 + age_range | ⚠️ | 失败模式缺失 |
| v1.2.8 | Repair Loop | ValidationReport + Repair | ❌ | **无回滚** |
| v1.2.9 | Diff Guard | DiffReport + Drift Guard | ❌ | **无退路** |
| v1.2.10 | Multi-model Profile | 7 指标观测 | ⚠️ | 边界未定义 |
| v1.2.11 | InputBundle | Placeholder | ✅ | 约束无执行 |

---

## 七、一句话总结

> 路线设计质量高，边界清晰、原则明确、不做清单比做清单更有力。但 v1.2.8/v1.2.9 缺少运行时回退机制是结构性缺陷——Repair Loop 是 LLM 驱动的不确定系统，没有回滚等于没有安全网。解决这 2 个 HOLD 项后，整条路线可放心推进。

---

*审计团队：5 Agent 并行执行，共检查 13 个源文件、6 个文档文件，采集 150+ 条源码证据，覆盖 9 个版本、13 条总验收条件、6 条防漂移规则。*
