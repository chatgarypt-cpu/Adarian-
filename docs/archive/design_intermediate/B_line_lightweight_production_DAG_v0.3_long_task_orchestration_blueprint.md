# B线轻量生产 DAG 工作流 v0.3：无监督长程任务执行与分布式节点编排蓝图

> 版本：v0.3  
> 状态：设计蓝图 / 不是 A 线 workflow_core / 不是正式权威源  
> 来源：AI创意出版第三次作业归盘、B线轻量生产 DAG v0.2、PM Runtime 通讯层实战、Owner 新增设计意见  
> 适用对象：Owner / Control Agent / Hermes PM Runtime / Claude Code / Codex / DS Team / 未来 B 线执行 Agent  
> 核心定位：demo / pipeline / idea validation line  
> 关键词：无监督长程任务执行、分布式执行节点、AI 修 AI、渐进式边界确认、分阶段验收、可控升格  

---

## 0. v0.3 一句话定义

B 线不是小号 A 线，也不只是课程作业 workflow。

B 线 v0.3 是一套面向 demo、pipeline、实验项目、课程作业和想法验证的轻量长程任务生产系统：

```text
Owner 提出目标
→ 中控收集上下文与边界
→ 中控持续向 Owner 追问关键缺口
→ 上下文齐全后形成最终任务方案
→ 用户确认
→ 中控拆解 DAG / agent team / 分布式节点
→ 下游 Agent 执行
→ AI 审查 AI / AI 修 AI
→ 分阶段分层验收
→ 产出 demo / pipeline / 成品
→ 归盘
→ 判断是否升格 A 线
```

核心不是全自动替 Owner 决策，而是：

```text
让中控在足够上下文下自主规划、编排、调度和验收；
让 Owner 从低价值搬运中解放出来；
让 Owner 只在方向、边界、交付程度、最终 Gate 上做关键判断。
```

---

## 1. v0.3 相比 v0.2 的升级点

v0.2 主要解决：

```text
Hermes × Claude Code DAG：
Hermes 调度；
Claude Code 执行节点；
Owner 做样张 Gate；
Control 做归盘。
```

v0.3 进一步加入：

```text
1. 无监督长程任务执行能力；
2. 分布式执行节点；
3. AI 修 AI 闭环；
4. 任务等级 / 大小 / 风险自适应规划；
5. 中控渐进式追问与上下文补齐；
6. 最终任务书动态更新；
7. 分阶段、分层次验收；
8. 工作线 / 记忆 / 权责隔离；
9. 交付完成度协商；
10. 产物升格判断。
```

v0.3 的目标不是“更复杂”，而是让 B 线能处理更长、更复杂但仍不需要 A 线重治理的任务。

---

## 2. B 线 v0.3 的核心能力总览

### 2.1 Context Completion：上下文补齐能力

中控必须先判断当前任务上下文是否足够。

它需要确认：

```text
任务目标；
交付物；
截止时间；
输入材料；
输出格式；
质量标准；
允许使用哪些工具；
是否需要联网；
是否需要数据；
是否需要代码；
是否需要图表；
是否需要文档排版；
是否需要多 agent；
是否需要审查；
Owner 最关心什么；
哪些内容不能做。
```

如果上下文不足，中控不能直接执行，而应持续追问 Owner。

追问原则：

```text
只问关键缺口；
一次最多问 3—5 个问题；
不要把全部问题一次性抛给用户；
能基于已有上下文合理假设的，明确写出假设并请用户确认；
用户确认后再推进。
```

---

### 2.2 Plan Finalization：最终方案形成能力

中控在上下文足够后，应形成一份最终方案。

最终方案可来自：

```text
原始任务书；
Owner 后续补充；
Hermes / Control 的建议；
DS / Claude / Codex 的预审反馈；
历史经验；
当前工作线规则。
```

形成的最终方案应包括：

```text
任务目标；
交付物定义；
完成度标准；
DAG 节点；
节点执行器；
节点输入输出；
质量门；
Repair Loop；
分阶段验收；
Owner 决策点；
禁止事项；
失败策略；
归盘要求。
```

Owner 同意后，才进入执行编排。

---

### 2.3 Task Sizing：任务等级与大小判断能力

中控需要根据任务大小决定工作流强度。

建议任务等级：

```text
S-Level：轻量单点任务
M-Level：中等多步骤任务
L-Level：长程多阶段任务
XL-Level：跨天、多 agent、多产物任务
```

判断维度：

```text
交付物数量；
是否需要数据；
是否需要联网；
是否需要图表；
是否需要代码；
是否需要多个执行节点；
是否需要多个 Gate；
失败成本；
截止时间；
是否会影响 A 线资产。
```

示例：

```text
S-Level：润色一段文字、改一个图表标题；
M-Level：做一份短报告、单图可视化、简单 PPT；
L-Level：采集+清洗+可视化+PDF；
XL-Level：课程作业合集、MVP demo 管线、多 agent 分布式任务。
```

---

### 2.4 Agent Team Generation：自主生成与编排 Agent Team

中控应根据任务等级和节点类型，自主决定是否需要 agent team。

不是所有任务都需要 team。

推荐规则：

```text
S-Level：单 agent 或 Control 直接完成；
M-Level：Hermes + 一个执行 Agent；
L-Level：Hermes + Claude Code / Codex + 轻量审查 Agent；
XL-Level：Hermes 组织多个分布式节点，必要时引入 DS Team / sidecar。
```

Agent Team 类型：

```text
执行 Agent：Claude Code / Codex / Python runner；
审查 Agent：DS / Claude read-only reviewer；
质控 Agent：sidecar / subagent；
归盘 Agent：Hermes / Control；
路由 Agent：Hermes PM Runtime。
```

中控必须明确每个 Agent 的：

```text
native identity；
project overlay；
allowed scope；
forbidden scope；
input；
output；
receipt；
是否可写；
是否可联网；
是否可 yolo；
是否需要 Owner Gate。
```

---

### 2.5 Distributed Node Execution：分布式执行节点能力

B 线 v0.3 的关键升级是分布式节点执行。

任务不再是单 agent 串行完成，而是：

```text
多个节点并行或分阶段运行；
每个节点有自己的 dispatch；
每个节点有自己的 receipt；
每个节点有自己的 memory scope；
每个节点有自己的 artifact；
Hermes / PM Runtime 负责回收与汇总。
```

适合分布式的节点：

```text
多图表样张；
多数据源探针；
多关键词采集；
多章节草稿；
多方案对比；
多版本版式；
多工具 smoke test；
多 agent 审查。
```

不适合分布式的节点：

```text
Owner 最终方向判断；
最终成品 Gate；
跨线升格判断；
高风险治理修改；
A 线 closeout。
```

---

### 2.6 AI Fix AI：AI 修 AI 能力

B 线质量门和 A 线不同。B 线不是只做“人类审查后打回”，而是允许：

```text
AI 发现 AI 的错误；
带着问题、错误、日志、失败分类返回给执行 Agent；
执行 Agent 根据错误上下文修复；
修复后再进入轻量复验。
```

典型闭环：

```text
Executor 产物
→ Reviewer / Gate 发现问题
→ 生成 issue packet
→ 返回 Executor 修复
→ Executor 输出 patch / revised artifact
→ Reviewer 复验
→ Owner 只看关键结果
```

AI 修 AI 的边界：

允许：

```text
字段解析错误；
格式错误；
路径错误；
图表标签错误；
PDF 溢出；
报告结构缺项；
receipt 字段缺失；
小范围代码 bug；
样张局部修复。
```

必须回 Owner：

```text
任务目标变了；
分析结论方向变了；
图表变量组合变了；
数据源要换；
需要新增/删除核心产物；
需要扩大权限；
需要修改 A 线资产；
需要高风险自动化。
```

---

### 2.7 Layered Validation：分阶段分层次验收

B 线验收不等于 A 线 closeout。

B 线验收应分层：

```text
Node-Level Validation：节点级验收；
Stage-Level Validation：阶段级验收；
Product-Level Validation：成品级验收；
Retrospective-Level Validation：归盘级验收；
Promotion-Level Validation：升格级验收。
```

节点级验收：

```text
文件是否生成；
命令是否成功；
receipt 是否存在；
是否触碰 forbidden scope；
是否满足节点输出。
```

阶段级验收：

```text
采集阶段是否可进入清洗；
清洗阶段是否可进入可视化；
样张阶段是否可进入正式生产。
```

成品级验收：

```text
是否可交付；
是否符合课程 / demo / pipeline 目标；
是否需要小修。
```

归盘级验收：

```text
是否记录卡点；
是否沉淀经验；
是否列出 skill candidates。
```

升格级验收：

```text
是否值得成为 A 线资产；
是否需要 DS / Owner-Control 正式审查。
```

---

## 3. B 线 v0.3 的工作流主循环

```text
Task Intake
→ Context Completion
→ Plan Finalization
→ Owner Approval
→ DAG Decomposition
→ Agent Team Generation
→ Distributed Execution
→ AI Review / AI Fix Loop
→ Layered Validation
→ Product Assembly
→ Owner Final Gate
→ Retrospective
→ Promotion Decision
```

可以简化成：

```text
问清楚 → 写方案 → 用户确认 → 拆节点 → 派 Agent → AI 修 AI → 分层验收 → 交付 → 归盘 → 判断升格
```

---

## 4. 中控的核心职责

中控不是执行器，而是任务操作系统的调度和判断层。

中控负责：

```text
1. 判断上下文是否足够；
2. 向 Owner 追问关键边界；
3. 根据补充形成最终方案；
4. 判断任务等级；
5. 决定是否需要 agent team；
6. 拆解 DAG；
7. 组织分布式节点；
8. 为每个节点生成 dispatch；
9. 回收 receipt；
10. 组织 AI 修 AI；
11. 做分阶段验收；
12. 识别是否需要 Owner Gate；
13. 给 Owner 提供选项与建议；
14. 判断是否可以进入下一阶段；
15. 做归盘与升格建议。
```

中控不负责：

```text
1. 假装本地执行；
2. 替 Owner 做方向判断；
3. 自动升格 B 线资产到 A 线；
4. 绕过权限；
5. 隐藏失败；
6. 把 process success 伪装成 task success；
7. 把 demo pass 说成 production-ready。
```

---

## 5. Owner 交互模式

### 5.1 中控什么时候问 Owner

必须问：

```text
任务目标不清；
交付物不清；
完成度不清；
质量标准不清；
权限边界不清；
需要扩大 scope；
需要换数据源；
需要改变分析方向；
需要进入全量执行；
需要最终交付；
需要升格 A 线。
```

可以建议但不强行：

```text
哪个方案更优；
是否开并行；
是否使用 DS 审查；
是否先做样张；
是否降级交付。
```

不应该问：

```text
每个小路径；
每个小格式；
每个可自动修复的小 bug；
已在允许范围内的小修。
```

### 5.2 中控如何给选择

Owner 不应该被丢一堆无结构选择。

推荐格式：

```text
我建议选 A，理由是……
B 可选但成本更高……
C 不建议，风险是……
需要你确认的是：是否按 A 执行？
```

### 5.3 交付完成度协商

B 线应允许“合理完成度”而不是追求完美。

完成度可分：

```text
draft：初稿可看；
demo：能跑能展示；
usable：可交付；
polished：较高完成度；
archive-ready：可归盘沉淀；
promotion-ready：可升格评估。
```

中控应主动建议：

```text
当前做到 usable 已足够；
再往 polished 走会多耗时间；
是否继续打磨？
```

---

## 6. B 线质量门：区别于 A 线

A 线质量门强调：

```text
版本边界；
代码正确性；
测试；
审计；
closeout；
长期维护。
```

B 线质量门强调：

```text
想法是否被验证；
demo 是否能说明问题；
样张是否能支持判断；
成品是否能提交；
AI 修 AI 是否把明显错误修掉；
经验是否可归盘。
```

B 线质量门不是为了阻止执行，而是为了快速决定：

```text
继续；
小修；
降级；
回方案；
终止；
升格。
```

---

## 7. B 线质量门清单 v0.3

### Gate 0：Context Gate

```yaml
question: 上下文是否足够进入方案阶段？
verdict:
  - enough
  - ask_owner
  - hold
```

检查：

```text
任务目标；
交付物；
输入材料；
完成度；
截止时间；
禁止事项。
```

---

### Gate 1：Plan Gate

```yaml
question: 最终方案是否得到 Owner 同意？
verdict:
  - approved
  - revise_plan
  - hold
```

---

### Gate 2：DAG Gate

```yaml
question: 节点拆解是否合理？
verdict:
  - ready_to_dispatch
  - simplify
  - split
  - hold
```

检查：

```text
节点数量；
是否可并行；
每个节点输入输出；
Agent 角色；
是否需要样张；
是否需要 AI 审查。
```

---

### Gate 3：Node Gate

```yaml
question: 单节点是否完成？
verdict:
  - pass
  - ai_fix_required
  - owner_decision_required
  - fail
```

---

### Gate 4：AI Repair Gate

```yaml
question: AI 修 AI 是否解决问题？
verdict:
  - repaired
  - retry_once
  - escalate_to_owner
  - discard
```

默认最多两轮 repair。

---

### Gate 5：Stage Gate

```yaml
question: 当前阶段是否可进入下一阶段？
verdict:
  - proceed
  - repair_stage
  - owner_gate
  - downgrade
```

---

### Gate 6：Product Gate

```yaml
question: 成品是否达到约定完成度？
verdict:
  - usable
  - minor_repair
  - polish_optional
  - hold
```

---

### Gate 7：Retrospective Gate

```yaml
question: 是否完成归盘与资产候选提炼？
verdict:
  - archived
  - recap_needed
  - skip_with_reason
```

---

### Gate 8：Promotion Gate

```yaml
question: 是否值得升格 A 线？
verdict:
  - discard
  - keep_B_asset
  - promotion_candidate
  - promote_to_A_after_review
```

---

## 8. Agent Team 编排规则

### 8.1 默认角色池

```text
Hermes：中台 / 调度 / 状态 / 回执；
Claude Code：B 线节点执行器；
Codex：A 线工程执行器，B 线中只在需要代码落盘或强工程修改时使用；
DS Team：高价值审查，不默认开；
Sidecar：只读质控；
Control Agent：方案、边界、Gate、归盘；
Owner：最终方向与质量判断。
```

### 8.2 编排策略

```text
S-Level：Control / Hermes 直接处理；
M-Level：Hermes + Claude Code；
L-Level：Hermes + Claude Code 节点 + sidecar；
XL-Level：Hermes 编排多个节点，可引入 DS Team 审查。
```

### 8.3 分布式节点原则

每个节点必须有：

```text
node_id；
node_type；
executor；
input；
allowed_actions；
forbidden_actions；
output；
receipt；
memory_scope；
gate。
```

每个节点不得：

```text
自行扩大任务；
读取无关项目记忆；
改动非本节点产物；
替 Owner 做最终判断；
自动升格经验。
```

---

## 9. 记忆与权责隔离

### 9.1 必要性

没有记忆隔离，B 线 DAG 会出现：

```text
A 线规则污染 B 线；
课程作业经验污染主项目；
图1节点上下文污染图2节点；
Claude Code 把上个任务路径带进新任务；
Hermes 把临时 demo 经验当成正式规则。
```

### 9.2 最小字段

```yaml
lane_context:
  lane_id: A | B | tooling | coursework | experiment
  project_id:
  task_id:
  node_id:
  agent_role:
  native_identity:
  project_overlay:
  memory_read_scope: []
  memory_write_scope: []
  forbidden_memory_scope: []
  context_packet_path:
  evidence_paths: []
  promotion_policy:
```

### 9.3 Context Packet

每次派发节点前，中控 / Hermes 生成最小上下文包：

```text
当前 lane；
当前 project；
当前 task；
当前 node；
允许读取的记忆；
禁止注入的上下文；
上游产物；
当前决策；
输出要求；
失败策略。
```

### 9.4 经验升格规则

```text
node lesson → task retrospective；
task lesson → project lesson_candidate；
project lesson_candidate → B 线 asset；
B 线 asset → A 线 promotion candidate；
A 线 promotion candidate → Owner/Control/DS 审查后正式落地。
```

---

## 10. 渐进式披露

### 10.1 对 Owner

每次只让 Owner 做一个判断：

```text
是否按这个方案走？
样张是否通过？
当前完成度是否够？
是否需要继续打磨？
是否升格？
```

### 10.2 对 Agent

每个 Agent 只获得当前节点需要的信息：

```text
任务目标；
输入；
约束；
输出；
Gate；
receipt；
失败策略。
```

### 10.3 对产物

先小后大：

```text
小样本；
单图；
单页；
单章节；
小 demo；
再全量。
```

---

## 11. 迭代路线 v0.3 → v1.0

### v0.3：中控式长程任务蓝图

完成：

```text
无监督长程任务执行；
分布式节点；
AI 修 AI；
分层 Gate；
记忆隔离；
渐进式披露。
```

### v0.4：节点任务卡与 receipt 标准

产物：

```text
b_line_node_dispatch_template.md
b_line_node_receipt_template.md
owner_gate_record_template.md
ai_fix_issue_packet_template.md
```

### v0.5：最小 DAG Manifest

产物：

```text
dag.yaml
node_manifest.yaml
gate_log.md
promotion_candidates.md
```

### v0.6：Hermes 调度协议

产物：

```text
hermes_b_line_orchestration_protocol.md
status_first_reporting.md
node_state_model.md
```

### v0.7：Claude Code 节点执行规范

产物：

```text
claude_code_b_line_node_executor_role.md
readonly_review_yolo_lane.md
memory_scope_injection.md
```

### v0.8：课程作业 / Demo 实战模板

产物：

```text
coursework_pipeline_template/
demo_pipeline_template/
visualization_pipeline_template/
document_freeze_pipeline_template/
```

### v0.9：升格机制

产物：

```text
promotion_candidate_template.md
b_to_a_asset_review_protocol.md
```

### v1.0：B-Line Lightweight Production System

标准：

```text
能稳定处理课程作业、demo、MVP、实验项目；
能无痛切换上下文；
能自动组织节点；
能让 AI 修 AI；
能分层验收；
能归盘并输出升格候选。
```

---

## 12. v0.3 的最小可用模板

### 12.1 最小任务书

```yaml
task_id:
lane: B
project_id:
task_type: coursework | demo | pipeline | validation | experiment
owner_goal:
deliverables:
deadline:
completion_target: draft | demo | usable | polished | archive-ready
non_goals:

context_status:
  enough: true | false
  missing_questions: []

plan:
  summary:
  recommended_path:
  alternatives:
  owner_approval_required: true

dag:
  nodes: []

agent_team:
  required: true | false
  roles: []

quality_gates:
  context_gate:
  plan_gate:
  dag_gate:
  node_gate:
  ai_repair_gate:
  product_gate:
  retrospective_gate:
  promotion_gate:

memory_scope:
  read: []
  write: []
  forbidden: []

handoff:
  report_path:
  receipt_path:
  retrospective_path:
```

### 12.2 最小 AI Fix Issue Packet

```yaml
issue_id:
source_node:
reviewer:
executor_to_fix:
problem_type:
evidence:
expected_fix:
allowed_scope:
forbidden_scope:
retry_limit:
owner_decision_required: true | false
```

### 12.3 最小 Node Receipt

```yaml
node_id:
executor:
status:
input_files:
output_files:
actions_taken:
commands_run:
issues_found:
issues_fixed:
remaining_issues:
needs_owner_decision:
next_recommendation:
```

---

## 13. 最终判断

B 线 v0.3 的核心能力是：

```text
中控在足够上下文下，能够逐步追问、形成方案、拆解任务、组织 agent team、调度分布式节点、让 AI 修 AI，并通过分阶段分层验收，把想法推进成 demo / pipeline / 可交付产物。
```

它最重要的原则：

```text
不是全自动；
是足够上下文后的自主编排。

不是替 Owner 决策；
是把 Owner 的决策点前置并压缩。

不是 A 线重治理；
是 B 线快速验证与资产孵化。

不是更多记忆；
是有边界的记忆。

不是更多 agent；
是按任务等级合理编排 agent。
```

---

## 14. 一句话版本

```text
B 线 v0.3 是一个带记忆隔离和 AI 修 AI 闭环的轻量长程任务生产系统：它让中控在补齐上下文并获得 Owner 同意后，自主拆解任务、编排分布式 Agent 节点、执行分阶段验收，并把有价值的 demo / pipeline / skill 候选沉淀为可升格资产。
```
