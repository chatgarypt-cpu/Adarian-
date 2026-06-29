# Adarian — 平行世界舆情推演系统

[![GitHub](https://img.shields.io/badge/GitHub-chatgarypt--cpu/Adarian--blue?logo=github)](https://github.com/chatgarypt-cpu/Adarian-)

面向公共突发事件舆情研判场景的多智能体推演系统，基于宏微观结合的舆情演化模拟。
通过让多个具有独立人格的 LLM 驱动智能体在微型社交网络中进行多轮交互，观察群体情绪的涌现与演化，
最终识别多个平行世界的风险类型并生成舆情研判报告。

**核心理念**：不是预测单一未来，而是探索一组可能路径。通过多模型平行推演暴露盲区、识别分歧、
发现不同模型感知到的风险维度差异。

---

## 核心能力

- **事件结构化建模** — 从舆情文本中抽取事件主体、时间线、议题焦点、关键冲突点与传播触发因素
- **群体画像生成** — 基于传播行为与内容特征，构建不同立场、关注点、情绪倾向的网民群体
- **关系网络建模** — 描述群体之间的信息流动、影响关系与潜在扩散路径
- **多轮模拟推演** — 微型社交网络中的 Tick 0~N 群体互动，观察情绪涌现与演化
- **多模型平行世界** — 基于不同 LLM 模型生成多条舆情演化路径，对比分歧与共性
- **风险分层分析** — 识别舆情风险等级、关键触发因素、扩散节点与治理窗口
- **报告生成** — 输出结构化舆情研判报告（含附录审计）

---

## 系统架构

```
种子文本 / 事件描述
  │
  ▼ Phase 1 — 实体提取与群体生成
事件实体 + 意见传播群体（含立场 / 易感性 / 确认偏差等参数）
  │
  ▼ Phase 2 — 社交拓扑构建
带信息流拓扑的微型社交网络
  │
  ▼ Phase 3 — 多轮模拟推演
Tick 0~N 群体互动，情绪涌现与立场演变
  │
  ▼ 分析层
风险分析 + 拐点检测 + 立场演变 + 风险类型分类（确定性算法）
  │
  ▼ 数据集编排（parser）
simulation_dataset.json — 自包含的完整推演数据集
  │
  ▼ 报告生成
结构化舆情研判报告（含附录 B 审计产物）
```

---

## 快速开始

### 前置条件

| 工具 | 版本要求 |
|------|---------|
| Python | >= 3.10 |
| Node.js | >= 18（构建前端） |
| npm | >= 9 |

### 第 1 步：克隆并安装 Python 依赖

```bash
git clone git@github.com:chatgarypt-cpu/Adarian-.git
cd Adarian-

# 创建虚拟环境
python3 -m venv .venv

# 安装依赖（两种方式任选其一）
.venv/bin/pip install -r requirements.txt
# 或: .venv/bin/pip install -e .
```

### 第 2 步：配置 LLM API

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

填入你的 LLM API 信息：

```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com     # 你的 LLM endpoint URL
LLM_PROVIDER=deepseek                      # deepseek / openai / qwen 等
DEFAULT_MODEL=deepseek-chat                # 默认模型名
```

> 注意：系统需要连接一个兼容 OpenAI 接口的 LLM 服务来驱动多智能体推演。  
> `model_router.py` 支持按任务类型路由不同模型，并提供内网不通时的自动 fallback。具体配置见 `.env.example`。

### 第 3 步：构建前端

```bash
cd frontend/
npm install
npm run build
cd ..
```

构建产物在 `frontend/dist/`，Flask 后端会自动服务。

### 第 4 步：运行

#### Web 控制台（推荐）

**macOS** — 双击 `start.command`，或命令行：

```bash
./adarian.sh serve
# 浏览器打开 http://127.0.0.1:9788
```

后台模式：

```bash
./adarian.sh up
# Web UI 在 9788，CLI 可用其他命令
```

#### 单次 Pipeline 执行

```bash
./adarian.sh run [种子文件路径]
# 默认种子: seeds/test8.txt
```

#### 多模型平行推演

```bash
./adarian.sh batch --models qwen36-35b,ds,minimax --tag my-batch
```

#### 检查已有批次产物

```bash
./adarian.sh inspect <batch-dir-path>
```

等价于 `python -m adarian <子命令>`（需在 src/ 上级目录执行）。

### 查看产物

输出目录：`outputs/runs/YYYY-MM-DD/`，每次运行产出：

| 文件 | 说明 |
|------|------|
| `simulation_dataset.json` | 完整推演数据集（规范输出，下游消费契约） |
| `run.log` | 运行摘要（含 Token 消耗、阶段耗时、错误回放） |
| `whitebox/` | 诊断数据（白盒追踪，可选） |

---

## 可用种子文件

| 文件 | 事件 |
|------|------|
| `seeds/test1.txt` | 基础示例事件 |
| `seeds/test2.txt` | 网络热点事件 |
| `seeds/test3.txt` | 公共事件 |
| `seeds/test4.txt` | — |
| `seeds/test5.txt` | 文旅事件 |
| `seeds/test6.txt` | — |
| `seeds/test7.txt` | — |
| `seeds/test7_1.txt` | — |
| `seeds/test8.txt` | 默认种子（最常用） |
| `seeds/example_event.txt` | 示例格式参考 |

---

## 项目结构

```
Adarian-/
├── start.command          # macOS 双击启动
├── adarian.sh             # CLI 统一入口
├── pyproject.toml         # Python 包配置 pip install -e .
├── .env.example           # LLM API 配置模板
│
├── src/
│   └── adarian/           # 产品入口包（python -m adarian）
│       ├── __main__.py    # CLI 路由器（run/serve/batch/inspect/dev）
│       ├── run.py         # 单次 pipeline 执行
│       ├── serve/         # Web 控制台 Flask 后端
│       │   ├── api/       # REST API 路由（14 个 endpoint）
│       │   ├── db.py      # SQLite 状态持久化
│       │   ├── static.py  # SPA 前端静态文件服务
│       │   └── paths.py   # 路径配置
│       ├── batch.py       # 多模型并行推演
│       ├── inspect.py     # 检查 batch 产物
│       ├── report/        # 报告生成模块（v1.5.2 重构）
│       │   ├── runner.py  # 报告任务调度
│       │   ├── writer.py  # LLM 自然语言写作
│       │   ├── appendix_builder.py  # 结构化审计数据
│       │   ├── quality.py # 质量检查与审计
│       │   └── config.py  # 报告配置
│       ├── config.py      # 全局配置
│       ├── model_router.py# 模型路由表
│       ├── output_paths.py# OCP 输出路径策略
│       ├── llm_client.py  # LLM 统一调用
│       ├── parser.py      # 数据集编排聚合
│       ├── phase1/        # 实体提取与群体生成
│       ├── phase2/        # 社交拓扑构建
│       ├── phase3/        # 多轮模拟推演
│       ├── analysis/      # 分析层（风险/拐点/立场/分类）
│       ├── display/       # CLI 可视化
│       ├── schemas/       # Pydantic 数据模型
│       ├── whitebox/      # 诊断追踪
│       └── utils/         # 工具类
│
├── frontend/              # Vue 3 + Vite 前端 SPA
│   ├── src/               # 页面组件（vue-router 路由）
│   ├── dist/              # 构建产物
│   └── package.json
│
├── seeds/                 # 种子材料
├── spec/                  # 规格文档（风险映射表等）
├── tools/                 # 工具脚本
└── tests/                 # 单元测试
```

---

## CLI 命令参考

所有命令通过 `./adarian.sh` 或 `python -m adarian` 调用。

| 命令 | 说明 | 示例 |
|------|------|------|
| `serve` | 启动 Web 控制台 | `./adarian.sh serve` |
| `up` | Web 后台 + 返回 CLI | `./adarian.sh up` |
| `run [seed]` | 单次 pipeline | `./adarian.sh run seeds/test8.txt` |
| `batch --models X` | 多模型平行推演 | `./adarian.sh batch --models qwen36-35b,ds` |
| `inspect <dir>` | 检查 batch 产物 | `./adarian.sh inspect outputs/runs/...` |
| `dev [seed]` | Web + pipeline 一键启动 | `./adarian.sh dev seeds/test8.txt` |

---

## 关键参数

| 参数 | 说明 | 范围 |
|------|------|------|
| `stance_score` | 立场分（越批评越接近 10） | 1.0 - 10.0 |
| `susceptibility` | 易感性（被说服程度） | 0.0 - 1.0 |
| `confirmation_bias` | 确认偏差 | none / weak / strong |
| `event_temperature` | 事件热度 | 0.0 - 1.0 |
| `polarization_index` | 极化指数（std/mean） | >0.5 高度极化 |
| `risk_level` | 风险等级 | none / low / medium / high / critical |

---

## 模型路由

系统通过 `model_router.py` 按任务类型路由到不同模型。`ROUTES` 字典定义了任务到模型 ID 的映射：

| 任务 | 说明 |
|------|------|
| Phase 1~3、报告生成 | 高性能文本生成模型 |
| 格式化检查 / 快速测试 | 轻量模型 |
| Fallback | 外网 API 兜底 |

路由表在 `src/adarian/model_router.py` 中配置，`.env` 中的 `LLM_BASE_URL` 为统一 endpoint。

---

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v1.5.2.2 | 2026-06 | Legacy Phase 4 退役；Legacy Pipeline 清理 |
| v1.5.2.1 | 2026-06 | 报告阅读器前端 + skill 发现 API + 前端杂项修复 |
| v1.5.2 | 2026-06 | 实时日志 SSE 流 + 04-run 实时滚动 |
| v1.5.1 | 2026-06 | 后端 API 补全（Review/Report/World Detail/Observability） |
| v1.5.0 | 2026-06 | 入口收敛 + E2E 验收 + Vue 前端 SPA |
| v1.4.1 | 2026-06 | 入口收敛（adarian/ 包 + adarian.sh） |
| v1.4.0 | 2026-06 | Scheduler MVP、平行世界推演控制台 |
| v1.3.x | 2026-06 | 观测层 consolidation、三层 error recovery、OCP 输出路径 |
| v1.2.x | 2026-05 | Source Tree Governance、并行架构、profiling |

---

## 依赖清单

### Python 运行时

| 包 | 用途 |
|----|------|
| flask | Web 控制台后端 |
| flask-cors | 跨域支持 |
| httpx | LLM API HTTP 调用 |
| pydantic | 数据模型校验 |
| rich | CLI 可视化（StatusBar、Panel） |
| python-dotenv | .env 配置加载 |
| pyyaml | YAML 规格文档读写 |

### 前端构建

| 包 | 用途 |
|----|------|
| Vue 3 + Vite | SPA 框架 |
| vue-router | 前端路由 |
| Pinia | 状态管理 |
| TypeScript | 类型安全 |

---

## 部署

### 一键部署（Linux / macOS）

```bash
# 1. 准备环境
git clone git@github.com:chatgarypt-cpu/Adarian-.git
cd Adarian-
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. 构建前端
cd frontend/
npm install && npm run build
cd ..

# 3. 配置 .env
cp .env.example .env
# 编辑 .env 填入 API Key

# 4. 启动
./adarian.sh serve --host 0.0.0.0
# 访问 http://<your-ip>:9788
```

### Docker（TODO）

Docker 化部署正在规划中，欢迎贡献。

---

## ❌ 常见问题

**Q: 启动后页面空白？**
- 确保前端已构建：`cd frontend/ && npm install && npm run build`
- 检查 Flask 日志，确认 9788 端口正常

**Q: LLM 调用失败？**
- 检查 `.env` 中 `LLM_BASE_URL` 和 `LLM_API_KEY` 是否正确
- 确认网络可访问 LLM endpoint（内网需加 `noproxy`）
- 检查 `model_router.py` 中的模型名是否匹配 endpoint 支持的范围

**Q: 数据库显示 batch 一直 running？**
- 服务重启会自动恢复：检查每个 world 的 run.log，有 `RUN END` 标记的将被标记为 completed

---

## 许可

内部项目。详细许可信息请联系项目维护者。
