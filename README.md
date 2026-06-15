# Adarian: 多智能体异步舆情预判系统 / Adarian-多智能体舆情推演系统

基于**宏微观结合 (Macro-Micro Linkage)** 的舆情推演系统原型。通过让多个具有独立人格的 LLM 驱动智能体 (Agent) 在微型社交网络中进行多轮交互，观察群体情绪的涌现与演化，最终提取宏观社会情绪指标 $x(t)$。

---

## 项目愿景

验证"微观涌现 → 宏观预测"闭环：
$$\text{种子文本} \xrightarrow{\text{LLM解析}} \text{实体分类} \xrightarrow{\text{多轮交互}} \text{情绪涌现} \xrightarrow{\text{Report Agent}} x(t)$$

该指标将在后续版本中分别喂入 **AD 快模块**（热度峰值预判）和**增强型 SEIR 慢模块**（90天情绪演化推演）。

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：
```bash
LLM_PROVIDER=deepseek
LLM_API_KEY=***
LLM_BASE_URL=https://api.deepseek.com
DEFAULT_MODEL=deepseek-chat
```

### 3. 运行模拟

```bash
# 运行完整流程
py main.py seeds/test1.txt

# 查看输出
cat outputs/final_report.md
```

### 4. 当前可用种子

| 文件 | 事件 |
|------|------|
| `seeds/test1.txt` | 示例事件 |
| `seeds/test2.txt` | 胖猫事件 |
| `seeds/test3.txt` | 某事件 |
| `seeds/test5.txt` | 南通文旅事件 |

---

## 项目结构

```
adarian/
├── README.md                      # 本文件（项目入口）
├── CLAUDE.md                      # Claude Code 开发规范
├── config.py                      # 全局配置
├── main.py                        # 主入口
│
├── docs/
│   ├── dev_spec.md                # 【权威技术文档】架构、参数定义、版本变更
│   ├── dev_workflow.md            # 开发流程指南
│   └── iterations/                # 详细迭代记录
│       ├── CHANGELOG.md          # 版本变更历史
│       ├── TASK_LOG.md           # 开发任务日志
│       └── v1.1.*.md             # 各版本详细文档
│
├── seeds/                         # 种子材料
├── src/                           # 源代码
│   ├── schemas.py                 # Pydantic 数据模型
│   ├── llm_client.py              # LLM 统一调用
│   ├── phase1/                    # 实体提取与群体生成 package
│   │   ├── __init__.py            # Phase 1 package 入口
│   │   ├── extraction.py          # Analyzer/Generator/Validator 主链
│   │   └── prompts.py             # Phase 1 prompt 常量
│   ├── phase2/                    # 社交拓扑构建 package
│   │   ├── __init__.py
│   │   └── topology_builder.py
│   ├── phase3/                    # 多轮模拟推演 package
│   │   ├── __init__.py
│   │   ├── tick_simulation.py
│   │   ├── speaker_selector.py
│   │   ├── context_builder.py
│   │   ├── simulation_card.py
│   │   └── state_updater.py
│   ├── phase4/                    # 报告生成 package
│   │   ├── __init__.py
│   │   └── report_agent.py
│   └── whitebox/                  # 白盒运行产物检查
│
├── outputs/                       # 运行结果
│   ├── entities_and_relations.json
│   ├── agents_profile.json
│   ├── social_graph.json
│   ├── final_report.md
│   └── tick_logs/
│
└── tests/                         # 单元测试
```

---

## 核心概念

### 两种实体类型

| 类型 | 说明 | 发言时机 |
|------|------|---------|
| **事件实体** | 直接参与事件的核心方 | Tick 0 发言 |
| **意见传播实体** | 评论事件的网民群体 | Tick 1+ 发言 |

### 关键参数

| 参数 | 说明 | 取值 |
|------|------|------|
| `stance_score` | 立场分（1=最支持，10=最批评） | 1.0-10.0 |
| `susceptibility` | 易感性（被说服程度） | 0.0-1.0 |
| `confirmation_bias` | 确认偏差（接受倾向） | none/weak/strong |
| `event_temperature` | 事件热度 | 0.0-1.0 |
| `event_intensity` | 事件烈度 | 0.0-1.0 |

**详细定义见 [dev_spec.md](./docs/dev_spec.md) 第3章「核心参数定义手册」**

---

## 当前版本

**v1.2.8** | 详细技术文档：[docs/dev_spec.md](./docs/dev_spec.md)

### 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v1.2.8 | 2026-06-08 | 平行世界调度器、三层 error recovery、OCP 输出路径、v1.3.2 风险类型扩展 |
| v1.3.1.x | 2026-06-07 | 观测层 consolidation、Phase4 dataset-only 重构 |
| v1.2.5.1 | 2026-05-07 | Source Tree Governance closeout |
| v1.1.10 | 2026-03-31 | stance描述修正、LLM角色重命名 |
| v1.1.9 | 2026-03-30 | susceptibility 接入、立场数据修复 |
| v1.1.8 | 2026-03-29 | 报告 Agent 优化（10章节结构） |
| v1.1.7 | 2026-03-29 | 群体分布策略优化 |
| v1.1.0 | 2026-03-25 | MVP 基线版本 |

完整变更记录：[docs/iterations/CHANGELOG.md](./docs/iterations/CHANGELOG.md)

---

## 开发指南

### 工作流程

本项目使用 superpowers 进行流程管理：

```
brainstorming → writing-plans → executing → verification → review
```

### 开发步骤

1. **需求探索**：使用 `superpowers:brainstorming`
2. **生成计划**：使用 `superpowers:writing-plans`
3. **执行实现**：使用 `superpowers:executing-plans`
4. **验证完成**：使用 `superpowers:verification-before-completion`
5. **代码审查**：使用 `superpowers:requesting-code-review`

详细流程：[docs/dev_workflow.md](./docs/dev_workflow.md)

### 开发规范

1. **所有 LLM 调用必须通过 `llm_client.py`**
2. **所有数据结构必须在 `schemas.py` 中定义**
3. **文档驱动开发**：所有修改基于迭代文档
4. **每次运行后同步 outputs 到百度云**

---

## 硬性约束 (Hard Constraints)

| 约束 | 内容 | 理由 |
|------|------|------|
| HC-01 | 禁止使用云端 RAG，本地 ChromaDB | 数据主权安全 |
| HC-02 | Agent 数量由 LLM 动态推断，≤15 | 避免冗余 |
| HC-03 | 输入仅为本地文本文件 | 降低复杂度 |
| HC-04 | LLM 输出必须经过 Pydantic 校验 | 保证可靠性 |
| HC-05 | Phase 1 必须经过 Validator 校验 | 保证质量 |

---

## 后续版本路线图

| 版本 | 目标 | 规模 |
|------|------|------|
| V1.1 (当前) | MVP：验证微观涌现 | 5-15 Agents |
| V1.2 | Zep Docker + Graph RAG | ≤15 Agents |
| V1.3 | CAMEL-AI 底座集成 | ≤15 Agents |
| V2.0 | AD 快模块 | 50-100 Agents |
| V3.0 | SEIR 慢模块 + 前端 | 500+ Agents |

详细路线图：[docs/dev_spec.md](./docs/dev_spec.md) 第8章
