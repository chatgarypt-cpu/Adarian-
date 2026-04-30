# Profiling Prep Report

生成时间：2026-04-14
版本：v1.1.20
基于：Prompt Inventory v1

---

## 1. Executive Summary

本次 Prompt Asset Extraction 覆盖了 Adarian MVP 的 4 个 Phase（Phase 1-4）+ Profiling Pipeline，共识别出 **13 个独立 prompt family**。

### 关键发现

1. **Phase 1 复杂度最高**：14 字段的 opinion_spreader schema + 18 条校验规则
2. **Phase 3 有动态 prompt 注入**：confirmation_bias、opinion_pressure 等随状态变化
3. **Phase 4 输出是 freeform markdown**：最难结构化测量
4. **存在 v1.1.14 架构迁移**：legacy P1-G 仍在代码中，但主流程已切换到 P1-F/P1-P/P1-W

---

## 2. Prompt Family Profiles for Profiling

### 2.1 高价值 Profiling 对象（适合 reduced-schema probe）

#### P1-A (Analyzer) ⭐⭐⭐

**推荐理由**：
- 输出 schema 最小（5 字段）
- 核心能力可分离测量（数值估计 vs 文本生成）
- 是 Phase 1 的守门人（如果 event_scale/controversy 错，后面全错）

**Reduced-schema 方案**：
```
L1: "输出 event_scale 和 event_controversy (0.0-1.0)"
→ 测模型对"事件规模/争议性"概念的理解

L2: 保留 event_summary 输出，去掉 event_type 和 reasoning
→ 测模型能否用一句话概括事件

L3: 当前生产版
```

**建议 profiling 顺序**：第一个测 P1-A（输入最简单，信号最干净）

---

#### P1-V (Validator) ⭐⭐⭐

**推荐理由**：
- 输出 schema 极简（pass/message/errors 三字段）
- 18 条规则可分层剥离
- 是系统鲁棒性的关键节点

**Reduced-schema 方案**：
```
L1: 基本 JSON 语法校验（规则 1-3）
L2: 字段存在性 + 类型检查（规则 4-12）
L3: 完整 18 条校验

分层价值：可以定位模型在哪一层开始失效
```

---

#### PR-S (Simple Profiling) ⭐⭐⭐

**推荐理由**：
- 已有现成实现（profiling/prompts.py）
- 2 字段输出，最适合作为 baseline 对照
- 可测量模型的"基础 JSON 跟随能力"

**现状**：已经用于 profiling simple_benchmark.py

---

### 2.2 中等价值 Profiling 对象

#### P1-F (Fact Extractor) ⭐⭐

**推荐理由**：
- 从 P1-G 解耦出来，专门测实体提取
- 相比 P1-G少了 opinion_spreader 生成负担
- Schema：event_entities (7 fields) + relations (3 fields)

**Reduced-schema 方案**：
```
L1: 只提取实体名称和类型
L2: 保留 can_speak 和 original_statement
L3: 当前生产版
```

---

#### P1-P (Group Planner) ⭐⭐

**推荐理由**：
- 从 P1-G 解耦，专门测群体结构生成
- Schema：6 字段 skeleton（不含 persona）
- I 值分布规则是核心业务逻辑

**Reduced-schema 方案**：
```
L1: 只生成群体名称
L2: 保留 I 和 susceptibility
L3: 当前生产版 + raw_weight 归一化约束
```

---

#### P3-C (Context Builder) ⭐⭐

**推荐理由**：
- 相比 P3-A 更轻量（系统 prompt 约 300 字 vs 600+ 字）
- 输入：simulation_card + event_summary + followed + history
- 输出：3 字段 JSON

**Reduced-schema 方案**：
```
L1: "作为[群体名]说一句话评论这个事件"
L2: 保留 persona_name + 简单立场描述
L3: 当前生产版（完整 lightweight context）
```

---

### 2.3 低优先级 Profiling 对象

#### P1-W (Persona Writer) ⭐

**理由**：
- 7 字段 persona schema，复杂度适中
- 但 persona 生成依赖上游 P1-P 的 skeleton
- 独立测量意义有限（除非专门测 persona 多样性）

**建议**：作为 P1-P profiling 的延伸，测 skeleton + persona 联合输出质量

---

#### P3-E (Event Entity Post) ⭐

**理由**：
- 2 字段输出，schema 简单
- 但触发条件依赖 Phase 2 的 can_speak 判断
- 作为 P3-A profiling 的 warm-up 可能更合适

---

### 2.4 高复杂度/低优先级对象

#### P1-G (Legacy Generator) ❌

**理由**：
- v1.1.14 已解耦为 P1-F/P1-P/P1-W
- 主流程不再使用
- 14 字段 schema 复杂度过高
- **建议**：不测 legacy prompt，测新的 decoupled 版本

---

#### P3-A (Agent Post Full) ❌

**理由**：
- 动态 prompt 注入机制复杂（confirmation_bias_prompt 等随状态变化）
- 600+ 字系统 prompt
- **建议**：先用 P3-C 测 context building 能力，P3-A 在集成测试中覆盖

---

#### P4-R (Report Agent) ❌

**理由**：
- 输出是 500-800 行 freeform markdown
- 10 个章节结构
- 难以量化测量（report quality 是主观的）
- **建议**：在 scheduler v0 完成后，用 human evaluation 或 embedding similarity 做粗粒度评估

---

## 3. Recommended Profiling Sequence

### Phase A: 基础 JSON 跟随能力（信号最干净）

```
Step A1: PR-S (Simple Prompt)
  - 目的：建立 baseline，测模型能否输出最简 JSON
  - 输入：固定 2 行
  - 输出：2 字段
  - 预期：所有模型应该接近 100% pass

Step A2: P1-V (Validator)
  - 目的：测模型的格式校验能力
  - 输入：故意构造的 invalid JSON
  - 输出：pass/errors
  - 预期：不同模型在错误检测能力上有差异
```

### Phase B: 核心业务逻辑（Phase 1 为主）

```
Step B1: P1-A (Analyzer)
  - 目的：测模型对"事件规模/争议性"概念的理解
  - 输入：种子文本
  - 输出：event_scale, event_controversy (0.0-1.0)
  - 预期：与人工标注对比，测概念对齐

Step B2: P1-F (Fact Extractor)
  - 目的：测实体提取的准确性
  - 输入：种子文本 + event parameters
  - 输出：event_entities + relations
  - 预期：与 golden set 对比 recall/precision

Step B3: P1-P (Group Planner)
  - 目的：测群体结构生成的质量
  - 输入：fact extraction 结果
  - 输出：opinion_spreader skeletons
  - 预期：I 分布符合业务规则（event_scale → 人数）

Step B4: P1-W (Persona Writer) + P1-P
  - 目的：测 skeleton + persona 联合输出
  - 预期：persona 多样性、 occupation 差异性
```

### Phase C: Phase 3 上下文能力（可选，视资源而定）

```
Step C1: P3-C (Context Builder)
  - 目的：测 lightweight context 对输出的影响
  - 输入：simulation_card + event data
  - 输出：comment (≤50 chars)
  - 预期：不同模型对人设字段的遵循度差异
```

### Phase D: 集成测试（最后阶段）

```
Step D1: P1-F → P1-P → P1-W 端到端
  - 目的：测 pipeline 质量
  - 预期：最终 opinion_spreaders 的 persona 完整度

Step D2: Full Pipeline (Phase 1 → Phase 2 → Phase 3 → Phase 4)
  - 目的：测完整流程的 end-to-end 质量
  - 指标：final_report 可读性、tick 日志完整性
  - 注意：Phase 4 (P4-R) 不做量化测量
```

---

## 4. Report Agent (P4-R) 选型建议

### 核心问题

P4-R 的输出是 **freeform markdown**，难以用传统 pass/fail 指标衡量。

### 建议方案

**Approach 1: Human-in-the-loop Evaluation（推荐用于 Scheduler v0）**

```
不追求自动评分，而是：
1. 固定 3 个 seed，每个模型生成 1 份报告
2. 用 embedding similarity 测"报告结构完整性"
   - 与 template 的 cosine similarity
   - 与 golden report 的 cosine similarity
3. 人工抽检 10% 报告质量
```

**Approach 2: LLM-as-Judge（如果资源允许）**

```
用更强的模型（如 GPT-4）评估：
1. 报告是否包含所有 10 个章节
2. 风险等级判断是否合理
3. 关键洞察是否有实质性内容
```

**Approach 3: Structural Check Only（最小化方案）**

```
只检查：
1. 是否包含所有 10 个 emoji 章节标题
2. 报告长度是否在 300-1000 行
3. 是否包含 x(t) 序列
不评估内容质量
```

---

## 5. 模型池建议

基于 profiling 结果，模型可分为：

| Pool | Criteria | Use Case |
|------|----------|----------|
| **fast** | stability ≥ 0.9, pass_rate ≥ 0.85 | P1-A, P1-V, P3-C (轻量任务) |
| **heavy** | pass_rate ≥ 0.9, 吞吐量可接受 | P1-F, P1-P, P1-W (中等复杂度) |
| **fragile** | pass_rate < 0.85 or timeout_rate > 0.15 | 不进入调度 |
| **fallback** | 最稳定的模型 | 兜底使用 |

---

## 6. 下一步行动

### 立即可做（今天）

1. **运行 simple_benchmark**（PR-S）：建立 baseline
2. **准备 P1-A test cases**：3 个 seed × 期望 event_scale/controversy 标注
3. **确认 profiling pipeline 可用**：`profiling/run_profile.py` 能否正常执行

### 本周内（Codex 可执行）

1. **Step A1-A2**：PR-S + P1-V profiling
2. **Step B1**：P1-A profiling with 3 seeds
3. **生成 profiling prep 报告**：输出 model_profiles.json

### 待确认（需要 Human Decision）

1. **P4-R 评估方案**：Approach 1/2/3 中选择哪个
2. **Golden set 来源**：P1-F/P1-P 是否有人工标注数据
3. **Scheduler v0 字段映射**：是否需要新增字段

---

## 7. 附录：Prompt Complexity Matrix

| Prompt | System Prompt 长度 | User Prompt 长度 | Schema 字段数 | 动态注入 | 总复杂度 |
|--------|------------------|-----------------|--------------|---------|---------|
| PR-S | ~20 字 | ~50 字 | 2 | 无 | ★☆☆ |
| P1-A | ~400 字 | ~20 字 | 5 | 无 | ★★☆ |
| P1-V | ~500 字 | ~50 字 | 3 | 无 | ★★☆ |
| P1-F | ~500 字 | ~150 字 | 10 | 无 | ★★☆ |
| P3-C | ~300 字 | ~200 字 | 3 | 无 | ★★☆ |
| P1-P | ~500 字 | ~200 字 | 6 | 无 | ★★★ |
| P1-W | ~300 字 | ~150 字 | 7 | 无 | ★★☆ |
| P3-E | ~400 字 | ~20 字 | 2 | 无 | ★★☆ |
| P1-G | ~1200 字 | ~150 字 | 24 | 无 | ★★★ |
| P3-A | ~600 字 | ~250 字 | 3 | 3处 | ★★★ |
| P4-R | ~500 字 | ~1000 字 | N/A (markdown) | 无 | ★★★ |

---

## 8. Open Questions

1. **Golden set 来源**：Phase 1 的 golden entity extraction 是否有历史数据可以复用？
2. **I 分布验收标准**：event_scale → 人数 的映射规则是否有 ground truth？
3. **P1-W persona 多样性**：如何量化评估 occupation/personality 的差异性？
4. **Phase 3 tick 数量**：当前 max_ticks=10，是否需要测不同 tick 数的稳定性？
