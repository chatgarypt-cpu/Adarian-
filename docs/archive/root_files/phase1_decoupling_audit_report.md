# Phase 1 LLM Decoupling Audit Report

生成时间：2026-04-14
版本：v1.1.20
目标：分析 Phase 1 各模块 LLM 负载，识别可解耦点

---

## 1. Phase 1 当前架构

### 1.1 模块调用链

```
run_phase1_orchestrator()
│
├── extract_entity_facts()          # P1-A + P1-F
│   ├── analyzer_set_parameters()    # LLM 调用 1 (P1-A)
│   └── extract_entity_facts()       # LLM 调用 2 (P1-F)
│
├── plan_opinion_groups()           # P1-P
│   └── generate opinion spreaders   # LLM 调用 3 (P1-P)
│       └── 6 fields × N groups
│
├── enrich_group_plan_with_personas() # P1-W
│   └── write_persona_for_group()    # LLM 调用 4-N (P1-W)
│       └── 7 fields × N groups
│
├── apply_rules()                    # 无 LLM (代码逻辑)
│   ├── P 推导 (I → P)
│   └── percentage 归一化
│
├── _post_process_entities()        # 无 LLM (代码逻辑)
│   ├── can_speak 修正常识
│   └── original_statement 修正
│
└── validator_check_format()       # LLM 调用 N+1 (P1-V)
    └── 18 条规则校验
```

### 1.2 LLM 调用统计

| 模块 | LLM 调用次数 | 输出复杂度 |
|------|-------------|-----------|
| P1-A (Analyzer) | 1 | 5 字段 JSON |
| P1-F (Fact Extractor) | 1 | ~10 字段 JSON |
| P1-P (Group Planner) | 1 | ~6 字段 × N groups |
| P1-W (Persona Writer) | N (每group一次) | 7 字段 × N groups |
| P1-V (Validator) | 1 | pass/errors 三字段 |
| **总计** | **2 + N + 1** | — |

**问题：N = opinion spreader 数量，通常 3-10 个**

---

## 2. 当前 P1-P 输出结构分析

### 2.1 P1-P 当前 Schema

**Source**: `src/phase1/group_planner.py:16-83`

```python
# GROUP_PLANNER_SYSTEM_PROMPT 输出格式：
{
  "opinion_spreaders": [
    {
      "group_name": "群体名称",           # string
      "related_event_entity": "关联实体", # string (必须在 event_entities)
      "description": "15-50字的群体骨架描述", # string
      "I": 1.0到10.0之间的浮点数,        # float
      "susceptibility": 0.0到1.0之间的浮点数, # float
      "raw_weight": 大于0的浮点数,        # float (>0)
      "entity_category": "opinion_spreader"
    }
  ]
}
```

**约束规则**：
- I 分布必须符合 event_scale 规则
- raw_weight > 0
- related_event_entity 必须在 event_entities 中存在
- 至少有支持方和反对方

### 2.2 P1-W 当前 Schema

**Source**: `src/phase1/persona_writer.py:26-82`

```python
# PERSONA_WRITER_SYSTEM_PROMPT 输出格式：
{
  "persona_name": "中文名字",        # string (Chinese name)
  "age_range": "18-24",             # string (XX-XX format)
  "occupation": "职业或身份",         # string
  "personality": "性格特征",         # string
  "motivation": "发言核心动机",       # string
  "typical_phrases": ["口头禅1", "口头禅2", "口头禅3"],  # array 2-3
  "communication_style": "该群体典型说话风格"  # string
}
```

**约束规则**：
- persona_name 必须是中文名字，不能重复
- age_range 必须符合 XX-XX 格式
- typical_phrases 长度为 2-3

---

## 3. LLM 过重问题分析

### 3.1 问题：一次性输出完整 JSON

当前 P1-P 和 P1-W 都是让 LLM **一次性输出完整的 JSON 数组**，包含多个字段和复杂约束。

**具体问题**：

1. **I 分布约束容易被忽略**
   - LLM 需要同时记住"每个 spreader 的 I 值要符合 event_scale 分布规则"
   - 当 I=8-10 只能出现在支持方（P=+1）时，LLM 容易出错

2. **跨字段约束难以保持一致**
   - `related_event_entity` 必须引用已存在的 event_entity
   - `group_name` 和 `description` 语义一致性
   - `raw_weight` 相对大小关系

3. **Persona 字段格式约束容易被违反**
   - `age_range` 格式（"18-24" 而非 "18-24岁"）
   - `typical_phrases` 数组长度（2-3 而非 1 或 4）
   - `persona_name` 中文姓名字符串

4. **重试成本高**
   - Validator 失败后，整个 JSON 都需要重新生成
   - 无法针对特定字段做精准修复

### 3.2 Validator 常见错误（来自 prompt_risk_report.md）

```
Top 5 P1-P/P1-W 错误：
1. estimated_percentage 之和 ≠ 100        → P1-P 不直接输出 percentage，但后处理会计算
2. related_event_entity 不存在于 event_entities → LLM 虚构
3. persona_name 重复                    → LLM 生成时忘记检查
4. age_range 格式错误                   → "18-24岁" 而非 "18-24"
5. typical_phrases 数组长度错误           → 1 个或 4 个
```

---

## 4. 解耦改进方案

### 4.1 方案：字段级生成 + 代码拼接

**核心思想**：让 LLM **每次只生成一个字段**，用**代码逻辑**处理字段间约束。

#### P1-P 拆分（6 字段 → 3 次 LLM 调用）

| 步骤 | LLM 调用 | 输出 | 约束处理 |
|------|---------|------|---------|
| 1 | `generate_group_names()` | group_name × N | 代码校验唯一性 |
| 2 | `assign_I_values()` | I × N | 代码强制 event_scale 分布 |
| 3 | `generate_spreader_details()` | description, susceptibility, raw_weight | 代码校验范围 |

#### P1-W 拆分（7 字段 → 2-3 次 LLM 调用）

| 步骤 | LLM 调用 | 输出 | 约束处理 |
|------|---------|------|---------|
| 1 | `generate_persona_essentials()` | persona_name, occupation, age_range | 代码校验格式 |
| 2 | `generate_persona_details()` | personality, motivation, typical_phrases | 代码校验数组长度 |

### 4.2 详细设计

#### P1-P Step 1: 生成群体名称（轻量）

**Prompt**:
```
你是一个事件分析专家。请为这个事件生成 N 个意见传播群体名称。

事件摘要：{event_summary}
事件类型：{event_type}
需要生成：{count} 个群体

要求：
1. 群体名称要简洁，2-4 个字
2. 每个群体对应一个事件实体
3. 支持方和反对方都要有
4. 不同群体名称要有差异

输出格式（每行一个名称）：
群体1名称
群体2名称
...
```

**输出**：纯文本，每行一个名称，无 JSON

**优势**：
- 无结构约束，LLM 压力最低
- 代码校验唯一性
- 可快速迭代直到名称满意

#### P1-P Step 2: 分配 I 值（代码逻辑）

**不需要 LLM！** 代码根据 event_scale 直接计算：

```python
def assign_I_values(group_count: int, event_scale: float, positions: list[int]) -> list[float]:
    """根据 event_scale 规则分配 I 值"""
    if event_scale < 0.3:
        i_range = (3, 6)
        total_i = random.randint(3*group_count, 6*group_count) / group_count
    elif event_scale < 0.7:
        i_range = (4, 7)
    else:
        i_range = (3, 10)

    # 支持方（P=+1）I 更高，反对方法 I 更低
    # 代码逻辑，无需 LLM
```

**优势**：
- 消除 LLM 的 I 分布约束错误
- 100% 确定性，符合业务规则

#### P1-P Step 3: 生成群体详情（中量）

**Prompt**:
```
请为以下群体生成详情描述。

群体名称：{group_name}
关联事件实体：{related_entity}
事件摘要：{event_summary}

请输出 JSON：
{{
  "description": "15-50字的人群描述",
  "susceptibility": 0.0到1.0之间的浮点数,
  "raw_weight": 大于0的浮点数
}}

注意：
- description 要简洁有特色，15-50字
- susceptibility 表示被说服程度，0.0-1.0
- raw_weight 表示群体相对规模，不需要归一化
```

**输出**：单个 JSON 对象，3 个字段

**优势**：
- 每次只输出 3 个字段，约束简单
- Validator 失败时只重试这一个群体

### 4.3 预期改进

| 指标 | 当前 | 改进后 |
|------|------|-------|
| P1-P LLM 调用 | 1 次（复杂 JSON） | 2 次（轻量文本 + 简单 JSON） |
| P1-W LLM 调用 | N 次（完整 JSON） | 2 次（essentials + details） |
| I 分布错误 | 常见 | 0（代码逻辑） |
| persona_name 重复 | 常见 | 0（代码校验） |
| Validator 重试次数 | 3-5 次 | 1-2 次 |
| 单次 LLM 输出长度 | ~2000 tokens | ~500 tokens/次 |

---

## 5. 实施路径

### Phase A: 最小可行解耦（P1-P 的 I 值）

**目标**：将 I 值分配从 LLM 迁移到代码逻辑

**改动文件**：
- `src/phase1/group_planner.py`

**改动内容**：
1. 移除 `GROUP_PLANNER_SYSTEM_PROMPT` 中的 I 分布约束
2. 新增 `assign_I_values()` 函数
3. 修改 `plan_opinion_groups()` 返回 raw_I 列表

**验证**：
- 相同 seed 运行 3 次，I 分布应一致
- Validator 错误减少

### Phase B: P1-P 结构化解耦

**目标**：P1-P 分 2 步走

**改动文件**：
- `src/phase1/group_planner.py`（重构）

**改动内容**：
1. 新增 `generate_group_names()` — LLM 生成群体名称
2. 新增 `generate_spreader_details()` — LLM 生成 description/susceptibility/raw_weight
3. 代码处理 I 分配和关联

### Phase C: P1-W 结构化解耦

**目标**：P1-W 分 2 步走

**改动文件**：
- `src/phase1/persona_writer.py`（重构）

**改动内容**：
1. 新增 `generate_persona_essentials()` — persona_name, occupation, age_range
2. 新增 `generate_persona_details()` — personality, motivation, typical_phrases
3. 代码校验格式和唯一性

---

## 6. 风险与注意事项

1. **多 LLM 调用的累积延迟**：分步骤后总 LLM 调用次数可能增加，但单次失败影响更小
2. **代码逻辑复杂度增加**：需要新增校验函数
3. **与现有 Validator 的兼容性**：确保分步输出仍能通过 Validator

---

## 7. 总结

### 当前问题

Phase 1 的 P1-P 和 P1-W 要求 LLM **一次性输出完整 JSON 数组**，包含多个字段和复杂约束，导致：
- I 分布错误
- 字段格式错误（age_range、typical_phrases）
- 唯一性错误（persona_name 重复）
- Validator 重试次数多

### 改进方向

1. **LLM 只生成语义内容**（名称、描述、态度）
2. **代码处理结构约束**（格式、唯一性、分布）
3. **分步骤生成 + 代码拼接**

### 推荐实施顺序

```
Phase A（P1-P I 值解耦）→ Phase B（P1-P 结构化）→ Phase C（P1-W 结构化）
```

---

## 附录：源码位置索引

| 文件 | 位置 | 说明 |
|------|------|------|
| Orchestrator | `src/phase1/orchestrator.py` | 主编排逻辑 |
| P1-A (Analyzer) | `src/phase1_entity_extraction.py:36-79` | 事件参数分析 |
| P1-F (Fact Extractor) | `src/phase1/entity_extractor.py:17-91` | 事实提取 |
| P1-P (Group Planner) | `src/phase1/group_planner.py:16-83` | 群体规划 ⭐ |
| P1-W (Persona Writer) | `src/phase1/persona_writer.py:26-82` | Persona 生成 ⭐ |
| P1-V (Validator) | `src/phase1_entity_extraction.py:218-275` | 格式校验 |
| Rules Engine | `src/phase1/rules_engine.py` | P 推导、归一化 |
| Schemas | `src/schemas.py:69-199` | OpinionSpreader 定义 |
