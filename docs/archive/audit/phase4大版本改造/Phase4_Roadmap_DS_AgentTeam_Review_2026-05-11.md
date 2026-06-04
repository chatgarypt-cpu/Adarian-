# DS Agent Team Review Report: Phase 4 Report Product Governance Track Roadmap v0.1

**Date**: 2026-05-11
**Review Type**: roadmap_review
**Team Mode**: true（4 Agent 并行：Workflow Governance / Phase 4 Architecture / Product Report Contract / Engineering Feasibility）
**Review Target**: `audit/phase4大版本改造/Phase4_Report_Product_Governance_Track_Roadmap_v0.1.md`
**Reference PRD**: `audit/phase4大版本改造/Adarian_Report_Product_Contract_PRD_v0.1.md`

---

## 1. Metadata

```text
review_target: Phase4_Report_Product_Governance_Track_Roadmap_v0.1.md
review_type: roadmap_review
team_mode_used: true
review_date: 2026-05-11
timezone: Asia/Tokyo
ds_verdict: CONDITIONAL_GO
```

---

## 2. Reviewer Agents

```text
1. Workflow Governance Reviewer:
   verdict: CONDITIONAL_GO
   key_findings:
   - 路线图遵循 doc-driven → audit-first → 最小落地原则
   - v1.2.6 closeout 被正确承认
   - PRD 在迭代文档前已冻结
   - 唯二问题：§13.1 Day1→Day2 缺少显式 Doc Patch 缓冲日；attempt_id 命名约定未明确

2. Phase 4 Architecture Reviewer:
   verdict: CONDITIONAL_GO
   key_findings:
   - 路线图正确将最终架构定位于 v1.2.13，但 §15 的目标模块清单有诱导过早拆分的风险
   - v1.2.7 唯一需要的是修改 report_agent.py + 扩展 schemas/phase4.py + 新增测试 + 可选 whitebox check
   - audience_router.py / risk_taxonomy.py / prefill_loader.py / quote_grounding.py / inflection_grounding.py / report_prompt_builder.py / report_markdown_writer.py / report_json_writer.py 均应推迟至后续版本
   - _llm_generated_markdown 全局状态是架构拆分的隐性陷阱

3. Product Report Contract Reviewer:
   verdict: CONDITIONAL_GO
   key_findings:
   - 整体方向与 8 项产品 contract 原则高度一致
   - 发现 4 项违规 + 5 项未明确 + 4 项 PRD-Roadmap 对齐问题
   - 最关键：v1.2.7 使用 primary_risk_types 但白名单在 v1.2.9 才建立
   - report_schema_0507.md 与 PRD/Roadmap 在拐点检测归属上冲突
   - 风险等级枚举（4级 vs 6级）未确定

4. Engineering Feasibility Reviewer:
   verdict: CONDITIONAL_GO
   key_findings:
   - v1.2.7 规模合理：~23 工时，6-7 文件，~400-500 行变更
   - 7 天排期可行，建议 Day3 溢出到 Day4 上午
   - 推荐 2 次 attempt，与路线图一致
   - 最高风险：whitebox REQUIRED_SECTION_GROUPS 与 PRD 五章模板不匹配
   - v1.2.10 偏薄、v1.2.13 偏厚，建议合并调整
```

---

## 3. Overall Verdict

# CONDITIONAL_GO

**路线图方向正确，可以作为 v1.2.7+ 阶段规划输入。但存在 9 项需在写 v1.2.7 迭代文档前修正的具体问题。**

---

## 4. Blockers

**No hard blockers.**

四项 reviewer 均未发现阻止进入 v1.2.7 的硬阻塞。所有问题都是文档/边界/范围层面的可修正问题。

---

## 5. Scope Drift Risks

```text
1. 是否过早进入双输出模式：否。PRD §2.2 和 Roadmap §3 均明确禁止，各版本持续冻结。
2. 是否过早进入外部检索 / 政策知识库：否。明确禁止且推迟到 v1.2.13+。
3. 是否过早实现完整 risk classifier：否。v1.2.9 仅做白名单校验，非完整分类器。
4. 是否过早实现完整 quote selector / inflection detector：否。v1.2.11 仅做追溯治理，非重构。
5. 是否改动 Phase 1-3 主链：否。所有版本均明确禁止。
6. 是否扩大 whitebox 职责：低风险。路线图未将 whitebox 提升为 runtime authority，但为每个检查创建独立 whitebox 模块是过度设计。
7. 是否让 LLM 承担核心评分或重算职责：否。PRD §6 明确降权，各版本持续约束。
```

---

## 6. Version Split Assessment

```text
v1.2.7:
  是否适合作为第一落地版本：是
  是否一周可完成：是（~23工时，7天充裕）
  是否需要拆 attempt：是（recommend 2 attempts，与路线图一致）
  核心风险：v1.2.7 使用 primary_risk_types 但白名单在 v1.2.9 → 需明确过渡策略

v1.2.8:
  版本边界是否合理：是。audience routing 是聚焦的单一功能。

v1.2.9:
  版本边界是否合理：是。白名单建立在 v1.2.7 风险表达字段之上。

v1.2.10:
  版本边界是否合理：偏薄。prefill loader 约100-150行代码。建议与 v1.2.12 合并。

v1.2.11:
  版本边界是否合理：是。引用追溯 + 拐点一致性，范围适中。

v1.2.12:
  版本边界是否合理：若合并 v1.2.10，则范围合理。单独存在偏薄。

v1.2.13:
  版本边界是否合理：偏厚。742行 report_agent.py 拆为5+模块，预估300-500行重构。
  建议将模块拆分逐步前移到早期版本（如 v1.2.7 就提取 report_json_writer）。
```

---

## 7. Recommended Corrections

### Must fix before v1.2.7 iteration doc:

1. **解决 v1.2.7 风险类型过渡问题**：要么将白名单提前至 v1.2.7 scope，要么明确标记 v1.2.7 的 `primary_risk_types` 为 "unvalidated placeholder until v1.2.9"

2. **确定风险等级枚举**：PRD 6 级（低/中低/中/中高/高/重大）vs 当前代码 4 级（LOW/MEDIUM/HIGH/CRITICAL）→ 二选一，写入 v1.2.7 scope

3. **明确 audience_mode 在 v1.2.7 的填充策略**：默认 `generic_government`，或简单关键词匹配（"公安"→law_enforcement_facing），路由逻辑正式实现在 v1.2.8

4. **将 PRD §10.3 的禁止伪装表达纳入 v1.2.7 Markdown grounding**：
   - "综合全网信息显示" → 禁止（无外部检索）
   - "依据相关法规建议" → 禁止（无政策知识库）
   - "系统已识别最具代表性观点" → 禁止（无完整 selector）

5. **将 PRD §19 的对策建议边界纳入 v1.2.7 prompt 约束**：不输出行政决策、法律判断、责任定性

6. **明确五章模板迁移策略**：v1.2.7 是"迁移到 PRD 模板"还是"保持当前代码结构"→ 二选一，且需同步更新 whitebox `REQUIRED_SECTION_GROUPS`

7. **在 §13.1 Day1 和 Day2 之间增加 Doc Patch 缓冲日**：若 DS Pre-Audit 发现问题，需在 Codex 开始前修补迭代文档

8. **解决 report_schema_0507.md 拐点检测归属冲突**：更新为 code-owned 方向，与 PRD §7.4 对齐（拐点由代码侧/deterministic logic 提供，LLM 只负责解释）

9. **白盒检查 section headings 与 PRD 五章模板对齐**：当前 `REQUIRED_SECTION_GROUPS` 使用旧标题（事件概述、舆情态势、风险评估等），需更新为（舆情概要、演化分析、风险研判、对策建议、附录）

### Can defer:

1. v1.2.10/v1.2.12 合并决策（不阻塞 v1.2.7）
2. v1.2.13 模块拆分前移到早期版本的策略（不阻塞 v1.2.7）
3. prefill 接口在 v1.2.7 还是 v1.2.10 的定位（建议 v1.2.7 留接口/占位，v1.2.10 正式实现加载逻辑）
4. attempt_id 命名约定规范化

### Do not implement in current big stage:

1. 双输出模式
2. 外部检索 / 政策知识库
3. 完整风险分类器 / 代表性发言选择器 / 拐点检测器重构

---

## 8. v1.2.7 Readiness Recommendation

```text
Can Control Agent write v1.2.7 iteration document now?
conditional — 上述 9 项 Must fix 需先落地到路线图/PRD 修订版，再写迭代文档

Recommended v1.2.7 title:
v1.2.7 - Report Product Contract & Markdown Grounding

Recommended v1.2.7 attempt split:
attempt-01: Schema 扩展（ReportMeta + AudienceMode + risk expression 字段）
           + report_agent wire + generated_at 输出
           + test_report_product_contract
attempt-02: Markdown 模板改写（指标后台化）
           + prompt 约束（模拟推演口径 / 禁止现实事实化 / 对策建议边界 / 禁止伪装）
           + test_report_markdown_grounding

Recommended v1.2.7 hard acceptance criteria:
1. final_report.md 顶部包含 generated_at（非 LLM 生成）
2. final_report.json 包含 generated_at，与 md 一致
3. 报告明确为"模拟推演型舆情风险研判报告"
4. 正文不裸露 event_scale / polarization_index 等技术指标
5. 不出现"全网已经""公众普遍认为"等现实事实化表达
6. 风险研判采用"风险等级 + 主要风险类型 + 风险解释"结构
7. 对策建议不越界（无行政决策/法律判断/责任定性）
8. py_compile / pytest / import checks 通过
9. closeout smoke test 通过

Recommended v1.2.7 forbidden scope:
1. 不改 Phase 1-3 主链
2. 不做双输出模式
3. 不创建 audience_router.py / risk_taxonomy.py / quote_grounding.py /
   inflection_grounding.py / report_prompt_builder.py /
   report_markdown_writer.py / report_json_writer.py
4. 不接外部检索 / 政策知识库
5. 不让 LLM 自由发明风险类型
6. 不让 LLM 自行重算拐点
7. 不修改 RuntimeLogger / whitebox 职责
```

---

## 9. Final DS Recommendation

```text
路线图方向正确，v1.2.7 一周可落地。
v1.2.7 没有太大——23 工时、400-500 行变更、6-7 个文件、两次 attempt，
在 7 天排期内有充裕的缓冲。

建议先完成 9 项 Must fix（主要是风险类型过渡策略、枚举选择、模板明确、
禁止表达纳入 prompt、白盒标题对齐），更新路线图至 v0.2，
然后直接写 v1.2.7 正式迭代文档。

不建议再次审查——9 项修正均为文档级边界问题，不需要第二轮 DS Agent Team。
```

---

## Appendix: Reviewer Detail Logs

### A1. Architecture Reviewer — Modules To Defer

| 模块 | 建议版本 | 理由 |
|------|----------|------|
| `audience_router.py` | v1.2.8 | 路由逻辑约15行，v1.2.7 可内嵌于 report_agent.py |
| `risk_taxonomy.py` | v1.2.7 可选 / 否则 v1.2.9 | 若需独立白名单审计工件则可创建，否则推迟 |
| `risk_expression.py` | v1.2.9 | 3行结构拼接，v1.2.7 可内嵌 |
| `prefill_loader.py` | v1.2.10 | 15行文件读取，非 v1.2.7 核心 |
| `quote_grounding.py` | v1.2.11 | 尚未有代表性引用可追溯 |
| `inflection_grounding.py` | v1.2.11 | 拐点逻辑已存在于 report_agent.py |
| `report_prompt_builder.py` | v1.2.13 | Prompt 80行，架构收口前不需分离 |
| `report_markdown_writer.py` | v1.2.13 | 与 _llm_generated_markdown 全局状态耦合 |
| `report_json_writer.py` | v1.2.13 | 15行，应与 markdown_writer 一起提取 |

### A2. Engineering Reviewer — v1.2.7 Effort Breakdown

| Task | Hours | Risk |
|------|-------|------|
| Schema: ReportMeta + AudienceMode + risk expression | 1.5 | Low |
| report_agent.py: metadata wiring | 2.5 | Low |
| report_agent.py: markdown template rewrite | 4.0 | Medium |
| Prompt changes: simulation wording, no real-facts | 2.0 | Medium |
| test_report_product_contract.py | 3.0 | Low |
| test_report_markdown_grounding.py | 3.0 | Low |
| Whitebox check sync | 1.0 | Medium |
| Documentation (iteration doc, TASK_LOG, CHANGELOG) | 2.0 | Low |
| Buffer/debug/closeout | 4.0 | — |
| **Total** | **23.0** | |

### A3. Product Contract Reviewer — PRD-Roadmap Alignment Issues

| # | Issue | Severity |
|---|-------|----------|
| 1 | Chapter template mismatch (code vs PRD) | HIGH |
| 2 | Risk level enum mismatch (4-level vs 6-level) | HIGH |
| 3 | v1.2.7 risk types without v1.2.9 whitelist | HIGH |
| 4 | Prefill timing conflict (PRD says v1.2.7, Roadmap says v1.2.10) | MEDIUM |
| 5 | report_schema_0507.md inflection detection ownership conflict | MEDIUM |
