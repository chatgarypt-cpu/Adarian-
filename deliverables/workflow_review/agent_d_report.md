# Hermes / TaskOps Hub v0.1 迁移方案设计报告

> 产出人：系统架构设计 Agent（Agent-D）
> 日期：2026-05-15
> 参考文献：二师兄 DAG 工作流流水线分层架构（Layer 0-9）、Adarian workflow_core.md v3.0

---

## 一、明确 Hermes 的定位（不是什么）

Hermes 的命名来自希腊神话中的信使之神——在 Olympian 诸神之间传递信息、护送灵魂。这个隐喻精确映射了 Hermes 在 Adarian 体系中的角色：它是任务治理的中转枢纽，不是任务执行者。

### 1.1 Hermes 不是自动开发平台

Hermes 不写代码、不跑测试、不部署服务。它不会像 GitHub Actions 或 Jenkins 那样定义一个 CI/CD 流水线，然后自动触发构建。它的职责是**确保正确的任务在正确的时间以正确的信息交给正确的角色执行**。执行的依然是 DS Team、Codex、Control Agent 和 Owner 这些人类或 AI Agent。

类比：Hermes 是机场塔台，不是飞机。

### 1.2 Hermes 是长程任务治理中台

Adarian 当前的开发流程是文档驱动、审计优先的多角色协作模式。一个版本从 User 提出需求到 Closeout，经历 Pre-Audit、Scope Freeze、Codex Attempt、DS Verify、DS Accept、Closeout Gate 等多个阶段，跨越 DS Team、Control Agent、Codex 三个执行角色，可能持续数小时到数天。

Hermes 的核心价值在于**治理长程任务的状态流转**：
- 当前版本处于哪个阶段（exploration / audit / execution / validation / closeout）
- 哪些前置条件已满足、哪些尚未满足
- 当前阻塞是谁的责任
- 下游角色需要等待什么

没有 Hermes，这些状态信息散落在迭代文档、TASK_LOG、CHANGELOG 和聊天记录中，需要人工拼凑。有了 Hermes，状态是机器可读、可查询、可自动推进的。

### 1.3 Hermes 是 Relay Hub

借鉴二师兄 DAG 工作流中 "Plan -> Compile -> Validate -> Repair -> Materialize" 的流水线思想，Hermes 将 Adarian 现有的角色间交接（handoff）标准化为可追踪的 **Task Relay**。

当前流程中，Control Agent 把迭代文档交给 DS Team 做 Pre-Audit，DS Team 返回 Audit Report，Control Agent 再冻结 Scope 交给 Codex 执行——这些交接点是隐式的，依赖人工记忆和文档约定。

Hermes 把每个交接点建模为 DAG 中的一条边（edge），包含：
- `from_role`：当前工作由谁完成
- `to_role`：下一步工作交给谁
- `deliverable`：需要传递什么产物（Audit Report / Iteration Doc / Code Diff）
- `gate`：什么条件满足才能流转（GO / CONDITIONAL_GO / HOLD）

这与二师兄的 `WorkflowPlanEdge`（from/to/edge_type/condition）完全同构。

### 1.4 Hermes 是 DAG State Manager

二师兄的 `DAGScheduler` 通过拓扑排序确定节点执行顺序，通过 `DAGNode.status`（pending/running/done/failed）追踪运行时状态。

Hermes 直接继承这一设计：每个 TaskOps 任务是一个 Node，节点间的依赖关系构成 Edge。Hermes 维护全局 DAG 状态：
- 哪些节点的前置条件已满足，可以进入执行
- 哪些节点正在执行中（由哪个角色持有）
- 哪些节点已完成（产物路径、验收结果）
- 哪些节点失败（失败原因、是否需要 repair）

关键区别：二师兄的节点由 Agent SDK Session 自动执行，Hermes 的节点由**人类角色或 AI Agent 手动认领并执行**。这意味着 Hermes 的 DAG 管理增加了一个"认领/分配"层，但核心的拓扑排序、状态机、阻塞检测逻辑完全可复用。

### 1.5 Hermes 是 Prompt Factory

二师兄 Layer 5 的七层 prompt 组装是最值得直接迁移的设计之一。每个节点的 `task_prompt.md` 包含：任务描述、上游产物摘要、资源提示、数据读取协议、工具纪律、SCOPE_LINES、输出合约。

Hermes 继承这一能力，为不同类型的 TaskOps 任务生成结构化 prompt：
- **DS Pre-Audit Prompt**：注入源码树事实、迭代文档范围、禁止文件清单、审计输出模板
- **Codex Execution Prompt**：注入允许修改文件清单、禁止文件清单、验收标准、交付说明模板
- **Control Agent Prompt**：注入版本状态、DS 建议、Gate 选项、closeout 判断标准
- **产品侧任务卡**：注入需求描述、验收标准、边界约束

### 1.6 Hermes 是 Evidence Ledger

Adarian 的 workflow_core.md 已经定义了完整的审计事实权威源体系：DS Pre-Audit Report、DS Verify Report、DS Accept Report、TASK_LOG、CHANGELOG。

Hermes 将这些分散的证据统一收集、索引、关联到对应的 task_id / audit_id / attempt_id / acceptance_id，形成一个**不可篡改的证据账本**：
- 每一次 Gate 决策都有完整的证据链支撑
- Closeout 时自动收集所有关联证据
- 历史版本可复盘：当时为什么做了这个决策、依据是什么

### 1.7 Hermes 是 Owner Gate Console

Adarian 的 Closeout Gate 有六种状态：GO / CONDITIONAL_GO / HOLD / FAIL / CLOSEOUT_PASS / CLOSEOUT_PASS_WITH_KNOWN_ISSUES。当前这些 Gate 判断由 Control Agent 和 User/Owner 在聊天中完成。

Hermes 将 Gate 决策形式化为一个 Console：
- 当前 Gate 状态、触发条件、建议选项
- 所有前置证据（Audit Report、Verify Report、Accept Report）一键可查
- Owner 通过结构化选项（而非自然语言）做出 Gate 决策
- 决策结果自动记录到 Evidence Ledger

---

## 二、角色职责边界

| 角色 | 负责 | 不负责 |
|------|------|--------|
| **Hermes** | DAG 状态管理、Task Relay 流转、Prompt 生成、Evidence Ledger 维护、Gate Console 呈现 | 不执行审计、不写代码、不做 Gate 决策、不定义版本范围 |
| **DS API / DS Team** | 执行 Pre-Audit / Verify / Accept、生产审计事实、返回结构化审计报告 | 不做版本方向决策、不替 Control Agent 做最终 Gate、不扩大架构 |
| **ChatGPT / Control Agent** | 版本定位与治理、编写迭代文档、冻结 Scope、采纳/不采纳 DS 建议、最终 closeout 判断 | 不落盘代码、不执行测试、不把 Gate 判断交给 DS |
| **Codex** | 按迭代文档执行代码修改、运行自检级测试、回传 attempt report | 不自行决定范围、不更新 closeout、不越界设计 |
| **Product-side Agent** | 提供产品需求、验收标准、边界约束 | 不干预技术实现方案、不参与代码审计 |
| **Owner** | 最终方向判断与审批权、重大 Gate 决策 | 不直接执行、不承担测试流水线 |

Hermes 与每个角色的交互协议：

```
Hermes → DS Team：  发送 Pre-Audit Prompt → 接收 Audit Report → 更新 Evidence Ledger
Hermes → Codex：     发送 Execution Prompt → 接收 Attempt Report → 更新 DAG 状态
Hermes → Control：  发送 Gate Options → 接收 Gate Decision → 推进 DAG
Hermes → Owner：     发送 Closeout Console → 接收最终 Gate → 记录决策
```

Hermes 自身不持有任何角色的能力，它只是**路由 Task、组装 Context、记录 Evidence**。

---

## 三、可迁移机制分类

### P0：直接迁移（几乎照搬）

| 机制 | 来源 | 迁移理由 |
|------|------|---------|
| **WorkflowPlan / Node / Edge Schema** | 二师兄 Layer 1 | 核心数据结构完全同构。Adarian 的 task/audit/attempt/acceptance 天然对应节点的分层拓扑。`data_dependency` 边类型精确表达"DS Accept 完成 → Codex 才能开始"的依赖。`conditional` 边类型精确表达"仅当涉及 schema 变更时才需要 DS Pre-Audit"的条件依赖。 |
| **Plan → Compile → Validate → Repair 循环** | 二师兄 Layer 2 | Hermes 生成的 TaskOps DAG 同样可能包含结构错误（循环依赖、孤立节点、引用不存在的角色），需要一个轻量级的 repair loop。但 Hermes 的 repair 不调用 LLM 重新生成 DAG，而是向 Control Agent 呈现错误并要求修正——因为 DAG 的"正确性"定义来自版本治理规则，不是 LLM 可以自行修复的。 |
| **Prompt 七层组装** | 二师兄 Layer 5 | 角色层、任务上下文层、范围边界层、输入产物层、执行要求层、证据与验收层、输出 Schema 层——每层直接映射到 Hermes 的不同 prompt 类型。详见第五节。 |
| **Workspace 隔离（input/meta/output/debug/upstream）** | 二师兄 Layer 6 | Hermes 不需要 Docker 容器，但每个 TaskOps 任务同样需要一个隔离的文件系统工作区来存放 prompt、元数据、产出物、上游产物引用。详见第六节。 |
| **Event ID 体系（task_id/audit_id/attempt_id/acceptance_id）** | Adarian workflow_core | 已精确定义，Hermes 直接作为 Evidence Ledger 的索引键。 |
| **SCOPE_LINES 作用域约束** | 二师兄 Layer 5 | 节点级行为边界声明直接适用于 Hermes 的 prompt 组装——每个 TaskOps 任务同样需要精确的行为边界，防止角色越界。 |
| **幂等性执行** | 二师兄 决策 10 | 同一 task_id 的同一 audit_id 多次提交应产生相同结果。Hermes 通过检查 Evidence Ledger 中是否已有对应的 Audit Report 来决定是跳过还是执行。 |

### P1：需裁剪迁移

| 机制 | 来源 | 如何裁剪 |
|------|------|---------|
| **Skill Auto-Binder** | 二师兄 Layer 3 | 二师兄用正则规则引擎将节点 ID 映射到 Skill 注册表。Hermes 没有 Skill 注册表，但有一个**角色路由表**：根据任务类型（audit / execute / verify）和涉及范围，自动路由到对应角色。本质相同：都是确定性映射。裁剪方案：将四层匹配逻辑改为 `task_type → role dispatch`，核心的正则/白名单匹配引擎保留。 |
| **DAG 物化器（Materializer）** | 二师兄 Layer 4 | 二师兄的物化器做拓扑排序 + 搜索注入 + agent_config 构建。Hermes 的物化器做：拓扑排序 + **角色分配** + **Gate 注入** + prompt_config 构建。裁剪方案：保留 `assign_layers_orders()` 拓扑排序逻辑，删除搜索子节点注入，替换为 Gate 节点注入（在关键检查点自动插入 Owner Gate 节点）。 |
| **Docker 容器复用** | 二师兄 Layer 7 | Hermes 不需要 Docker。但工作区隔离的思想保留：每个 TaskOps 任务在文件系统中有独立目录，上游产出以符号链接或副本形式挂载到下游的 `upstream/` 目录。 |
| **Redis Streams 事件管道** | 二师兄 Layer 9 | 如果 Hermes 需要实时 Dashboard，事件管道仍需。但不需要 Redis——可以用简单的文件轮询（每个 TaskOps 任务完成后写一个 state.json），或使用 WebSocket 直连（因为 Hermes 和 Dashboard 在同一进程内）。 |
| **Search 子节点注入** | 二师兄 Layer 4 | 二师兄对标记了 `external_search` 的节点自动插入搜索子节点。Hermes 可以类比：对标记了 `requires_audit` 的任务节点自动插入 DS Pre-Audit 子节点。裁剪方案：保留"条件性子节点注入"机制，替换注入内容。 |
| **DAG 调度 vs 单 Agent 双模式** | 二师兄 决策 7 | Adarian 同样需要双模式：简单修补（单阶段）走简化流程，大版本迭代走完整 DAG。裁剪方案：保留双模式架构，但"单 Agent 模式"不是调用 Agent SDK，而是跳过多角色流转，直接在 Control Agent + Codex 之间压缩执行。 |

### P2：暂时不做

| 机制 | 原因 |
|------|------|
| **Docker 容器** | Adarian 当前不需要沙箱隔离。所有角色在同一個文件系统中协作。将来如果需要为 Codex 提供隔离执行环境，可以再加。 |
| **Redis Streams** | Dashboard 初期不需要实时事件流。文件轮询 + 手动刷新足够。 |
| **Agent SDK Session 执行** | Hermes 不直接执行 Agent Session，它只调度角色间的 Task Relay。节点执行由人类或外部 AI Agent 完成。 |
| **Skill 注册表（35+ Skills）** | Adarian 不是多领域平台，不需要动态 Skill 发现和绑定。角色路由是固定的（DS / Codex / Control / Owner）。 |
| **MCP 工具（Knowledge / Web Search）** | Hermes 本身不访问外部知识库或搜索引擎。如果将来 DS Team 需要 automated fact-checking，可以再加。 |
| **CSV 任务规格（csv_task_spec）** | 二师兄的 agenda_setter 通过 CSV 分发子任务。Hermes 的任务分发通过结构化 prompt 和 TaskOps Edge 完成，不需要 CSV 中间格式。 |
| **前端 ReactFlow DAG 可视化** | 初期用 Markdown 或简单文本展示 DAG 状态即可。Dashboard 可视化是 v0.2 的事。 |
| **Subagent 委派（8 角色 Team Comm）** | Hermes 的核心角色只有 6 个（含自身），不需要复杂的 subagent 通信协议。 |
| **Planner SDK 双通道生成** | Hermes 的 DAG 生成不是 LLM 驱动的——DAG 是从迭代文档的流程描述中确定性编译出来的。除非将来要做"从自然语言需求自动推导 DAG"。 |
| **Election-specific 领域包加载** | Adarian 是单一领域（代码审计与版本治理），不需要多领域包机制。 |

---

## 四、核心 Schema 草案（概念级）

### 4.1 TaskOpsPlan

顶层计划模型，对应二师兄的 `WorkflowPlan`。

| 字段 | 类型 | 用途 | 来源 | 消费者 | 缺失风险 |
|------|------|------|------|--------|---------|
| `plan_id` | `str` | 计划唯一标识，格式 `plan-vX.Y.Z-{topic}` | Control Agent 创建迭代文档时生成 | Hermes、Dashboard、Evidence Ledger | 缺失则无法关联任务到版本 |
| `version` | `str` | 对应 Adarian 版本号，如 `v1.3.0` | Control Agent | 所有角色（版本上下文） | 缺失则 Evidence Ledger 无法按版本索引 |
| `nodes` | `list[TaskOpsNode]` | 任务节点列表 | Control Agent 定义迭代流程 | Hermes（调度）、Dashboard（展示） | 缺失则无任务可执行 |
| `edges` | `list[TaskOpsEdge]` | 任务依赖边列表 | Control Agent 定义依赖关系 | Hermes（拓扑排序、阻塞检测） | 缺失则无法判断执行顺序，但允许空（单一任务） |
| `status` | `PlanStatus` | 枚举：`draft / active / completed / failed / closed` | Hermes（状态机推进） | Dashboard、Control Agent | 缺失则无法判断计划是否还在进行中 |
| `created_at` | `datetime` | 计划创建时间 | Hermes（自动时间戳） | Evidence Ledger | 低风险，可自动补全 |
| `closed_at` | `datetime \| None` | closeout 时间 | Hermes（closeout 时记录） | Evidence Ledger | 低风险 |

### 4.2 TaskOpsNode

任务节点模型，对应二师兄的 `WorkflowPlanNode` + `DAGNode`。

| 字段 | 类型 | 用途 | 来源 | 消费者 | 缺失风险 |
|------|------|------|------|--------|---------|
| `node_id` | `str` | 节点唯一标识，如 `audit-v1.3.0-01`、`attempt-v1.3.0-01` | Control Agent 定义 | Hermes（调度）、Evidence Ledger（索引） | 缺失则所有关联断裂 |
| `task_type` | `TaskType` | 枚举：`pre_audit / verify / accept / codex_attempt / control_review / owner_gate` | Control Agent 定义 | Hermes（Prompt Factory 选择模板） | 缺失则无法生成正确的 prompt |
| `assigned_role` | `Role` | 枚举：`ds_team / codex / control_agent / owner` | Hermes（根据 task_type 自动分配） | Hermes（路由）、Dashboard（责任人展示） | 缺失则任务无人认领 |
| `status` | `NodeStatus` | 枚举：`pending / claimed / in_progress / completed / failed / skipped` | 执行角色更新 | Hermes（拓扑推进）、Dashboard | 缺失则 DAG 调度停滞 |
| `critical` | `bool` | 失败后是否阻塞下游，默认 `true` | Control Agent 定义 | Hermes（阻塞传播） | 缺失则按默认值 true 处理，可能导致过度阻塞 |
| `layer` | `int` | 拓扑层级（由 Hermes 计算） | Hermes（物化时计算） | Hermes（并行调度） | 低风险，物化时自动计算 |
| `input_artifacts` | `list[ArtifactRef]` | 上游产物引用列表 | Hermes（从 edges 推导） | Hermes（prompt 中的上游产物摘要）、执行角色 | 缺失则执行角色缺少上下文 |
| `required_outputs` | `list[OutputSpec]` | 必须产出的文件/报告清单 | Control Agent 定义 | Hermes（校验节点完成度）、执行角色 | 缺失则无法验收节点是否真正完成 |
| `gate` | `GateConfig \| None` | 该节点是否需要 Owner Gate 审批 | Control Agent 定义 | Hermes（Gate Console）、Owner | 缺失则默认无 Gate |

### 4.3 TaskOpsEdge

任务依赖边模型，对应二师兄的 `WorkflowPlanEdge`。

| 字段 | 类型 | 用途 | 来源 | 消费者 | 缺失风险 |
|------|------|------|------|--------|---------|
| `from_node` | `str` | 上游节点 ID | Control Agent 定义 | Hermes（拓扑排序） | 缺失则边无效 |
| `to_node` | `str` | 下游节点 ID | Control Agent 定义 | Hermes（拓扑排序） | 缺失则边无效 |
| `edge_type` | `EdgeType` | 枚举：`blocking / reference / conditional`，默认 `blocking` | Control Agent 定义 | Hermes（阻塞判断） | 缺失则按 blocking 处理 |
| `condition` | `str \| None` | 条件表达式，仅 `conditional` 使用。如 `"involves_schema_change"` | Control Agent 定义 | Hermes（条件评估） | 仅 conditional 边需要 |
| `deliverable` | `ArtifactRef` | 上游完成后需要传递的具体产物，如 `audit_report.md` | Control Agent 定义 | Hermes（验证产物存在） | 缺失则下游角色不清楚需要什么输入 |

### 4.4 TaskReceipt

任务回执，记录一次角色对任务的执行结果。对应二师兄的 `result.json`。

| 字段 | 类型 | 用途 | 来源 | 消费者 | 缺失风险 |
|------|------|------|------|--------|---------|
| `receipt_id` | `str` | 回执唯一标识 | Hermes（自动生成） | Evidence Ledger | 低风险 |
| `node_id` | `str` | 关联的任务节点 | Hermes（自动关联） | Evidence Ledger | 缺失则回执孤立 |
| `role` | `Role` | 执行角色 | 执行角色自报 | Evidence Ledger | 低风险 |
| `status` | `ReceiptStatus` | 枚举：`success / partial_fail / hard_fail / blocked` | 执行角色 | Hermes（状态推进）、Control Agent | 缺失则 Hermes 无法判断下一步 |
| `artifacts` | `list[ArtifactRef]` | 产出物文件路径列表 | 执行角色 | 下游节点（通过 upstream）、Evidence Ledger | 缺失则下游无输入 |
| `warnings` | `list[str]` | 执行过程中的警告/已知问题 | 执行角色 | Control Agent（closeout 判断） | 低风险 |
| `duration_seconds` | `int` | 执行耗时 | Hermes（自动计算） | Dashboard | 低风险 |
| `submitted_at` | `datetime` | 提交时间 | Hermes（自动时间戳） | Evidence Ledger | 低风险 |

### 4.5 EvidenceLedger

证据账本，关联所有审计与验收记录。这是 Hermes 最核心的原创 Schema。

| 字段 | 类型 | 用途 | 来源 | 消费者 | 缺失风险 |
|------|------|------|------|--------|---------|
| `ledger_id` | `str` | 账本条目标识 | Hermes（自动生成） | — | 低风险 |
| `plan_id` | `str` | 关联的 TaskOpsPlan | Hermes（自动关联） | 版本复盘 | 缺失则无法追溯到版本 |
| `event_type` | `EventType` | 枚举：`pre_audit / verify / accept / codex_attempt / owner_gate / closeout` | Hermes（自动分类） | Dashboard（事件时间线） | 缺失则无法分类展示 |
| `event_ids` | `dict` | 关联的 task_id / audit_id / attempt_id / acceptance_id | 各角色（遵循 workflow_core 格式） | 交叉验证 | 缺失则证据链断裂 |
| `source_file` | `str` | 证据源文件路径（如 `audit/phase1大版本审计/v1.3.0-pre-audit-2026-05-15.md`） | Hermes（根据命名规范推断） | 人工复查 | 缺失则无法追溯原始报告 |
| `key_facts` | `dict` | 提取的关键事实摘要（verdict、风险列表、blockers 等） | Hermes（解析报告结构） | Dashboard（快速概览） | 缺失则需手动打开原始报告 |
| `gate_decision` | `GateResult \| None` | 关联的 Gate 决策（如有） | Owner / Control Agent | 版本复盘 | 仅 Gate 事件类型需要 |
| `recorded_at` | `datetime` | 记录时间 | Hermes（自动时间戳） | 时间线展示 | 低风险 |

### 4.6 OwnerGate

Owner 审批关卡，形式化 Adarian workflow_core 的 Closeout Gate。

| 字段 | 类型 | 用途 | 来源 | 消费者 | 缺失风险 |
|------|------|------|------|--------|---------|
| `gate_id` | `str` | Gate 唯一标识 | Hermes（自动生成） | Evidence Ledger | 低风险 |
| `node_id` | `str` | 触发 Gate 的任务节点 | Hermes（自动关联） | 上下文展示 | 缺失则 Gate 无上下文 |
| `gate_type` | `GateType` | 枚举：`scope_freeze / pre_audit / codex_start / closeout` | Control Agent 预设 | Owner（理解决策影响） | 缺失则 Owner 不清楚这是什么决策 |
| `options` | `list[GateOption]` | 可用选项：GO / CONDITIONAL_GO / HOLD / FAIL / CLOSEOUT_PASS / CLOSEOUT_PASS_WITH_KNOWN_ISSUES | Control Agent | Owner（决策输入） | 缺失则无选项可选 |
| `evidence_summary` | `dict` | 决策所需证据摘要（audit verdict、verify result、accept result） | Hermes（自动聚合 EvidenceLedger） | Owner（决策依据） | 缺失则 Owner 决策缺乏依据 |
| `decision` | `GateOption \| None` | Owner 的选择 | Owner | Hermes（推进 DAG） | Gate 未决前为 None |
| `decided_by` | `str` | 决策人标识 | Owner | Evidence Ledger（审计追踪） | 低风险 |
| `decided_at` | `datetime \| None` | 决策时间 | Hermes（自动时间戳） | Evidence Ledger | 低风险 |
| `rationale` | `str \| None` | 决策理由（Owner 备注） | Owner | 版本复盘 | 低风险 |

### 4.7 TaskWorkspace

任务工作区，对应二师兄的 `NodeFilesystemLayout`。

| 字段 | 类型 | 用途 | 来源 | 消费者 | 缺失风险 |
|------|------|------|------|--------|---------|
| `workspace_root` | `str` | 工作区根路径，如 `taskops/workspaces/v1.3.0/audit-01/` | Hermes（自动创建） | 所有角色 | 低风险 |
| `input/` | `dir` | 存放 prompt 文件和上游产物引用 | Hermes（写入 prompt） | 执行角色（读取任务说明） | 缺失则角色不知道做什么 |
| `meta/` | `dir` | 存放 node_context.json、time_context.json | Hermes（写入元数据） | 执行角色（读取上下文） | 缺失则角色缺少关键元数据 |
| `output/` | `dir` | 角色产出物存放目录 | 执行角色（写入报告/代码） | 下游节点（通过 upstream/）、Hermes（验收） | 缺失则交付物无处存放 |
| `debug/` | `dir` | 调试和中间产物 | 执行角色（可选写入） | 问题排查 | 低风险 |
| `upstream/` | `dir` | 上游节点产出物的符号链接/副本 | Hermes（自动挂载） | 执行角色（读取上游产物） | 缺失则角色无法获取上下文 |

---

## 五、Prompt Factory 设计

借鉴二师兄 Layer 5 的七层组装，Hermes 扩展为八层（新增 Owner Gate Policy Layer）。以下是四种核心 prompt 的生成逻辑。

### 5.1 八层结构

```
Layer 1: Role Layer            — 角色身份声明与权威边界
Layer 2: Task Context Layer    — 当前任务在整体 DAG 中的位置
Layer 3: Scope Boundary Layer  — 明确"做什么/不做什么"
Layer 4: Input Artifact Layer  — 上游产物引用与读取指引
Layer 5: Execution Requirement Layer — 具体执行步骤与约束
Layer 6: Evidence & Acceptance Layer — 交付物清单与验收标准
Layer 7: Receipt Schema Layer  — 回执需要填写的结构化字段
Layer 8: Owner Gate Policy Layer — 是否需要 Gate、Gate 选项
```

### 5.2 DS Prompt（Pre-Audit / Verify / Accept）

**生成时机**：当 DAG 推进到标记为 `ds_team` 角色的节点时。

**Layer 1 — Role Layer：**
```
你是 Adarian DS Team 的审计 Agent。你的职责是依据 workflow_core.md 执行审计，
生产结构化审计事实。你不是版本方向决策者，不是最终 Gatekeeper。
```

**Layer 2 — Task Context Layer：**
```
当前版本: v1.3.0
当前阶段: Pre-Audit（在 Scope Freeze 之前）
DAG 位置: 节点 audit-v1.3.0-01，上游无依赖，下游是 control_review
```

**Layer 3 — Scope Boundary Layer：**
```
可以做：
- 检查源码树事实（import 链、依赖关系）
- 对照迭代文档的 allowed/forbidden files
- 列出风险和 blockers
- 输出建议执行范围

不可以做：
- 重新设计版本范围
- 扩大架构
- 把建议项自动升级为 blocker
- 替 Control Agent 做最终 Gate
```

**Layer 4 — Input Artifact Layer：**
```
必须读取以下文件：
- docs/iterations/v1.3.0-xxx.md（迭代文档）
- src/（源码树，通过 git diff 确定变更范围）
- docs/dev_spec.md（开发规范）
- docs/skills/workflow_core.md（流程规则）

上游产物：无（这是 DAG 起始节点）
```

**Layer 5 — Execution Requirement Layer：**
审计执行顺序（参考 workflow_core.md §8 和 §9）：
1. 读取迭代文档，确认版本边界
2. 执行静态检查（py_compile）
3. 执行 forbidden files 检查（git diff + 对照 §6.3）
4. 执行 import 完整性检查
5. 输出审计报告到指定路径
```

**Layer 6 — Evidence & Acceptance Layer：**
```
必须产出的交付物：
- audit/phase1大版本审计/v1.3.0-xxx-2026-05-15.md
  必须包含: audit_id, verdict, source tree facts, risk list, blockers

验收标准：
- verdict 必须是 GO / CONDITIONAL_GO / HOLD / FAIL 之一
- risk list 必须至少包含对 main chain 的分析
- 不得包含"建议进入下一版本"等越权陈述
```

**Layer 7 — Receipt Schema Layer：**
```
完成后填写 TaskReceipt：
{
  "node_id": "audit-v1.3.0-01",
  "role": "ds_team",
  "status": "success | partial_fail | hard_fail",
  "artifacts": ["audit/phase1大版本审计/v1.3.0-xxx-2026-05-15.md"],
  "warnings": [...]
}
```

**Layer 8 — Owner Gate Policy Layer：**
```
本任务不需要 Owner Gate。DS Pre-Audit 完成后自动流转到 Control Agent。
但如果 verdict 为 FAIL，Hermes 将自动 HOLD DAG 并通知 Control Agent。
```

### 5.3 Codex Prompt（Execution Attempt）

**Layer 1 — Role Layer：**
```
你是 Adarian 的 Codex 执行 Agent。你的职责是按迭代文档严格执行代码修改，
运行自检级测试，回传 attempt report。你不得自行扩大范围或越界设计。
```

**Layer 3 — Scope Boundary Layer（重点）：**
```
允许修改的文件：
- src/phase1_entity_extraction.py
- src/phase4/report_agent.py

禁止修改的文件：
- main.py
- config.py
- src/schemas.py
- docs/

操作约束：
- 只改迭代文档声明范围内的内容
- 不做"顺手优化"
- 不重构不相关的代码
- 发现新问题只记录不修复
```

**Layer 5 — Execution Requirement Layer（重点）：**
```
执行顺序：
1. 读取 docs/iterations/v1.3.0-xxx.md §6（详细修改指令）
2. 逐条执行代码修改
3. 运行自检：./.venv/bin/python -m py_compile src/phase1_entity_extraction.py
4. 运行自检：./.venv/bin/python -c "from src.phase1_entity_extraction import ..."
5. 运行 smoke：./.venv/bin/python main.py seeds/test1.txt
6. 生成 attempt report
```

### 5.4 产品侧任务卡（Product-side Task Card）

**生成时机**：当产品侧需要确认功能需求或验收标准时。

**与 DS/Codex Prompt 的核心区别**：
- 不含技术实现细节（py_compile、import 路径等）
- 聚焦用户可感知的功能和验收条件
- 使用产品语言而非工程语言

**Layer 3 — Scope Boundary Layer（产品侧版本）：**
```
功能范围：
- 新增"风险-对策映射表"功能
- 在报告末尾展示每个风险类型对应的信号和应对策略

不在此范围：
- 不改变现有的风险评估算法
- 不新增数据采集流程
- 不修改前端展示（本次仅后端）
```

**Layer 6 — Evidence & Acceptance Layer（产品侧版本）：**
```
验收条件：
1. 运行 test7.txt 后，final_report.md 末尾有"风险-对策映射表"章节
2. 映射表中风险类型至少有 5 种
3. 每种风险至少对应 1 个信号和 1 条对策
4. 映射表内容来自 whitebox_summary.json 的已知风险分类
```

### 5.5 Control Prompt（版本治理）

**Layer 1 — Role Layer：**
```
你是 Adarian 的 Control Agent。你的职责是版本治理：判断当前阶段、
编写迭代文档、冻结版本范围、采纳/不采纳 DS 建议、做最终 closeout。
```

**Layer 8 — Owner Gate Policy Layer（重点）：**
```
当前 Gate 状态：等待 closeout 决策

DS Accept 结果: pass_with_known_issues
Hard Targets: 5/5
Soft Targets: 3/4
Carry-over:
  - R1 前置条件中的"文档漂移标注"尚未完成（不影响本版本功能）
  - profiling 输出中有一个非关键 warning

可用选项：
- CLOSEOUT_PASS: 所有目标满足，允许进入下一版本
- CLOSEOUT_PASS_WITH_KNOWN_ISSUES: 允许但带技术债，carry-over 进入下一版本
- HOLD: 暂停，等待补充证据
- FAIL: 不通过，必须修复后重新验收

请选择一项并提供理由。
```

---

## 六、Workspace Layout 设计

借鉴二师兄 Layer 6 的 `NodeFilesystemLayout`，Hermes 为每个 TaskOps 任务创建独立的文件系统工作区。

### 6.1 完整布局

```
taskops/workspaces/{task_id}/{node_id}/
  input/
    task_prompt.md              ← Hermes 生成的完整 prompt（八层结构）
    upstream_manifest.json      ← 上游产物文件路径索引
  meta/
    node_context.json           ← 节点上下文（task_id, node_id, assigned_role, edges, gate_config）
    time_context.json           ← 时间基准（创建时间、超时时间）
    scope.json                  ← 允许/禁止的操作范围（从迭代文档提取）
  output/
    ...                         ← 执行角色的产出物（Audit Report / Code Diff / Acceptance Report）
  debug/
    execution.log               ← 可选的执行日志
    intermediate/               ← 调试用中间产物
  upstream/                     ← 上游节点 output/ 的符号链接
    {upstream_node_id}/         ← 如 audit-v1.3.0-01/output/
```

### 6.2 各目录解释

| 目录 | 内容 | 为什么需要隔离 |
|------|------|---------------|
| `input/` | Hermes 写入的 prompt 文件和上游引用。执行角色只读。 | 防止角色在执行过程中修改任务定义，确保可追溯"当时收到的任务是什么"。 |
| `meta/` | 节点元数据：上下文、时间、范围边界。 | 将"关于任务的任务"与任务输入分离，方便 Hermes 状态机读取元数据而不污染 input/。 |
| `output/` | 执行角色的交付物。角色可写，Hermes 事后只读。 | 清晰的产出边界，下游通过 upstream/ 引用，Hermes 通过此目录判断节点是否完成。 |
| `debug/` | 调试日志、中间产物。 | 可选写入，不影响 output/ 的验收判断。失败排查时可以查看但不作为正式交付物。 |
| `upstream/` | 上游节点 output/ 的只读引用。 | 防止角色修改上游产物（审计证据不可篡改），同时提供清晰的依赖溯源路径。 |

### 6.3 隔离的必要性

当前 Adarian 的协作模式中，DS Audit Report、Codex Attempt Report、各种迭代文档都散落在 `audit/`、`docs/iterations/`、`outputs/runs/` 等目录中。问题：
1. **版本交叉污染**：v1.2.9 的 Audit Report 和 v1.3.0 的混在同一个 audit/ 目录
2. **上游溯源困难**：Codex 执行时需要知道 DS 的 Audit Report 在哪里，需要人工查找
3. **重复执行风险**：无法判断一个任务是否已经被执行（没有幂等性检查）

按 `task_id/node_id` 隔离后：
1. 每个版本的每个任务有独立目录，永不交叉
2. 上游产物自动通过 `upstream/` 挂载，Codex 不需要手动搜索 DS 的报告
3. Hermes 可以检查 `output/` 是否已有有效产物，实现幂等性

---

## 七、Dashboard 与 Owner Gate 设计

### 7.1 Dashboard 展示内容

**v0.1 最小 Dashboard（Markdown/文本界面）：**

```
==================================================================
  Hermes TaskOps Dashboard — Plan v1.3.0-realtime-risk-signal
  Status: ACTIVE | Created: 2026-05-15 10:30 | Owner Gate: PENDING
==================================================================

DAG Topology:
  [audit-v1.3.0-01] DS Pre-Audit ........... COMPLETED (success)
       |
       v
  [control-v1.3.0-01] Scope Freeze ......... COMPLETED (success)
       |
       v
  [attempt-v1.3.0-01] Codex Execution ..... IN_PROGRESS (Codex)
       |
       v
  [verify-v1.3.0-01] DS Verify ............. PENDING (waiting: attempt-v1.3.0-01)
       |
       v
  [accept-v1.3.0-01] DS Accept ............. PENDING (waiting: verify-v1.3.0-01)
       |
       v
  [gate-v1.3.0-01] OWNER GATE .............. BLOCKED (waiting: accept-v1.3.0-01)

Evidence Ledger (latest):
  [2026-05-15 10:35] Pre-Audit: GO
    → audit/phase1大版本审计/v1.3.0-pre-audit-2026-05-15.md
    Risks: 3 | Blockers: 0
  [2026-05-15 10:40] Scope Freeze: CONFIRMED
    → docs/iterations/v1.3.0-realtime-risk-signal.md

Active Blockers: NONE
Next Action: Wait for Codex to complete attempt-v1.3.0-01
==================================================================
```

### 7.2 Owner Gate 选项

| 选项 | 含义 | 后续行为 | 使用场景 |
|------|------|---------|---------|
| `GO` | 无条件通过 | Hermes 自动推进到下一节点 | 所有条件满足，无已知问题 |
| `CONDITIONAL_GO` | 有条件通过 | 推进但标记条件，Hermes 在条件不满足时自动 HOLD | "可以开始 Codex，但如果 DS Pre-Audit 后续发现新问题必须暂停" |
| `HOLD` | 暂停等待 | DAG 冻结当前节点，等待外部事件 | 等待更多证据、等待外部确认 |
| `FAIL` | 不通过 | 标记当前节点为 failed，触发 repair loop | 审计发现关键问题、验收不达标 |
| `CLOSEOUT_PASS` | 版本关闭（全通过） | 标记 plan status 为 closed，归档所有 workspace | 正常 closeout |
| `CLOSEOUT_PASS_WITH_KNOWN_ISSUES` | 版本关闭（带技术债） | 标记 plan status 为 closed，carry-over 写入下一版本迭代文档 | 软目标未全满足但可接受 |

### 7.3 三种流转决策

**必须停（HOLD/FAIL）：**
- DS Pre-Audit verdict 为 FAIL
- DS Verify 发现 hard_fail（forbidden files 被修改）
- Acceptance hard target 不满足
- Codex 回报无法在允许范围内完成
- 任何角色越权（如 DS 扩大版本范围）→ Hermes 检测到 drift 并自动 HOLD

**可以自动继续：**
- DS Pre-Audit verdict 为 GO 或 CONDITIONAL_GO → 自动流转到 Scope Freeze
- DS Verify 结果为 all_pass → 自动流转到 DS Accept
- DS Accept 结果为 pass → 自动流转到 Closeout Gate
- 非关键节点（critical=false）失败 → 自动跳过，不影响下游

**打回 repair：**
- DS Verify 发现 partial_fail（非 forbidden files 的静态检查失败）→ 自动打回 Codex
- Codex attempt 自检失败 → Codex 自己发起 re-attempt（不占用新的 attempt_id）
- Control Agent 在 closeout 时发现证据不完整 → 打回对应角色补充证据

---

## 八、第一版不做清单（至少 10 条）

1. **不做 Docker 容器隔离**：v0.1 阶段所有角色在同一文件系统中操作，通过 workspace layout 实现逻辑隔离即可。
2. **不做实时 Dashboard（ReactFlow 可视化）**：使用 Markdown/文本输出的 DAG 状态报告，通过文件查看或 CLI 输出即可。
3. **不做 LLM 驱动的 DAG 自动生成**：DAG 由 Control Agent 从迭代文档的流程描述中确定性编译出来，不引入 LLM 生成的不确定性。
4. **不做 Redis Streams 事件管道**：不使用消息队列，Hermes 通过轮询 workspace 目录的状态文件来判断节点进展。
5. **不做 Subagent 委派**：不实现多 Agent 间通信协议。角色间通信通过 workspace 文件交换完成。
6. **不做多版本并行 DAG**：同一时间只运行一个版本的 DAG。多版本并行调度是 v0.2 的事。
7. **不做自动化的证据解析（NLP 提取 Audit Report 关键事实）**：v0.1 阶段，EvidenceLedger 的 key_facts 由各角色在提交 TaskReceipt 时手动填写，不做自动提取。
8. **不做 Web 前端**：所有交互通过 CLI 和文件系统完成。Dashboard 报告以 Markdown 文件形式输出。
9. **不做 Skill Registry / Auto-Binder**：任务到角色的路由是固定的 6 种映射（基于 task_type），不需要动态发现和绑定。
10. **不做 MCP 工具集成（Knowledge / Web Search）**：Hermes 自身不需要外部知识检索能力。
11. **不做 Slack/钉钉/飞书通知**：状态变更不推送外部通知。Owner 通过查看 Dashboard 文件或定期检查获知 Gate 状态。
12. **不做跨项目/多仓库支持**：v0.1 仅支持单个 Adarian 项目仓库。

---

## 九、风险与防漂移策略（至少 8 条）

### 风险 1：Hermes 变成瓶颈（过度中心化）

**描述**：如果每个角色的每一步操作都需要 Hermes 确认和 Gate，Hermes 将成为流程瓶颈。DS Team 做完 Pre-Audit 后无法直接通知 Codex，必须等 Hermes 轮询并推进。

**防漂移策略**：
- Hermes 对非 Gate 节点的推进采用**事件驱动而非轮询**：角色提交 TaskReceipt 时主动触发 Hermes 状态推进（通过 Hermes 提供的 CLI 命令或 API）。
- 对于 `critical=false` 的节点和非 Gate 节点，推进策略设为**自动流转**（auto_advance=true），不等待人工确认。
- 监控指标：统计每个节点的"等待 Hermes"时间占总耗时的比例，目标 < 5%。

### 风险 2：DAG 过度设计（简单任务被复杂化）

**描述**：借鉴 workflow_core.md 的"双模式"设计（DAG 调度 vs 单 Agent）。如果一个版本只需要改一行代码，走完整 DAG（Pre-Audit → Scope Freeze → Codex → Verify → Accept → Closeout）是极大的浪费。

**防漂移策略**：
- 在 `TaskOpsPlan` 中增加 `complexity` 字段（`simple / standard / complex`），由 Control Agent 在创建计划时设定。
- `simple` 模式：压缩为 Control Agent + Codex 的 2 节点 DAG，跳过 DS Pre-Audit 和 DS Accept。
- `standard` 模式：标准六节点 DAG。
- `complex` 模式：在 critical 节点后插入额外的 Owner Gate 节点。
- 强制规则：Control Agent 必须显式声明复杂度等级，否则默认 `standard`。

### 风险 3：Evidence Ledger 信息过载

**描述**：随着版本迭代，EvidenceLedger 积累大量记录，Owner 在 Gate Console 中面对信息过载导致"一键通过"综合征。

**防漂移策略**：
- Gate Console 中只展示**最近 3 条 Evidence**和**总体摘要**，完整证据链通过链接展开。
- 每个 Gate Option 旁显示**风险指示灯**（绿/黄/红），基于 DS verdict 和 carry-over 数量自动计算。
- 如果 Owner 在一分钟内做出 Gate 决策，Hermes 弹出二次确认："你确定已审阅所有证据？"

### 风险 4：Schema 漂移与 workflow_core.md 不同步

**描述**：Hermes 的 TaskOps Schema（GateOption、TaskType、Role 等枚举）可能与 workflow_core.md 的更新不同步。例如 workflow_core.md 新增一种角色，但 Hermes 的 Role 枚举未更新。

**防漂移策略**：
- Hermes 启动时校验：读取 `docs/skills/workflow_core.md` 的"角色分工"表，与内部 Role 枚举对比，不一致时发出警告并 HOLD。
- Schema 版本号：`TaskOpsPlan.schema_version` 与 workflow_core.md 的 `version` 字段保持同步。
- Git hook：当 workflow_core.md 被修改时，触发 Hermes schema 校验脚本。

### 风险 5：Workspace 膨胀（磁盘占用）

**描述**：每个 task/node 都有独立 workspace，一个版本可能产生 6+ 个 workspace 目录，多个版本积累后磁盘占用快速增长。

**防漂移策略**：
- Closeout 后自动归档：`taskops/workspaces/{task_id}/` → `taskops/archived/{task_id}__{timestamp}/`。
- 归档策略：保留最近 3 个已关闭版本的完整 workspace，更早的版本只保留 Evidence Ledger 索引 + output/ 关键产物。
- 可配置的清理策略：用户可设置 `HERMES_WORKSPACE_MAX_VERSIONS` 环境变量。

### 风险 6：Prompt Factory 的模板维护成本

**描述**：随着 workflow_core.md 规则演进，DS Prompt、Codex Prompt 等模板需要同步更新。如果维护不及时，Hermes 生成的 prompt 可能包含过时的约束。

**防漂移策略**：
- 将 Prompt 模板中的规则性约束（如"DS 不得替 Control Agent 做最终 Gate"）以**引用而非硬编码**的方式注入：模板只写 `{{WORKFLOW_CORE_DS_RULES}}`，实际内容从 workflow_core.md 指定段落动态渲染。
- Prompt 模板版本号：每次修改模板时递增，并在生成的 prompt 末尾打印"本 prompt 基于模板 vX"。
- 定期审计：每个版本 closeout 时，Hermes 对比本版本使用的 prompt 模板与最新 workflow_core.md 的一致性。

### 风险 7：角色越权（DS 或 Codex 绕过 Hermes）

**描述**：DS Team 或 Codex 可能不通过 Hermes 的任务路由，直接手动操作文件并口头通知下游。这会导致 Hermes 的 DAG 状态与实际不一致。

**防漂移策略**：
- Hermes 做**事后一致性校验**而非**事前强制**：每次推进 DAG 时，检查实际文件状态是否与 DAG 预期一致。例如推进到 `verify-v1.3.0-01` 时，检查 `taskops/workspaces/v1.3.0/attempt-v1.3.0-01/output/` 是否存在有效产物。
- 如果发现不一致（如 DS 的口头确认早于 Hermes 记录），Hermes 记录 drift warning 并尝试自动修复状态，但如果无法自动修复则 HOLD 并通知 Control Agent。
- 不在 v0.1 做权限强制——不通过文件锁或 git hook 阻止角色操作。信任但验证。

### 风险 8：Hermes 自身成为单点故障

**描述**：如果 Hermes 进程崩溃或状态文件损坏，所有正在进行的版本 DAG 状态可能丢失。

**防漂移策略**：
- Hermes 的状态文件（`taskops/state/plans.json`）采用**追加写 + 定期快照**模式，崩溃时从最后一个快照恢复。
- 关键状态变更（Gate 决策、Closeout）不仅写入 Hermes 状态文件，同时**同步写入对应的 workspace/meta/ 目录**，形成双写。
- Hermes 启动时执行**状态重建**：扫描所有 `taskops/workspaces/*/` 目录，从现有文件反推 DAG 状态，覆盖状态文件中可能损坏的数据。
- v0.1 不实现热备或分布式部署——单实例运行，通过双写和状态重建保证可恢复性。

### 风险 9：与现有文档体系的重叠与冲突

**描述**：Hermes 引入的 Evidence Ledger、TaskReceipt 可能与会 workflow_core.md 已定义的 TASK_LOG.md、CHANGELOG.md 产生功能重叠——同一个审计事实被记录在两处。

**防漂移策略**：
- **明确权威源层级**（workflow_core.md §5 已定义）：
  - TASK_LOG.md 和 CHANGELOG.md 仍然是人工可读的权威记录。
  - Hermes 的 Evidence Ledger 是机器索引和快捷查询层，**不替代** TASK_LOG.md。
- EvidenceLedger 的每个 entry 必须包含 `source_file` 字段指回 TASK_LOG.md 或 Audit Report 中的原始记录。
- 如果 TASK_LOG.md 和 EvidenceLedger 对同一事件的记录不一致，以 TASK_LOG.md 为准（Human-written authority over machine-parsed），Hermes 记录差异并标记为 `needs_reconciliation`。

---

## 十、总结

Hermes / TaskOps Hub v0.1 的核心设计哲学是：**用二师兄 DAG 工作流的工程化机制，替换 Adarian 当前隐式的、依赖人工记忆的角色协作流程**。

迁移策略的核心判断：
- **照搬结构，替换内容**：Plan/Node/Edge Schema、Repair Loop、Prompt Assembly、Workspace Layout ——这些是工程骨架，直接迁移。
- **保留边界，简化机制**：去掉 Docker、Redis、LLM DAG 生成等重型依赖，保留最小可用的文件系统和 CLI 交互。
- **对齐现有规范**：Gate 选项、Event ID、角色分工必须与 workflow_core.md v3.0 精确对齐，Hermes 不创造新规则，只工程化现有规则。

v0.1 的目标不是做一个全自动平台，而是做一个**状态可查询、交接可追溯、决策有记录**的任务治理中台。这是 Adarian 从"文档驱动"走向"系统治理"的第一步。
