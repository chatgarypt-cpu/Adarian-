# Enhanced SEIR Stance 模型重构设计文档

**文档版本**：v1.0
**日期**：2026-03-30
**基于 Paper**：Enhanced SEIR Model（SEIR增强模型.pdf）
**作者**：Claude Code

---

## 一、背景与目标

### 1.1 为什么需要重构

当前 Phase 3 的 stance 计算存在以下问题：

| 问题 | 描述 |
|------|------|
| 单一维度混淆 | stance_score 1-10 同时表示方向和强度，概念混乱 |
| confirmation_bias 仅做截断 | 只限制了最大变化幅度（±0.3），未实现方向性影响 |
| susceptibility 从未使用 | 字段存在但未接入计算逻辑 |
| 信息新颖度缺失 | agent 之间缺乏"信息差异"的衰减机制 |
| Consistency 约束缺失 | 缺乏对核心信念一致性的校验机制 |

### 1.2 重构目标

1. 实现 Paper 中定义的 I/P/C 三维度 stance 模型
2. 实现基于确认偏差的方向性影响函数 f_A
3. 实现信息新颖度 D(A,B) 衰减机制
4. 实现 Consistency 约束校验
5. 启用 susceptibility 字段

### 1.3 参考 Paper

- **论文名称**：Enhanced SEIR Model（SEIR增强模型.pdf）
- **核心概念**：IPC 模型（Intensity / Position / Consistency）

---

## 二、Stance 的三维度表示

### 2.1 当前表示 vs Paper 表示

| | 当前实现 | Paper 设计 |
|--|---------|-----------|
| 表示方式 | 单一分数 1-10 | 三维度 I/P/C |
| 方向 | 1-5 反对，5 中立，6-10 支持 | P = +1 或 -1 |
| 强度 | 和方向混在一起 | I = 1-10，独立于方向 |
| 一致性 | 无 | C = -1 到 1 |

### 2.2 三维度定义

```
I (Intensity): 1-10，表示立场坚定程度
    - I = 1: 极度动摇，容易改变
    - I = 10: 极度坚定，极难改变

P (Position): +1 或 -1，表示立场方向
    - P = +1: 支持立场
    - P = -1: 反对立场

C (Consistency): -1 到 1，表示与核心信念的一致性
    - C > 0: 当前立场与核心信念一致
    - C < 0: 当前立场与核心信念冲突
    - C = 0: 立场中立

S (Strength of Core Belief): 1-10，核心信念强度（新增，从 susceptibility 派生）
    - S = 1 - susceptibility
    - S 高的人（susceptibility 低）核心信念强，不容易被改变
```

### 2.3 转换公式

**从当前格式转换**：
```
原 stance_score = 1-10
→ I = stance_score / 10（归一化到 0.1-1.0）
→ P = +1 (if stance_score > 5) else -1
→ C = P × I
→ S = 1 - susceptibility
```

**映射回 1-10**：
```
stance_score = I × 10（保留方向符号用于显示）
```

### 2.4 数据结构变更

**旧格式**（schemas.py）：
```python
agent_stances: Dict[int, float]  # agent_id -> stance_score (1-10)
```

**新格式**：
```python
@dataclass
class StanceState:
    I: float          # Intensity: 1-10
    P: int            # Position: +1 或 -1
    C: float          # Consistency: -1 到 1
    S: float          # Core Belief Strength: 1-10

agent_stances: Dict[int, StanceState]  # agent_id -> I/P/C/S
```

---

## 三、确认偏差函数 f_A

### 3.1 Paper 定义

f_A(B → A) 表示 agent B 对 agent A 的影响方向和幅度：

```
f_A(B → A) = 影响力方向和强度系数
```

**计算公式**：

```python
def compute_f_A(C_A: float, I_A: float, I_B: float,
                confirmation_bias_level: str) -> float:
    """
    C_A: agent A 的 consistency
    I_A: agent A 的 intensity
    I_B: agent B 的 intensity
    返回: f_A，方向性影响系数
    """

    # 提取确认偏差系数
    if confirmation_bias_level == "strong":
        alpha = 0.02   # 同立场接受系数
        beta = 0.02    # 反立场拒绝系数
    elif confirmation_bias_level == "weak":
        alpha = 0.05
        beta = 0.05
    else:  # "none"
        alpha = 0.10
        beta = 0.10

    # 计算强度比
    intensity_ratio = I_B / I_A if I_A > 0 else 0

    # f_A = α × C × (I_B / I_A)
    # C > 0 时，同立场加强；C < 0 时，反立场加强
    f_A = alpha * C_A * intensity_ratio

    return f_A
```

### 3.2 f_A 的物理意义

| C_A | I_B / I_A | f_A | 含义 |
|-----|-----------|-----|------|
| 0.9（坚定支持者） | 1.0 | 正向强化 | 同立场的人让 A 更坚定 |
| 0.9（坚定支持者） | 0.5 | 正向但弱 | 弱立场者对 A 影响小 |
| -0.3（轻微反对者） | 1.0 | 负向 | 反立场者让 A 更坚定（确认偏差） |
| 0.0（完全中立） | 任意 | 0 | 中立者不受影响 |

### 3.3 与当前实现的区别

| | 当前实现 | 新实现 |
|--|---------|--------|
| 同立场影响 | 无 | f_A > 0，强化现有立场 |
| 反立场影响 | 简单截断 | f_A < 0，负向强化（但比同立场弱） |
| 受 intensity 比影响 | 无 | 强立场者影响弱立场者 |
| 受 consistency 影响 | 无 | C 越高，偏差越强 |

---

## 四、信息新颖度 D(A,B)

### 4.1 Paper 定义

D(A,B) 表示信息从 B 传递到 A 时的新颖程度：

```
D(A,B) = w_P × |P_B - P_A| × I_B + w_C × |C_B - C_A| × I_B
```

**第一项**：立场方向差异带来的新意
- |P_B - P_A| = 2 表示完全相反立场，0 表示完全一致
- I_B 表示 B 的强度——B 越坚定，其立场差异越"有新意"

**第二项**：一致性差异带来的新意
- |C_B - C_A| 表示 A 和 B 对自己立场的自信程度差异
- 两人自信程度差异大时，也有新意

### 4.2 计算公式

```python
def compute_D_AB(P_A: int, P_B: int,
                C_A: float, C_B: float,
                I_B: float,
                w_P: float = 0.7,
                w_C: float = 0.3) -> float:
    """
    w_P: 立场方向差异权重
    w_C: 一致性差异权重
    返回: D(A,B)，信息新颖度
    """

    # 立场方向差异项
    position_diff = abs(P_B - P_A)  # 0 或 2

    # 一致性差异项
    consistency_diff = abs(C_B - C_A)  # 0 到 2

    D_AB = (w_P * position_diff * I_B +
             w_C * consistency_diff * I_B)

    return D_AB
```

### 4.3 默认参数

| 参数 | 默认值 | 说明 |
|------|-------|------|
| w_P | 0.7 | 立场方向差异权重 |
| w_C | 0.3 | 一致性差异权重 |

---

## 五、完整变化公式

### 5.1 ΔI_A 计算

```
ΔI_A = f_A × R_A × D(A,B)

其中：
    f_A = 确认偏差影响系数（见第三章）
    R_A = receptivity = susceptibility（从 schema 读取）
    D(A,B) = 信息新颖度（见第四章）
```

### 5.2 实现代码

```python
def compute_stance_change(
    A_stance: StanceState,
    B_stance: StanceState,
    confirmation_bias_level: str,
    susceptibility: float,
    w_P: float = 0.7,
    w_C: float = 0.3
) -> StanceState:
    """
    计算 agent A 在看到 agent B 的发言后的新 stance
    """

    # 1. 计算 f_A
    f_A = compute_f_A(
        C_A=A_stance.C,
        I_A=A_stance.I,
        I_B=B_stance.I,
        confirmation_bias_level=confirmation_bias_level
    )

    # 2. 计算 D(A,B)
    D_AB = compute_D_AB(
        P_A=A_stance.P,
        P_B=B_stance.P,
        C_A=A_stance.C,
        C_B=B_stance.C,
        I_B=B_stance.I,
        w_P=w_P,
        w_C=w_C
    )

    # 3. 计算 ΔI_A
    R_A = susceptibility
    delta_I = f_A * R_A * D_AB

    # 4. 更新 I
    new_I = A_stance.I + delta_I
    new_I = clamp(new_I, 1.0, 10.0)  # 限制在 [1, 10]

    # 5. Consistency 约束校验
    S_A = 1 - susceptibility
    new_C = A_stance.P * new_I / S_A

    # 如果 consistency 和 P 符号冲突，scale down
    if new_C * A_stance.P < 0:
        # 缩放 I 使 C 保持同符号
        new_I = A_stance.I * abs(A_stance.C) / abs(new_C)
        new_I = clamp(new_I, 1.0, 10.0)
        new_C = A_stance.P * new_I / S_A

    # 6. 返回新状态
    return StanceState(
        I=round(new_I, 2),
        P=A_stance.P,  # P 方向不变
        C=round(new_C, 2),
        S=round(S_A, 2)
    )
```

---

## 六、Agent 视野扩展

### 6.1 当前问题

当前 agent 每轮只看到 followee 的最新 1 条发言，且大多数 spreader 只看 Core 节点。

### 6.2 扩展方案

**每轮发言前，agent 先获取上下文**：

```python
def get_agent_context(agent_id: int, tick: int) -> List[AgentPost]:
    """
    获取 agent 在本轮看到的发言列表
    """

    # 1. 获取关注对象的最新发言
    followed_posts = get_followed_comments(agent_id, max_posts=5)

    # 2. 获取同群体其他 agent 在上一轮的发言（新增）
    same_group_posts = get_group_comments(agent_id, tick - 1)

    # 3. 获取事件实体的 Tick 0 发言（如果还没看过）
    event_posts = get_event_entity_posts()

    # 合并，去重
    all_posts = merge_and_deduplicate(followed_posts, same_group_posts, event_posts)

    return all_posts[:config.MAX_POSTS_PER_TICK]
```

### 6.3 视野扩展的效果

| 场景 | 扩展前 | 扩展后 |
|------|-------|-------|
| Agent 5 | 只看 Agent 0（胖貓，无发言） | 看 Agent 0 + 同群体其他人 + 事件实体 |
| Agent 8 | 只看 Agent 2（譚竹） | 看 Agent 2 + 同群体 + 其他事件实体 |

---

## 七、对现有代码的改动

### 7.1 schemas.py 改动

**新增 StanceState 数据类**：

```python
@dataclass
class StanceState:
    I: float          # Intensity: 1-10
    P: int            # Position: +1 或 -1
    C: float          # Consistency: -1 到 1
    S: float          # Core Belief Strength: 1-10

    @staticmethod
    def from_legacy_score(score: float, susceptibility: float) -> "StanceState":
        """从旧的 1-10 分数转换"""
        I = score
        P = +1 if score > 5 else -1
        C = P * (score / 10) * (1 - susceptibility)  # 近似
        S = 1 - susceptibility
        return StanceState(I=I, P=P, C=C, S=S)

    def to_legacy_score(self) -> float:
        """转回 1-10 分数（用于显示）"""
        return self.I
```

**GraphNode 修改**：

```python
class GraphNode(BaseModel):
    # ... 现有字段 ...

    # 改动：将 stance_score: float 改为 stance_state: StanceState
    stance_state: StanceState

    # 保留便捷访问
    @property
    def stance_score(self) -> float:
        return self.stance_state.I

    @property
    def susceptibility(self) -> float:
        return 1 - self.stance_state.S
```

### 7.2 phase2_topology_builder.py 改动

**apply_individual_jitter 函数修改**：

```python
def apply_individual_jitter(agents: List[GraphNode]) -> List[GraphNode]:
    """为 Agent 添加个体差异化随机扰动"""
    jittered_agents = []
    for agent in agents:
        if agent.role == NodeRole.CORE:
            jitter_range = 0.05
        else:
            jitter_range = 0.15

        # 对 I 添加扰动
        jitter_I = agent.stance_state.I * random.uniform(-jitter_range, jitter_range)
        new_I = round(max(1.0, min(10.0, agent.stance_state.I + jitter_I)), 2)

        # 更新 C
        new_C = agent.stance_state.P * new_I / agent.stance_state.S

        new_state = StanceState(
            I=new_I,
            P=agent.stance_state.P,
            C=round(new_C, 2),
            S=agent.stance_state.S
        )

        jittered_agents.append(GraphNode(
            ...,
            stance_state=new_state
        ))

    return jittered_agents
```

### 7.3 phase3_tick_simulation.py 改动

**SimulationEngine 修改**：

```python
class SimulationEngine:
    def __init__(self, ...):
        # ... 现有代码 ...

        # 改动：agent_stances 从 Dict[int, float] 改为 Dict[int, StanceState]
        self.agent_stances: Dict[int, StanceState] = {}
        for node in phase2_output.nodes:
            legacy_score = node.stance_score
            susceptibility = node.susceptibility
            self.agent_stances[node.id] = StanceState.from_legacy_score(
                legacy_score, susceptibility
            )
```

**generate_opinion_spreader_post 修改**：

```python
def generate_opinion_spreader_post(self, agent: GraphNode) -> Tuple[str, StanceState, str]:
    """
    返回: (comment, new_stance_state, reasoning)
    """

    # 1. 获取上下文发言
    context_posts = self.get_agent_context(agent.id, self.current_tick)

    # 2. 对每条发言，计算对 A 的影响
    for post in context_posts:
        B_state = self.agent_stances[post.agent_id]

        # 计算变化
        new_state = compute_stance_change(
            A_stance=self.agent_stances[agent.id],
            B_stance=B_state,
            confirmation_bias_level=agent.confirmation_bias_level,
            susceptibility=agent.susceptibility
        )

        # 累积影响（取最大变化方向）
        self.agent_stances[agent.id] = new_state

    # 3. 生成发言（基于最终 stance）
    comment = self.llm_spreader.generate_comment(
        agent=agent,
        stance_state=self.agent_stances[agent.id],
        context_posts=context_posts
    )

    return comment, self.agent_stances[agent.id], reasoning
```

**apply_stance_constraint 替换为 compute_stance_change**：

原 `apply_stance_constraint` 函数整个替换为新实现。

### 7.4 phase4_report_agent.py 改动

**数据来源修正**：

```python
def build_full_report_context(tick_logs: List[TickLog],
                             phase1_output: EntityExtractionOutput) -> dict:
    """构建报告上下文"""

    # 读取最终立场：从 tick_log 最后一步读取，不用 archetype
    final_stances = {}
    for entry in tick_logs[-1].entries:
        final_stances[entry.agent_id] = entry.current_stance  # 已经是 StanceState

    # ... 其余不变 ...
```

---

## 八、新增文件

| 文件路径 | 说明 |
|---------|------|
| `src/stance_computer.py` | stance 计算核心逻辑（f_A、D(A,B)、IPC 模型） |
| `src/agent_memory.py` | Agent 视野管理（扩展上下文获取） |

---

## 九、参数配置

### 9.1 新增 config.py 参数

```python
# =============================================================================
# Phase 3 Stance 计算参数（新增）
# =============================================================================

# f_A 确认偏差系数
F_A_ALPHA_STRONG = 0.02   # strong 确认偏差：同立场接受系数
F_A_BETA_STRONG = 0.02    # strong 确认偏差：反立场拒绝系数
F_A_ALPHA_WEAK = 0.05     # weak 确认偏差
F_A_BETA_WEAK = 0.05
F_A_ALPHA_NONE = 0.10      # 无确认偏差
F_A_BETA_NONE = 0.10

# D(A,B) 信息新颖度权重
D_WEIGHT_POSITION = 0.7    # 立场方向差异权重
D_WEIGHT_CONSISTENCY = 0.3  # 一致性差异权重

# Agent 视野参数
MAX_POSTS_PER_TICK = 5     # 每轮最多看到的发言数（原为3）
INCLUDE_GROUP_POSTS = True  # 是否包含同群体其他 agent 的发言
INCLUDE_EVENT_POSTS = True  # 是否始终包含事件实体发言
```

### 9.2 可调参项清单

| 参数 | 范围 | 说明 | 调参优先级 |
|------|------|------|-----------|
| F_A_ALPHA_STRONG | 0.01-0.10 | 同立场强化系数 | P1 |
| F_A_BETA_STRONG | 0.01-0.10 | 反立场弱化系数 | P1 |
| D_WEIGHT_POSITION | 0.5-1.0 | 立场差异权重 | P2 |
| D_WEIGHT_CONSISTENCY | 0.0-0.5 | 一致性差异权重 | P2 |
| MAX_POSTS_PER_TICK | 3-10 | 每轮视野宽度 | P1 |

---

## 十、测试与验证计划

### 10.1 单元测试

| 测试项 | 验证内容 |
|-------|---------|
| StanceState 转换 | from_legacy_score 和 to_legacy_score 互逆 |
| f_A 计算 | 同立场正向，反立场负向 |
| D(A,B) 计算 | 立场相反时更大，一致时更小 |
| Consistency 约束 | C 和 P 符号冲突时 scale down |

### 10.2 集成测试

| 测试 | 验证内容 |
|------|---------|
| test2（胖貓） | Agent 5 stance 不应 5 轮完全不变 |
| test3（鼠头） | 极化曲线应有合理演化 |

### 10.3 评估指标

| 指标 | 计算方式 | 目标 |
|------|---------|------|
| stance 变化率 | 每轮 stance 变化的 agent 比例 | > 30% agent 有变化 |
| 发言多样性 | 每轮 unique bigram 数量 | 逐轮增长 |
| 极化合理性 | x(t) 序列是否符合舆情演化规律 | 需人工判断 |

---

## 十一、工作量估算

| 任务 | 预计工时 |
|------|---------|
| schemas.py StanceState 数据类 | 0.5 天 |
| stance_computer.py 核心计算 | 1 天 |
| agent_memory.py 视野扩展 | 0.5 天 |
| phase2_topology_builder.py 适配 | 0.5 天 |
| phase3_tick_simulation.py 重构 | 1.5 天 |
| phase4_report_agent.py 数据源修复 | 0.5 天 |
| 单元测试 + 调试 | 1 天 |
| **总计** | **6 天** |

---

## 十二、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 计算复杂度上升 | 运行时间增加 | 先用简化版验证思路 |
| 参数调优困难 | 输出不符合预期 | 预留充足 case study 时间 |
| 与现有 Phase 1/2 接口不兼容 | 需要额外适配 | 保持 legacy score 兼容层 |
| f_A/D(A,B) 公式与 paper 不完全一致 | 学术严谨性问题 | 注释中明确标注差异 |

---

## 十三、后续优化方向

1. **GraphRAG 接入**：为每轮发言建立向量索引，检索"已覆盖角度"
2. **可视化**：生成 stance 演化的时序图
3. **自动化调参**：用贝叶斯优化找最优参数组合
4. **多语言支持**：Embedding 模型适配

---

## 十四、附录

### A. 关键论文公式索引

| 公式 | Paper 中的位置 |
|------|--------------|
| IPC 定义 | Section 2.2 |
| f_A 定义 | Eq. (5) |
| D(A,B) 定义 | Eq. (6) |
| ΔI_A 完整公式 | Eq. (7) |
| Consistency 约束 | Eq. (8) |

### B. 相关文件

| 文件 | 路径 |
|------|------|
| Paper | `paper/SEIR增强模型.pdf` |
| 当前 phase3 | `adarian mvp/src/phase3_tick_simulation.py` |
| 当前 schemas | `adarian mvp/src/schemas.py` |
| 问题诊断报告 | `BaiduSyncdisk/文件快传/docx(cloud)/2026-03-30_问题诊断报告.md` |

---

*文档创建时间：2026-03-30*
