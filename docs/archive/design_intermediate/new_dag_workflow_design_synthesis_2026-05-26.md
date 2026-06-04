# 新 DAG 工作流与原生态防漂移架构整合稿

> 文档类型：工作流设计整合 / 方法论沉淀  
> 项目语境：workyb / Relay Runtime / Hermes / Codex / DS Team / Owner-Control  
> 当前状态：conversation synthesis / 可作为后续设计审查与沉淀草稿  
> 生成目的：整合本会话中关于新 DAG 工作流、三大底座、防漂移架构、handoff 机制与敏捷开发原则的关键设计。  
> Owner：Gary  

---

## 0. 一句话总结

这套工作流的核心不是“多 agent 越多越好”，而是：

```text
以真实任务为驱动，把工作拆成低耦合变化节点；
每个节点只负责一个变化；
用 Relay Runtime 保持运行现场；
用 Memory / Handoff 保持上下文连续；
用 Skill / MCP / Hook Registry 管能力边界；
用 Code Reality Review 把设计拉回真实代码；
用 Owner-Control 做最终 gate。
```

更短地说：

```text
低耦合施工，现场优先，代码现实校验，敏捷长出系统。
```

---

## 1. 背景：为什么需要新工作流

过去 Adarian / workyb 推进中出现过一个明显问题：

```text
设计很多
→ 真正落地少
→ 缺少运行反馈
→ 只能继续在脑子里修设计
→ 设计越来越复杂
→ 越复杂越不敢落地
→ 继续设计
```

这不是设计能力差，而是设计反馈回路太慢。新的工作流要解决的是：

```text
不再让系统长期停留在思辨；
每个想法都尽快落成最小可验证闭环；
从真实运行中的 bug、HOLD、artifact、report 中反推下一步设计。
```

Relay Runtime R1 是一次关键验证：

```text
不是先设计完美通讯层；
而是先做 tmux executor；
跑 smoke；
卡 dialog；
补 bash permission；
卡 basename；
补 file creation；
卡 scrollback；
补 PaneStateParser；
最终 exit 0。
```

这说明：系统设计不是凭空抽象出来的，而是在真实任务压力下长出来的。

---

## 2. 新 DAG 工作流的核心形态

目标形态：

```text
多个 team 并发施工
→ 多个 team 并发审查
→ 一个验收 team 统一运行验证
→ Owner 最终核查、判断哪个 team 执行不到位
```

这不是“多 agent 混战”，而是低耦合分区施工。

### 2.1 施工节点原则

每个施工节点只负责一个清晰变化：

```text
一个 node = 一个主要变化原因
```

每个节点应明确：

```yaml
node_id:
role:
input:
allowed_read:
allowed_write:
forbidden:
expected_output:
handoff_to:
verification:
failure_policy:
```

### 2.2 并发前提

并发施工的前提不是“大家一起改一堆文件”，而是：

```text
文件边界分离；
接口约定清楚；
产物路径固定；
每个 team 不互相覆盖。
```

---

## 3. Single Change Responsibility Principle

本会话中最重要的代码与工作流原则之一：

```text
一个类只管一个变化；
一个节点只管一个变化；
一个模块只管一个变化；
一个 scope 只管一类上下文。
```

准确表述：

```text
一个类 / helper / 模块应当围绕一个主要变化原因设计。
如果两个逻辑未来会因为不同需求、不同 bug、不同策略变化而分别修改，
它们就不应该长期混在同一个类里。
```

### 3.1 它不等于机械拆类

它不是说：

```text
类越多越好；
每个函数都要拆一个类；
为了架构漂亮强行拆文件；
R1 就要平台化重构。
```

而是说：

```text
当某个需求变化时，应该能清楚知道改哪里。
dialog 规则变化，不该改 ArtifactDetector。
heartbeat schema 变化，不该改 DialogHandler。
sound notification 变化，不该改 runtime_state 判断。
expected_outputs 路径规则变化，不该改 tmux session 管理。
```

### 3.2 在 Relay Runtime 中的映射

理想职责边界：

```text
TmuxSessionManager：只负责 tmux session 生命周期。
PaneStateParser：只负责 pane 输出状态解析。
ClaudeDialogHandler：只负责 dialog 分类、安全确认、dedup。
ArtifactDetector：只负责 expected_outputs、路径合同、artifact 完成判定。
RuntimeFileWriter：只负责 heartbeat / progress / result / pane_capture 等 runtime 文件写入。
SoundNotifier：只负责终态声音提醒。
ClaudeTmuxExecutor：只负责主流程编排，不吃掉所有细节。
```

### 3.3 当前经验

Relay Runtime R1 的 Code Reality Review 判断：

```text
tmux_executor.py 虽然 1600+ 行，但不是单一巨类。
当前是一个文件内多类共置。
真正需要 R2 拆的是 ArtifactDetector 中 Bash permission validator 这类独立安全关注点。
```

这说明：低耦合不是看文件行数，而是看变化原因是否被清楚隔离。

---

## 4. 三大底座

当前工作流先敲定三大底座，不做过多提前设计：

```text
1. Memory Governance
2. Relay Runtime
3. Skill / MCP / Hook Registry
```

### 4.1 Memory Governance：管上下文

回答的问题：

```text
什么该记？
记在哪里？
哪个 scope 能用？
哪些内容不能串线？
下一次会话怎么恢复？
```

目标：

```text
防上下文污染；
防课程任务污染 Adarian 主线；
防任务进度塞进长期记忆；
防跨会话断裂。
```

### 4.2 Relay Runtime：管运行现场

回答的问题：

```text
agent 怎么被拉起来？
运行中怎么监听？
卡住了怎么 HOLD？
人怎么接管？
产物怎么回收？
结束怎么提醒？
```

核心资产：

```text
tmux executor
heartbeat.json
heartbeat_history.jsonl
pane_capture.log
progress.yaml
result.json
sound notification
dialog handling
expected_outputs contract
```

目标：

```text
防黑盒执行；
防长程任务失联；
防任务运行漂移；
防无法接管现场。
```

### 4.3 Skill / MCP / Hook Registry：管能力资源

回答的问题：

```text
每个 agent 有哪些 skill？
哪些 MCP 可用？
哪些 hook 会自动触发？
作用在哪个 workspace？
真实路径在哪里？
权限边界是什么？
风险等级是什么？
谁能调用？
```

目标：

```text
防工具能力漂移；
防路径黑盒；
防 agent 能力边界不清；
防 hook 暗箱触发。
```

### 4.4 关于 MultiCA 的边界

当前路线明确：

```text
不计划接入 MultiCA；
不围绕 MultiCA 做适配；
不把 Relay Runtime 设计成服务 MultiCA 的底座。
```

MultiCA 是曾经体验不佳的对照案例，不是当前主路线。

---

## 5. 原生态防漂移架构

本会话中形成的原生态防漂移结构：

```text
1. Memory Governance
   防上下文漂移、scope 污染、跨会话断裂。

2. Relay Runtime
   防任务运行漂移、黑盒执行、长程失联、现场不可接管。

3. Skill / MCP / Hook Registry
   防工具能力漂移、路径黑盒、agent 能力边界不清。

4. Hermes 现场优先
   防小 runtime bug 被升级成过度设计。

5. Codex 执行边界
   防代码修改越界、顺手重构、git 污染。

6. DS Team Code Reality Review
   防任务书想象替代真实代码、设计架构和实现架构脱节。

7. Owner-Control Gate
   防执行完成被误判为版本完成。
```

这不是思辨，而是在实践中长出来的结构。

### 5.1 从提示词治理到运行时治理

以前防漂移更多靠提示：

```text
不要扩大 scope；
不要越界；
不要误判 closeout；
不要污染记忆。
```

现在有运行承载物：

```text
memory_registry.yaml
.session_handoff.md
tmux executor
heartbeat_history.jsonl
pane_capture.log
result.json
task_dir/outputs
Code Reality Review
DS Team 审查
Hermes 现场 hotfix
```

结构变成：

```text
上下文漂移 → scope memory / handoff
执行漂移 → relay runtime / heartbeat / result
现场漂移 → tmux attach / pane capture
代码漂移 → allowed files / git staging boundary
架构漂移 → Code Reality Mapping
能力漂移 → Skill / MCP / Hook Registry
验收漂移 → DS Team + Owner-Control Gate
```

---

## 6. DS Team Code Reality Review

这是防漂移架构里最狠的一刀。

核心判断：

```text
任务书里说已经这样设计
≠
代码里真的这样实现
```

Code Reality Review 不从任务书倒推代码，而是：

```text
先看真实代码；
再描述真实系统；
再画 Mermaid；
最后才和设计架构做轻量比对。
```

### 6.1 它防什么

它防 AI 工作流里的“文字闭环”：

```text
任务卡写得很漂亮；
Codex 回传说完成；
Hermes 摘要说通过；
DS 按任务书验了一遍；
Owner 看到报告觉得差不多；
但真实代码已经变成另一个东西。
```

### 6.2 它必须输出

```text
真实文件清单
真实类/函数职责
真实调用链
真实 runtime artifact flow
Mermaid 图
设计 vs 实现差异
代码粘稠度判断
是否需要拆分
哪些只是 R2 backlog
```

### 6.3 固定 Gate

未来底座级模块完成 R0/R1 后，应固定做 Code Reality Review：

```text
Relay Runtime
Memory Governance
Skill / MCP / Hook Registry
PM Runtime
Handoff
Agent Team DAG
```

---

## 7. 现场优先原则

本会话中形成了另一个关键规则：

```text
谁最接近运行现场，谁优先处理现场型小故障。
```

### 7.1 Hermes 适合什么

Hermes 适合：

```text
tmux 现场卡点；
dialog 识别问题；
heartbeat / pane / result 异常；
长任务中途保活；
小范围 runtime hotfix；
现场 smoke / dogfood 调试。
```

### 7.2 Codex 适合什么

Codex 适合：

```text
完整实现单元；
多文件代码落盘；
测试补强；
明确任务卡下的结构化修复；
需要较强代码综合能力的 patch。
```

### 7.3 Control Agent 适合什么

Control Agent 适合：

```text
判断边界；
收口任务；
写任务卡；
识别谁该做；
做 gate；
防止范围漂移。
```

不适合直接隔空修现场型 runtime bug。

### 7.4 规则沉淀

```text
Runtime 现场型小 bug，优先 Hermes hotfix；
结构性代码修复，交 Codex；
验收和架构审查，交 DS Team；
最终 gate，回 Owner-Control。
```

---

## 8. Relay Runtime R1 的实践启示

Relay Runtime R1 是新 DAG 工作流的实践样本。

### 8.1 修复路径

```text
R0 方向跑通
→ Codex R1 hardening
→ Hermes smoke/demo
→ Bash permission blocker
→ Codex patch
→ file creation basename blocker
→ Codex patch
→ PaneStateParser scrollback blocker
→ Hermes 现场 hotfix
→ exit 0
→ dogfood Code Reality Review
→ PASS_WITH_FINDINGS
```

### 8.2 关键事实

Relay Runtime R1 已经证明：

```text
tmux relay 可以启动 Claude；
可以发送 prompt；
可以自动处理 dialog；
可以写 expected_outputs；
可以写 heartbeat / pane_capture / result；
可以声音提醒；
可以自闭环 exit 0；
可以承载 5 agent 的真实 dogfood review。
```

### 8.3 仍需记录的 known issues

```text
clauderemote active 与 fallback_used 状态记录不一致；
dialog_handling 字段在 result.json 中可能为空；
BASH_PERMISSION_DIALOG 未在最终 smoke 中显式触发；
多行 / 反斜杠路径的 bash permission parser 在长任务中仍暴露过问题；
ArtifactDetector 职责偏重，R2 可拆 BashPermissionValidator；
extractors.py 当前 orphaned，R2 需接入或移除。
```

---

## 9. Handoff 机制：连续工作状态账本

核心原则：

```text
Handoff 不是日报，也不是会话摘要。
Handoff 是连续工作状态账本。
相近会话默认增量合并；阶段 closeout 后才允许压缩重置。
```

### 9.1 为什么不能全量覆盖

相近会话不是完全切换主题，而是连续推进。每次会话结束时，都带着新的成果、问题、待办、发现和决策。

正确语义：

```text
上一轮已有成果 / 决策 / 文件索引 / 未完成问题
+
本轮新增成果 / 新发现 / 新问题 / 新待办 / 新风险
=
下一轮启动所需上下文
```

错误语义：

```text
replace latest summary
```

正确语义：

```text
accumulate working state
```

### 9.2 Handoff Writer 的问题

本会话暴露的问题：

```text
write_file 更顺手；
handoff-writer.py 更正确；
但正确路径阻力更高；
agent 会自然走阻力更低的路径。
```

这不是纪律问题，而是机制设计问题。

### 9.3 Handoff R0 最小修复方向

Hermes 审查后给出 `GO_WITH_SIMPLIFICATION`：

```text
协议完整，但路径诱因不对。
```

R0 最小补丁：

```text
1. handoff-writer.py 增加 --replace flag；
2. 默认 merge / append；
3. replace 必须显式；
4. 即使 replace 也要 archive；
5. 写完自动调用 session-end-stamp.py；
6. 输出 update summary；
7. 不做过重 write_file 拦截；
8. 不做复杂语义合并；
9. 不做状态管理平台。
```

### 9.4 推荐 handoff 章节结构

```markdown
# Session Handoff — YYYY-MM-DD HH:MM → HH:MM（~XhYm）

## 当前状态
一句话说明当前在做什么。

## ✅ 本轮完成
刚做了什么。

## 📋 待 Owner 审批
等 Owner 拍板的事项。

## ⏩ 下一步
明确优先级和分工。

## 🧩 关键决策记录
为什么做这个、不做那个。

## 📁 关键文件索引
报告、receipt、result、pane_capture、review_report 等路径。

## ⚠️ 已知问题 / Blockers
下一轮必须知道的问题。
```

### 9.5 Continuous vs Milestone

建议定义两种模式：

```text
Continuous Handoff Mode
- 相近会话连续推进；
- 默认追加 / 合并；
- 不全量替换；
- 保留上一轮未完成事项和关键路径。

Milestone Reset Mode
- 阶段真正 closeout；
- 旧 handoff 归档；
- 生成新的压缩 baseline；
- 必须明确 owner_authorized 或 closeout_confirmed。
```

---

## 10. Context Recovery Architecture

本会话中又长出一层重要机制：会话启动时自动恢复上下文。

当前机制：

```text
首轮 LLM 调用触发
  → 记录开始时间到 ~/.hermes/.session_start
  → 注入时间上下文：开始时间 + 已耗时
  → 搜索 .session_handoff.md → 注入“会话进度恢复”
  → 搜索 资产/memory_governance/handoffs/ 最近一条 → 注入“上一轮会话存档”
  → 注入到 LLM 上下文
```

意义：

```text
不用靠泛化记忆；
不用靠大量手动复制；
靠结构化 handoff / archive 恢复“昨晚在干嘛”。
```

这把 handoff 从文档约定升级成了会话启动协议。

---

## 11. Handoff 与 Memory 的边界

### 11.1 Memory 存什么

Memory 应存：

```text
长期偏好；
稳定身份；
项目惯例；
工具环境；
长期路线；
重要但稳定的工作流原则。
```

### 11.2 Handoff 存什么

Handoff 应存：

```text
当前状态；
下一步；
未审批事项；
active blocker；
关键决策；
活跃 task id；
关键文件路径；
最近 verdict。
```

### 11.3 Handoff 不该存什么

不应存完整证据：

```text
长报告全文；
大段日志；
已解决 bug 的完整过程；
完整审查正文；
完整 pane_capture。
```

Handoff 应引用路径，而不是替代证据本体。

---

## 12. 敏捷开发精神

最终收束出一条工程纪律：

```text
先跑通真实小闭环，再从真实痛点里抽象，不为未来幻想提前造大系统。
```

### 12.1 设计规则

```text
不预先设计大架构；
不追求一次性完美；
一个版本只解决一个主要变化；
一个类只管一个变化；
一个 agent team 只负责一个清晰任务；
能用 MVP 验证，就不用宏大规划替代验证；
跑通后再审查，审查后再固化。
```

### 12.2 设计刹车

每个新设计必须问：

```text
它的最小可验证版本是什么？
本周能不能跑一次？
跑完以后要留下什么 evidence？
谁最接近现场？
当前是否有真实痛点支撑？
```

### 12.3 防止过度设计

如果一个设计：

```text
不能在真实任务里验证；
不能产出 artifact；
不能减少人肉 relay；
不能改善上下文连续性；
不能降低耦合或漂移；
```

就先不要做成正式系统。

---

## 13. A/B 双线 Portfolio 工作流

本会话中也确认了 portfolio thinking：

```text
A 线：Adarian 正式主线
B 线：课程作业 / MVP / 实验项目 / 玩具项目
workyb：工作流中台与资产仓
```

原则：

```text
B 线低风险试错
→ 抽象出能力
→ workyb 固化为资产
→ DS / Hermes 审查
→ Owner 判断是否 promotion
→ A 线吸收成熟能力
```

含义：

```text
实验不污染主线；
但好实验可以被吸收。
```

---

## 14. 角色卡的位置

当前不要过早做“角色卡统一管理大系统”。

角色卡必须建立在三大底座之上：

```text
Memory Governance 决定它能读什么；
Relay Runtime 决定它怎么跑；
Skill / MCP / Hook Registry 决定它能用什么；
Task Card 决定它要产出什么；
Receipt / Report 决定它如何回收；
Owner-Control 决定它是否通过。
```

当前层级：

```text
第一层：三大底座
- Memory Governance
- Relay Runtime
- Skill / MCP / Hook Registry

第二层：任务协议
- task card
- dispatch
- receipt
- result
- handoff

第三层：角色卡
- reviewer
- executor
- auditor
- verifier
- mapper
- PM runtime agent
```

---

## 15. 当前工作流角色分工

### 15.1 Owner-Control

```text
最终 gate；
判断是否 closeout；
判断哪个 team 执行不到位；
决定哪些 finding 进入 R1.1 / R2；
防止执行完成被误判为版本完成。
```

### 15.2 Hermes / PM Runtime

```text
现场运行；
tmux / pane / heartbeat / result 监控；
long task 保活；
现场 hotfix；
派发 DS Team；
回收 receipt / report / summary。
```

### 15.3 Codex

```text
结构化代码实现；
多文件落盘；
测试补强；
明确任务卡下的 patch；
不做最终 closeout。
```

### 15.4 DS Team

```text
多 agent 审查；
Code Reality Review；
架构与实现比对；
Mermaid 图；
低耦合审查；
验收建议。
```

### 15.5 Control Agent

```text
边界判断；
任务卡生成；
角色分配；
gate 判断；
防止范围漂移；
不假装自己能看本地现场。
```

---

## 16. 后续路线建议

### 16.1 Relay Runtime R1 closeout

```text
Relay Runtime R1 已实现 exit 0 self-closing；
dogfood Code Reality Review verdict 为 PASS_WITH_FINDINGS；
建议 closeout。
```

### 16.2 R1.1 候选

```text
修 dialog_handling metadata capture；
修 remote_mode_status active 类型不一致；
移除 _contains_any；
移除或接入 pane_mentions_expected_output；
补 README.md / CONFIG.md / RUNTIME_CONTRACT.md。
```

### 16.3 R2 候选

```text
抽 BashPermissionValidator；
接入或移除 extractors.py；
抽 shared utilities；
解决 relay_runner 与 tmux_executor 的 lazy circular import；
补 ARCHITECTURE.md / TROUBLESHOOTING.md；
Codex communication layer。
```

### 16.4 Skill / MCP / Hook Registry R0

后续重点之一：

```text
登记每个 agent 的 skill / MCP / hook；
记录能力范围；
记录作用 workspace；
记录真实路径；
记录权限边界；
记录自动触发条件；
记录风险等级。
```

### 16.5 Handoff Writer R0 Patch

优先级较高：

```text
handoff-writer.py 默认 merge；
新增 --replace；
自动 archive；
自动 end-stamp；
输出 update summary；
不做过重 write_file 拦截。
```

---

## 17. 核心原则清单

```text
1. 系统设计不是凭空抽象出来的，而是在真实任务中长出来的。

2. 不预先设计大系统，先跑最小闭环。

3. 一个 DAG 节点只负责一个变化。

4. 一个代码类只负责一个变化。

5. Runtime 现场型小 bug，优先现场方 Hermes hotfix。

6. 结构性代码修复交 Codex。

7. 代码现实与架构审查交 DS Team。

8. 最终 closeout 只能由 Owner-Control 判断。

9. Handoff 是连续工作状态账本，不是会话摘要。

10. 相近会话 handoff 默认增量合并，阶段 closeout 后才允许压缩重置。

11. 不靠 agent 自觉防漂移，要靠机制让正确路径成为阻力最小路径。

12. Code Reality Review 是防任务书幻想替代真实代码的硬门。

13. Skill / MCP / Hook 必须登记，否则能力资源会黑盒漂移。

14. 实验不污染主线，但好实验可以被 promotion 到正式工程资产。

15. 报告、receipt、result、pane_capture 是 evidence；口头 summary 不是 closeout。
```

---

## 18. 方法论命名候选

### 18.1 敏捷 DAG 施工法

```text
不预设大架构；
只定义小变化；
并发施工；
并发审查；
统一验收；
Owner 收口。
```

### 18.2 原生态防漂移架构

```text
由真实痛点自然长出的多层防漂移结构：
memory、runtime、skill registry、code reality review、handoff、Owner gate。
```

### 18.3 Code Reality First

```text
所有设计判断最终必须回到真实代码、真实调用链、真实 artifact、真实运行证据。
```

### 18.4 Context Recovery Architecture

```text
用 handoff、archive、hook 和时间上下文恢复跨会话现场，而不是依赖泛化记忆。
```

---

## 19. 最终收束

本会话最重要的成果不是某一个任务卡，而是形成了一套可实践的工作流判断：

```text
先用敏捷方式跑出真实小闭环；
用现场运行暴露问题；
让最接近现场的 agent 修现场 bug；
用 Codex 做结构化实现；
用 DS Team 从真实代码回读架构；
用 Handoff / Memory 保持上下文连续；
用 Skill Registry 管能力边界；
最后由 Owner-Control 收口。
```

这套东西不是在思辨，而是在 Relay Runtime R1、dogfood review、handoff bug、Hermes hotfix、Code Reality Review 中被验证出来的。

一句话：

```text
你们不是在设计一个 AI 工作流系统；
你们已经在用这个工作流系统生产和修复它自己。
```
