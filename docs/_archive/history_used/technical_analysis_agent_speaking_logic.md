# Adarian MVP 技术细节报告：Agent 发言逻辑与事件参数

> 归档说明
> 本文档基于 2026-03-30 的旧架构分析，仍包含 `event_temperature`、`event_intensity`、
> `phase1_persona_engine.py` 等历史实现引用，不代表 2026-04-08 之后的当前代码状态。
> 现行实现以 `docs/dev_spec.md`、`README.md` 和 `src/` 主流程源码为准。

**生成日期**：2026-03-30
**报告目的**：详尽说明每轮 Agent 发言逻辑、event_temperature 和 event_intensity 的生成依据及其影响

---

## 一、每轮 Agent 发言逻辑

### 1.1 整体架构

模拟分为 **Tick 0** 和 **Tick N (N≥1)** 两个阶段：

```
Tick 0  → 事件实体发言（event_entity）
Tick 1  → 意见传播实体发言（opinion_spreader）
Tick 2  → 意见传播实体发言
Tick 3  → 意见传播实体发言
...
```

**结论：不是基于概率，所有符合条件的实体在各自轮次都会发言。**

---

### 1.2 Tick 0 — 事件实体发言

**源文件**：`src/phase3_tick_simulation.py:227-270`

```python
def run_tick_0(self) -> List[AgentEntry]:
    """执行 Tick 0：事件实体发言"""

    event_nodes = [
        n for n in self.phase2_output.nodes
        if n.entity_category == "event_entity"
    ]

    for node in event_nodes:
        # 1. 获取对应的 Entity 信息
        entity = None
        for e in self.extraction_output.event_entities:
            if e.name == node.related_entity:
                entity = e
                break

        # 2. 检查 can_speak（v1.1.6 新增）
        if not entity.can_speak:
            # 不生成发言，标记为"被讨论"
            reason = entity.original_statement or "（该实体不可发言）"
            self.event_entity_posts[node.id] = reason
            entry = AgentEntry(..., comment=reason, reasoning="实体不可发言")
            entries.append(entry)
            continue

        # 3. 优先使用 original_statement
        if entity.original_statement:
            comment = entity.original_statement  # 直接使用原始发言
            reasoning = "原始发言（从种子材料提取）"
            ...
            continue

        # 4. 无原始发言，LLM 生成
        response = self.llm_event_entity.generate(...)
        comment, reasoning = self._parse_event_entity_response(response)
        ...
```

**Tick 0 发言决策流程：**

```
是事件实体吗？
    ↓
can_speak = false?
    ↓ yes → 标记为"被讨论"，不生成发言
    ↓ no
original_statement 存在?
    ↓ yes → 直接使用原始发言
    ↓ no → LLM 生成发言
```

---

### 1.3 Tick N (N≥1) — 意见传播实体发言

**源文件**：`src/phase3_tick_simulation.py:636-687`

```python
def run_tick(self, tick: int) -> TickLog:
    """执行一轮模拟（Tick N：意见传播实体发言）"""

    entries = []

    # 只处理意见传播实体
    spreader_nodes = [
        n for n in self.phase2_output.nodes
        if n.entity_category == "opinion_spreader"
    ]

    # 遍历所有意见传播实体
    for node in spreader_nodes:
        previous_stance = self.agent_stances[node.id]

        # 生成发言（每个节点都会生成）
        comment, new_stance, reasoning, change_reason = \
            self.generate_opinion_spreader_post(node)

        # 更新立场
        self.agent_stances[node.id] = new_stance
        self.agent_comments[node.id].append(comment)

        entry = AgentEntry(...)
        entries.append(entry)

    return TickLog(tick=tick, entries=entries, global_metrics=...)
```

**关键发现：所有 opinion_spreader 在每一轮都会发言，无筛选逻辑。**

---

### 1.4 配置参数（未生效）

**源文件**：`config.py:131`

```python
# 每个 Agent 每轮最多读取的发言数
MAX_POSTS_PER_TICK = 3
```

**问题**：此参数定义但**从未在代码中使用**，起不到限制发言数量的作用。

---

### 1.5 验证数据（test5）

**源文件**：`outputs/outputs_test5/tick_logs/`

| Tick | 发言实体数 | 实体列表 |
|------|-----------|----------|
| Tick 0 | 2 | 兵团禁毒, 南通文旅 |
| Tick 1 | 6 | 政策批评者, 法律支持者, 网络调侃群体, 媒体评论员, 社会观察者, 粉丝群体 |
| Tick 2 | 6 | 同上（全量） |
| Tick 3 | 6 | 同上（全量） |
| Tick 4 | 6 | 同上（全量） |
| Tick 5 | 6 | 同上（全量） |

---

## 二、事件温度（event_temperature）生成依据

### 2.1 源文件

**定义**：`src/schemas.py:152-155`
```python
event_temperature: float = Field(
    ...,
    description="事件热度参数：0.0=冷门事件，1.0=全网热议"
)
```

**生成 Prompt**：`src/phase1_entity_extraction.py:36-43`
```python
【事件温度（event_temperature）】
- 0.0 = 冷门事件，几乎无人讨论
- 1.0 = 全网热议，全民关注
- 判断标准：
  - 涉及范围：个人事件(0.2) < 群体事件(0.5) < 全社会事件(0.8)
  - 争议性：事实清晰(0.3) < 存在争议(0.6) < 高度对立(0.9)
  - 社会影响：局部(0.2) < 行业(0.5) < 全国(0.8)
- 综合三个维度取平均值
```

### 2.2 计算公式

```
event_temperature = (涉及范围 + 争议性 + 社会影响) / 3
```

### 2.3 判断维度表

| 维度 | 0.2 | 0.5 | 0.8 |
|------|-----|-----|-----|
| 涉及范围 | 个人事件 | 群体事件 | 全社会事件 |
| 争议性 | 事实清晰 | 存在争议 | 高度对立 |
| 社会影响 | 局部 | 行业 | 全国 |

### 2.4 缺失内容

**没有**按事件类型（如食品安全、医疗事故）来调整，纯粹是 LLM 主观判断。

---

## 三、事件烈度（event_intensity）生成依据

### 3.1 源文件

**定义**：`src/schemas.py:156-158`
```python
event_intensity: float = Field(
    ...,
    description="事件烈度参数：0.0=极低，1.0=极高"
)
```

**生成 Prompt**：`src/phase1_entity_extraction.py:45-52`
```python
【事件烈度（event_intensity）】
- 0.0 = 事件烈度极低，只有少量客观网友简单评价
- 1.0 = 事件烈度极高，引发大规模、多样化的舆论反应
- 判断标准：
  - 情绪强度：平和(0.2) < 激动(0.5) < 愤怒(0.8) < 疯狂(1.0)
  - 参与多样性：单一群体(0.2) < 多个群体(0.5) < 全民参与(0.8)
  - 烈度高时会出现多种类型的意见传播者（粉丝、专家、批评者、支持者等）
  - 烈度低时只有少量客观网友评价
```

### 3.2 计算公式

```
event_intensity = (情绪强度 + 参与多样性) / 2
```

### 3.3 判断维度表

| 维度 | 0.2 | 0.5 | 0.8 | 1.0 |
|------|-----|-----|-----|-----|
| 情绪强度 | 平和 | 激动 | 愤怒 | 疯狂 |
| 参与多样性 | 单一群体 | 多个群体 | 全民参与 | - |

### 3.4 缺失内容

**没有**按事件类型来调整。同样是纯主观评分。

---

## 四、event_temperature 和 event_intensity 的影响

### 4.1 影响范围

| Phase | 是否受影响 | 影响内容 |
|-------|-----------|----------|
| **Phase 0** | ✅ 是 | 初始定义 |
| **Phase 1 (Persona Engine)** | ✅ 是 | Agent 总数、极端派占比、传播者多样性 |
| **Phase 2 (Social Graph)** | ❌ 否 | 不使用 |
| **Phase 3 (Simulation)** | ❌ 否 | **未使用** |
| **Phase 4 (Report)** | ✅ 是 | 报告中展示 |

### 4.2 Phase 1 中的具体影响规则

**源文件**：`src/phase1_persona_engine.py:51-57`

```python
# event_temperature 影响 archetype 数量
- event_temperature < 0.3：生成 3-5 个 archetype
- 0.3 <= event_temperature < 0.7：生成 5-7 个 archetype
- event_temperature >= 0.7：生成 7-10 个 archetype

# event_temperature 影响极端派占比
- event_temperature < 0.5：极端派总占比 < 20%
- event_temperature >= 0.5：极端派总占比 30-50%

# event_intensity 影响传播者多样性
- event_intensity 高：多种类型（粉丝、专家、批评者、支持者）
- event_intensity 低：少量客观网友
```

### 4.3 重要发现：Phase 3 未使用

**源文件**：`src/phase3_tick_simulation.py`

执行以下命令验证：
```bash
grep -n "event_temperature\|event_intensity" src/phase3_tick_simulation.py
# 无匹配结果
```

这两个参数**只影响初始 Agent 的数量和类型构成**，但不影响：
- 每轮发言概率
- 立场演化幅度
- 极化程度
- 任何模拟动态

---

## 五、group_distribution_strategy（v1.1.7 新增）

### 5.1 源文件

**Prompt 定义**：`src/phase1_entity_extraction.py:54-73`

### 5.2 判断逻辑

| 条件 | 策略 | 说明 |
|------|------|------|
| 高烈度(≥0.8) + 负面事件 + 官方延迟回应/拒不承认 | no_supporters | 完全不生成支持者 |
| 高烈度(≥0.8) + 负面事件 + 官方延迟回应但认错 | minimal_supporters | 极少数支持者（5-10%） |
| 高烈度(≥0.8) + 负面事件 + 官方及时回应且认错 | normal | 正常生成（20-30%） |
| 其他情况 | normal | 正常生成 |

### 5.3 判断标准

```python
- 及时回应：事件发生后 24 小时内回应
- 延迟回应：事件发酵后才回应，或被舆论压力逼迫回应
- 拒不承认：官方否认/甩锅/试图掩盖
- 负面事件：涉及食品安全、医疗事故、校园暴力、官员不当行为等
```

**注意**：这是**唯一**有事件类型判断的地方，但只用于群体分布策略，不用于 event_temperature 或 event_intensity。

---

## 六、已识别的问题

### 6.1 Critical Bug：除零漏洞（已修复）

**源文件**：`src/phase1_entity_extraction.py:498-504`

**问题**：当 `filtered_spreaders` 为空时，虽然不会进入除法块，但缺少明确防护。

**修复**：已添加 `len(filtered_spreaders) > 0` 检查。

---

### 6.2 MAX_POSTS_PER_TICK 未生效

**源文件**：`config.py:131`

**问题**：定义了 `MAX_POSTS_PER_TICK = 3`，但代码中从未使用。

---

### 6.3 事件类型未纳入温度/烈度判断

**源文件**：`src/phase1_entity_extraction.py:36-52`

**问题**：event_temperature 和 event_intensity 的判断没有考虑事件类型特征。

---

## 七、数据验证

### 7.1 test5 输出示例

**源文件**：`outputs/outputs_test5/entities_and_relations.json:3-4`

```json
"event_temperature": 0.7,
"event_intensity": 0.8,
```

### 7.2 test5 Tick 日志示例

**源文件**：`outputs/outputs_test5/tick_logs/tick_1.json`

```json
{
  "tick": 1,
  "entries": [
    {
      "agent_id": 2,
      "group_name": "政策批评者",
      "previous_stance": 8.6,
      "current_stance": 8.3,
      "stance_delta": -0.3,
      "comment": "南通文旅？禁毒政策还带特权？别骗人了。",
      "reasoning": "表面维护实则包庇，立场动摇"
    }
  ],
  "global_metrics": {
    "mean_stance": 5.46,
    "std_stance": 1.88,
    "polarization_index": 0.34
  }
}
```

---

## 八、总结与建议

### 8.1 当前实现总结

1. **发言逻辑**：全量发言，无概率筛选
2. **event_temperature**：基于涉及范围、争议性、社会影响的主观评分
3. **event_intensity**：基于情绪强度、参与多样性的主观评分
4. **参数影响**：仅影响初始人群构成，不影响模拟动态

### 8.2 改进建议

1. **发言逻辑**：可考虑增加基于概率的发言筛选，引入 `event_temperature` 影响发言率
2. **事件类型**：在 LLM1 判断时增加事件类型附加调整系数
3. **Phase 3 动态**：可考虑让 event_intensity 影响立场演化幅度

---

## 九、核心参数详解

### 9.1 stance_score（立场分）

| 项目 | 内容 |
|------|------|
| **定义** | Agent 的当前立场，1.0-10.0 |
| **语义** | 1.0-3.0=强烈批评，4.0-6.0=中立观望，7.0-10.0=强烈支持 |
| **生成** | LLM2 在 Phase 1 生成 archetype 时判断 |
| **变化** | 每轮通过 `apply_stance_constraint()` 约束后更新 |
| **注意** | 1分=最支持（正面），10分=最批评（负面），方向反向直觉 |

**源文件**：
- 定义：`src/schemas.py:250`
- 语义规则：`src/phase3_tick_simulation.py:40-46`
- 约束逻辑：`src/phase3_tick_simulation.py:498-553`

---

### 9.2 susceptibility（易感性）

| 项目 | 内容 |
|------|------|
| **定义** | Agent 被他人发言影响的程度，0.0-1.0 |
| **语义** | 越高越容易被说服改变立场 |
| **生成** | LLM2 在 Phase 1 生成 archetype 时判断 |
| **作用** | 调制 stance 变化幅度（×0.75 ~ ×1.25） |

**计算公式**：
```python
susceptibility_modulation = 1 + config.SUSCEPTIBILITY_MODULATION_FACTOR * (susceptibility - 0.5)
# SUSCEPTIBILITY_MODULATION_FACTOR = 0.5
# susceptibility=1.0 → modulation=1.25
# susceptibility=0.0 → modulation=0.75
```

**源文件**：
- 定义：`src/schemas.py:251`
- 接入逻辑：`src/phase3_tick_simulation.py:529-534`

---

### 9.3 confirmation_bias_level（确认偏差级别）

| 项目 | 内容 |
|------|------|
| **定义** | Agent 对信息的接受倾向，none/weak/strong |
| **语义** | strong=只接受同立场，weak=有限接受，none=理性无差别 |
| **生成** | 根据 stance_score 和 susceptibility 规则分配 |
| **作用** | 决定 stance 变化幅度上限（±0.3/±1.0/±2.0） |

**分配规则**（`src/phase1_persona_engine.py:59-62`）：
```
极端立场(<3 或 >7) + susceptibility < 0.5 → strong
中立立场(4-6) + susceptibility > 0.7 → none
其他 → weak
```

**Prompt 规则**（`src/phase3_tick_simulation.py:49-71`）：
| 级别 | Prompt 描述 | 变化上限 |
|------|------------|---------|
| strong | 只接受同立场，忽略/反驳反对意见 | ±0.3 |
| weak | 有限接受，可能略微被影响 | ±1.0 |
| none | 理性观察者，愿根据论点改变 | ±2.0 |

**源文件**：
- 定义：`src/schemas.py:252-254`
- Prompt 模板：`src/phase3_tick_simulation.py:49-71`
- 约束逻辑：`src/phase3_tick_simulation.py:522-527`

---

### 9.4 susceptibility 与 confirmation_bias 的关系

**当前机制**：两者在 `apply_stance_constraint()` 中叠加作用于变化幅度。

```python
# 1. confirmation_bias → 基础变化上限
base_delta_map = {"strong": 0.3, "weak": 1.0, "none": 2.0}
base_delta = base_delta_map.get(confirmation_bias_level, 1.0)

# 2. susceptibility → 调制系数
susceptibility_modulation = 1 + 0.5 * (susceptibility - 0.5)
effective_delta = base_delta * susceptibility_modulation
```

**效果示例**：
| confirmation_bias | susceptibility | 最终变化上限 |
|------------------|----------------|-------------|
| strong (0.3) | 1.0 (+25%) | 0.3 × 1.25 = **0.375** |
| strong (0.3) | 0.0 (-25%) | 0.3 × 0.75 = **0.225** |
| none (2.0) | 1.0 (+25%) | 2.0 × 1.25 = **2.5** |
| none (2.0) | 0.0 (-25%) | 2.0 × 0.75 = **1.5** |

**问题**：两个参数语义不同（confirmation_bias=接受倾向，susceptibility=变化幅度），但效果叠加容易混淆。

**重构方向**：
- **方向1**：合并为一个参数 `change_resistance`
- **方向2**：分离关注点——confirmation_bias 管"接受倾向"，susceptibility 管"变化幅度上限"
- **方向3**：维持现状，confirmation_bias 只影响 Prompt，不参与硬性计算

---

### 9.5 三者关系图

```
初始立场（LLM2生成）
    ↓
apply_stance_constraint() 约束
    ├── confirmation_bias_level → 基础变化上限（Prompt影响）
    ├── susceptibility → 调制系数（×0.75 ~ ×1.25）
    └── group_distribution_strategy → 舆论压力额外调制
    ↓
最终 stance（每轮更新）
```

---

### 9.6 event_temperature 与 event_intensity 对比

| 项目 | event_temperature | event_intensity |
|------|------------------|-----------------|
| **定义** | 事件热度/关注度 | 事件烈度/情绪激烈程度 |
| **范围** | 0.0=冷门，1.0=全网热议 | 0.0=平和，1.0=疯狂 |
| **生成** | LLM1：涉及范围+争议性+社会影响 | LLM1：情绪强度+参与多样性 |
| **当前影响** | Agent数量、极端派占比 | 传播者多样性 |
| **Phase 3 影响** | **未使用** | **未使用** |

---

## 十、改进优先级

### 10.1 问题清单

| 优先级 | 问题 | 改动量 | 理由 |
|--------|------|--------|------|
| **1️⃣** | C. 事件类型纳入温度/烈度判断 | 小（30-60min） | 最小改动，立竿见影 |
| **2️⃣** | A. susceptibility 与 confirmation_bias 重叠 | 中（2-4h） | 架构层面优化，语义更清晰 |
| **3️⃣** | B. event_temperature/intensity 接入 Phase 3 | 中（2-4h） | 让模拟动态与事件特征联动 |
| **4️⃣** | A2. Phase 3 发言逻辑优化 | 中（1-2h） | 核心模拟机制改进 |
| **5️⃣** | D. IPC stance 模型重构 | 大（1-2天） | 工作量最大，延后 |

### 10.2 建议路径

```
1. C（快速见效）→ 2. A（架构优化）→ 3. B（动态联动）
```

### 10.3 各问题详细说明

**问题 C：事件类型纳入温度/烈度判断**
- 当前：纯主观评分，无事件类型区分
- 修复：LLM1 prompt 增加事件类型附加系数
  - 食品安全、医疗事故 → 基础温度 +0.1
  - 校园暴力、未成年人 → 基础烈度 +0.15
  - 官员不当行为 → 争议性 +0.2

**问题 A：susceptibility 与 confirmation_bias 重叠**
- 当前：两者叠加限制变化幅度
- 修复：分离关注点
  - confirmation_bias → 只影响 Prompt 行为描述
  - susceptibility → 接管变化幅度调制

**问题 B：event_temperature/intensity 接入 Phase 3**
- 当前：只在 Phase 1 影响初始人群构成
- 修复：
  - event_intensity → 调制变化幅度上限（×1.0 ~ ×1.3）
  - event_temperature → 影响发言概率（可选）

**问题 A2：Phase 3 发言逻辑**
- 当前：全量发言，无筛选
- 修复：引入发言概率
  - 基于 susceptibility 或 event_temperature
  - 或使用优先级队列

**问题 D：IPC stance 模型重构**
- 当前：单一维度 stance_score
- 修复：三维度
  - Intensity（强度）
  - Polarity（极性）
  - Certainty（确定性）
- 工作量：涉及 schemas.py、Phase 3、报告格式重构
