# Adarian Report Product Contract PRD v0.1

> 文档类型：产品侧需求冻结 / Report Product Contract  
> 适用系统：Adarian 多智能体舆情推演系统  
> 当前基线：v1.2.6 Schema Split Governance & Contract Library Boundary 已收口  
> 建议后续版本：v1.2.7 - Report Product Contract & Markdown Grounding  
> 文档状态：R0 Frozen / Ready for DS Review  
> 生成日期：2026-05-11  

---

## 0. 文档定位

本文档用于冻结 Adarian 舆情推演系统的报告产品侧需求。

本 PRD 不直接规定底层算法实现方式，而是定义报告产品在下一阶段工程落地时必须遵守的产品 contract，包括：

```text
1. 报告阅读主体路由
2. 报告默认结构
3. 报告表达风格
4. 指标呈现边界
5. 风险表达结构
6. 拐点与代表性发言原则
7. 对策建议边界
8. 模拟推演口径
9. 生成时间与元信息
10. Markdown Prefill 接口
11. JSON / whitebox 追溯要求
12. 一周落地边界
```

本 PRD 的核心目标：

```text
把当前 final_report.md 从“技术结果说明 / 测试报告风格”，升级为“面向政府、公安、监管部门等业务场景可读的模拟推演型舆情风险研判报告”。
```

---

## 1. 产品目标

### 1.1 北极星目标

Adarian 报告产品的目标不是展示系统内部跑了什么，而是回答业务部门最关心的问题：

```text
1. 当前事件风险高不高？
2. 风险主要指向谁？
3. 哪些群体、叙事或情绪在推动风险？
4. 舆情是否出现关键变化节点？
5. 承压主体应该优先防范什么？
6. 后续回应应避免什么？
```

### 1.2 产品定位

默认报告类型为：

```text
模拟推演型舆情风险研判报告
```

含义：

```text
模拟推演型：报告结论来自系统推演，不等同于现实舆情监测事实。
舆情风险：报告关注风险识别、扩散方向与防范建议。
研判报告：报告服务业务阅读和决策支持，不是技术测试报告。
```

---

## 2. 当前版本范围

### 2.1 本 PRD 支持的下一阶段落地范围

下一阶段建议落地以下最小产品能力：

```text
1. 默认详尽版研判报告
2. 阅读主体路由
3. 生成时间与元信息展示
4. 模拟推演口径约束
5. 风险等级 + 主要风险类型 + 风险解释
6. 指标后台化，判断前台化
7. Markdown Prefill 接口
8. final_report.json / whitebox 追溯
9. 基于现有五章模板做章内产品化升级
```

### 2.2 当前阶段明确不做

```text
1. 不实现双输出模式
2. 不接入外部检索
3. 不接入政策知识库
4. 不做复杂可视化
5. 不实现完整风险分类器
6. 不实现完整 representative comment selector
7. 不重构完整 inflection detector
8. 不修改 Phase 1-3 主链行为
9. 不让 LLM 承担核心打分职责
10. 不让报告生成器替代行政决策
```

---

## 3. 报告阅读主体路由

### 3.1 核心规则

```text
谁承压，报告就服务谁；
无人明确承压，则默认服务泛政府 / 公安 / 舆情监管场景。
```

### 3.2 承压主体定向报告

若种子材料、模拟过程或未来外部检索材料中，出现对特定政府机构、监管部门、执法部门、公共管理主体的不利指向，则报告应优先面向该主体生成。

示例：

```text
1. 市场监督管理局 / 市监局 / 食药监 → 涉监管主体视角
2. 公安 / 交警 / 派出所 / 执法部门 → 涉执法主体视角
3. 教育局 / 卫健委 / 住建局 / 属地政府 / 街道办 → 涉公共管理主体视角
```

报告应重点分析该主体面临的：

```text
1. 舆情压力
2. 公信力风险
3. 程序风险
4. 回应风险
5. 责任质疑风险
6. 后续防范建议
```

### 3.3 默认泛政府舆情监管报告

若不存在明确承压主体，则报告默认面向：

```text
政府 / 公安 / 舆情监管部门
```

默认关注：

```text
1. 整体传播风险
2. 群体情绪演化
3. 风险扩散方向
4. 处置建议
5. 次生风险
```

### 3.4 推荐 audience_mode 枚举

```text
generic_government
regulator_facing
law_enforcement_facing
public_management_facing
```

### 3.5 最小路由规则

```text
出现“公安 / 交警 / 派出所 / 执法 / 警方”：
  law_enforcement_facing

出现“市场监督管理局 / 市监局 / 监管部门 / 食药监”：
  regulator_facing

出现“教育局 / 卫健委 / 住建局 / 属地政府 / 街道办”：
  public_management_facing

否则：
  generic_government
```

短期可采用 hybrid 方式：

```text
代码侧基于实体、关键词、关系和 seed_input 生成 audience_mode candidate；
LLM 只负责解释，不得自行改写最终 audience_mode。
```

长期目标：

```text
audience_mode 应逐步转为 code-owned / deterministic-owned 字段。
```

---

## 4. 默认报告结构

产品侧已审核通过的默认五章式结构应保持不变：

```text
一、舆情概要
二、演化分析
三、风险研判
四、对策建议
五、附录
```

当前版本不强制新增“核心结论”作为第一章。

### 4.1 后续双模式预留

后续可扩展双输出模式，但当前大版本不实现：

```text
1. 简洁版汇报
   - 面向领导快速阅读
   - 判断前置
   - 少表格，少过程
   - 适合会议汇报、PPT 摘要、上报材料

2. 详尽版研判
   - 面向舆情研判人员、业务人员和复盘场景
   - 保留完整演化分析
   - 保留风险研判、对策建议与附录
   - 适合归档、审查和后续复盘
```

当前工程要求：

```text
不得要求 Codex 在本轮实现 mode 参数、双模板、双 prompt 或双输出文件。
```

---

## 5. 指标呈现原则

### 5.1 核心原则

```text
指标后台化，判断前台化。
```

### 5.2 正文表达要求

Markdown 报告正文不以以下专业指标作为主要展示对象：

```text
event_scale
event_controversy
polarization_index
stance_delta
risk_score
urgency_score
credibility_score
```

这些指标应主要保存在：

```text
1. final_report.json
2. whitebox_summary.json
3. whitebox/report_completeness.json
4. 后续 report audit / metric grounding 产物
```

正文应优先解释指标背后的业务含义。

### 5.3 示例

不推荐：

```text
本轮 event_scale = 0.72，event_controversy = 0.81，polarization_index = 0.48。
```

推荐：

```text
本轮模拟显示，事件具备较强扩散潜力和较高争议性。不同群体之间的态度分化已较为明显，舆论存在继续向责任质疑和程序争议扩散的风险。从后台指标看，相关极化水平已进入高风险区间，应重点关注负面叙事进一步聚合的可能。
```

---

## 6. LLM 评分降权原则

### 6.1 核心规则

LLM 不适合承担高可信数值评分工作。

后续修改 Phase 1 / Phase 3 / Phase 4 prompt 时，应减少让 LLM 直接输出大量分数、等级、阈值判断的设计。

### 6.2 LLM 主要负责

```text
1. 语义理解
2. 文本归纳
3. 风险解释
4. 表达组织
5. 报告润色
```

### 6.3 代码 / whitebox / deterministic logic 主要负责

```text
1. 指标计算
2. 阈值判断
3. 极化识别
4. stance_delta 计算
5. 拐点检测
6. 一致性校验
7. 风险类型候选校验
```

### 6.4 治理要求

```text
1. 不继续扩大 LLM 打分字段。
2. 不让 LLM 同时给 event_scale、event_controversy、risk_score、polarization_score、credibility_score、urgency_score 等大量分数。
3. 如确需保留 LLM 初始判断，只能作为 weak signal，不得作为最终 runtime authority。
```

---

## 7. 拐点定义与呈现原则

### 7.1 核心规则

```text
拐点宁缺毋滥，不强行生成。
```

### 7.2 定义

拐点不是单纯某个 tick 的数值波动，而是以下任一维度发生明显变化的节点：

```text
1. 舆论叙事
2. 风险焦点
3. 群体立场
4. 极化水平
5. 承压主体风险指向
```

### 7.3 报告呈现

若本轮模拟没有出现足够显著的变化，报告应明确写：

```text
本轮模拟未发现显著拐点。
```

不得为了补齐章节而让 LLM 编造拐点，也不得让 LLM 独立重算拐点。

### 7.4 工程边界

```text
1. 拐点由代码侧 / whitebox / deterministic logic 提供。
2. LLM 只负责解释拐点为什么重要。
3. 没有拐点就如实说明没有。
```

---

## 8. 代表性发言选择原则

### 8.1 核心规则

```text
代表性发言服务于风险解释，不服务于文本观赏性。
```

### 8.2 优先选择

```text
1. 触发或接近触发拐点的发言
2. 推动负面叙事聚合的发言
3. 体现承压主体风险的发言
4. 体现关键群体立场变化的发言
5. 代表主流疑虑，而不是最极端情绪的发言
```

### 8.3 明确禁止

```text
1. 为了报告好看选择最夸张的发言
2. 选择与风险判断无关的金句
3. 把单个极端发言包装成主流观点
4. 让 LLM 自行虚构代表性发言
5. 夸大模拟发言的现实代表性
```

### 8.4 推荐表达

代表性发言后应补充风险解释：

```text
该发言反映出部分群体已将关注点从事件事实转向监管责任和处置透明度，对承压主体形成进一步公信力压力。
```

---

## 9. 对策建议边界

### 9.1 核心规则

```text
系统输出的是舆情风险防范建议，不是法律意见、行政处罚建议或正式决策指令。
```

### 9.2 允许建议

```text
1. 补齐事实链
2. 统一回应口径
3. 明确调查节点
4. 公开程序依据
5. 回应高敏群体关切
6. 避免刺激性、辩解性、甩锅式表达
7. 对承压主体开展信任修复
8. 关注负面叙事聚合趋势
9. 提前准备次生传播应对
```

### 9.3 禁止建议

```text
1. 建议立即处罚某具体人员
2. 建议认定某机构违法
3. 建议启动具体法律程序
4. 直接替政府部门作行政决策
5. 输出未经依据支持的责任定性
6. 将模拟推演结果包装为调查结论
```

---

## 10. 占位能力边界

### 10.1 核心规则

```text
允许占位，但必须显式占位；不得伪装成已完成能力。
```

### 10.2 允许占位

```text
1. 关系网络图：可先用文字、ASCII、简表表达。
2. 代表性发言选择：可先使用 code-owned 候选，不做完整 selector。
3. 拐点检测：没有显著拐点时如实说明。
4. 对策建议：可先采用规则化舆情回应建议。
5. 外部检索：当前不接入，只保留未来扩展位。
6. 可视化：当前不做复杂图表。
7. 政策知识库：当前不接入，只保留后续能力接口。
```

### 10.3 禁止伪装

```text
1. 没有外部检索，不得写“综合全网信息显示”。
2. 没有政策知识库，不得写“依据相关法规建议”。
3. 没有完整 selector，不得声称“系统已识别最具代表性观点”。
4. 没有真实可视化，不得暗示已生成正式关系图谱。
5. 只有模拟结果时，不得包装成真实舆情监测结论。
```

---

## 11. 模拟推演口径

### 11.1 核心规则

```text
报告默认采用“模拟推演口径”，不得把模拟结果写成现实舆情事实。
```

### 11.2 允许表达

```text
1. 本轮模拟显示……
2. 推演结果提示……
3. 若类似叙事继续扩散，可能……
4. 模拟中部分群体表现出……
5. 从模拟结果看……
```

### 11.3 禁止表达

```text
1. 全网舆情已经……
2. 公众普遍认为……
3. 现实中已经形成……
4. 该事件必然导致……
5. 网民已经一致认为……
```

### 11.4 示例

推荐：

```text
本轮模拟显示，若事件回应不及时，舆论可能由事实争议进一步转向对处置程序和责任主体的质疑。
```

不推荐：

```text
当前全网舆论已经由事实争议转向程序争议。
```

除非未来接入真实监测数据、外部检索或平台数据，否则 Markdown 报告必须保持“推演口径”。

---

## 12. 报告生成时间与元信息

### 12.1 生成时间

报告必须展示模拟生成时间，精确到现实时间的年月日、时、分。

要求：

```text
1. generated_at 由代码侧生成。
2. LLM 不自行填写当前时间。
3. 时间字段进入 report context。
4. Markdown 顶部必须展示。
5. final_report.json 中必须保留。
6. whitebox 可检查 Markdown 时间与 JSON 时间是否一致。
```

### 12.2 推荐字段

```json
{
  "report_meta": {
    "generated_at": "2026-05-11 15:42",
    "timezone": "Asia/Tokyo",
    "simulation_run_id": "test1_20260511_154200"
  }
}
```

### 12.3 报告顶部最小元信息

报告顶部至少包含：

```text
1. 报告标题
2. 作者
3. 生成时间
4. 事件名称
5. 模拟轮次
6. 报告类型
```

推荐格式：

```text
# [事件名称]舆情风险研判报告

作者：
生成时间：2026年5月11日15时42分
报告类型：模拟推演型舆情风险研判报告
模拟轮次：6轮
```

---

## 13. Markdown Prefill 接口

### 13.1 核心规则

说明性板块采用外部 Markdown 文件注入机制。

当前大版本只留接口，不写死 prefill 内容，不使用假数据。

### 13.2 适用内容

```text
1. 项目介绍
2. 模拟口径说明
3. 数据来源说明
4. 指标解释
5. 计算口径
6. 公式说明
7. 模型限制
```

### 13.3 推荐文件结构

当前先保留一个总入口：

```text
docs/report_prefill/
  report_appendix_static.md
```

后续如内容变多，再拆分：

```text
docs/report_prefill/
  project_intro.md
  simulation_scope.md
  data_source_note.md
  metric_explanation.md
  formula_note.md
  model_limitations.md
```

### 13.4 运行时接口设计

Phase 4 报告生成时：

```text
读取指定 Markdown 文件
↓
作为 stable_prefill_blocks 传入 report context
↓
报告附录按原文或轻量排版插入
```

建议字段：

```json
{
  "prefill_blocks": {
    "enabled": true,
    "source_type": "markdown_file",
    "source_path": "docs/report_prefill/report_appendix_static.md",
    "content": "..."
  }
}
```

### 13.5 边界规则

```text
1. 当前大版本只留接口。
2. 不用假数据填充说明板块。
3. 不把说明性内容硬编码进 prompt。
4. 说明性 Markdown 文件由人维护，后续可版本化。
5. LLM 不得改写公式、指标定义和能力边界。
6. 若 Markdown 文件不存在，报告生成不得失败；可跳过该板块并在 whitebox 中记录 missing_prefill。
```

---

## 14. 表格策略

### 14.1 核心规则

```text
正文少表格，附录 / final_report.json / whitebox 承接完整数据。
```

### 14.2 正文可以保留的小表格

```text
1. 核心风险点列表
2. 关键主体风险摘要
3. 重点群体立场变化摘要
4. 对策建议清单
```

### 14.3 正文不建议大面积展示

```text
1. 每个 tick 的完整数据
2. 全量 agent 发言
3. 全量 stance matrix
4. 大段指标明细
5. 技术调试信息
```

### 14.4 结构化数据承接位置

完整指标表、群体矩阵、tick-by-tick 数据、立场变化明细，应优先进入：

```text
1. 附录
2. final_report.json
3. whitebox_summary.json
4. 后续 report audit 产物
```

---

## 15. 报告类型与标题命名

### 15.1 默认标题

```text
[事件名称]舆情风险研判报告
```

### 15.2 报告类型

```text
模拟推演型舆情风险研判报告
```

### 15.3 命中特定承压主体时的标题

若事件材料中存在明确承压主体，可在标题中加入轻量主体标识：

```text
1. [事件名称]涉监管主体舆情风险研判报告
2. [事件名称]涉执法主体舆情风险研判报告
3. [事件名称]涉公共管理主体舆情风险研判报告
```

### 15.4 禁止标题

标题不得写成：

```text
1. 具体行政指令
2. 法律意见
3. 调查结论
4. 处置决定
5. 新闻标题
6. 营销化标题
7. 情绪化标题
```

### 15.5 文件命名建议

工程侧建议：

```text
report_<event_slug>_<YYYYMMDD_HHMM>.md
report_<event_slug>_<YYYYMMDD_HHMM>.json
```

中文命名可保留：

```text
舆情风险研判报告_<事件简称>_<YYYYMMDD_HHMM>.md
```

但工程侧优先英文 slug，减少路径和编码问题。

---

## 16. 风险表达结构

### 16.1 核心规则

报告风险研判应采用：

```text
风险等级 + 主要风险类型 + 风险解释
```

### 16.2 推荐格式

```text
风险等级：中高风险
主要风险类型：程序争议风险、监管责任质疑风险、回应滞后风险
```

或：

```text
总体风险等级：高风险

主要风险类型：
1. 执法程序公信力风险
2. 负面叙事聚合风险
3. 属地部门回应压力风险
```

随后补充自然语言解释：

```text
本轮模拟显示，事件争议焦点已由个案事实分歧进一步转向处置程序和责任主体质疑。若后续回应节奏滞后，相关讨论可能继续围绕程序透明度、责任追究和公信力问题扩散。
```

### 16.3 风险等级中文枚举

```text
低风险
中低风险
中风险
中高风险
高风险
重大风险
```

### 16.4 JSON 英文枚举建议

```text
low
medium_low
medium
medium_high
high
critical
```

---

## 17. 风险类型白名单

### 17.1 核心规则

```text
风险类型白名单应作为 report schema / report contract 接口维护。
Prompt 只消费，不自由发明风险类型。
```

### 17.2 推荐字段

```json
{
  "risk_assessment": {
    "risk_level": "medium_high",
    "risk_level_label": "中高风险",
    "primary_risk_types": [
      "procedure_dispute_risk",
      "regulatory_accountability_risk",
      "response_delay_risk"
    ],
    "risk_type_labels": [
      "程序争议风险",
      "监管责任质疑风险",
      "回应滞后风险"
    ],
    "risk_explanation": "本轮模拟显示……"
  }
}
```

### 17.3 初始白名单草案

```text
fact_dispute_risk               事实争议风险
procedure_dispute_risk          程序争议风险
regulatory_accountability_risk  监管责任质疑风险
law_enforcement_trust_risk      执法公信力风险
response_delay_risk             回应滞后风险
information_opacity_risk        信息不透明风险
negative_narrative_risk         负面叙事聚合风险
group_polarization_risk         群体对立风险
secondary_spread_risk           次生传播风险
overseas_amplification_risk     境外放大风险
rumor_spread_risk               谣言扩散风险
institution_image_risk          机构形象风险
local_governance_pressure_risk  属地治理压力风险
```

### 17.4 当前阶段边界

```text
1. 本阶段只冻结接口与白名单草案。
2. 不要求立即实现完整风险分类器。
3. 可先由 deterministic rule / report context 生成候选 primary_risk_types。
4. LLM 只负责解释风险类型，不负责自由创造风险类型。
```

---

## 18. JSON / Whitebox 追溯要求

### 18.1 必须进入 JSON / whitebox 的字段

```text
1. generated_at
2. report_type
3. audience_mode
4. risk_level
5. risk_level_label
6. primary_risk_types
7. risk_type_labels
8. prefill_loaded
9. prefill_source_path
10. markdown_generated_at_match_json
11. simulation_disclaimer_present
12. metric_grounding_status
```

### 18.2 可进入 whitebox 的检查项

```text
1. final_report.md 是否包含 generated_at
2. final_report.json 是否包含 generated_at
3. Markdown 与 JSON 时间是否一致
4. 是否出现现实事实化表达
5. 是否大面积裸露技术指标
6. 是否出现未授权风险类型
7. 是否加载 Markdown prefill
8. prefill 缺失时是否降级
9. 是否出现 LLM 自行重算指标倾向
10. 是否触碰双模式输出
```

---

## 19. 当前五章模板的最小改造方式

### 一、舆情概要

允许调整：

```text
1. 展示报告类型
2. 展示生成时间
3. 明确模拟推演口径
4. 用自然语言概括事件风险
```

不建议：

```text
1. 大面积展示 event_scale / event_controversy
2. 开头堆技术字段
3. 写成系统测试摘要
```

### 二、演化分析

允许调整：

```text
1. 保留实体 / 群体 / 拐点 / 代表性发言结构
2. 少表格，多风险解释
3. 用群体变化解释风险形成
4. 不强行制造拐点
```

### 三、风险研判

必须采用：

```text
风险等级 + 主要风险类型 + 风险解释
```

### 四、对策建议

必须聚焦：

```text
舆情防范与回应建议
```

不得升级为：

```text
行政决策 / 法律判断 / 责任定性
```

### 五、附录

可承接：

```text
1. Markdown prefill
2. 模拟口径说明
3. 指标说明
4. 数据来源说明
5. 模型限制说明
```

---

## 20. 一周落地边界

### 20.1 一周内允许落地

```text
1. report metadata 增强
   - generated_at
   - report_type
   - event_name
   - total_ticks
   - audience_mode

2. 阅读主体路由
   - generic_government
   - regulator_facing
   - law_enforcement_facing
   - public_management_facing

3. 风险表达结构
   - risk_level_label
   - primary_risk_types
   - risk_type_labels
   - risk_explanation

4. Markdown 正文表达调整
   - 指标少裸露
   - 多风险解释
   - 保留现有五章结构

5. Prefill Markdown 接口
   - 支持读取一个外部 md
   - 不存在则跳过并记录

6. Whitebox / JSON 追溯
   - 记录指标是否进入后台
   - 记录 generated_at 是否一致
   - 记录 prefill 是否加载
```

### 20.2 一周内禁止落地

```text
1. 不实现双输出模式
2. 不实现外部检索
3. 不实现政策知识库
4. 不实现复杂图表
5. 不改 Phase 1-3 主逻辑
6. 不让 LLM 重新打分
7. 不扩大 schema split 之外的底层治理
8. 不实现完整风险分类器
9. 不实现完整 representative comment selector
10. 不重构完整 inflection detector
```

---

## 21. 验收标准建议

下一版本落地时建议至少检查：

```text
1. final_report.md 顶部包含 generated_at。
2. final_report.json 包含 generated_at，且与 md 一致。
3. final_report.md 明确是模拟推演口径。
4. 报告不出现“全网已经”“公众普遍认为”等现实事实化表达。
5. 风险研判章节包含风险等级。
6. 风险研判章节包含主要风险类型。
7. 专业指标不在正文中大面积裸露。
8. whitebox 或 JSON 保留关键指标追溯。
9. prefill md 存在时可注入，不存在时不失败。
10. 不修改 Phase 1-3 主链行为。
11. 不实现双输出模式。
12. 不接入外部检索 / 政策知识库。
13. 不让 LLM 自由发明风险类型。
14. 不让 LLM 自行重算拐点、立场矩阵、全局指标。
```

---

## 22. 建议后续版本

建议下一版本命名：

```text
v1.2.7 - Report Product Contract & Markdown Grounding
```

### 22.1 建议版本目标

```text
在不改变 Phase 1-3 主链行为的前提下，建立 Phase 4 报告产品 contract：
1. 生成时间与元信息
2. 阅读主体路由
3. 风险等级 + 主要风险类型
4. 模拟推演口径约束
5. Markdown Prefill 接口
6. 指标后台化表达
7. JSON / whitebox 追溯检查
```

### 22.2 建议 attempt 拆分

```text
attempt-01：
Report context / metadata / generated_at / audience_mode / risk fields

attempt-02：
Phase 4 Markdown 表达调整 + risk type labels + prefill md interface + whitebox checks
```

### 22.3 建议验证策略

本版本属于 report product contract 和 Phase 4 Markdown grounding，不建议每个 attempt 都跑完整烟雾测试。

优先：

```text
1. py_compile
2. import check
3. Phase 4 fixture-based report generation
4. targeted tests
5. final closeout 再跑一次 smoke test
```

---

## 23. DS Review Scope 建议

DS Team 审查时应重点检查：

```text
1. PRD 是否与 v1.2.6 Contract Library Boundary 不冲突。
2. 是否越界进入外部检索 / 政策知识库 / 双模式。
3. 是否保留现有五章模板。
4. 是否正确区分模拟推演结果与现实舆情事实。
5. 是否避免 LLM 自由打分和自由发明风险类型。
6. 是否将指标放入 JSON / whitebox 追溯，而不是正文大面积裸露。
7. 是否允许 Markdown Prefill 接口缺失时 graceful degrade。
8. 是否存在行政决策、法律定性越界。
9. 是否能在一周内最小落地。
```

DS 不负责最终 gate。

---

## 24. Closeout Note

本 PRD 作为 Product Report Design R0 的冻结产物。

当前结论：

```text
Product Report Design R0 frozen.
Ready for DS Review.
Ready to become v1.2.7 iteration input after v1.2.6 closeout.
```

