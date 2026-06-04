# IPC 框架 Phase 1 重构设计文档

**文档版本**：v1.0
**日期**：2026-04-01
**状态**：待与导师讨论

---

## 一、背景与目标

### 1.1 为什么重构

当前 `event_temperature` 职责混杂：
- 同时决定**人数规模**（3-5 / 5-7 / 7-10）
- 同时决定**极端派占比**（<20% / 30-50%）

这违反了**单一职责原则**，且 event_intensity 在 Phase 3 中完全未使用。

### 1.2 重构目标

1. 拆分 event_temperature → event_scale（规模）+ event_controversy（争议性）
2. 引入 SEIR Paper 的 IPC 框架（I/P/C）作为 Agent stance 的原生表示
3. 废除 confirmation_bias_level（从未正确实现其"调节发言多样性"的设计初衷）
4. 极化从 I/P/C 分布中**自然涌现**，而非直接指定比例
5. group_distribution_strategy 合并进 event_controversy

---

## 二、Phase 1 架构变更

### 2.1 参数体系对比

| 当前 | 重构后 |
|------|--------|
| event_temperature | event_scale + event_controversy |
| event_intensity | 废除（功能并入 event_controversy 或 event_type） |
| group_distribution_strategy | 合并进 event_controversy |
| confirmation_bias_level | 废除 |
| stance_score | 拆分为 I + P |
| susceptibility | 保留 |
| C | 系统固定推导，不作为独立字段 |

### 2.2 新参数定义

#### event_scale（事件规模）

**定义**：事件涉及的规模范围，0.0-1.0

**语义**：0.0=个人事件，1.0=全社会事件

**子维度**：
| 维度 | 0.2 | 0.5 | 0.8 |
|------|-----|-----|-----|
| 涉及范围 | 个人 | 群体 | 全社会 |
| 参与多样性 | 单一群体 | 多个群体 | 全民参与 |

**作用**：
- 影响 Agent 总人数上限
- 影响 I 的分布（规模大 → I 标准差可能更大，人群多样性强）

#### event_controversy（争议性）

**定义**：事件的争议程度，0.0-1.0

**语义**：0.0=事实清晰、对错分明，1.0=高度对立、黑白颠倒

**子维度**：
| 维度 | 0.2 | 0.5 | 0.8 |
|------|-----|-----|-----|
| 是非清晰度 | 清晰 | 存在争议 | 高度对立 |
| 道德判断 | 明确对错 | 灰色地带 | 黑白颠倒 |

**事件类型附加系数**（可调参接口）：
| 事件类型 | 争议性偏移 |
|---------|-----------|
| 食品安全/医疗事故/校园暴力/官员不当行为 | +0.15 ~ +0.20 |
| 环境灾害/产品质量问题 | +0.05 ~ +0.10 |
| 学术不端/政策争议 | 0 ~ +0.05 |
| 普通事故/娱乐八卦 | 0 |

**合并功能**：接管 group_distribution_strategy 的职责
- 高争议 + 官方拒不承认 → 极低支持者比例
- 高争议 + 官方认错 → 低支持者比例
- 低争议 → 正常支持者比例

#### event_type（事件类型）

**定义**：事件的分类类型

**用途**：
- 作为可调参接口，影响 event_controversy 的偏移系数
- 留有扩展空间

### 2.3 IPC 框架定义

#### I（Intensity，立场强度）

**定义**：Agent 立场的坚定程度，1-10

**语义**：
| 范围 | 语义 |
|------|------|
| 1-3 | 极度动摇，容易被说服改变 |
| 4-6 | 中等坚定，有一定立场但可偏移 |
| 7-10 | 极度坚定，极难被说服改变 |

**生成方式**：Generator 在 Analyzer 给出的约束范围内自主判断

#### P（Position，立场方向）

**定义**：Agent 立场方向，+1 或 -1

**语义**：
| 值 | 语义 |
|----|------|
| +1 | 支持/维护 |
| -1 | 批评/反对 |

**分裂点**：stance_score ≥ 6 → P=+1；≤ 5 → P=-1

**分布控制**：由 event_controversy 驱动不对称比例
- 高争议(>0.7) → 70% 反对 / 30% 支持
- 中争议(0.3-0.7) → 55% 反对 / 45% 支持
- 低争议(<0.3) → 40% 反对 / 60% 支持

#### C（Consistency，一致性）

**定义**：Agent 立场与核心信念的一致性，-1 到 +1

**计算公式**（系统固定推导）：
```
C = P × (I / 10)
```

**语义**：
| C 值 | 语义 |
|------|------|
| +0.8 ~ +1.0 | 坚定支持者，与核心信念高度一致 |
| +0.2 ~ +0.7 | 弱支持者，立场有一定一致性 |
| -0.7 ~ -0.2 | 弱批评者，立场有一定一致性 |
| -0.8 ~ -1.0 | 坚定批评者，与核心信念高度一致 |

**注意**：C 不作为 Generator 的独立输出字段，由系统自动计算。

---

## 三、Generator Prompt 约束机制

### 3.1 Analyzer → Generator 约束传递

Analyzer 输出数值，Generator Prompt 以**语义描述**注入，LLM 在框架内自主生成具体值。

**示例**：
```
event_scale: 0.7（高规模）
event_controversy: 0.8（高争议）
event_type: 食品安全

→ Generator Prompt 约束描述：
"该事件为全社会高度关注的食品安全事件，人群分化严重。
  预计生成 7-10 个 Agent，人群 I 分布偏高中（多数 6-9），
  立场分布：约 70% 持批评/反对立场，30% 持支持/维护立场。
  I 范围约束：4-9（大多数在 6-8 之间）"
```

### 3.2 I/P 分布参数（供 Prompt 使用）

**I 分布约束**（由 event_scale 决定）：
| event_scale | 人数范围 | I 分布描述 |
|------------|---------|-----------|
| < 0.3 | 3-5 | 多数偏中立（3-6），少量坚定（7-9） |
| 0.3-0.7 | 5-7 | 中等分布（4-7 为主） |
| ≥ 0.7 | 7-10 | 高度分化（3-10 都有，极端多） |

**P 分布约束**（由 event_controversy 决定）：
| event_controversy | 反对/支持比例 |
|-------------------|--------------|
| < 0.3 | 40% / 60% |
| 0.3-0.7 | 55% / 45% |
| > 0.7 | 70% / 30% |

**group_distribution_strategy 合并逻辑**：
| 条件 | P 支持比例修正 |
|------|--------------|
| 高争议 + 官方拒不承认 | 0-5% |
| 高争议 + 官方延迟认错 | 5-15% |
| 其他 | 按 event_controversy 正常比例 |

---

## 四、IPC 定义上下文

### 4.1 内嵌形式

IPC 定义以 Prompt 内嵌形式提供给 Agent，供 Generator 在生成 archetype 时理解 I/P/C 的语义。

**内嵌内容**：
```
【I（Intensity，立场强度）】
- 定义：Agent 立场的坚定程度，1-10
- 语义：I 越高，越不容易被说服改变立场
- 示例：I=8-10 极度坚定，I=4-6 中等，I=1-3 极易动摇

【P（Position，立场方向）】
- 定义：Agent 立场方向，+1 或 -1
- +1 = 支持/维护官方或品牌
- -1 = 批评/反对
- 由 stance_score 决定：≥6 → +1，≤5 → -1

【C（Consistency，一致性）】
- 定义：立场与核心信念的一致性，-1 到 +1
- 计算公式：C = P × (I / 10)，系统自动计算
- 不需要你生成，系统会根据 I 和 P 自动推导
```

### 4.2 未来扩展接口

当前：Prompt 内嵌 IPC 定义

未来可切换为 RAG：
- ChromaDB 存储 IPC 论文片段
- Generator 执行前先检索相关上下文

---

## 五、schemas.py 数据结构变更

### 5.1 废除字段

```python
# 废除
event_temperature: float
event_intensity: float
confirmation_bias_level: str  # "none" | "weak" | "strong"
```

### 5.2 新增/修改字段

```python
# 新增
event_scale: float = Field(..., description="事件规模：0.0=个人，1.0=全社会")
event_controversy: float = Field(..., description="事件争议性：0.0=清晰，1.0=高度对立")
event_type: str = Field(..., description="事件类型，如：食品安全、医疗事故")

# OpinionSpreader 修改
class OpinionSpreader(BaseModel):
    # 原有字段
    group_name: str
    related_event_entity: str
    description: str
    susceptibility: float

    # stance_score 替换为 I 和 P
    I: float = Field(..., description="立场强度 1-10，越高越坚定")
    P: int = Field(..., description="立场方向：+1=支持，-1=反对")

    # C 由系统计算，不存储
    # @property
    # def C(self) -> float:
    #     return self.P * (self.I / 10)

    # 废除 confirmation_bias_level
```

### 5.3 I/P/C 便捷访问接口

```python
class OpinionSpreader(BaseModel):
    @property
    def stance_score(self) -> float:
        """兼容属性：将 I/P 映射回 1-10 分数"""
        if self.P == +1:
            return self.I  # 7-10
        else:
            return 11 - self.I  # 映射：P=-1 时 I=10 → score=1

    @property
    def C(self) -> float:
        """一致性：系统计算"""
        return self.P * (self.I / 10)
```

---

## 六、Phase 1 Prompt 变更

### 6.1 Analyzer Prompt 变更

**变更点**：
1. 输出 event_temperature + event_intensity → 改为 event_scale + event_controversy + event_type
2. 增加 event_type 分类选项表（可调参接口）
3. 群体分布策略逻辑合并进 event_controversy 判断

### 6.2 Generator Prompt 变更

**变更点**：
1. 输入：event_temperature + event_intensity → event_scale + event_controversy + event_type
2. 输出：stance_score → I (1-10) + P (+1/-1)
3. 移除 confirmation_bias_level 相关描述
4. 增加 IPC 定义上下文
5. 约束传递：event_scale/controversy → I 分布描述 + P 分布比例

### 6.3 Validator Prompt 变更

**变更点**：
1. 校验：stance_score → I + P
2. 校验规则更新：I ∈ [1,10]，P ∈ {+1, -1}
3. C 的合理性由系统保证，无需校验

---

## 七、文件变更清单

| 文件 | 变更类型 |
|------|---------|
| `src/schemas.py` | 修改：废除字段、新增字段、I/P 替换 stance_score |
| `src/phase1_entity_extraction.py` | 修改：Analyzer/Generator/Validator Prompt 重写 |
| `src/phase1_persona_engine.py` | 可能废除或大幅简化（Generator 已接管 I/P 生成） |
| `src/phase3_tick_simulation.py` | 无变更（本次只做 Phase 1） |
| `src/phase4_report_agent.py` | 无变更（本次只做 Phase 1） |
| `config.py` | 可能新增 event_type 偏移系数配置 |
| `docs/dev_spec.md` | 更新：第 3 章参数定义、第 4 章数据流 |

---

## 八、验收标准

### 8.1 Phase 1 验收

- [ ] Analyzer 输出 event_scale + event_controversy + event_type
- [ ] Generator 输出 I (1-10) + P (+1/-1)，不再有 stance_score
- [ ] C = P × (I/10) 系统自动计算
- [ ] Validator 校验 I ∈ [1,10]，P ∈ {+1, -1}
- [ ] group_distribution_strategy 行为由 event_controversy 接管
- [ ] confirmation_bias_level 完全废除

### 8.2 端到端验收

- [ ] 运行 `python main.py seeds/test*.txt`
- [ ] entities_and_relations.json 包含 I + P 字段
- [ ] 极化从 I/P 分布自然涌现（不再直接指定极端派比例）
- [ ] Phase 3/4 正常工作（依赖 stance_score 兼容属性）

---

## 九、待讨论项

以下内容留到与导师讨论后决定：

1. **event_scale 是否需要按事件类型分级？**
   - 比如食品安全事件天然规模更大？

2. **event_type 的完整分类体系**
   - 当前只是初步列举，需要系统性设计

3. **event_controversy 的事件类型偏移系数**
   - 具体偏移量需要标定

4. **Phase 1 之外的 IPC 变化逻辑**
   - Phase 3 的 f_A + D(A,B) 机制本次不做

---

*文档创建时间：2026-04-01*
