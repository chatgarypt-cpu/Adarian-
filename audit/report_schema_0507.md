# Adarian 舆情报告 Schema（供开发对接用）

版本：基于 report_writing_assistant SKILL.md v2.13.0
日期：2026-05-07

---

## 一、报告输入 Schema

开发侧需提供以下数据供报告生成消费。支持两种方式：**目录路径**（自动读取文件）和**结构化 JSON**（直接传入）。

### 1.1 目录模式所需文件

| 文件名 | 必需 | 说明 |
|--------|------|------|
| `benchmark_summary.json` | 是 | 测试概要信息 |
| `final_report.json` | 是 | 舆情分析结果 |
| `entities_and_relations.json` | 是 | 实体与关系数据 |
| `social_graph.json` | 是 | 社交图谱数据 |
| `tick_logs.json` | 否 | 时间序列日志（有则提供，拐点检测需要） |
| `seed_input.txt` | 否 | 种子文本（原始事件材料） |

### 1.2 结构化 JSON 模式

```json
{
  "input_type": "structured_data",
  "metadata": {
    "event_name": "string — 事件名称",
    "simulation_date": "string — 模拟日期，格式 YYYY-MM-DD",
    "prompt_version": "string — prompt 版本号，如 v1.1.21",
    "llm_api": "string — 使用的 LLM API，如 MiniMax",
    "total_ticks": "integer — 总 tick 轮次数（含 Tick 0）",
    "event_scale": "float — 事件规模，0.0-1.0",
    "event_controversy": "float — 事件争议性，0.0-1.0"
  },
  "event_summary": "string — 事件简要描述，1-3句话概括核心矛盾与社会反应",
  "stakeholders": {
    "event_entities": [
      {
        "name": "string — 实体名称",
        "type": "string — individual | organization | group",
        "role": "string — 在事件中的角色描述",
        "entity_category": "string — 固定值 'event_entity'",
        "can_speak": "boolean — 是否具有发言权限",
        "original_statement": "string | null — 从种子材料提取的原始发言",
        "initial_stance": "float — 初始立场分，1.0-10.0"
      }
    ],
    "opinion_spreaders": [
      {
        "group_name": "string — 群体名称",
        "related_event_entity": "string — 关联的事件实体名称",
        "I": "float — 立场强度，1.0-10.0",
        "P": "integer — 立场方向，+1(支持) 或 -1(反对)",
        "susceptibility": "float — 易感性，0.0-1.0",
        "confirmation_bias_level": "string — none | weak | strong",
        "estimated_percentage": "integer — 预估占总人群百分比，0-100",
        "initial_stance": "float — 初始立场分",
        "final_stance": "float — 最终立场分",
        "persona_name": "string | null — 人设名称",
        "age_range": "string | null — 年龄段",
        "occupation": "string | null — 职业",
        "personality": "string | null — 性格描述",
        "motivation": "string | null — 动机",
        "communication_style": "string | null — 沟通风格",
        "typical_phrases": "string | null — 典型用语"
      }
    ]
  },
  "emotion_trajectory": [
    {
      "tick": "integer — tick 序号",
      "mean_stance": "float — 情绪均值（所有 Agent 立场分算术平均）",
      "std_stance": "float — 标准差（立场分歧程度）",
      "polarization_index": "float — 极化指数（std / mean）",
      "key_event": "string — 该 tick 的关键事件描述"
    }
  ],
  "inflection_points": [
    {
      "tick": "integer — 拐点所在 tick",
      "agent_id": "integer — 触发拐点的 agent ID",
      "group_name": "string — 触发拐点的群体名称",
      "pivotal_comment": "string — 触发拐点的代表性发言",
      "impact_description": "string — 拐点影响描述"
    }
  ],
  "risk_assessment": {
    "risk_level": "string — low | medium | high | critical",
    "risk_assessment": "string — 整体风险研判文字",
    "risk_points": [
      {
        "name": "string — 风险点名称",
        "level": "string — 风险等级",
        "description": "string — 具体风险点描述"
      }
    ]
  },
  "relations": [
    {
      "source": "string — 源实体名称",
      "target": "string — 目标实体名称",
      "type": "string — 关系类型（合作关系/质疑关系/批评关系/代言关系等）"
    }
  ]
}
```

### 1.3 关键字段语义说明

| 字段 | 取值范围 | 语义 | 业务逻辑 |
|------|---------|------|---------|
| `metadata.event_scale` | 0.0-1.0 | 事件规模 | 决定 Agent 总人数：<0.3→3-5人，0.3-0.7→5-7人，≥0.7→7-10人 |
| `metadata.event_controversy` | 0.0-1.0 | 事件争议性 | 控制 P 分布：<0.3→反对40%/支持60%，0.3-0.7→反对55%/支持45%，>0.7→反对70%/支持30% |
| `event_entities.can_speak` | bool | 发言权限 | false 时该实体在 Tick 0 不生成发言，标记为"被讨论" |
| `opinion_spreaders.I` | 1.0-10.0 | 立场强度 | I≥6 → P=+1(支持)；I≤5 → P=-1(反对) |
| `opinion_spreaders.P` | +1/-1 | 立场方向 | +1=支持，-1=反对。与 I 联动：P=+1 时 stance=I，P=-1 时 stance=11-I |
| `opinion_spreaders.susceptibility` | 0.0-1.0 | 易感性 | 调制立场变化幅度：1.0时变化×1.25，0.5时不变，0.0时×0.75 |
| `opinion_spreaders.confirmation_bias_level` | none/weak/strong | 确认偏差 | 已废除字段，由 I 值推导（保留兼容） |
| `emotion_trajectory[].polarization_index` | 0-∞ | 极化指数 | <0.15低极化，0.15-0.25中等，0.25-0.35偏高，>0.35高危 |
| `risk_assessment.risk_level` | low/medium/high/critical | 风险等级枚举 | 用于风险矩阵呈现 |

---

## 二、报告输出 Schema

### 2.1 报告元信息

| 字段 | 位置 | 格式 |
|------|------|------|
| 主标题 | 第一行，一级 Markdown 标题 | `[事件名称]舆情风险研判` |
| 作者 | 标题下方 | 保留空白，待用户填写 |
| 日期 | 作者下方 | 生成日期 |
| 文件名 | - | `报告_YYYY-MM-DD_HHMM.md` |
| 输出目录 | - | `D:\chou\adarian\reports\output\` |

### 2.2 报告章节结构

```
# [事件名称]舆情风险研判                    ← 一级标题 h1
作者：
日期：

## 一、舆情概要                               ← 二级标题 h2
## 二、演化分析                               ← 二级标题 h2
### （一）实体分析：[核心判断]                   ← 三级标题 h3
#### 1. 事件实体分析：[核心判断]                  ← 四级标题 h4
#### 2. 意见传播实体分析：[核心判断]               ← 四级标题 h4
#### 3. 实体关系网络：[核心判断]                   ← 四级标题 h4
### （二）过程分析：[核心判断]                   ← 三级标题 h3
#### 1. Tick 0情况：[核心判断]                   ← 四级标题 h4
#### 2. 情绪与极化演化情况：[核心判断]              ← 四级标题 h4
#### 3. 立场演化变化：[核心判断]                   ← 四级标题 h4
#### 4. 实体代表性观点对比：[核心判断]              ← 四级标题 h4
#### 5. 关键拐点分析：[核心判断]                   ← 四级标题 h4
#### 6. 演化阶段分析：[核心判断]                   ← 四级标题 h4
## 三、风险研判                               ← 二级标题 h2
## 四、对策建议                               ← 二级标题 h2
## 五、附录                                   ← 二级标题 h2
### （一）项目说明                             ← 三级标题 h3
### （二）数据说明                             ← 三级标题 h3
```

### 2.3 各章节数据依赖

#### 一、舆情概要

**消费字段**：`metadata.event_name`, `metadata.event_scale`, `metadata.event_controversy`, `event_summary`, `metadata.total_ticks`

**产出内容**：以真实事件及舆论反应开篇（含具体日期、核心矛盾、社会争议），随后引入模拟参数。汇报实体数量、总计发言消息数量、事件规模分数、事件争议性分数。

**字数**：A版约250字 / B版约400字

---

#### 二、演化分析 — （一）实体分析

##### 1. 事件实体分析

**消费字段**：`stakeholders.event_entities[]` → `name`, `type`, `role`, `initial_stance`, `can_speak`

**产出表格**：
| 实体 | 类型 | 角色 | 初始立场分 | 发言权限 |
|------|------|------|-----------|---------|

**注**：`can_speak` 映射为"允许/禁止"。

##### 2. 意见传播实体分析

**消费字段**：`stakeholders.opinion_spreaders[]` → `group_name`, `related_event_entity`, `I`, `P`, `susceptibility`, `estimated_percentage`

**产出表格**：
- **表2**：意见传播实体信息（群体、关联实体、I值、P值、易感性）
- **表3**：意见传播实体占比分布（群体、占比）

##### 3. 实体关系网络

**消费字段**：`relations[]` → `source`, `target`, `type`；`social_graph.json` → `nodes`, `edges`

**产出内容**：根据社交网络拓扑绘制实体关系网络图（当前版本为 ASCII 文本绘制，可视化待后期迭代）。

---

#### 二、演化分析 — （二）过程分析

##### 1. Tick 0 情况

**消费字段**：`event_entities[].original_statement`, `event_entities[].initial_stance`, `opinion_spreaders[].initial_stance`

**产出内容**：事件实体在 Tick 0 的原始发言及立场分；意见传播群体 Tick 0 初始立场分分布。

**产出表格**：
- **表4**：意见传播群体 Tick 0 初始立场分数分布

##### 2. 情绪与极化演化情况

**消费字段**：`emotion_trajectory[]` → `tick`, `mean_stance`, `std_stance`, `polarization_index`, `key_event`

**产出表格**：
- **表5**：情绪演化数据（Tick阶段、情绪均值、标准差、极化指数、关键事件）
- **表6**：极化演化数据（Tick阶段、极化指数、变化量、极化程度）

**极化程度参考标准**：<0.15 低极化，0.15-0.25 中等极化，0.25-0.35 偏高极化，>0.35 高危极化。

##### 3. 立场演化变化

**消费字段**：每个群体在每个 tick 的立场分（需从 `tick_logs.json` 提取）

**产出表格**：
- **表7**：意见传播群体立场变化（各 Tick 立场分 + 总变化值 + 趋势）
- **表8**：群体立场变化矩阵（Tick 0-5）

**趋势符号**：↑ 上升，↓ 下降，→ 持平。

##### 4. 实体代表性观点对比

**消费字段**：各实体在 Tick 0 和 Tick 5 的发言内容与立场分

**产出表格**：
- **表9**：实体代表性观点对比（Tick 0 发言摘要、立场分 vs Tick 5 发言摘要、立场分、变化）

##### 5. 关键拐点分析

**拐点识别标准**（报告生成侧独立判断，不依赖 `inflection_points` 字段）：
- 条件 A：某一 Tick 极化指数较前一 Tick 变化绝对值 > 0.05
- 条件 B：任意群体单轮立场偏移绝对值 > 1.5
- 任一满足即判为拐点

**消费字段**：`tick_logs.json`（逐轮极化指数、各群体立场分）

**产出表格（仅当满足标准时生成）**：
- **表10**：拐点信息（序号、时间、实体、占比、极化指数变化值、立场分数变化值）

**注意**：若 `inflection_points` 为空但原始数据满足标准，仍需生成拐点分析。若不满足标准，不生成表10，文字说明无显著拐点，后续表格编号顺延。

##### 6. 演化阶段分析

**消费字段**：综合以上所有过程数据

**产出内容**：阶段划分与特征归纳（各阶段情绪特征、极化水平、关键事件），趋势判断（主要方向、趋势特征、未来预测）。

---

**演化分析字数**：A版约550字 / B版约1800字

#### 三、风险研判

**消费字段**：`risk_assessment.risk_level`, `risk_assessment.risk_assessment`, `risk_assessment.risk_points[]`

**写作角度（六大类）**：
1. 政治安全与意识形态（境外干预、国家形象、政策误读、意识形态渗透）
2. 社会稳定与公共安全（矛盾激化、舆论撕裂、心理危机）
3. 经济安全（制裁传导、市场恐慌、营商环境污名化）
4. 网络与信息安全（AI滥用、数据安全、信息茧房）
5. 制度与治理（信任危机、治理失效）
6. 文化安全（文化渗透、本土文化弱化）

**写作要求**：每条风险——命名精准（先定性再展开）、因果链条完整（触发条件→演化路径→最终危害）、指向具体主体。

**字数**：A版约500字 / B版约1200字

#### 四、对策建议

**写作角度（八大类）**：
1. 舆情监测与预警
2. 舆论引导与叙事权争夺
3. 法律与制度完善
4. 国际合作与话语权建设
5. 教育与素养提升
6. 技术与平台治理
7. 人文关怀与民生纾困
8. 分类施策与精准治理

**写作要求**：每条建议须回答——谁来执行（主体）、通过什么机制或工具（抓手）、解决哪个具体风险（针对性）。须引用演化分析或风险研判中至少一个具体发现作为依据。

**字数**：A版约200字 / B版约600字

#### 五、附录

##### （一）项目说明
固定模板：介绍 Adarian 系统（宏微观结合的舆情推演系统，LLM 驱动智能体在多轮交互中观察群体情绪涌现与演化）。

##### （二）数据说明
**核心参数定义**（9个）：
| 参数 | 范围 | 定义 |
|------|------|------|
| event_scale | 0.0-1.0 | 事件规模，决定 Agent 总人数和 I 分布 |
| event_controversy | 0.0-1.0 | 事件争议性，控制 P 分布 |
| stance_score | 1.0-10.0 | 立场分，1-3=强烈批评，4-6=中立观望，7-10=强烈支持 |
| I（立场强度） | 1.0-10.0 | 立场坚定程度，I≥6→P=+1，I≤5→P=-1 |
| P（立场方向） | +1/-1 | +1=支持，-1=反对 |
| C（一致性） | 系统推导 | C=P×(I/10) |
| susceptibility | 0.0-1.0 | 易感性，调制立场变化幅度 |
| can_speak | bool | 发言权限，false 时不生成发言 |
| polarization_index | 0-∞ | 极化指数，std/mean |

**计算方法**（3个）：
- 情绪均值 Mean(t) = (1/N) × Σ stance_i(t)
- 标准差 Std(t) = sqrt((1/N) × Σ(stance_i(t) - Mean(t))²)
- 极化指数 Polarization(t) = Std(t) / Mean(t)

**判别标准**（2个）：
- 拐点识别：极化指数变化 > 0.05 或 群体立场偏移 > 1.5
- 极化判断：<0.3 温和，0.3-0.5 中等，>0.5 高对立

##### 报告生成信息
生成时间、数据来源、模拟模型、LLM API、运行时长、总字数。

---

### 2.4 版本规格

| 版本 | 总字数 | 舆情概要 | 演化分析 | 风险研判 | 对策建议 |
|------|--------|---------|---------|---------|---------|
| A版（便捷速览） | 1400-1500字 | ~250字 | ~550字 | ~500字 | ~200字 |
| B版（详细阅读） | 3800-4000字 | ~400字 | ~1800字 | ~1200字 | ~600字 |

**注**：附录章节及表格内字数不计入上述字数规定。

---

### 2.5 Markdown 标题层级规范

遵循 GB/T9704-1999 公文格式：

| 层级 | 编号格式 | Markdown 语法 | 适用章节 |
|------|---------|--------------|---------|
| 第一层 | 一、二、三 | `#` (h1) | 报告主标题 |
| 第二层 | 一、二、三 | `##` (h2) | 章标题 |
| 第三层 | （一）（二）（三） | `###` (h3) | 节标题 |
| 第四层 | 1. 2. 3. | `####` (h4) | 小节标题 |
| 第五层 | （1）（2）（3） | `#####` (h5) | 细项（极少使用） |

**禁止使用纯加粗文本代替 Markdown 标题语法，禁止使用 emoji。**

---

### 2.6 表格规范

- 表名位于表格上方，格式为"表X 标题"
- 图表名位于图片下方，"图X 标题"
- 统一编号，按出现顺序连续
- 表格中趋势符号（↑↓→）和正负号（+/-）需在表下方附图例说明
- 采用等宽字体保持框线对齐

---

## 三、开发侧对接要点

### 3.1 必须提供的字段（最小可用集）

若资源有限，以下字段为报告生成的最小依赖：

```
metadata.event_name           — 主标题直接使用
metadata.event_scale          — 一、三章使用
metadata.event_controversy    — 一、三章使用
event_summary                 — 一章开篇使用
stakeholders.event_entities   — 二（一）使用
stakeholders.opinion_spreaders — 二（一）（二）使用
emotion_trajectory            — 二（二）表5、表6使用
risk_assessment               — 三章使用
tick_logs                     — 二（二）拐点检测、立场演化使用
relations + social_graph      — 二（一）关系网络使用
```

### 3.2 报告侧独立计算的能力

以下分析由报告生成侧独立完成，**不依赖**开发侧预设字段：

- **拐点检测**：报告侧逐轮检查 tick_logs，依据极化指数变化 > 0.05 或立场偏移 > 1.5 标准独立判定，不使用 `inflection_points` 字段（该字段仅作参考）
- **趋势判断**：↑↓→ 标记由报告侧根据立场分变化方向计算
- **极化程度标注**：报告侧根据极化指数自行标注（低/中等/偏高/高危）
- **文字阐述**：所有数值解读、因果分析、建议撰写均由报告侧 LLM 完成

### 3.3 字段废弃说明

以下字段在 v1.1.11 后已废弃，报告侧不使用：

- `confirmation_bias_level` — 已由 I 值推导替代
- `group_distribution_strategy` — 已由 event_controversy 控制替代
- `event_temperature` / `intensity` — 已废除