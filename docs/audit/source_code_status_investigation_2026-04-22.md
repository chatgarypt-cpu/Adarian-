# 源码状态调查报告

**调查时间**: 2026-04-22
**调查目的**: 判断当前源码真实状态及最接近的历史版本
**硬约束**: 禁止修改源码、禁止恢复架构、禁止补丁修复

---

## 1. Current Real Source Structure

### Phase 1 真实存在的源码文件

| 文件 | 路径 | 状态 | 最后修改 |
|------|------|------|----------|
| `phase1_entity_extraction.py` | `src/` | **真实源码** | Apr 22 14:20 |
| `phase1_persona_engine.py` | `src/` | **真实源码** | Apr 20 19:12 |
| `src/phase1/` 目录 | `src/phase1/` | **不存在** | - |
| `src/phase1/__pycache__/` | - | **不存在** | - |

### Phase 3 真实存在的源码文件

| 文件 | 路径 | 状态 | 最后修改 |
|------|------|------|----------|
| `speaker_selector.py` | `src/phase3/` | **真实源码** | Apr 22 14:20 |
| `phase3_tick_simulation.py` | `src/` | **真实源码** | Apr 20 18:39 |
| `context_builder.py` | `src/phase3/` | **不存在** | - |
| `simulation_card.py` | `src/phase3/` | **不存在** | - |
| `state_updater.py` | `src/phase3/` | **不存在** | - |

### 其他关键文件

| 文件 | 状态 |
|------|------|
| `main.py` | **真实源码** (version banner 显示 v1.1.4，严重过时) |
| `src/phase2_topology_builder.py` | 需验证 |
| `src/phase4_report_agent.py` | 需验证 |

---

## 2. Missing-but-Still-Referenced Files

以下文件**被代码引用但不存在**：

| 被引用文件 | 引用位置 | 引用类型 | 后果 |
|-----------|---------|---------|------|
| `src.phase1.orchestrator` | `phase1_entity_extraction.py:559, 591` | 条件导入 | 死代码（条件分支不触发）|
| `src.phase3.context_builder` | `phase3_tick_simulation.py:36` | 顶层导入 | **会直接失败** |
| `src.phase3.simulation_card` | `phase3_tick_simulation.py:37` | 顶层导入 | **会直接失败** |
| `src.phase3.state_updater` | `phase3_tick_simulation.py:39` | 顶层导入 | **会直接失败** |

---

## 3. Ghost Artifacts

| 类型 | 说明 |
|------|------|
| `__pycache__` 残影 | **无** — 目录不存在，无缓存痕迹 |
| 历史注释 | `phase1_entity_extraction.py` 写明"v1.1.14+ 已迁移到 src/phase1/"，但该目录从未创建 |
| 设计目标态 | Phase 3 的 `context_builder/simulation_card/state_updater` 是文档目标态，从未实现 |

---

## 4. Actual Current Execution Path

### Phase 1 当前链路

```
main.py:61 → from src.phase1_entity_extraction import extract_entities_from_file
          → extract_entities_from_file() → extract_entities_with_validation()（本地定义）
```

**关键发现**：
- `main.py` 使用的 `extract_entities_from_file` 是 `phase1_entity_extraction.py` 中直接定义的函数
- `phase1_entity_extraction.py` 第 559、591 行的 `from src.phase1.orchestrator import` 是**死代码**
  - 这些是兼容入口的条件分支，但 `main.py` 走的是另一条路径
- `phase1_entity_extraction.py` 第 21-22 行注释明确说明：

  ```python
  # ⚠️ LEGACY FILE — v1.1.14+ 已迁移到 src/phase1/
  # 本文件保留用于兼容，新代码请使用 src.phase1/ 模块
  ```

### Phase 3 当前状态

- `phase3_tick_simulation.py` 顶层包含 `from src.phase3.context_builder import ...`
- 由于 `context_builder`、`simulation_card`、`state_updater` 均不存在，该文件**无法作为模块导入**
- 如果直接执行 `py src/phase3_tick_simulation.py`，会在导入阶段直接失败

---

## 5. Version Feature Comparison

### 关键源码特征对照

| 特征 | v1.1.12 | v1.1.14 | v1.1.15~18 | v1.1.21 | v1.1.22(文档目标) |
|------|---------|---------|------------|---------|-------------------|
| `src/phase1/` 目录存在 | ✗ | 计划未落地 | ? | ? | 目标态 |
| `src/phase1/orchestrator.py` | ✗ | 计划但不存在 | ? | ? | 目标态 |
| `src/phase3/context_builder.py` | ✗ | ✗ | ? | ? | 目标态 |
| `src/phase3/simulation_card.py` | ✗ | ✗ | ? | ? | 目标态 |
| `src/phase3/state_updater.py` | ✗ | ✗ | ? | ? | 目标态 |
| `phase1_entity_extraction.py` 旧单文件 | ✓ | ✓ | ✓ | ✓ | 残留 |
| `speaker_selector.py` 存在 | ✗ | ✗ | ✓ | ✓ | ✓ |

### CHANGELOG 版本记录

| 版本 | 日期 | 主题 |
|------|------|------|
| v1.1.21 | 2026-04-15 | Workflow Governance Closeout |
| v1.1.20 | 2026-04-13 | Execution Isolation & Hard Kill Timeout |
| v1.1.19 | 2026-04-13 | Model Pool Profiling Pipeline |
| v1.1.18 | 2026-04-09 | Phase 3 Adaptive Scheduler |
| v1.1.17 | 2026-04-09 | Runtime Observability and CLI Logs |
| v1.1.16 | 2026-04-09 | Persona Parallelization |
| v1.1.15 | 2026-04-09 | Rules Engine Refactor |
| v1.1.14 | 2026-04-09 | Phase 1 Architecture Decoupling |

**注意**: v1.1.22 迭代文档不存在。

### Git History 最近 20 条 commit

```
4227175 shitmountain                          ← 最近（仅文档变更）
cd1ef0f align v1.1.21 closeout record with tag
0a846d7 redefine v1.1.21 as workflow governance closeout
461047b record v1.1.21 freeze blocker
163367d close out v1.1.21 workflow governance refactor
d9d9068 docs: add Phase 1 LLM decoupling audit report
25a384e chore: structure cleanup - archive historical files
65f700e docs: update cleanup task to use staging instead of delete
3c4aafd docs: add structure audit report v1
6fbc34e docs: add prompt risk report
78a2d1e docs: update prompt inventory with Phase 3 source map
c6a3d2e docs: add prompt inventory and profiling prep report
cd36ce2 docs: add workflow transformation A+ design
8a994dd stabilize profiling execution isolation
4c52d2a feat(v1.1.19): add profiling pipeline and closeout
25c03b2 fix: validate non-full speaker selection counts
8cfd948 docs(v1.1.9): update CHANGELOG
e204a5a fix(v1.1.9): use tick_log[1] as initial stance for opinion spreaders
ffa8e58 feat(v1.1.9): integrate susceptibility modulation into apply_stance_constraint
```

**关键发现**: commit "shitmountain" (4227175) 仅添加了 5030 行文档（v1.1.12~18.2 历史迭代文档），**无任何源码变更**。

---

## 6. Closest Historical Version

**当前源码最接近: v1.1.14 状态（Phase 1 解耦起点）**

### 判断依据

1. `phase1_entity_extraction.py` 的注释写明"v1.1.14+ 已迁移到 src/phase1/"，但 `src/phase1/` 目录从未创建
2. CHANGELOG 中 v1.1.14 标题是"Phase 1 Architecture Decoupling"，但实际解耦**未落地**
3. Phase 3 的 `speaker_selector.py` 存在（v1.1.18+ 特征），但 `context_builder/simulation_card/state_updater` 三个子模块缺失
4. `main.py` banner 仍显示 v1.1.4，已严重脱离实际版本进度

### 版本状态分类

| 分类 | 说明 |
|------|------|
| 旧版主链 | `phase1_entity_extraction.py` 仍作为主链核心 |
| 新版残影 | `speaker_selector.py` 存在，但其他 Phase3 子模块缺失 |
| 半回退混合态 | **当前实际状态** — 部分架构升级存在，但不完整 |

---

## 7. Is Current Source a Clean Baseline: **NO**

---

## 8. Single Primary Reason

**源码处于"半回退混合态"**：
- Phase 1 停留在 v1.1.14 前（旧单文件，解耦计划搁置）
- Phase 3 部分子模块存在但核心依赖缺失
- 最新 commit "shitmountain" 添加了大量历史文档，但无对应源码变更
- CHANGELOG 记录到 v1.1.21，但实际代码架构远落后于文档描述

---

## 9. Recommended Next Single Action

**执行 git blame 审计**：追踪 `phase1_entity_extraction.py` 和 `phase3_tick_simulation.py` 最近一次"有效修改"（非文档更新）的 commit，确定真正可运行的源码版本基准。

在确认安全基准前，**不适合作为恢复起点**，因为：
1. 导入链存在断点（Phase3 三个子模块缺失）
2. 文档与源码严重脱节
3. 存在未记录的重大变更（"shitmountain" commit）

---

## 附录：版本归属判断树状图

```
v1.1.14: Phase 1 解耦计划启动
  ├─ 计划: 创建 src/phase1/ 目录
  ├─ 计划: 将 phase1_entity_extraction.py 迁移到 src/phase1/
  └─ 实际: src/phase1/ 目录从未创建

v1.1.18: Phase 3 Adaptive Scheduler
  ├─ 计划: 创建 src/phase3/ 子模块
  │   ├─ context_builder.py  ← 缺失
  │   ├─ simulation_card.py  ← 缺失
  │   ├─ state_updater.py   ← 缺失
  │   └─ speaker_selector.py  ← 存在
  └─ 实际: 仅 speaker_selector.py 落地

当前状态
  ├─ Phase 1: 停留在 v1.1.14 前（旧单文件）
  ├─ Phase 3: 部分落地（speaker_selector）+ 部分缺失
  └─ 结论: 半回退混合态，最接近 v1.1.14
```
