# Adarian: 多智能体异步舆情预判系统

基于**宏微观结合 (Macro-Micro Linkage)** 的舆情推演系统原型。通过让多个具有独立人格的 LLM 驱动智能体 (Agent) 在微型社交网络中进行多轮交互，观察群体情绪的涌现与演化，最终提取宏观社会情绪指标 $x(t)$。

## MVP 核心闭环

```
种子文本 → LLM解析 → 动态Agent生成 → 多轮交互 → 情绪涌现 → Report Agent → x(t)提取
```

## 项目结构

```
adarian/
├── README.md                # 项目说明
├── requirements.txt         # Python依赖
├── config.py                # 全局配置
│
├── seeds/                   # 种子材料目录
│   └── example_event.txt    # 示例事件
│
├── src/                     # 核心源代码
│   ├── __init__.py
│   ├── schemas.py           # Pydantic 数据模型
│   ├── llm_client.py         # LLM 统一调用封装
│   ├── phase1_persona_engine.py    # 动态人群生成器
│   ├── phase2_topology_builder.py   # 社交拓扑构建
│   ├── phase3_tick_simulation.py    # 异步时间步推演
│   └── phase4_report_agent.py       # 宏观洞察生成器
│
└── outputs/                 # 运行结果输出
    ├── agents_profile.json
    ├── social_graph.json
    ├── tick_logs/
    └── final_report.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# LLM Provider: openai, deepseek, zhipu, qwen
LLM_PROVIDER=deepseek
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com
DEFAULT_MODEL=deepseek-chat
```

### 3. 运行 Phase 1 (独立测试)

```bash
# 使用默认种子文件
python src/phase1_persona_engine.py

# 或指定种子文件
python src/phase1_persona_engine.py seeds/your_event.txt
```

## Phase 1 输出示例

```json
{
  "event_summary": "某知名美妆品牌防晒霜重金属超标...",
  "conflict_axes": ["品牌方vs消费者权益", "KOL公信力vs商业利益"],
  "archetypes": [
    {
      "group_name": "品牌死忠粉",
      "description": "长期使用该品牌，情感依赖强...",
      "stance_score": 2.0,
      "susceptibility": 0.3,
      "estimated_percentage": 15,
      "communication_style": "攻击性强，善用反问句"
    }
  ]
}
```

## 开发规范

1. **所有 LLM 调用必须通过 `llm_client.py`**：禁止在业务代码中直接 `import openai`
2. **所有数据结构必须在 `schemas.py` 中定义**：模块间传递数据必须经过 Pydantic 校验
3. **每个模块必须可独立测试**
4. **禁止一次性生成所有模块代码**：必须按顺序逐模块开发

## 硬性约束 (Hard Constraints)

| 约束编号 | 内容 | 理由 |
|---------|------|------|
| HC-01 | 禁止使用云端 RAG，所有记忆存储在本地 ChromaDB | 数据主权安全 |
| HC-02 | 禁止硬编码 Agent 数量，由 LLM 动态推断 (5-15个) | 避免冗余 |
| HC-03 | 禁止依赖网络爬虫，输入仅为本地文本文件 | 降低工程复杂度 |
| HC-04 | LLM 输出必须经过 Pydantic 校验 | 保证数据流可靠性 |

## 版本路线图

| 版本 | 目标 | 规模 |
|------|------|------|
| V1.1 (当前) | 验证微观涌现链路 | 5-15 Agents |
| V2.0 | 引入 AD 快模块 (BiHill 方程) | 50-100 Agents |
| V3.0 | 引入 SEIR 慢模块 + Vue3 前端 | 500+ Agents |
