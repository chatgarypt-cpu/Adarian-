# Adarian MVP 变更日志 (CHANGELOG)

所有重要版本变更都会记录在此文档中。

---

## 文档变更记录

### 2026-03-30

| 文档 | 变更内容 |
|------|---------|
| `README.md` | 重写，更新项目结构、核心概念、当前版本为 v1.1.9 |
| `dev_spec.md` | 新增第3章「核心参数定义手册」，修订章节编号，添加变更记录表头 |
| `dev_workflow.md` | 精简为流程指南，移除过时内容，引用 dev_spec.md |

---

## 代码变更记录

## v1.1.11 (2026-04-02)（已完成）

**主题**：IPC 框架 Phase 1 重构 - 引入 SEIR 观点动力学三维参数

### Breaking Change
- **event_temperature/event_intensity 废除** → 替换为 event_scale/event_controversy
- **stance_score 废除** → 替换为 I（强度）+ P（方向）
- **confirmation_bias_level 废除** → 由 I 推导
- **group_distribution_strategy 废除** → 由 event_controversy 控制

### 新增
- [schemas.py] `OpinionSpreader.I` - 立场强度 (1-10)
- [schemas.py] `OpinionSpreader.P` - 立场方向 (+1/-1)
- [schemas.py] `OpinionSpreader.C` - 一致性（计算属性，C = P × I/10）
- [schemas.py] `OpinionSpreader.stance_score` - 兼容属性（I/P → 1-10 映射）
- [schemas.py] `OpinionSpreader.confirmation_bias_level` - 兼容属性（由 I 推导）
- [schemas.py] `EntityExtractionOutput.event_scale` - 事件规模
- [schemas.py] `EntityExtractionOutput.event_controversy` - 事件争议性

### 修改
- [Phase 1] Analyzer Prompt 重写 - 输出 event_scale + event_controversy + event_type
- [Phase 1] Generator Prompt 重写 - 输出 I + P，移除 stance_score/confirmation_bias_level
- [Phase 1] Validator Prompt 重写 - 校验 I ∈ [1,10]，P ∈ {+1,-1}
- [Phase 1] 后处理逻辑更新 - 校验双向对立（P=+1 和 P=-1）
- [main.py] event_temperature/intensity 引用 → event_scale/event_controversy
- [phase4_report_agent.py] 报告中的事件参数引用更新
- [dev_spec.md] 第3章参数定义、第4章数据流全面更新

### 功能
- ✅ IPC 三维参数框架：I（强度）/ P（方向）/ C（一致性）
- ✅ event_scale 决定 Agent 总人数和 I 分布
- ✅ event_controversy 决定 P（立场方向）分布比例
- ✅ 极化从 I/P 分布自然涌现

### 向后兼容
- `OpinionSpreader.stance_score` 作为兼容属性保留
- `OpinionSpreader.confirmation_bias_level` 作为兼容属性保留
- Phase 2/3/4 无需修改即可正常工作

**详细文档**：[v1.1.11_ipc_phase1_redesign.md](./v1.1.11_ipc_phase1_redesign.md)
**完成时间**：2026-04-02

---

## v1.1.10 (2026-03-31)（已完成）

### Bug Fix
- **stance_score 描述修正**：修复 dev_spec.md 第3.1节内部矛盾，删除错误的警告文字（原"1分=最支持，10分=最批评"）
- **schemas.py stance_score 描述修正**：`src/schemas.py` OpinionSpreader 和 Archetype 的 stance_score description 修正为"1.0-3.0=强烈批评，4.0-6.0=中立观望，7.0-10.0=强烈支持"

### Documentation
- **LLM 角色重命名**：Phase 1 的 LLM1/2/3 正式更名为 Analyzer/Generator/Validator
  - `llm1_set_parameters` → `analyzer_set_parameters`
  - `llm2_generate_entities` → `generator_create_entities`
  - `llm3_validate` → `validator_check_format`
  - Prompt 常量全部重命名（LLM1_SYSTEM_PROMPT → ANALYZER_SYSTEM_PROMPT 等）
- **更新所有引用文件**：main.py, README.md, CLAUDE.md, schemas.py, __init__.py, dev_spec.md

### 详细文档
- [v1.1.10_stance_and_naming_fix.md](./v1.1.10_stance_and_naming_fix.md)
- **完成时间**：2026-03-31

---

## v1.1.9 (2026-03-30)（已完成）

### Bug Fix
- **数据源修复**：最终报告立场变化数据从 tick_log[1] 和 tick_log[-1] 读取，而非 tick_log[0]（事件实体）和 tick_log[-1]。修复了意见传播实体立场变化始终为 0 的问题。

### Feature
- **susceptibility 简单接入**：susceptibility 字段接入 stance 变化约束逻辑，高 susceptibility agent 可获得更大的变化幅度（通过 SUSCEPTIBILITY_MODULATION_FACTOR 调制）
- **tick_log 扩展**：AgentEntry 新增 `susceptibility` 和 `change_reason` 字段，便于后续分析

### 配置
- 新增 `SUSCEPTIBILITY_MODULATION_FACTOR = 0.5` 参数

---

## v1.1.8 - 2026-03-29（已完成）

**主题**：报告 Agent 优化 - 增强报告可读性和洞察深度

### 新增
- [Phase 4] 新增 `build_full_report_context` 函数 - 构建完整报告上下文数据
- [Phase 4] 新增模块级变量 `_llm_generated_markdown` - 存储 LLM 生成的 Markdown

### 修改
- [Phase 4] 重构 `REPORT_SYSTEM_PROMPT` - 新的 Markdown 报告结构和生成指令
- [Phase 4] 重构 `generate_report_with_llm` - 直接生成 Markdown 格式报告
- [Phase 4] 修改 `parse_llm_report_response` - 适配新的 Markdown 响应格式
- [Phase 4] 修改 `save_markdown_report` - 使用 LLM 生成的 Markdown 内容

### 功能
- ✅ 报告结构重构（10 个章节：概要 → 实体 → Tick0发言 → 拐点 → 演化 → 立场变化 → 极化轨迹 → 洞察 → 态势 → 风险）
- ✅ 增加 Tick 0 事件实体发言展示
- ✅ 增加关键拐点识别（极化变化 > 0.05 或立场偏移 > 1.5）
- ✅ 增加 Tick 1-N 意见演化展示（首尾对比）
- ✅ 增加最终立场变化表格
- ✅ 增加极化演化轨迹可视化
- ✅ 增加关键洞察生成（3-6 条核心发现）
- ✅ 增加舆论态势判断（四维度分析）

**详细文档**：[v1.1.8_report_agent_enhanced.md](./v1.1.8_report_agent_enhanced.md)
**完成时间**：2026-03-29

---

## v1.1.8 - 2026-03-29（已完成）

**主题**：报告 Agent 优化 - 增强报告可读性和洞察深度

### 新增
- [Phase 4] 新增 `build_full_report_context` 函数 - 构建完整报告上下文数据
- [Phase 4] 新增模块级变量 `_llm_generated_markdown` - 存储 LLM 生成的 Markdown

### 修改
- [Phase 4] 重构 `REPORT_SYSTEM_PROMPT` - 新的 Markdown 报告结构和生成指令
- [Phase 4] 重构 `generate_report_with_llm` - 直接生成 Markdown 格式报告
- [Phase 4] 修改 `parse_llm_report_response` - 适配新的 Markdown 响应格式
- [Phase 4] 修改 `save_markdown_report` - 使用 LLM 生成的 Markdown 内容

### 功能
- ✅ 报告结构重构（10 个章节：概要 → 实体 → Tick0发言 → 拐点 → 演化 → 立场变化 → 极化轨迹 → 洞察 → 态势 → 风险）
- ✅ 增加 Tick 0 事件实体发言展示
- ✅ 增加关键拐点识别（极化变化 > 0.05 或立场偏移 > 1.5）
- ✅ 增加 Tick 1-N 意见演化展示（首尾对比）
- ✅ 增加最终立场变化表格
- ✅ 增加极化演化轨迹可视化
- ✅ 增加关键洞察生成（3-6 条核心发现）
- ✅ 增加舆论态势判断（四维度分析）

**详细文档**：[v1.1.8_report_agent_enhanced.md](./v1.1.8_report_agent_enhanced.md)
**完成时间**：2026-03-29

---

## v1.1.7 - 2026-03-29（已完成）

**主题**：意见传播者群体生成优化 - 修复强制立场分布问题

### 新增
- [schemas.py] 新增 `group_distribution_strategy` 字段（normal/minimal_supporters/no_supporters）
- [schemas.py] 新增 `has_official_response` 字段（官方是否回应）
- [schemas.py] 新增 `official_admits_fault` 字段（官方是否承认错误）

### 修改
- [Phase 1] LLM1 Prompt 增加群体分布策略判断逻辑
- [Phase 1] LLM2 Prompt 根据策略调整群体生成规则（no_supporters 时不生成支持者）
- [Phase 1] LLM3 Prompt 增加群体分布合理性校验
- [Phase 1] `llm1_set_parameters` 返回新增的策略字段
- [Phase 1] `llm2_generate_entities` 增加 `group_distribution_strategy` 参数
- [Phase 1] `llm3_validate` 增加 `group_distribution_strategy` 参数
- [Phase 1] `extract_entities_with_validation` 传递策略参数到各函数
- [Phase 3] `SimulationEngine` 增加 `group_distribution_strategy` 属性
- [Phase 3] `generate_opinion_spreader_post` 增加舆论压力提示
- [Phase 3] `apply_stance_constraint` 增加舆论压力机制（minimal_supporters 策略下）

### 功能
- ✅ 高烈度负面事件（鼠头、胖猫）不再生成不真实的"校方支持者"、"譚竹支持者"
- ✅ LLM1 自动判断群体分布策略
- ✅ LLM3 校验群体分布是否符合策略
- ✅ minimal_supporters 策略下支持者立场会受舆论压力影响略微下降

**详细文档**：[v1.1.7_opinion_spreader_distribution_fix.md](./v1.1.7_opinion_spreader_distribution_fix.md)
**完成时间**：2026-03-29

---

## v1.1.6 - 2026-03-29（已完成）

**主题**：事件实体发言逻辑修复 - 禁止已故/匿名实体发言，提取原始发言

### 新增
- [schemas.py] 新增 `can_speak: bool` 字段 - 是否可以发言（无默认值）
- [schemas.py] 新增 `original_statement: Optional[str]` 字段 - 原始发言（从种子材料提取）

### 修改
- [Phase 1] LLM2 Prompt 增加 `can_speak` 和 `original_statement` 字段说明
- [Phase 1] LLM3 Prompt 增加 `can_speak` 合理性校验规则
- [Phase 3] `run_tick_0()` 增加 `can_speak` 检查
- [Phase 3] `run_tick_0()` 优先使用 `original_statement`
- [Phase 3] `EVENT_ENTITY_POST_SYSTEM_PROMPT` 增加"禁止事后声明"指令
- [Phase 4] 报告生成区分"发言实体"和"被讨论实体"

### 功能
- ✅ 已故/匿名实体（如胖猫、当事学生）不再在 Tick 0 发言
- ✅ 从种子材料中提取原始发言（如"哪位少爺吸了"）
- ✅ Tick 0 优先使用原始发言，不调用 LLM 生成
- ✅ 报告中区分"发言实体"和"被讨论实体"

**详细文档**：[v1.1.6_entity_speak_logic_fix.md](./v1.1.6_entity_speak_logic_fix.md)
**完成时间**：2026-03-29

---

## v1.1.5 - 2026-03-26（已完成）

**主题**：Agent 多样性增强与发言差异化

### 新增
- [src] 新增 `agent_quality_analyzer.py` Agent 质量分析模块

### 修改
- [Phase 1] LLM2 temperature=0.7（输出更发散）
- [Phase 1] description 长度约束 15-50 字
- [Phase 1] communication_style 要求多样化
- [Phase 3] 事件实体使用 temperature=0.3（输出更稳定）
- [Phase 3] 意见传播者使用 temperature=0.8（输出更多样化）

### 功能
- ✅ Agent 质量分析工具：立场分布、描述多样性、风格多样性、逻辑一致性
- ✅ Phase 3 差异化温度配置

---

## v1.1.4 - 2026-03-26（已完成）

**主题**：实体分类与LLM1/2/3协作架构

### 新增
- [schemas.py] 新增 `EntityCategory` 枚举（event_entity / opinion_spreader）
- [schemas.py] 新增 `OpinionSpreader` 模型
- [Phase 1] `phase1_entity_extraction.py` 实现 LLM1/2/3 三阶段协作架构

### 修改
- [schemas.py] `Entity` 模型增加 `entity_category` 字段
- [schemas.py] `EntityExtractionOutput` 输出改为 event_entities + opinion_spreaders 双列结构
- [schemas.py] 新增 `event_intensity` 字段
- [Phase 1] LLM1：设置 event_temperature + event_intensity
- [Phase 1] LLM2：提取事件实体 + 生成意见传播者
- [Phase 1] LLM3：格式校验，失败则 LLM2 重试（最多3次）
- [Phase 2] 事件实体作为 Core 节点，意见传播实体作为 Periphery 节点
- [Phase 2] 事件实体之间互相关注（Core ↔ Core）
- [Phase 3] Tick 0 只有事件实体发言
- [Phase 3] Tick 1+ 只有意见传播实体发言（必须看到 Tick 0 的事件实体发言）

### 功能
- ✅ 两种实体类型区分：事件实体 vs 意见传播实体
- ✅ LLM1/2/3 迭代校验机制
- ✅ 事件实体=Core，传播实体=Periphery 的拓扑结构
- ✅ Tick 0/1+ 分阶段发言机制

**详细文档**：[v1.1.4_entity_classification.md](./v1.1.4_entity_classification.md)
**完成时间**：2026-03-26

---

## v1.1.3 - 2026-03-25（已完成）

**主题**：Stance 语义修复与社交拓扑优化

### 修改
- [schemas.py] `GraphNode` 增加 `confirmation_bias_level` 字段
- [schemas.py] `EdgeType` 增加 `FOLLOWS_CROSS_GROUP` 和 `FOLLOWS_CORE_CROSS` 边类型
- [Phase 1] `phase1_persona_engine.py` 传递 `confirmation_bias_level` 到 GraphNode
- [Phase 2] `phase2_topology_builder.py` 新增跨圈层关注机制（50% 概率 + 30% Core 互关）
- [Phase 2] `phase2_topology_builder.py` 新增 Agent 个体差异化扰动（Core ±5%, Periphery ±15%）
- [Phase 3] `phase3_tick_simulation.py` 新增 stance_score 语义定义（1-3 批评，4-6 中立，7-10 支持）
- [Phase 3] `phase3_tick_simulation.py` 新增确认偏差 Prompt 约束
- [Phase 3] `phase3_tick_simulation.py` 新增代码层 stance 变化硬性限制

### 功能
- ✅ 跨圈层信息传递：65% Agent 能看到不同群体的发言
- ✅ stance_delta 约束：strong=±0.3, weak=±1.0, none=±2.0 全部生效
- ✅ 同群体 Agent 差异化：stance_score 不再完全相同

**详细文档**：[v1.1.3_stance_and_topology_fix.md](./v1.1.3_stance_and_topology_fix.md)
**完成时间**：2026-03-25

---

## v1.1.2 - 2026-03-25（已完成）

**主题**：Phase3 发言中体现实体信息

### 修改
- [schemas.py] `GraphNode` 增加 `related_entity` 字段
- [Phase 2] `phase2_topology_builder.py` 传递 `related_entity` 到 GraphNode
- [Phase 3] `phase3_tick_simulation.py` 发言 Prompt 加入实体信息
- [schemas.py] `Phase1Output` 验证器增加自动校正百分比逻辑

### 功能
- ✅ Agent 发言中包含关联实体名称（如"某知名美妆品牌"）
- ✅ 发言内容与实体相关

### 验收结果
- ✅ GraphNode 有 related_entity 字段
- ✅ Phase3 发言 Prompt 包含实体信息
- ✅ Agent 发言中出现关联实体名称
- ✅ 端到端运行成功

**详细文档**：[v1.1.2_entity_in_post.md](./v1.1.2_entity_in_post.md)
**完成时间**：2026-03-25

---

## v1.1.1 - 2026-03-25（已完成）

**主题**：引入实体提取与基于实体的 Agent 生成

### 新增
- [Phase 0] `phase0_entity_extraction.py` - 实体提取模块
- [Phase 1] `related_entity` 字段 - 关联核心实体
- [Phase 1] `confirmation_bias_level` 字段 - 确认偏差强度
- [Phase 1] `event_temperature` 参数 - 事件热度控制
- [schemas.py] 新增 `Entity`, `Relation`, `EntityExtractionOutput` 模型
- [schemas.py] 新增 `ConfirmationBiasLevel` 枚举

### 修改
- [Phase 1] `phase1_persona_engine.py` - 基于实体生成 Agent
- [schemas.py] `Archetype` 增加 `related_entity` 和 `confirmation_bias_level` 字段
- [main.py] 增加 Phase 0 调用逻辑

### 修复
- Agent 生成与事件脱节的问题
- Agent 数量无法根据事件热度动态调整的问题

### 功能
- ✅ Phase 0: 从种子文本提取 3-5 个核心实体
- ✅ Phase 0: 输出 event_temperature (0.0-1.0)
- ✅ Phase 1: 基于实体生成 Agent，每个 Agent 关联 core_entity
- ✅ Phase 1: confirmation_bias_level 字段 (none/weak/strong)
- ✅ Phase 1: 根据 event_temperature 动态决定 Agent 数量

### 验收结果
- ✅ Phase 0 能够提取 3-5 个核心实体
- ✅ event_temperature 在 0.0-1.0 范围内
- ✅ 每个 archetype 都有 related_entity 字段
- ✅ 每个 archetype 都有 confirmation_bias_level 字段
- ✅ archetypes 百分比之和 = 100
- ✅ 端到端运行成功

**详细文档**：[v1.1.1_entity_extraction.md](./v1.1.1_entity_extraction.md)
**完成时间**：2026-03-25

---

## v1.1.0 - 2026-03-25（已完成）

**主题**：MVP 基线版本 - Phase 1-4 基础功能

### 新增
- [Phase 1] `phase1_persona_engine.py` - 动态人群生成器
- [Phase 2] `phase2_topology_builder.py` - 微型社交拓扑构建
- [Phase 3] `phase3_tick_simulation.py` - 异步时间步推演
- [Phase 4] `phase4_report_agent.py` - 宏观洞察生成器
- [Core] `schemas.py` - Pydantic 数据模型定义
- [Core] `llm_client.py` - LLM 统一调用封装
- [Main] `main.py` - 四阶段串联主入口

### 修改
- [Config] `config.py` - 全局配置（API、路径、参数）
- [Docs] 新增 `docs/PROJECT_SPEC_v1.1.md` - 项目技术规格书
- [Docs] 新增 `docs/skills/dev_workflow.md` - 开发规范文档

### 功能
- ✅ Phase 1: 从种子文本识别 3-8 类人群原型，生成 5-15 个 Agent
- ✅ Phase 2: 构建核心-边缘社交网络拓扑
- ✅ Phase 3: 多轮 Agent 交互模拟，计算 x(t) 序列
- ✅ Phase 4: 生成 Markdown 舆情报告，包含风险评估
- ✅ 端到端闭环：从 `main.py` 一键运行，输入 txt，输出报告

### 验收结果
- ✅ Pydantic 校验通过
- ✅ Archetypes 数量 3-8，占比之和 = 100
- ✅ Agent 数量符合 5-15 约束
- ✅ 社交网络拓扑验证通过
- ✅ 多轮模拟收敛检测正常
- ✅ 最终报告生成成功

**详细文档**：[v1.1.0_baseline.md](./v1.1.0_baseline.md)
**完成时间**：2026-03-25
