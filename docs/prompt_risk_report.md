# Prompt Risk Report - 高风险 Prompt 识别

生成时间：2026-04-14
版本：v1.1.20
基于：docs/prompt_inventory.md

---

## 1. 执行摘要

本报告识别出两类高风险 Prompt：

| 风险类型 | Prompt | 风险等级 |
|---------|--------|---------|
| 重Schema | P1-G, P1-P, P4-R | 🔴 高 |
| 易报错 | P1-V, P3-A, PR-G | 🔴 高 |

---

## 2. 重Schema Prompt 详解

### 2.1 P1-G (Legacy Generator) — 🔴 最高风险

**Source**: `src/phase1_entity_extraction.py:86-211`

**Schema 复杂度**：
```
event_entities[]:
  - name (string)
  - type (enum: individual|organization|group)
  - role (string)
  - entity_category (fixed: "event_entity")
  - can_speak (boolean)
  - original_statement (string|null)

opinion_spreaders[]:
  - group_name (string)
  - related_event_entity (string, must exist in event_entities)
  - description (string, 15-50 chars)
  - I (float, 1.0-10.0)
  - P (enum: +1|-1)
  - susceptibility (float, 0.0-1.0)
  - estimated_percentage (int, 0-100, sum=100)
  - communication_style (string)
  - entity_category (fixed: "opinion_spreader")
  - persona_name (string, Chinese name)
  - age_range (string, XX-XX format)
  - occupation (string)
  - personality (string)
  - motivation (string)
  - typical_phrases (array, 2-3 items)

relations[]:
  - source (string)
  - target (string)
  - type (string)

总计：~24 个字段，3 个嵌套数组，多条跨数组约束
```

**重Schema 原因**：
1. 字段数最多（~24 个）
2. 跨数组约束（related_event_entity 必须存在于 event_entities）
3. estimated_percentage 之和必须等于 100
4. persona_name 不能重复
5. age_range 必须符合 XX-XX 格式
6. typical_phrases 必须是 2-3 项数组

**风险点**：
- 模型容易在嵌套结构上出错
- 跨数组引用校验复杂
- percentage 归一化容易失误

---

### 2.2 P1-P (Group Planner) — 🔴 高风险

**Source**: `src/phase1/group_planner.py:16-83`

**Schema 复杂度**：
```
opinion_spreaders[]:
  - group_name (string)
  - related_event_entity (string, must exist in event_entities)
  - description (string)
  - I (float, 1.0-10.0)
  - susceptibility (float, 0.0-1.0)
  - raw_weight (float, >0)
  - entity_category (fixed: "opinion_spreader")

总计：~6 fields per spreader，但有 I 分布约束
```

**重Schema 原因**：
1. I 值分布必须符合 event_scale 规则（<0.3 时 3-5 人，0.3-0.7 时 5-7 人，≥0.7 时 7-10 人）
2. raw_weight > 0 且需要归一化
3. related_event_entity 必须存在于 event_entities

**风险点**：
- I 分布规则容易被忽略
- raw_weight 归一化需要后处理

---

### 2.3 P4-R (Report Agent) — 🟡 中高风险

**Source**: `src/phase4_report_agent.py:39-79`

**Schema 复杂度**：
```
输出格式：freeform markdown，500-800 行
章节结构：
1. 📊 事件概要
2. 🗺️ 实体图谱
3. 🎬 Tick 0 · 事件实体发言
4. 🔥 关键拐点
5. 📈 Tick 1-N · 意见演化
6. 📊 最终立场变化
7. 📉 极化演化轨迹
8. 💡 关键洞察（3-6 条）
9. 🎯 舆论态势判断
10. ⚠️ 风险评估
```

**重Schema 原因**：
1. 10 个章节结构，每章有明确的 emoji 格式要求
2. 拐点识别有量化标准（极化变化 > 0.05，立场偏移 > 1.5）
3. 立场变化趋势符号有明确定义
4. 舆论态势判断有分级标准

**风险点**：
- 模型可能遗漏章节或打乱顺序
- 量化标准可能被误解
- 输出长度可能超标

---

## 3. 易报错 Prompt 详解

### 3.1 P1-V (Validator) — 🔴 最高风险

**Source**: `src/phase1_entity_extraction.py:218-275`

**18 条校验规则**：
```
1.  必须是合法 JSON
2.  必须包含 event_entities 和 opinion_spreaders
3.  event_entities 每个元素 entity_category = "event_entity"
4.  opinion_spreaders 每个元素 entity_category = "opinion_spreader"
5.  event_entities + opinion_spreaders ≤ 15
6.  每个 opinion_spreader 有 related_event_entity 且存在于 event_entities
7.  estimated_percentage 之和 ≈ 100（±10 误差）
8.  I 为 1.0-10.0 浮点数
9.  P 为 +1 或 -1
10. susceptibility 为 0.0-1.0 浮点数
11. 至少有一个 P=+1 和一个 P=-1
12. event_entities 至少 1 个
13. relations 字段可选
14. entity_category 缺失时后处理自动补充
15. opinion_spreaders 必须包含 persona_name, age_range, occupation, personality, motivation, typical_phrases
16. typical_phrases 长度为 2-3
17. persona_name 不能重复
18. age_range 符合 XX-XX 格式
```

**易报错原因**：
1. 规则 6（跨数组引用）最容易失败
2. 规则 7（percentage 和）最容易出现 ±误差边界问题
3. 规则 15-18（persona 字段）是 v1.1.12 新增，容易被旧版模型忽略
4. JSON 解析失败时返回格式错误的 errors

**常见错误模式**：
- 模型输出的 JSON 带 markdown 代码块（```json ... ```）
- estimated_percentage 之和为 98 或 102（边界误差）
- related_event_entity 拼写与 event_entities 不一致
- typical_phrases 输出为字符串而非数组

---

### 3.2 P3-A (Agent Post) — 🔴 高风险

**Source**: `src/phase3_tick_simulation.py:125-178`

**动态注入风险**：
```
{stance_semantics}        — 注入自 STANCE_SEMANTICS 常量
{confirmation_bias_prompt} — 注入自 CONFIRMATION_BIAS_PROMPTS dict
{opinion_pressure_prompt}  — 条件注入（group_distribution_strategy）
```

**易报错原因**：
1. 动态注入的 prompt 片段可能与主 prompt 产生冲突
2. confirmation_bias 有 strong/weak/none 三种，内容不同
3. opinion_pressure_prompt 是 v1.1.7 新增，条件触发容易遗漏
4. LLM 可能在 JSON 输出中混入 prompt 指令内容

**常见错误模式**：
- 模型输出包含"你是一位..."等系统 prompt 内容
- new_stance 值超出 1.0-10.0 范围
- comment 长度超过 50 字限制
- reasoning 超过 30 字限制
- JSON 中出现转义字符问题

---

### 3.3 PR-G (Profiling Generator) — 🔴 高风险

**Source**: `profiling/prompts.py:26-42` (wraps P1-G)

**易报错原因**：
1. 实际调用的是 P1-G，而 P1-G 是最复杂的 prompt
2. case 数据注入可能破坏 prompt 结构
3. error_feedback 字段为空时模板行为可能异常

**常见错误模式**：
- 同 P1-G 的所有错误模式
- event_scale/controversy 注入格式问题

---

## 4. 错误模式汇总表

| Prompt | 常见错误 | 错误频率 | 影响范围 |
|--------|---------|---------|---------|
| P1-G | JSON 带 markdown 代码块 | 高 | 解析失败 |
| P1-G | estimated_percentage 之和 ≠ 100 | 高 | Validator 失败 |
| P1-G | related_event_entity 不存在 | 高 | 链路断裂 |
| P1-G | persona_name 重复 | 中 | 唯一性校验失败 |
| P1-V | 解析失败时返回错误格式 | 中 | 死循环 |
| P3-A | new_stance 超出 1.0-10.0 | 高 | 立场计算异常 |
| P3-A | 输出包含系统 prompt 内容 | 中 | comment 质量下降 |
| P3-A | JSON 转义字符问题 | 低 | 解析失败 |
| P4-R | 遗漏章节 | 中 | 报告不完整 |
| P4-R | 量化指标格式错误 | 低 | 风险评估失准 |

---

## 5. 风险矩阵

| Prompt | Schema 复杂度 | 错误易发性 | 综合风险 |
|--------|-------------|-----------|---------|
| P1-G | 🔴 24字段 | 🔴 高 | 🔴 最高 |
| P1-V | 🟡 3字段 | 🔴 18规则 | 🔴 高 |
| P3-A | 🟡 3字段 | 🔴 动态注入 | 🔴 高 |
| P1-P | 🔴 6字段+I约束 | 🟡 中 | 🟡 中高 |
| P4-R | 🔴 10章节 | 🟡 中 | 🟡 中高 |
| PR-G | 🔴 24字段 | 🔴 继承P1-G | 🔴 高 |
| P1-F | 🟢 10字段 | 🟢 低 | 🟢 低 |
| P1-W | 🟢 7字段 | 🟢 低 | 🟢 低 |
| P3-E | 🟢 2字段 | 🟢 低 | 🟢 低 |
| P3-C | 🟢 3字段 | 🟢 低 | 🟢 低 |
| PR-S | 🟢 2字段 | 🟢 低 | 🟢 低 |

---

## 6. 推荐优先级

### 6.1 优先 profiling 的重灾区

1. **P1-V (Validator)** — 最容易成为链路瓶颈
2. **P1-G (Generator)** — Schema 最复杂，错误模式最多
3. **P3-A (Agent Post)** — 动态注入增加了不确定性

### 6.2 优先做 reduced-schema probe 的

1. **P1-G → P1-F** — 先测实体提取，降低 Schema 复杂度
2. **P3-A → P3-C** — 先测轻量上下文，移除动态注入

### 6.3 需要特别注意的错误处理

| Prompt | 当前错误处理 | 建议加固 |
|--------|------------|---------|
| P1-G | JSON 解析失败抛出异常 | 增加 markdown 剥离 + 重试 |
| P1-V | JSON 解析失败返回 pass=false | 增加容错解析 |
| P3-A | 解析失败返回默认值 | 增加严格边界检查 |

---

## 7. 下一步行动

1. **立即**：为 P1-G/P1-V/P3-A 添加 reduced-schema 版本（L1/L2）
2. **本周**：在 profiling 时重点关注这三个 prompt 的错误模式
3. **后续**：根据 profiling 结果决定是否需要 prompt 简化
