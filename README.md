# Adarian — 多智能体舆情推演系统

基于 **宏微观结合（Macro-Micro Linkage）** 的舆情推演系统。通过让多个具有独立人格的 LLM 驱动智能体在微型社交网络中进行多轮交互，观察群体情绪的涌现与演化，最终识别风险类型并生成舆情研判报告。

---

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

### 3. 运行模拟

```bash
python main.py seeds/test1.txt
```

输出产物（`outputs/runs/YYYY-MM-DD/` 目录下）：
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

```
├── main.py              # 入口
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
| v1.3.2 | 2026-06 | 26 类型 RiskClassifier Agent、6 域风险映射体系 |
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
