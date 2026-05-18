# 优化后的模拟关键变化点定义与识别计算代码说明报告 v0.1

## 1. 报告目的

本报告用于统一产品侧与技术侧对"模拟关键变化点"的理解，并为后续风险补丁后的实现提供说明材料。

阅读对象：产品端（理解它是什么、报告怎么表达、为什么要等风险补丁）和技术侧（理解优化后识别逻辑、参考实现代码、输出字段）。

---

## 2. 一句话定义

**模拟关键变化点**，是系统在多轮舆情推演过程中，根据模拟立场、群体分化、关键群体迁移和风险信号变化，识别出的值得解释的模拟演化节点。

它不是现实舆情拐点，不代表全网舆情真实转折，只代表本轮模拟条件下的结构性变化。

它和现实舆情拐点的核心区别：

| | 模拟关键变化点 | 现实舆情拐点 |
|---|---|---|
| 数据来源 | 模拟推演 tick_logs | 真实社交媒体/新闻数据 |
| 因果性 | 模拟设定下的条件性结果 | 真实社会因果 |
| 可验证性 | 可通过重跑模拟复现 | 不可复现 |
| 治理含义 | 预警参考 | 可直接指导治理动作 |

---

## 3. 为什么需要优化

当前版本已经具备基础识别能力——系统可以根据模拟极化指数变化发现群体状态出现明显变化的轮次。

但为了让报告解释更稳定、更贴近业务研判，需要在后续版本中纳入更多结构化信号。优化目标是从：

> **单一波动识别**（仅看极化指数变化）

升级为：

> **多信号结构变化识别**（同时看立场转向、群体分化、关键群体迁移、风险升级）

这样做的业务价值是：报告不再只能说"第 X 轮极化指数变了"，而是能说"第 X 轮关键群体开始从观望转向质疑，同时群体分化加剧，值得关注"。

---

## 4. 优化后的识别信号

| 信号 | 含义 | 作用 |
|---|---|---|
| 模拟立场均值变化 | 群体整体态度是否明显转向 | 判断整体态度方向变化 |
| 模拟极化指数变化 | 群体之间分歧是否扩大 | 判断群体分化或对立增强 |
| 关键群体立场迁移 | 重点群体是否从观望转向质疑、放大或缓冲 | 判断风险推动者变化 |
| 风险等级变化 | 风险是否从低风险进入中高风险区间 | 判断风险升级 |
| 风险类型变化 | 风险性质是否从事实争议转向程序、监管、回应等问题 | 判断风险焦点变化 |

**重要说明**：风险等级变化和风险类型变化需要等待风险计算模块补丁完成后才能稳定接入。前三个信号（立场变化、极化变化、关键群体迁移）可以在风险补丁之前先接入。

---

## 5. 优化后的计算逻辑

### 5.1 模拟立场均值变化

```
stance_mean_delta_t = mean_stance_t - mean_stance_{t-1}
```

如果 `stance_mean_delta_t` 为显著负值（如 < -0.3），说明模拟群体整体更趋向质疑、批评或不信任。这个信号回答产品侧问题："哪一轮开始整体态度转向？"

### 5.2 模拟极化指数变化

```
polarization_delta_t = polarization_index_t - polarization_index_{t-1}
```

如果 `polarization_delta_t` 显著升高（如 > 0.1），说明不同群体之间分歧扩大，讨论可能从事实争议进入价值站队阶段。这个信号回答："哪一轮开始群体明显分化？"

### 5.3 关键群体立场迁移

```
group_stance_delta_{g,t} = group_stance_{g,t} - group_stance_{g,t-1}
```

按群体（如"质疑方""观望群体""支持方"）分别计算每轮立场均值变化。如果某个关键群体出现显著迁移（如 > 1.0），说明风险推动者或缓冲群体可能发生角色变化。这个信号回答："哪一轮关键群体开始转为风险放大器？"

### 5.4 多信号触发原则

系统不会因为单个信号的微小波动就标记关键变化点。当**多个信号同时触发**，且至少一个结构性信号（立场转向、极化加剧、群体迁移）成立时，才将某一轮标记为"模拟关键变化点"。

---

## 6. 优化后的识别计算逻辑

### 6.1 当前源码中的基础实现

当前仓库中 `src/phase4/report_agent.py:756-799` 的 `identify_inflection_points` 函数已实现了基础识别能力，核心逻辑为：

```python
# 当前真实源码（src/phase4/report_agent.py:778-796，简化展示）
for i in range(1, len(tick_logs)):
    prev_pol = tick_logs[i - 1].global_metrics.polarization_index
    curr_pol = tick_logs[i].global_metrics.polarization_index
    pol_delta = abs(curr_pol - prev_pol)

    # 唯一触发条件：极化指数变化超过 0.1
    if pol_delta > 0.1 and tick_logs[i].entries:
        max_entry = max(tick_logs[i].entries, key=lambda e: abs(e.stance_delta))
        inflection_points.append(InflectionPoint(
            tick=tick_logs[i].tick,
            agent_id=max_entry.agent_id,
            group_name=node.group_name if node else "未知",
            pivotal_comment=max_entry.comment[:50],
            impact_description=f"模拟极化指数变化 {pol_delta:.2f}，立场偏移 {max_entry.stance_delta:+.1f}",
        ))

return inflection_points[:3]
```

当前逻辑的数据来源是 `tick_logs[i].global_metrics`（定义于 `src/schemas/phase3.py`），其中 `polarization_index` 和 `mean_stance` 在每一轮模拟后都已计算并存储。

### 6.2 优化方向：从单信号扩展为多信号

在上述基础实现之上，优化的方向是增加两个立刻可用的信号：

**信号一：模拟立场均值变化**（数据已就绪）

`mean_stance` 已存在于 `tick_logs[i].global_metrics.mean_stance`（`src/schemas/phase3.py:64`），增加以下判断：

```python
prev_mean = tick_logs[i - 1].global_metrics.mean_stance
curr_mean = tick_logs[i].global_metrics.mean_stance
stance_mean_delta = curr_mean - prev_mean

if abs(stance_mean_delta) >= 0.30:
    trigger_signals.append("stance_mean_shift")
```

**信号二：关键群体立场迁移**（数据已就绪，需新增聚合逻辑）

每轮 `tick_logs[i].entries` 中每个 AgentEntry 已包含 `group_name`（`src/schemas/phase3.py:11`）和 `current_stance`（`src/schemas/phase3.py:14`）。新增按群体聚合的 stance 变化检测：

```python
# 对当前轮次的 entries 按 group_name 聚合 current_stance 均值
# 与上一轮同群体均值比较
# 当 abs(group_delta) >= 1.0 时，标记该群体为 affected_group
```

**信号三：模拟极化指数变化**（当前已实现，保留）

当前已有的 `polarization_delta > 0.1` 判断保持不变。优化点是保留方向性（区分极化加剧 vs 极化缓和），而非仅使用绝对值。

**信号四和五：风险等级变化 / 风险类型变化**（需等待风险补丁）

这两个信号依赖逐 tick 的风险计算结果。当前 `assess_risk()`（`src/phase4/report_agent.py:829-920`）仅在模拟结束时调用一次。风险补丁完成后，可增加以下判断：

```python
if per_tick_risk_levels[i] != per_tick_risk_levels[i - 1]:
    trigger_signals.append("risk_level_changed")
```

### 6.3 优化后的整体判断流程

在现有 `identify_inflection_points` 基础上，优化后的判断流程为：

1. 遍历每对相邻 tick，计算三个可立即接入的信号（立场均值变化、极化变化、关键群体迁移）
2. 当至少一个结构性信号触发时，记录本轮为候选变化点
3. 按触发信号数量和变化幅度排序，取 top-N
4. 风险等级/类型变化信号（等补丁后接入）作为加分项

核心变化总结：

| 维度 | 当前实现 | 优化后 |
|------|---------|--------|
| 触发信号数 | 1（polarization_delta） | 3（+ stance_mean_delta + key_group_stance_shift） |
| 风险信号 | 无 | 2（risk_level_changed / risk_type_changed，等补丁） |
| 排序方式 | FIFO（时间顺序） | 按触发信号数量 + 变化幅度降序 |
| 输出字段 | 5 个基础字段 | 扩展为含 change_type、trigger_signals、source_metrics、confidence |

以上优化基于当前仓库中已有的数据字段，不要求新增数据结构。具体实现将在风险补丁完成后进入开发迭代。

---

## 7. 输出字段建议

优化后的每个模拟关键变化点建议包含以下字段：

```json
{
  "tick": 2,
  "change_type": "polarization_increase",
  "trigger_signals": ["polarization_delta", "key_group_stance_shift"],
  "affected_groups": ["学生群体", "消费者群体"],
  "source_metrics": {
    "stance_mean_delta": -0.35,
    "polarization_delta": 0.12,
    "max_group_stance_delta": -1.1
  },
  "business_explanation": "第2轮附近，部分关键群体立场明显转向质疑，群体分化程度上升。",
  "confidence": "medium"
}
```

字段含义：

| 字段 | 含义 | 来源 |
|------|------|------|
| `tick` | 出现变化的模拟轮次 | code-owned（算法自动计算） |
| `change_type` | 主要变化类型 | code-owned（按优先级从触发信号中选择） |
| `trigger_signals` | 触发该变化点的信号列表 | code-owned（阈值判断结果） |
| `affected_groups` | 受影响的关键群体 | code-owned（按群体聚合 stance 变化） |
| `source_metrics` | 支撑判断的结构化指标值 | code-owned（从 tick_logs 直接计算） |
| `business_explanation` | 报告侧可读解释 | code-owned（模板化生成，可后续 LLM 润色） |
| `confidence` | 置信度（high/medium/low） | code-owned（按触发信号数量判定） |

设计原则：数值计算类字段由代码侧生成（可追溯、可复现），解释性文本由代码侧提供模板化初稿（可后续由 LLM 在约束下润色）。

---

## 8. 与风险计算补丁的关系

**风险计算补丁完成前**：

模拟关键变化点可以先基于立场变化、极化变化、关键群体迁移三个信号进行识别。这三个信号的数据在每一轮模拟推演中都已具备，不需要等待风险补丁。

**风险计算补丁完成后**：

可以进一步接入 `risk_level_changed` 和 `risk_type_changed`，使关键变化点能够解释"哪一轮开始风险升级"或"哪一轮风险性质发生变化"。这会让报告的研判深度进一步提升。

**风险补丁不是模拟关键变化点的前置必需条件，但它决定关键变化点能否和风险升级逻辑打通。**

简单来说：

- 不等补丁 → 可以说"第 2 轮关键群体态度转向，群体分化加剧"
- 等补丁后 → 还可以说"第 2 轮风险等级从低风险进入中风险"

---

## 9. 报告侧表达方式

### 有关键变化点时

> 本轮模拟显示，第 X 轮附近出现值得关注的模拟关键变化点，主要表现为【关键群体】立场明显变化，同时模拟群体分化程度上升。该节点仅代表本轮模拟设定下的演化特征，不等同于现实舆情传播拐点。

### 无关键变化点时

> 本轮模拟未发现显著模拟关键变化点。

### 禁止表达

报告不得出现以下表述：

- 现实舆情已经出现拐点。
- 全网舆情发生转折。
- 公众态度已经改变。
- 系统识别到真实传播拐点。
- 任何将模拟节点包装为现实事实的表述。

### 补充规则

- 模拟关键变化点只能来自代码侧识别结果，LLM 不得自行判断哪一轮是关键变化点。
- 无代码侧关键变化点时，报告必须写"本轮模拟未发现显著模拟关键变化点"，不得留空或写"待评估"。
- 报告中应使用"模拟关键变化点"这个完整术语，不使用"拐点""关键拐点"等简称。

---

## 10. 给产品侧的最终结论

1. **模拟关键变化点是模拟轨迹中的解释节点，不是现实舆情拐点。**它帮助分析师快速定位哪些轮次值得关注，但不代表真实世界已经发生的传播变化。

2. **优化方向是从单一极化波动升级为多信号综合识别。**当前版本只看极化指数的变化幅度，优化后会同时看立场转向、群体分化、关键群体迁移等多个维度，让判断更稳定。

3. **现阶段可先接入立场变化、极化变化、关键群体迁移。**这三个信号的数据在模拟过程中已经具备，不需要等待其他模块。

4. **风险补丁完成后，再接入风险等级变化和风险类型变化。**这样关键变化点就能进一步回答"哪一轮风险开始升级""哪一轮风险焦点发生转移"。

5. **报告侧只解释代码侧已识别的关键变化点，不允许 LLM 自行生成。**这是硬约束——代码侧没标记的轮次，报告不能声称有变化点；代码侧标记了的，报告可以解释但不能曲解。
