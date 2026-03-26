# Adarian MVP 变更日志 (CHANGELOG)

所有重要版本变更都会记录在此文档中。

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
