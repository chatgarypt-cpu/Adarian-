# Phase 1 Prompt Benchmark 交接任务书

## 摘要

这份任务书用于将 `Phase 1 Prompt Benchmark + Evaluation` 工作安全地交接给协作者。

本次交接的核心原则：

- 只优化 `Prompt + Benchmark + Evaluation`
- 不修改主流程行为定义
- 不修改 schema
- 所有结论必须基于 benchmark 和可量化指标

当前项目主链路：

`main.py -> phase1_entity_extraction.py -> phase2_topology_builder.py -> phase3_tick_simulation.py -> phase4_report_agent.py`

本任务只覆盖 `Phase 1`。

---

## 目录

1. [任务目标](#任务目标)
2. [范围与边界](#范围与边界)
3. [当前项目上下文](#当前项目上下文)
4. [Prompt 基线](#prompt-基线)
5. [当前 Prompt 功能定义](#当前-prompt-功能定义)
6. [冻结约束](#冻结约束)
7. [交付物](#交付物)
8. [评估维度](#评估维度)
9. [工作方式要求](#工作方式要求)
10. [验收标准](#验收标准)
11. [建议交接步骤](#建议交接步骤)

---

## 任务目标

你的任务不是重构系统，也不是修改主流程逻辑。

你的任务是：

1. 为 `Phase 1` 建立一套可重复执行的 benchmark
2. 在不破坏现有 schema 和 pipeline 的前提下，优化 Prompt 文案
3. 用 benchmark 比较 Prompt 版本差异
4. 输出一份评估报告，说明新版 Prompt 是否优于当前版本

当前项目的 `Phase 1` 负责：

- 从种子文本中提取事件实体
- 生成 `opinion_spreaders`
- 通过 `Validator` 校验输出格式和约束

关键文件：

- `src/phase1_entity_extraction.py`
- `src/schemas.py`

---

## 范围与边界

### 你可以做

- 优化 Prompt 文案
- 设计 benchmark case
- 定义 expectation / evaluation 规则
- 写 Prompt 对比测试脚本
- 输出评估报告

### 你不能做

- 不能修改 `schemas.py`
- 不能修改 `Phase 1` 输出字段
- 不能修改主流程调用顺序
- 不能修改 `_post_process_entities()`
- 不能修改 `extract_entities_with_validation()`
- 不能修改 Agent 数量硬约束、双向对立硬约束
- 不能擅自改 JSON schema

### 一句话边界

你负责“Prompt 行为优化与评估”，不负责“系统行为定义”。

### 快速判断标准

问自己一句：

> 这个改动如果失败，会不会破坏主链路？

- 会：不要做
- 不会：可以做

---

## 当前项目上下文

### 当前主链路

`main.py -> phase1_entity_extraction.py -> phase2_topology_builder.py -> phase3_tick_simulation.py -> phase4_report_agent.py`

### 本次只接手的模块

- `Phase 1 Prompt Benchmark`
- `Phase 1 Prompt Evaluation`

### 本次不接手的模块

- `Phase 2` 拓扑构建
- `Phase 3` stance / tick / simulation 逻辑
- `Phase 4` 报告生成逻辑
- `schemas.py` 数据结构定义

---

## Prompt 基线

### 唯一基线来源

当前 Prompt 的唯一真实来源文件：

- `src/phase1_entity_extraction.py`

### 当前使用的 Prompt 常量

1. `ANALYZER_SYSTEM_PROMPT`
2. `ANALYZER_USER_PROMPT`
3. `GENERATOR_SYSTEM_PROMPT`
4. `GENERATOR_USER_PROMPT`
5. `VALIDATOR_SYSTEM_PROMPT`
6. `VALIDATOR_USER_PROMPT`

### 基线要求

你所有优化都必须基于这 6 个 Prompt 的当前版本进行对比。

禁止：

- 脱离现有实现重新发明一套流程
- 另起炉灶定义新的 schema
- 通过改流程掩盖 Prompt 问题

---

## 当前 Prompt 功能定义

### Analyzer Prompt

#### `ANALYZER_SYSTEM_PROMPT`

职责：

- 从种子材料中分析并输出：
  - `event_scale`
  - `event_controversy`
  - `event_summary`
  - `event_type`
  - `reasoning`

当前核心要求：

- `event_scale` 范围 `0.0-1.0`
- `event_controversy` 范围 `0.0-1.0`
- `event_summary` 50 字以内
- `event_type` 必须有效

当前判断逻辑重点：

- `event_scale` 反映事件规模
- `event_controversy` 反映事件争议性
- 高争议事件倾向更低支持者比例

#### `ANALYZER_USER_PROMPT`

作用：

- 把 `seed_text` 喂给 Analyzer

---

### Generator Prompt

#### `GENERATOR_SYSTEM_PROMPT`

职责：

1. 提取 `event_entities`
2. 生成 `opinion_spreaders`
3. 可选生成 `relations`

当前 Generator 的核心设计是 IPC 框架：

- `I` = Intensity（立场强度）
- `P` = Position（立场方向）
- `C` = `P × (I/10)`，系统推导，不要求模型输出

#### 事件实体输出要求

每个 `event_entity` 需包含：

- `name`
- `type`
- `role`
- `entity_category`
- `can_speak`
- `original_statement`

#### 意见传播者输出要求

每个 `opinion_spreader` 需包含：

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

#### 当前 Generator 的硬约束

- `event_entities + opinion_spreaders <= 15`
- `estimated_percentage` 总和必须等于 `100`
- 必须至少有一个 `P=+1` 和一个 `P=-1`
- 每个 `opinion_spreader` 必须绑定有效的 `related_event_entity`
- `persona_name` 不能重复
- `occupation / personality / typical_phrases` 必须体现差异
- `typical_phrases` 必须有 `2-3` 个
- `age_range` 必须符合 `"18-24"` 这种格式

#### `GENERATOR_USER_PROMPT`

作用：

- 传入：
  - `seed_text`
  - `event_scale`
  - `event_controversy`
  - `event_type`
  - `event_summary`
  - `error_feedback`
- 用于支持 Validator 失败后的重试修正

---

### Validator Prompt

#### `VALIDATOR_SYSTEM_PROMPT`

职责：

- 校验 Generator 输出是否符合格式和业务约束

当前 Validator 校验重点包括：

1. JSON 格式合法
2. 必须有 `event_entities` 和 `opinion_spreaders`
3. `entity_category` 正确
4. 总数不超过 `15`
5. `related_event_entity` 必须有效
6. `estimated_percentage` 总和约等于 `100`
7. `I` 范围正确
8. `P` 只能是 `+1/-1`
9. `susceptibility` 范围正确
10. 必须存在双向对立
11. `event_entities` 至少 `1` 个
12. `relations` 可有可无
13. 新增人设字段必须存在
14. `typical_phrases` 长度必须为 `2-3`
15. `persona_name` 不能重复
16. `age_range` 格式正确

当前 Validator 的特殊规则：

- 不对 `can_speak` 做硬错误拦截，交给代码后处理修正
- 不对 `original_statement` 做硬错误拦截，交给代码后处理修正

#### `VALIDATOR_USER_PROMPT`

作用：

- 传入 `seed_text` 和待校验 JSON

---

## 冻结约束

以下内容视为冻结约束，不得改动。

### 冻结的数据结构

文件：

- `src/schemas.py`

尤其不能改：

- `EntityExtractionOutput`
- `Entity`
- `OpinionSpreader`
- `Relation`

### 冻结的流程逻辑

文件：

- `src/phase1_entity_extraction.py`

尤其不能改：

- `analyzer_set_parameters()`
- `generator_create_entities()`
- `validator_check_format()`
- `_post_process_entities()`
- `extract_entities_with_validation()`

### 冻结的业务规则

- 总实体数上限 `15`
- 双向对立必须存在
- `estimated_percentage` 总和必须为 `100`
- `related_event_entity` 必须合法
- 人设字段必须齐全

---

## 交付物

### 交付物总览

| 交付物 | 内容 | 必须程度 |
|------|------|------|
| Benchmark 数据集 | 文本 case + expectation | 必须 |
| Prompt 对比测试脚本 | 对比当前 Prompt 和候选 Prompt | 必须 |
| 评估报告 | 汇总结果、失败样例、结论 | 必须 |
| 候选 Prompt 文案 | Prompt 候选版本 | 可选但推荐 |

### 交付物 1：Benchmark 数据集

新建目录建议：

`benchmarks/phase1/`

建议结构：

```text
benchmarks/
  phase1/
    cases/
      case01_brand_crisis.txt
      case02_policy_event.txt
      case03_social_conflict.txt
      case04_campus_incident.txt
      case05_public_safety.txt
    expectations/
      case01_brand_crisis.json
      case02_policy_event.json
      case03_social_conflict.json
      case04_campus_incident.json
      case05_public_safety.json
```

每个 expectation 示例：

```json
{
  "event_scale_range": [0.4, 0.9],
  "event_controversy_range": [0.5, 1.0],
  "min_event_entities": 1,
  "min_opinion_spreaders": 3,
  "max_total_entities": 15,
  "must_have_bipolar_P": true,
  "percentage_sum_must_equal": 100,
  "notes": "品牌危机场景，应出现明显支持/反对分化"
}
```

### 交付物 2：Prompt 对比测试脚本

目标：

- 比较当前 Prompt 和候选 Prompt 的效果差异

脚本能力至少要回答：

- 哪个版本 schema 通过率更高？
- 哪个版本输出更稳定？
- 哪个版本人设差异更明显？
- 哪个版本更少出现胡编实体、无效关系、比例不守恒？

### 交付物 3：评估报告

至少包含：

1. benchmark case 列表
2. Prompt A / Prompt B 对比方法
3. 每个 case 的结果摘要
4. 汇总评分
5. 失败样例分析
6. 最终建议：是否替换当前 Prompt

### 交付物 4：候选 Prompt 文案

你可以提交：

- `ANALYZER_SYSTEM_PROMPT` 候选版
- `GENERATOR_SYSTEM_PROMPT` 候选版
- `VALIDATOR_SYSTEM_PROMPT` 候选版

要求：

- 只改文案表达、顺序、清晰度、示例
- 不改输出 schema
- 不改主流程契约

---

## 评估维度

建议最少做这 5 类指标：

### 1. 结构正确率

- JSON 是否可解析
- 字段是否齐全
- schema 是否通过

### 2. 约束命中率

- 总数是否 `<= 15`
- 百分比总和是否 `= 100`
- 是否存在 `P=+1` 和 `P=-1`
- `related_event_entity` 是否有效

### 3. 参数合理性

- `event_scale` 是否落在合理范围
- `event_controversy` 是否匹配事件类型
- `P` 分布是否大体符合 `event_controversy`

### 4. 人设多样性

- `persona_name` 是否重复
- `occupation` 是否重复过多
- `personality` 是否模板化
- `typical_phrases` 是否雷同

### 5. 可用性

- 输出是否便于后续 `Phase 2/3` 消化
- 是否经常触发 `_post_process_entities()` 大量修正
- 是否出现明显的“看起来过关，但语义很差”的情况

---

## 工作方式要求

### 每次提交候选 Prompt 时，必须附带

1. 修改了哪个 Prompt
2. 为什么改
3. 希望改善哪个问题
4. 跑了哪些 benchmark
5. 结果是否优于基线

### 禁止以下做法

- “我觉得新版更自然”
- “看起来更像人”
- “我直觉更好”

### 正确表达方式

- “在 8 个 benchmark case 上，schema 通过率从 62.5% 提升到 87.5%”
- “`estimated_percentage=100` 命中率从 5/8 提升到 8/8”

---

## 验收标准

满足以下条件，视为本任务完成：

- benchmark case 数量不少于 `5`
- 每个 case 都有 expectation 文件
- 有 Prompt 对比测试脚本
- 有一份完整评估报告
- 所有结论都有指标支撑
- 没有改动冻结约束中的任何内容

推荐进阶目标：

- benchmark case 数量达到 `8-12`
- 覆盖不同类型事件
- 有失败样例归因
- 能明确说明“为什么新 Prompt 更好”

---

## 建议交接步骤

### 第一步

先阅读：

- `src/phase1_entity_extraction.py`
- `src/schemas.py`

### 第二步

建立 benchmark 数据集：

- `benchmarks/phase1/cases/`
- `benchmarks/phase1/expectations/`

### 第三步

先跑基线 Prompt，记录当前表现：

- schema 通过率
- 约束命中率
- 人设重复率
- 失败样例

### 第四步

在自己的分支上提出候选 Prompt 版本，只改文案，不改流程。

### 第五步

再次跑 benchmark，对比：

- 基线版本
- 候选版本

### 第六步

提交以下内容：

- benchmark 数据集
- 对比测试脚本
- 评估报告
- 候选 Prompt 文案

---

## 最后的两句话

你不是来改系统架构的，你是来做 `Phase 1 Prompt Benchmark + Evaluation` 的。

你的成果不是“一个新 Prompt”，而是“一套能证明新 Prompt 更好的方法”。
