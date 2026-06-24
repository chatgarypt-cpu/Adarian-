# Adarian Multi-Agent Public Opinion Simulation System

Adarian 是一个面向公共突发事件舆情研判场景的多智能体推演系统，旨在将复杂舆情事件拆解为可结构化建模、可多路径推演、可风险识别的分析链路。

系统围绕“事件—群体—关系—演化—汇总分析”构建端到端推演流程，覆盖事件信息抽取、用户群体画像、关系网络建模、多模型平行世界模拟、风险分层与治理建议生成等环节，用于支持舆情趋势判断、风险预警与决策参考。

相比传统单次生成式分析，Adarian 支持基于不同模型、参数设定或初始状态生成多个平行推演结果，将舆情演化视为一组可能路径，而不是单一结论。系统通过对多条模拟路径进行汇总、对比与归纳，识别高频风险模式、关键分歧节点和潜在治理窗口，为复杂舆情事件提供更具鲁棒性的分析参考。


---
## 核心能力

* **事件结构化建模**：从舆情文本中抽取事件主体、时间线、议题焦点、关键冲突点与传播触发因素。
* **群体画像生成**：基于传播行为与内容特征，构建不同立场、关注点、情绪倾向和行为模式的用户群体。
* **关系网络建模**：描述群体之间的信息流动、影响关系、互动结构与潜在扩散路径。
* **多模型平行世界推演**：基于不同模型、参数设定或初始状态生成多条舆情演化路径，模拟不同条件下事件可能出现的传播结果。
* **汇总分析与路径对比**：对多个平行推演结果进行聚合、对比与归纳，识别高频风险模式、关键分歧节点与趋势共性。
* **风险分层分析**：识别舆情风险等级、关键触发因素、扩散节点与潜在治理窗口。
* **报告生成与决策支持**：输出结构化分析报告，为趋势研判、风险预警和治理策略提供参考。

## 核心流程

```
种子文本/事件描述
    ↓ Phase 1 — 实体提取与群体生成
事件实体 + 意见传播群体（含立场/易感性等参数）
    ↓ Phase 2 — 社交拓扑构建
带拓扑结构的微型社交网络
    ↓ Phase 3 — 多轮模拟推演
Tick 0~N 群体互动，情绪涌现
    ↓ 分析层
风险分析 + 拐点检测 + 立场演变 + 风险类型分类
    ↓ Phase 4 — 报告生成
舆情研判报告
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 LLM

复制 `.env.example` 为 `.env`，填入你的 LLM API 信息（支持 DeepSeek、Qwen 等兼容 OpenAI 接口的模型）：

```bash
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.deepseek.com
DEFAULT_MODEL=deepseek-chat
```

### 3. 运行

#### 方式一：双击启动（推荐新手）

在项目目录下双击 **`start.command`**，Terminal 自动打开，Web 控制台在 `http://127.0.0.1:9788` 启动。
浏览器打开即可操作推演。按 Ctrl+C 停止。

#### 方式二：一行命令启动（推荐开发者）

```bash
./adarian.sh up
```

同时启动 Web 控制台（`http://127.0.0.1:9788`）和 CLI 后台。浏览器打开操作，终端继续用 CLI 命令：

```bash
./adarian.sh run seeds/test8.txt     # 单次 pipeline
./adarian.sh serve                   # 仅 Web 控制台
./adarian.sh batch --models ...      # 多模型并行
./adarian.sh inspect <dir>           # 检查产物
```

等价于 `python -m adarian <子命令>`。

### 4. 查看产物

输出目录：`outputs/runs/YYYY-MM-DD/`，每次运行产出：

- `simulation_dataset.json` — 完整推演数据集（规范输出）
- `run.log` — 运行摘要（含 Token 消耗、阶段耗时）
- `whitebox/` — 诊断数据（白盒追踪）

### 当前可用种子

| 文件 | 事件 |
|------|------|
| `seeds/test1.txt` | 示例事件 |
| `seeds/test2.txt` | 网络热点事件 |
| `seeds/test3.txt` | 公共事件 |
| `seeds/test5.txt` | 文旅事件 |

---

## 项目结构

```text
├── start.command        # 双击启动（macOS）
├── adarian.sh           # 命令行启动脚本
├── adarian/             # 产品入口（python -m adarian）
│   ├── __main__.py      # CLI 路由器（run/serve/batch/inspect/dev）
│   ├── run.py           # 单次 pipeline 执行
│   ├── serve.py         # Web 控制台
│   ├── batch.py         # 多模型并行推演
│   ├── inspect.py       # 检查 batch 产物
│   └── config_ui.html   # 前端页面
├── main.py              # 库入口（保留向后兼容）
├── config.py            # 全局配置
├── seeds/               # 种子材料
├── src/
│   ├── schemas/         # Pydantic 数据模型
│   ├── llm_client.py    # LLM 统一调用
│   ├── phase1/          # 实体提取与群体生成
│   ├── phase2/          # 社交拓扑构建
│   ├── phase3/          # 多轮模拟推演
│   ├── phase4/          # 报告生成（纯消费端）
│   ├── analysis/        # 分析层（风险/拐点/立场/分类）
│   ├── parser/          # 数据集编排聚合
│   ├── display/         # CLI 可视化
│   └── whitebox/        # 诊断追踪
├── spec/                # 规格文档（风险映射表等）
├── tools/               # 工具脚本
├── tests/               # 单元测试
└── docs/                # 开发文档
```

---

## 最新特性

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v1.4.1 | 2026-06 | 入口收敛（adarian/ 包 + adarian.sh 统一启动）、seed_text 入 dataset |
| v1.4.0 | 2026-06 | Scheduler MVP Proof、平行世界推演控制台 R0 |
| v1.3.1.x | 2026-06 | 观测层 consolidation、Phase4 dataset-only 重构、平行世界调度器 |
| v1.2.8 | 2026-06 | 三层 error recovery、OCP 输出路径 |
| v1.2.5.1 | 2026-05 | Source Tree Governance closeout |

---

## 核心概念

### 实体类型

| 类型 | 说明 | 发言时机 |
|------|------|---------|
| **事件实体** | 直接参与事件的核心方 | Tick 0 发言 |
| **意见传播实体** | 评论事件的网民群体 | Tick 1+ 发言 |

### 关键参数

| 参数 | 说明 | 范围 |
|------|------|------|
| `stance_score` | 立场分（越批评越接近 10） | 1.0 - 10.0 |
| `susceptibility` | 易感性（被说服程度） | 0.0 - 1.0 |
| `confirmation_bias` | 确认偏差 | none / weak / strong |
| `event_temperature` | 事件热度 | 0.0 - 1.0 |

---

## 许可

内部项目。
