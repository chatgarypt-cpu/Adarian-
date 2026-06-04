# Adarian 真实态势感知型舆情推演系统远期规划 v0.2（校对修复版）

> 文档类型：远期路线规划 / 系统架构设计 / 模块功能说明 / 阶段排期修订  
> 适用项目：Adarian 多智能体舆情推演系统  
> 基于文档：`adarian_long_term_architecture_plan_v0.1.md`  
> 关联路线：Phase 4 Report Product Governance Track v0.2.1；Phase 1 Generation Governance Major Track v0.2  
> 当前状态：repaired draft / planning ready  
> 生成日期：2026-05-14  
> Control 判断：不立即进入动态态势感知实现；先修报告可信度债务与 Phase 1 生成稳定性债务。  

---

## 0. 修订摘要

v0.1 的方向是正确的：系统应从 seed-only simulation 升级为 situation-calibrated simulation，即从“LLM 根据种子材料想象舆情世界”升级为“从真实微博数据抽取当前舆论世界参数，再启动多智能体推演”。

但 v0.1 存在一个节奏问题：它把“微博数据库字段摸底”写成了当前唯一下一步。结合当前项目真实状态，这个 next action 需要修正。

当前更稳的推进顺序是：

```text
先补报告可信度；
再补 Phase 1 生成稳定性；
再接真实态势感知；
最后推进平行模拟与滚动态势。
```

因此，本 v0.2 修复版做了 5 项关键调整：

```text
1. 保留 v0.1 的总体架构和核心原则。
2. 将动态态势感知从“当前唯一下一步”降级为“已验证可行、等待契约化”的后续 Track。
3. 前置 v1.2.8.1 拐点识别逻辑修复，优先解决报告可信度债务。
4. 补入 Phase 1 Repair Loop 系列，优先解决 JSON / schema / parser 生成稳定性债务。
5. 新增 Single Run / Batch Synthesis / Final Report 三层产物契约，避免“每轮报告”和“最终报告”权威混乱。
```

一句话：

```text
微博数据证明未来方向可行，但当前不应打断技术债收口。
```

---

## 1. 当前 Gate 判断

### 1.1 当前阶段

```text
阶段：planning / roadmap repair
状态：dynamic situational awareness discovery ready，implementation hold
```

### 1.2 Gate

```text
Dynamic Situational Awareness 主链实现：HOLD
Weibo Data Capability Audit：GO later
Inflection Detection Logic Hardening：GO next
Phase 1 Repair Loop R0：GO after reality check
```

### 1.3 决策理由

当前系统已有微博推文表和微博用户表样本，说明动态态势感知层具备落地基础。但主链仍存在两个更紧迫的技术债：

```text
1. 报告侧拐点识别逻辑需要 code-owned / deterministic / whitebox-verifiable。
2. Phase 1 JSON / schema 输出仍缺少 Parser / Compiler / Validator 后的 Targeted Repair Loop。
```

如果现在直接接动态态势感知，会形成高风险错配：

```text
上游输入更真实；
下游报告判断和 Phase 1 生成链路仍不够稳。
```

因此，动态态势感知进入版本池，但不立即进入 Codex 实现。

---

## 2. 系统总定位

Adarian 远期目标不是简单生成一份舆情报告，而是建立一套可解释、可复盘、可验证的真实态势感知型舆情推演系统。

系统核心转变：

```text
旧模式：
种子材料 → LLM 生成群体 → 多智能体推演 → 最终报告

新模式：
种子材料 + 权威事实补充 + 真实舆情数据
  ↓
输入仲裁
  ↓
真实世界参数抽取
  ↓
初始态建模
  ↓
多轮平行推演
  ↓
中间结构化研判
  ↓
最终业务报告
  ↓
Whitebox / JSON / 验收审计
```

核心产品叙事：

```text
传统舆情系统偏“态”；
Adarian 补“势”。

态 = 当前真实舆情状态。
势 = 基于多智能体推演得到的未来可能趋势。
```

---

## 3. 总体架构图

```mermaid
flowchart TD
    A["Seed Input<br/>种子材料 / 初始事件线索"] --> B["Seed Fact Frame<br/>初始事件框架"]
    C["Authoritative Fact Supplements<br/>权威事实补充材料"] --> D["Authoritative Fact Frame<br/>权威事实框架"]
    E["Internal Weibo Database<br/>中心微博数据库"] --> F["Situational Snapshot<br/>真实态势快照"]

    B --> G["Input Arbitration Layer<br/>输入仲裁层"]
    D --> G
    F --> G

    G --> H["World Parameter Extraction<br/>真实世界参数抽取"]

    H --> H1["Agent Group Profile<br/>群体类型 / 占比 / 关注点"]
    H --> H2["Initial Stance Profile<br/>初始立场 / 情绪 / 易感性"]
    H --> H3["Communication Style Profile<br/>发言风格 / 典型句式"]
    H --> H4["Relation Network Profile<br/>转发 / 评论 / 影响关系"]
    H --> H5["Risk Signal Profile<br/>风险信号 / 燃点 / 争议点"]

    H --> I["Initial State Builder<br/>初始态构建器"]
    I --> J["Agent / Group Parameter Injection<br/>群体参数注入"]
    J --> K["Simulation Layer<br/>多智能体推演层：势"]

    K --> L1["Simulation Run 1<br/>平行世界 1"]
    K --> L2["Simulation Run 2<br/>平行世界 2"]
    K --> L3["Simulation Run 3<br/>平行世界 3"]
    K --> LN["Simulation Run N<br/>平行世界 N"]

    L1 --> M["Single-run Contract<br/>单轮结构化产物"]
    L2 --> M
    L3 --> M
    LN --> M

    M --> N1["Batch Evolution Summary<br/>多轮演化摘要"]
    M --> N2["Batch Risk Synthesis<br/>多轮风险研判"]
    M --> N3["Batch Recommendation Synthesis<br/>多轮建议聚合"]

    N1 --> O["Report Synthesis Context<br/>最终报告上下文"]
    N2 --> O
    N3 --> O
    G --> O

    O --> P["Final Report Agent<br/>最终报告 Agent"]
    P --> Q["Final Public Opinion Risk Report<br/>最终舆情风险研判报告"]

    O --> R["Whitebox / JSON Audit Layer<br/>白盒审计层"]
    Q --> R
```

---

## 4. 输入体系设计

系统远期输入分为三类：

| 输入 | 中文名称 | 主要作用 | 权威边界 |
|---|---|---|---|
| `seed_input` | 种子材料 | 定义初始事件框架与任务边界 | 初始框架，不保证最新 |
| `authoritative_fact_frame` | 权威事实补充 | 修正和补全事实、时间线、主体关系、官方回应 | 事实补充优先源 |
| `situational_snapshot` | 真实态势快照 | 抽取当前舆情状态、群体、情绪、话题、网络和风格 | 当前舆情状态优先源 |

核心原则：

```text
种子材料定题；
权威材料补事实；
微博数据定状态；
输入仲裁分层；
推演系统补势；
中间研判筛风险；
最终报告解释判断。
```

---

## 5. Seed Input：种子材料层

### 5.1 职责

种子材料层负责回答：

```text
这个事件是什么？
本次系统要围绕什么事件进行推演？
初始叙事框架是什么？
涉及哪些核心主体？
核心矛盾是什么？
```

### 5.2 边界

种子材料不是绝对事实权威，而是：

```text
初始事件框架权威源。
```

如果种子材料滞后、信息缺失或存在理解偏差，需要进入输入仲裁层处理。

### 5.3 建议结构

```json
{
  "event_name": "",
  "event_summary": "",
  "core_conflict": "",
  "involved_entities": [],
  "seed_time": "",
  "seed_authority_level": "high / medium / low / unknown",
  "known_limitations": []
}
```

---

## 6. Authoritative Fact Frame：权威事实补充层

### 6.1 设计决策

当前阶段不引入 MCP / 开放联网检索。

事实补充优先使用：

```text
官方通报
权威媒体报道
政府公告
平台声明
企业致歉
行业协会通报
人工指定材料
```

### 6.2 为什么不做 MCP

MCP / Web Search 会引入：

```text
来源可信度问题
检索噪声
网页变动
引用漂移
联网不稳定
prompt 注入
事实冲突
结果不可复现
```

当前更稳的路径是：

```text
权威材料人工指定 / 内部整理
  ↓
结构化事实补充
  ↓
输入仲裁
```

### 6.3 输出产物

建议产物：

```text
authoritative_fact_frame.json
```

结构：

```json
{
  "source_type": "official / authoritative_media / enterprise_statement / association_notice",
  "source_title": "",
  "published_at": "",
  "source_url_or_ref": "",
  "confirmed_facts": [],
  "timeline_updates": [],
  "involved_entities": [],
  "official_responses": [],
  "open_questions": [],
  "conflicts_with_seed": [],
  "do_not_infer": []
}
```

---

## 7. Situational Awareness：真实态势感知层

### 7.1 核心定位

真实态势感知层不是给报告补一章现状分析，而是：

```text
真实世界到模拟世界的参数转译器。
```

它的首要任务是从真实微博数据中抽取可校准模拟世界的参数：

```text
群体
比例
初始立场
情绪
语言风格
关系网络
KOL
传播结构
风险信号
```

### 7.2 当前数据事实

当前已获得：

```text
微博推文.xlsx
微博用户.xlsx
```

这说明动态态势感知层具备 R0 可行性。两张表可支撑：

```text
1. 声量趋势
2. 时间切片
3. 热度排序
4. 用户画像
5. KOL 识别
6. 转发关系弱建模
7. 发言风格抽取
8. 群体类型归纳
9. situational_snapshot.json R0
```

但当前仍不进入主链实现。

### 7.3 R0 不做内容

```text
1. 不直接接数据库主链。
2. 不做实时滚动。
3. 不做完整传播树。
4. 不做跨平台融合。
5. 不做自动事实核验。
6. 不让微博舆论数据直接改写事件事实。
```

---

## 8. Situational Snapshot Contract

### 8.1 目标

`situational_snapshot.json` 是真实态势感知层的核心输出。

它不是最终报告正文，而是用于：

```text
输入仲裁；
初始态建模；
群体生成；
网络结构构建；
推演参数校准；
最终报告第二章现状数据分析。
```

### 8.2 R0 建议结构

```json
{
  "snapshot_meta": {
    "event_name": "",
    "data_source": ["weibo"],
    "time_window": {
      "start": "",
      "end": ""
    },
    "sample_size": 0,
    "generated_at": ""
  },
  "event_relevance": {
    "query_terms": [],
    "filter_strategy": "",
    "relevance_confidence": "high / medium / low"
  },
  "volume_profile": {
    "post_count": 0,
    "comment_count": 0,
    "repost_count": 0,
    "peak_time": "",
    "trend": "rising / stable / declining / unknown"
  },
  "topic_clusters": [],
  "sentiment_profile": {},
  "group_profiles": [],
  "network_profile": {},
  "risk_signal_candidates": [],
  "recommended_simulation_parameters": {}
}
```

### 8.3 R0 必须稳定输出

```text
1. volume_profile
2. topic_clusters
3. sentiment_profile
4. group_profiles
5. weak_network_profile
6. recommended_simulation_parameters
```

---

## 9. Input Arbitration Layer：输入仲裁层

### 9.1 职责

输入仲裁层负责处理：

```text
种子材料滞后；
种子材料缺失；
种子材料与权威材料冲突；
权威事实与舆论说法冲突；
微博数据中的谣言 / 情绪 / 公众归因；
真实态势数据与模拟参数之间的映射边界。
```

### 9.2 核心原则

```text
事实不能由舆论数据直接改写；
但当前态势必须由真实数据校正。
```

### 9.3 输出产物

```text
input_arbitration_report.json
```

结构：

```json
{
  "seed_authority_level": "medium",
  "seed_lag_detected": true,
  "event_frame": {
    "event_name": "",
    "core_conflict": "",
    "involved_entities": []
  },
  "timeline_snapshot": {
    "seed_time": "",
    "latest_data_time": "",
    "current_stage": "",
    "missing_updates": []
  },
  "confirmed_facts": [],
  "situational_claims": [],
  "public_reactions": [],
  "conflicts": [],
  "fallback_fields": [],
  "recommended_simulation_start_state": {}
}
```

---

## 10. Initial State Builder：初始态构建器

### 10.1 职责

初始态构建器负责把输入仲裁后的结果转译为模拟系统可消费的初始状态。

输入：

```text
input_arbitration_report.json
situational_snapshot.json
authoritative_fact_frame.json
seed_input
```

输出：

```text
phase1_input_bundle.json
phase2_graph_seed.json
phase3_simulation_config.json
```

### 10.2 三种模拟起点模式

| 模式 | 条件 | 说明 |
|---|---|---|
| Seed-only Mode | 没有真实态势数据 | 从种子材料定义的初始事件开始推演 |
| Situation-calibrated Mode | 有真实态势快照，但不滚动 | 从当前态势快照开始推演 |
| Rolling Situation Mode | 有多时间窗口数据 | 每个窗口重新校准态势，再做短程推演 |

---

## 11. Parallel Simulation Output Contract：平行模拟产物契约

### 11.1 修订原因

v0.1 只写了“单次推演结构化结果”，但没有明确每轮平行时空模拟与最终报告之间的权威关系。

修订后采用三层契约：

```text
Single Run Contract
Batch Synthesis Contract
Delivery Report Contract
```

核心原则：

```text
每轮都可以有完整产物；
但只有多轮聚合后的 final_report 才是最终交付物。
```

---

### 11.2 Single Run Contract：单轮产物契约

每个平行 run 建议产出：

```text
parallel_runs/run_001/
  run_meta.json
  simulation_config.json
  tick_logs.json
  agent_trajectories.json
  run_summary.json
  evolution_summary.json
  risk_assessment.json
  recommendation_candidates.json
  representative_comment_candidates.json
  run_report.md
  run_quality_check.json
```

其中：

```text
run_report.md 可以保留；
但它不是 final_report.md；
它只代表 single-run evidence，不代表最终交付判断。
```

---

### 11.3 Batch Synthesis Contract：多轮聚合契约

所有 run 完成后，batch 层产出：

```text
intermediate/
  batch_evolution_summary.json
  batch_risk_synthesis.json
  batch_recommendation_synthesis.json
  report_synthesis_context.json
  parallel_run_quality_report.json
```

作用：

```text
1. 聚合多轮稳定趋势。
2. 识别多轮反复出现风险。
3. 区分偶然风险与稳定风险。
4. 将单轮建议候选压缩为最终建议依据。
5. 向最终报告 Agent 提供唯一主上下文。
```

---

### 11.4 Delivery Report Contract：最终交付报告契约

最终报告只在 batch 聚合后生成：

```text
final_report.json
final_report.md
```

最终报告职责：

```text
1. 面向人读。
2. 服务政府 / 公安 / 监管 / 企业决策者。
3. 解释多轮稳定风险。
4. 明确模拟推演口径。
5. 不罗列每个 run 的过程。
6. 不把模拟结果写成现实事实。
```

---

## 12. Final Report Agent：最终报告 Agent

### 12.1 输入

最终报告 Agent 应消费：

```text
1. input_arbitration_report.json
2. situational_snapshot.json
3. batch_evolution_summary.json
4. batch_risk_synthesis.json
5. batch_recommendation_synthesis.json
6. authoritative_fact_frame.json
7. report_synthesis_context.json
```

### 12.2 不应直接消费

```text
未经聚合的所有原始微博；
未经筛选的单轮推演全部发言；
未经中间层处理的裸指标；
未经标注的公众传言；
单轮 run 的偶然风险。
```

### 12.3 职责边界

最终报告 Agent 只负责：

```text
面向人读报告组织表达；
解释风险判断；
区分事实、舆论、推演；
减少裸指标；
保证报告业务可读。
```

不负责：

```text
重新计算风险等级；
重新识别拐点；
重新发明风险标签；
把模拟结果写成现实事实；
把公众说法写成事实定责。
```

---

## 13. 最终报告结构

推荐结构：

```text
一、舆情概要
二、舆情数据分析
三、演化推演分析
四、风险研判
五、对策建议
附录：方法 / 参数 / 数据说明
```

章节职责：

| 章节 | 作用 | 主要输入 |
|---|---|---|
| 舆情概要 | 说明事件背景、事实框架、核心矛盾 | seed_input + authoritative_fact_frame |
| 舆情数据分析 | 描述当前态势，即“态” | situational_snapshot |
| 演化推演分析 | 描述模拟得到的未来可能趋势，即“势” | batch_evolution_summary |
| 风险研判 | 解释稳定风险与现实可能后果 | batch_risk_synthesis |
| 对策建议 | 给出面向决策者的处置建议 | batch_recommendation_synthesis |
| 附录 | 方法说明、数据说明、模拟边界 | whitebox / JSON artifacts |

---

## 14. Whitebox / JSON Audit Layer：白盒审计层

### 14.1 定位

Whitebox 层只做：

```text
观察；
检查；
汇总；
验证；
审计。
```

不做：

```text
生成；
决策；
改变模拟行为；
替代 RuntimeLogger；
成为 runtime authority。
```

### 14.2 远期产物

```text
input_arbitration_report.json
situational_snapshot.json
batch_evolution_summary.json
batch_risk_synthesis.json
batch_recommendation_synthesis.json
report_synthesis_context.json
final_report.json
final_report.md
whitebox_summary.json
report_product_acceptance.json
parallel_run_consistency_check.json
```

### 14.3 验收检查

Whitebox 应检查：

```text
1. 最终报告是否区分事实、舆论、推演。
2. 风险是否来自 batch_risk_synthesis。
3. 报告是否引用不存在的事实。
4. 是否把公众说法写成事实。
5. 是否把单轮过程指标当作最终结论。
6. 是否出现未授权的风险等级重算。
7. 是否缺少生成时间。
8. 是否缺少模拟口径说明。
9. run_report.md 是否被误标为 final_report.md。
10. batch-level synthesis 是否存在质量检查。
```

---

## 15. 修复后的版本路线

### 15.1 总体排序

```text
v1.2.8.1
拐点识别可信度修复

v1.2.8.2
单轮 / 多轮 / 最终报告通用产物契约

v1.2.9.0
Phase 1 P/C/V Reality Check

v1.2.9.1
Phase 1 Targeted Repair Loop R0

v1.2.9.2
Repair Diff Guard & Fallback R0

v1.2.10
微博数据能力审计 + situational_snapshot 契约

v1.2.11
Excel Fixture Situational Snapshot Builder R0

v1.2.12
Parallel Run Batch Synthesis Contract

v1.2.13
Phase 4 Report Architecture Hardening
```

一句话：

```text
先补可信度，再补稳定性，再接真实世界。
```

---

## 16. 各版本规划

## 16.1 v1.2.8.1 — Inflection Detection Logic Hardening

### 定位

```text
报告可信度补丁版本。
```

### 主目标

```text
让拐点识别从“LLM解释 / 报告表达不稳定”收口为 code-owned / deterministic / whitebox-verifiable 的产物。
```

### 范围

```text
1. 拐点计算逻辑。
2. 拐点候选输出。
3. 无显著拐点时的稳定表达。
4. Markdown 与 JSON 一致性。
5. whitebox 拐点检查。
6. fixture-based tests。
```

### 不做

```text
1. 不接微博数据。
2. 不做平行模拟。
3. 不改 Phase 1 Repair Loop。
4. 不重构整个 Phase 4。
5. 不做代表性发言完整 selector。
```

### 验收

```text
1. inflection_points 由代码侧产生。
2. 无显著拐点时 Markdown 稳定表达：本轮模拟未发现显著拐点。
3. final_report.md 与 final_report.json 拐点信息一致。
4. whitebox 能检查拐点一致性。
5. targeted tests 通过。
6. closeout 阶段再跑一次 smoke test。
```

---

## 16.2 v1.2.8.2 — Run / Batch / Final Report Contract Design

### 定位

```text
平行模拟产物契约设计版。
```

### 主目标

```text
冻结三层产物权威关系：
Single Run Contract / Batch Synthesis Contract / Delivery Report Contract。
```

### 产物

```text
docs/contracts/parallel-run-output-contract-v1.2.8.2.md
docs/contracts/batch-synthesis-contract-v1.2.8.2.md
docs/contracts/delivery-report-contract-v1.2.8.2.md
```

### 执行方式

```text
文档优先；
可让产品侧参与结构映射；
可让 DS Team 做审查；
暂不 Codex 改源码。
```

---

## 16.3 v1.2.9.0 — Phase 1 P/C/V Reality Check

### 定位

```text
Phase 1 Repair Loop 前置审计 / reality check。
```

### 主目标

```text
确认当前 Phase 1 JSON parser、validator、schema、错误类型、fallback 的真实状态。
```

### 产物

```text
audit/phase1-generation-governance/v1.2.9.0-pcv-reality-check.md
```

### 重点检查

```text
1. 当前 JSON 解析失败类型矩阵。
2. 当前 parser / validator / repair 缺口。
3. 是否已有 ValidationReport 雏形。
4. Repair Loop R0 最小边界。
5. 是否需要先补 Parser / Compiler / Validator skeleton。
```

### 执行方式

```text
只读审计；
优先 DS Agent Team；
不改源码。
```

---

## 16.4 v1.2.9.1 — Phase 1 Targeted Repair Loop R0

### 定位

```text
生成稳定性债务修复版。
```

### 主目标

```text
让 Phase 1 的 JSON / schema / field-level 可修复错误进入 targeted repair，而不是整段重生成。
```

### R0 范围

```text
1. ValidationReport 最小结构。
2. failed_fields 定位。
3. object_key 定位。
4. repair_prompt_builder。
5. max_repair_attempts。
6. pre_repair_snapshot。
7. repair 后重新 parse / validate。
8. repair 失败 rollback。
```

### 不做

```text
1. 不做多模型路由。
2. 不做复杂 Diff Guard。
3. 不接外部输入。
4. 不做动态感知。
5. 不改 Phase 4 报告结构。
```

---

## 16.5 v1.2.9.2 — Repair Diff Guard & Fallback R0

### 定位

```text
Repair Loop 防漂移保护。
```

### 主目标

```text
repair 后知道改了什么；越界时能拒绝并回滚。
```

### R0 范围

```text
1. old_object vs repaired_object diff。
2. forbidden_changes 检查。
3. scope_creep 检查。
4. fallback_action。
5. explicit fail / pass_with_known_issues。
```

### 验收

```text
1. 每次 repair 有 DiffReport。
2. forbidden_changes 非空时拒绝 repaired_object。
3. forbidden_changes 后有 fallback，不死锁。
4. repair drift 被记录到 run artifact。
5. 下游契约不被破坏。
```

---

## 16.6 v1.2.10 — Weibo Data Capability Audit & Situational Snapshot Contract

### 定位

```text
动态态势感知 R0 前置契约。
```

### 主目标

```text
把 Excel 样本收口为 situational_snapshot.json R0 契约。
```

### 范围

```text
1. 字段能力矩阵。
2. 推文表 / 用户表 join 逻辑说明。
3. volume_profile。
4. topic_clusters。
5. sentiment_profile。
6. group_profiles。
7. network_profile R0。
8. recommended_simulation_parameters。
```

### 不做

```text
1. 不直接接数据库主链。
2. 不做实时滚动。
3. 不做完整传播树。
4. 不改 Phase 1-3。
5. 不让微博数据改写事件事实。
```

---

## 16.7 v1.2.11 — Excel Fixture Situational Snapshot Builder R0

### 定位

```text
Excel 样本到 situational_snapshot.json 的离线 builder。
```

### 主目标

```text
先用本地 Excel / CSV fixture 生成 situational_snapshot.json，不接真实数据库主链。
```

### 范围

```text
1. 读取微博推文样本。
2. 读取微博用户样本。
3. 输出 volume_profile。
4. 输出 user_group_profile。
5. 输出 weak_network_profile。
6. 输出 top_interaction_posts。
7. 输出 recommended_simulation_parameters 初版。
```

---

## 16.8 v1.2.12 — Intermediate Synthesis Contract & Parallel Run Batch Design

### 定位

```text
多轮平行模拟聚合层契约。
```

### 主目标

```text
建立 batch_evolution_summary / batch_risk_synthesis / batch_recommendation_synthesis。
```

### 范围

```text
1. 单轮 risk_assessment 到 batch_risk_synthesis。
2. 单轮 recommendation_candidates 到 batch_recommendation_synthesis。
3. 多轮稳定性字段。
4. run_frequency。
5. stability。
6. report_synthesis_context。
```

---

## 16.9 v1.2.13 — Phase 4 Report Architecture Hardening

### 定位

```text
Phase 4 架构收束。
```

### 主目标

```text
把 report_agent.py 中已经稳定的部分拆出去，形成可维护架构。
```

### 范围

```text
1. report_context_builder。
2. prompt_builder。
3. markdown_writer。
4. json_writer。
5. whitebox_checker。
```

### 禁止

```text
1. 不一次性重写 report_agent.py。
2. 不改 Phase 1-3。
3. 不接外部检索。
4. 不引入政策知识库。
5. 不新增复杂双输出模式。
```

---

## 17. 推荐两周档期

| 天数 | 版本 / 任务 | 交付物 | 执行主体 |
|---|---|---|---|
| Day 1-2 | v1.2.8.1 拐点识别逻辑修复 | 迭代文档、代码修复、targeted tests、whitebox check | Control + Codex + DS Verify |
| Day 3 | v1.2.8.2 产物契约设计 | 三层产物契约、产品端任务卡、DS 审查 Prompt | Control + 产品侧 + DS |
| Day 4 | v1.2.9.0 P/C/V Reality Check | DS Team 只读审计报告 | DS Team |
| Day 5-7 | v1.2.9.1 Targeted Repair Loop R0 | ValidationReport、repair loop、snapshot、rollback | Control + Codex + DS Verify |
| Day 8-9 | v1.2.9.2 Diff Guard & Fallback | DiffReport、forbidden_changes、fallback | Control + Codex + DS Verify |
| Day 10-11 | v1.2.10 微博数据能力契约 | 字段能力矩阵、situational_snapshot R0 contract | Control + 产品侧 + DS |
| Day 12-14 | 缓冲 / closeout / smoke | TASK_LOG、CHANGELOG、smoke、closeout | Control + DS + Codex |

---

## 18. 产品端并行任务

产品端可以并行推进，但不阻塞当前技术债修复。

### 18.1 建议任务

```text
平行模拟单轮产物契约与最终报告映射规则设计
```

### 18.2 任务重点

```text
1. run_report.md 应该包含什么。
2. risk_assessment 与 batch_risk_synthesis 的区别。
3. recommendation_candidates 与最终建议的区别。
4. 哪些内容必须后台化。
5. 哪些内容必须多轮稳定后才能进入 final_report。
6. 最终报告如何表达“多轮推演显示”，而不是“现实已经发生”。
```

### 18.3 产品端不做

```text
1. 不设计 JSON 字段名。
2. 不设计代码模块。
3. 不设计 SQL。
4. 不写工程迭代文档。
5. 不把产品建议自动升级为工程范围。
```

---

## 19. 当前不做清单

当前阶段明确不做：

```text
1. MCP 联网检索 Agent。
2. 实时滚动推演。
3. 大规模并发 agent。
4. 强化学习参数优化。
5. 跨平台态势融合。
6. 完整传播树还原。
7. 自动事实核验。
8. 自动法律定性。
9. 让最终报告 Agent 重算风险。
10. 让微博舆论数据直接改写事件事实。
11. 直接接数据库主链。
12. 每轮平行 run 都输出 final_report.md。
```

---

## 20. Closeout Judgment

v0.2 修复版的最终判断：

```text
Adarian 的远期方向仍然是 situation-calibrated simulation；
但当前阶段不能被动态态势感知的新能力牵引到主线漂移。
```

当前主线应收口为：

```text
先补报告可信度；
再补生成稳定性；
再接真实态势；
最后推进平行模拟与滚动感知。
```

最终产品故事：

```text
我们不是让大模型凭空想象舆情怎么发展；
我们先用真实微博数据库抽取当前舆论世界的参数，
再用多智能体推演探索可能趋势，
最后用中间结构化研判层把多次推演中稳定出现的风险压缩成面向决策者的报告。
```

这就是后续系统建设的主线。
