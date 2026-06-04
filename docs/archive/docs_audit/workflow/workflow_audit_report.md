# Workflow Audit Report

## 0. Audit Scope

本报告审计对象不是业务代码，而是当前正在使用或刚引入的多 agent 开发工作流本身。

审计时间基线：
- 当前主流程定义：`2026-04-07` 之后的 Codex + MiniMax 固定主从流程
- 新控制层设计：`2026-04-14` 建立的 control plane MVP

本报告聚焦三个问题：
- 当前 workflow 是否内部一致
- 当前 workflow 是否适合接入外部 orchestration / control workflow
- 当前版本治理与 rollback 能力是否足以支撑迁移

本轮新增审计关注点：
- 下一轮 workflow 是否满足“可被审查、可被解释”
- 当前 git 仓库管理是否足以支撑“每次版本迭代后顺利回滚到上一版本”

### 0.1 Audit Method

本报告不是纯主观 retrospective，而是基于已核实 artifact 的结构审计。

已直接核实的关键文件：

| Artifact | 状态 | 审计用途 | 核实结论 |
| --- | --- | --- | --- |
| `docs/skills/workflow_core.md` | 存在 | 主流程权威声明、角色、闭环、验收机制 | 确认存在，且明确声明自己是主流程 SSOT |
| `docs/skills/main_agent_delivery.md` | 存在 | Codex 行为约束 | 确认存在，强调 Review-before-code |
| `CLAUDE.md` | 存在 | 历史/系统级开发规范 | 确认存在，且其流程定义与 `workflow_core.md` 不完全同构 |
| `docs/iterations/TASK_LOG.md` | 存在 | 实际任务记录与验收留痕 | 确认存在，可见真实任务与阻塞记录 |
| `docs/iterations/CHANGELOG.md` | 存在 | 版本变更留痕 | 确认存在 |
| `docs/iterations/v1.1.21.md` | 存在 | 当前进行中 iteration 示例 | 确认存在，状态为进行中 |
| `docs/superpowers/specs/2026-04-14-workflow-transformation-design.md` | 存在 | control plane 原始设计基准 | 确认存在 |
| `control/state.json` | 存在 | control plane 运行态 | 确认存在，且已落地为 baseline-aware 变体 |
| `control/inbox.md` | 存在 | control plane 手工反馈入口 | 确认存在 |
| `control/snapshot.md` | 存在 | control plane 决策视图 | 确认存在 |
| `scripts/generate_snapshot.py` | 存在 | control plane 状态压缩脚本 | 确认存在，且实现包含 profiling-specific 硬编码 |
| `scripts/probes/reduced_schema_chain_probe.py` | 存在 | control plane 依赖面 | 确认存在，对 `control/state.json` / `control/inbox.md` 有代码依赖 |
| `scripts/probes/p1a_prompt_probe.py` | 存在 | control plane 依赖面 | 确认存在，对 `control/inbox.md` 有代码依赖 |
| `scripts/probes/p1g_prompt_probe.py` | 存在 | control plane 依赖面 | 确认存在，对 `control/inbox.md` 有代码依赖 |

审计边界说明：
- 本报告已核实主要 artifacts 的存在与关键内容。
- 本报告没有重放全部历史聊天上下文，因此对“每一次 handoff 事件”不做穷尽性重建，只引用已落盘的可见证据。

---

## 1. Current Workflow Inventory

### 1.1 Current Actors

当前 actor 需要按职责拆开看，而不是只按“谁”看。

| Actor / Layer | R | A | C | I |
| --- | --- | --- | --- | --- |
| Human-as-Decider | 任务定义、Review 批准、阶段决策 | iteration 是否推进 / 是否采纳结论 | Codex、MiniMax | 所有层 |
| Human-as-Relay | 人工转发 Codex 与 MiniMax 的消息 | 无正式架构权威，但实际承担消息总线 | Codex、MiniMax | Human-as-Decider |
| Codex | 实现、修复、Pre-Implementation Review、交付说明 | 代码改动正确性 | Human | MiniMax |
| MiniMax | 测试执行、验收记录、文档更新 | 测试结论与文档同步 | Human | Codex |
| Control Plane MVP | 状态摘要生成 | 不拥有正式审批权 | Human | Codex、MiniMax |

补充说明：
- `workflow_core.md` 明确把 MiniMax 定义为“测试与验收”以及文档更新者。
- `CLAUDE.md` 则更强调文档驱动、任务记录、变更记录、自迭代建议。
- 因此 MiniMax 的实际角色不是单一“测试框架执行器”，而是“测试执行 + 验收记录 + 文档维护”的复合角色。

### 1.1.1 MiniMax 实际职责界定

根据已核实文档，MiniMax 相关动作应分成两类：

- 测试执行动作
  - `workflow_core.md` 明确写有 `py -m py_compile src/<modified_file>.py`
  - `workflow_core.md` 明确写有 `py main.py seeds/test1.txt`
- 验收记录动作
  - 更新 `TASK_LOG.md`
  - 更新 `CHANGELOG.md`
  - 更新迭代文档状态

因此本报告后文中“MiniMax 负责测试与验收”不是把它简化为纯测试 runner，而是指：
- 它同时承担测试动作和验收落盘动作
- 这两个动作目前没有被严格拆开建模

### 1.2 Core Artifacts

- 流程规则
  - `docs/skills/workflow_core.md`
  - `docs/skills/main_agent_delivery.md`
  - `docs/skills/iteration_execution_guard.md`
- 项目执行产物
  - `docs/iterations/*.md`
  - `docs/iterations/TASK_LOG.md`
  - `docs/iterations/CHANGELOG.md`
  - `docs/dev_spec.md`
- 流程版本记录
  - `docs/logs/workflow_changelog.md`
- 新控制层
  - `control/state.json`
  - `control/inbox.md`
  - `control/snapshot.md`
  - `scripts/generate_snapshot.py`

### 1.3 Communication Channels

- 用户聊天窗口
- repo 内 markdown 文档
- 本地文件系统
- CLI 测试输出
- 用户人工 context handoff

当前没有稳定的 machine-readable handoff protocol。真正承担协作桥接的是人工转发。

### 1.4 Reconstructed Real Workflow

当前真实 workflow 不是单一路径，而是两层叠加。

#### Layer A: Main Delivery Workflow

1. Human 确认 iteration 目标。
2. MiniMax 准备 iteration 文档与 `TASK_LOG` 初始记录。
3. Codex 读取迭代文档、流程文档、相关代码。
4. Codex 输出 Pre-Implementation Review。
5. Human 审核 Review 并拍板。
6. Codex 执行一轮代码修改并提交交付说明。
7. MiniMax 执行测试与验收。
8. 若失败，MiniMax 输出失败信息，Human 再转发给 Codex。
9. Codex 修复，回到步骤 6。
10. 若通过，MiniMax 更新 `TASK_LOG`、`CHANGELOG`、迭代文档，必要时同步 `dev_spec.md`。

#### Layer B: Control Plane Workflow

1. Human 或 Agent 手动更新 `control/state.json`。
2. Human 或 Agent 手动写 `control/inbox.md`。
3. 手动运行 `scripts/generate_snapshot.py`。
4. 读取 `control/snapshot.md` 作为压缩后的决策视图。

这层 workflow 当前不驱动执行，只提供“状态摘要”和“profiling 决策口径整理”。

### 1.5 Key Observation

当前系统不是“一个 workflow”，而是：
- 一个文档驱动的人工作业闭环
- 外加一个刚落地的手工 control plane

两者并行存在，但尚未形成一致的 authority model。

### 1.6 Observed Conflict Events

以下冲突不是抽象推测，而是已在当前 artifacts 中直接观察到的实例。

#### Event-01: Control Plane 设计规格与实现状态不一致

设计基准：
- `2026-04-14-workflow-transformation-design.md` 规定 `state.json` 默认保留 6 个固定字段：`stage`、`status`、`current_focus`、`progress`、`risks`、`last_updated`
- 若启用 Baseline-Aware Variant，是“在 6 字段之外增加”扩展字段
- 同一文档规定 `status` 为三态：`in_progress / blocked / done`

实际运行态：
- `control/state.json` 不含 `stage`、`progress`、`risks`、`last_updated`
- 使用了 `updated_at` 而不是 `last_updated`
- `status` 实际值为 `baseline_locked_with_reduced_schema_probe_conclusion`

结论：
- 当前 control plane 不是“按设计扩展 6 字段”，而是直接偏离了设计规格
- 这是 concrete implementation drift，不是主观评价

#### Event-02: 主流程 iteration 状态与 control plane 焦点并行存在

可见证据：
- `docs/iterations/v1.1.21.md` 状态仍为 `🚧 进行中`
- 同时 `control/state.json` / `control/snapshot.md` 的当前焦点已经收敛到 profiling 结论与 baseline-only 决策

结论：
- iteration 层与 control plane 层同时对“当前系统正在做什么”发声
- 两者不是自动联动关系
- 这构成已观察到的多源状态并存实例

#### Event-03: Control Plane 存在真实代码依赖，不是纯文档层

可见证据：
- `scripts/generate_snapshot.py` 直接读取 `control/state.json` / `control/inbox.md`
- `scripts/probes/reduced_schema_chain_probe.py` 直接读取 `control/state.json` / `control/inbox.md`
- `scripts/probes/p1a_prompt_probe.py` 直接写入 `control/inbox.md`

结论：
- control plane 虽然触发频率低，但不是零依赖
- “移除”不是只删文档，而是要同时处理 probe/script 依赖

---

## 2. Structural Conflict Audit

### 2.1 Control Conflict

存在明显 control authority duplication。

- `workflow_core.md` 声称自己是主流程唯一真源。
- `control/state.json` 又被设计为“状态中枢”。
- `snapshot.md` 在实际使用上开始承担人类决策入口。
- `TASK_LOG.md` 与 iteration 文档仍然记录真实执行进度。

结果不是单中心控制，而是四个控制视角并存：
- 规则中心：`workflow_core.md`
- 执行中心：iteration 文档
- 验收中心：`TASK_LOG.md`
- 决策视图中心：`snapshot.md`

这不是 control plane，这是 competing control surfaces。

已观察到的具体实例：
- `workflow_core.md` 明确声明“唯一主流程定义（Single Source of Truth）”
- `2026-04-14-workflow-transformation-design.md` 又把 `control/state.json` 定义为“状态中枢”
- 当前 `control/snapshot.md` 进一步承担人类决策视图

这说明 authority claim 已经出现在至少两套文档中，而不是单一规则源。

### 2.2 State Conflict

当前存在多源状态冲突，且没有自动一致性保证。

主要状态源包括：
- iteration 文档状态
- `TASK_LOG.md`
- `CHANGELOG.md`
- `control/state.json`
- `control/inbox.md`
- `control/snapshot.md`

其中：
- `control/state.json` 由人工维护
- `inbox.md` 由人工写入
- `snapshot.md` 由脚本生成，但脚本输入仍是人工维护
- `TASK_LOG.md` 由 MiniMax 维护

因此当前系统不存在可验证的 single source of truth。

已观察到的具体实例：
- `v1.1.21.md` 仍处于进行中
- `control/state.json` 已经将焦点切换到 profiling baseline 与 reduced-schema probe 结论
- 两者之间不存在自动 reconciliation 机制

### 2.3 Review Conflict

Review 责任被拆成三段，但 closure rule 不明确。

- Codex 负责实现前架构审查
- MiniMax 负责实现后测试验收
- Human 负责最终批准

问题不在“三段 review”，而在没有统一规则说明：
- 什么条件下 task 算完成
- 谁能关闭 iteration
- 当 Review 结论和控制层状态冲突时谁优先

### 2.4 Artifact Conflict

artifact ownership 与 knowledge ownership 分离。

- Codex 最了解代码变化
- MiniMax 负责更新 `TASK_LOG`、`CHANGELOG`、迭代文档、`dev_spec.md`

这种设计的问题是：
- 文档滞后于代码
- 文档记录依赖人工转发后的二次理解
- 一次漏转发就可能造成代码、文档、验收结论不同步

### 2.5 Version Conflict

workflow version、project version、state version 混在一起，没有统一边界。

- `docs/dev_spec.md` 记录项目演进版本
- `docs/logs/workflow_changelog.md` 记录 workflow 变化
- `control/state.json` 记录当前 profiling 决策状态

但没有任何机制把以下对象绑定成一个版本单元：
- 某版 workflow 规则
- 某版任务文档
- 某次验收结果
- 某个 control snapshot

因此“当前在跑哪一版 workflow”并不严格可回答。

### 2.6 Responsibility Conflict

责任定义表面明确，实际仍有模糊区。

已明确的部分：
- Codex 写码
- MiniMax 测试
- Human 决策

未明确或相互覆盖的部分：
- 谁维护 authoritative state
- 谁负责把测试结果提升为正式状态
- 谁决定某条 inbox 记录何时成为正式决策
- 谁负责冻结 workflow version

### 2.7 Communication Conflict

当前 workflow 仍然高度依赖 manual context handoff，这是一级结构风险。

主要问题：
- handoff 没有 task id / attempt id / decision id
- 被转发的内容不是结构化事件
- agent 间无法确认对方看到的是不是同一版上下文
- control plane 也没有消除 handoff，只是新增一层手工摘要

结论：
- 当前沟通机制不是低效而已，而是不可审计

已观察到的具体实例：
- `workflow_core.md` 明确写的是 “MiniMax反馈 → TASK_LOG.md（用户转发）”
- `main_agent_delivery.md` 也明确写的是 “Codex交付 → 用户转发 → MiniMax测试 → 反馈 → Codex修复”
- `TASK_LOG.md` 虽然记录开始、完成、阻塞项，但没有 `task_id` / `attempt_id` / `review_id`
- 因此从落盘证据无法精确判断某条失败反馈属于哪一轮修复尝试

### 2.8 Control Plane Specific Conflict

昨天引入的 control plane 存在独立结构问题。以下判断以 `2026-04-14-workflow-transformation-design.md` 为原始设计基准，而不是以后验标准倒推。

#### 2.8.1 以原始目标为基准的评估

control plane 原始设计目标是：
- 一眼看清楚当前状态
- 一键生成压缩视图
- 减少复制粘贴和上下文传递成本

不做的事是：
- 不做自动回流
- 不做复杂任务系统
- 不做 agent 路由规则

因此本节不以“是否成为完整 orchestrator”评判其成败，而以这三个原始目标为基准。

#### 2.8.2 对原始目标 1 的评估：一眼看清楚当前状态

部分达成，但实现漂移明显。

达成处：
- `snapshot.md` 的前部确实比散落文档更集中

未达成处：
- 当前 `snapshot.md` 实际包含长附录和完整 baseline 摘要，已明显超出“摘要区一屏可读”的定位
- `state.json` 字段结构偏离设计规格，导致状态语义不稳定

结论：
- 可读性有局部提升
- 但这种提升不足以证明它已成为稳定控制面

#### 2.8.3 对原始目标 2 的评估：一键生成压缩视图

部分达成。

达成处：
- `scripts/generate_snapshot.py` 可生成压缩视图

未达成处：
- 脚本实现包含 profiling-specific 硬编码
- 输出并非通用 workflow 摘要，而是绑定 `v1.2.0_baseline` 的专用视图

结论：
- “一键生成”成立
- 但“压缩视图是否代表当前 workflow 全局状态”不成立

#### 2.8.4 对原始目标 3 的评估：减少复制粘贴和上下文传递成本

未达成。

原因不是它没接管 orchestrator，而是它引入了新的维护链：
- 手工维护 `state.json`
- 手工维护 `inbox.md`
- 手工运行脚本
- 再读取 `snapshot.md`

结合当前主流程仍依赖用户中转，这意味着：
- 复制粘贴并未消失
- 只是新增了一层“先整理再压缩”的中间劳动

#### 2.8.5 它引入了新的状态源

Control plane 试图解决“状态分散”，但方式是再新增一套状态文件：
- `state.json`
- `inbox.md`
- `snapshot.md`

结果不是收敛状态，而是新增同步成本。

#### 2.8.6 它把人类体验建立在二次维护上

当前体验差不是偶然，是结构决定的。

人类若想获得正确 snapshot，必须：
1. 先手动维护 `state.json`
2. 再手动整理 `inbox.md`
3. 再运行脚本
4. 再检查 `snapshot.md`

这条链路要求人类先做额外工作，才能看到状态。它没有降低认知负担，反而把“看状态”变成一项新的维护任务。

#### 2.8.7 它与主流程解耦过度

主流程真正产生状态变化的是：
- iteration 审批
- 代码交付
- 测试验收
- 文档更新

而 control plane 与这些动作没有自动绑定。

因此 control plane 里的状态很容易成为 stale mirror，而不是 live state。

#### 2.8.8 它包含硬编码和场景耦合

`scripts/generate_snapshot.py` 当前明显不是通用控制层脚本，而是绑定 profiling 场景的状态压缩器。

具体表现：
- baseline 文件名被硬编码为 `v1.2.0_baseline`
- 进展、风险、建议下一步大量写死为当前 profiling 语境
- snapshot 不是从事件生成，而是从手工状态和特定 baseline 文件拼接

结论：
- 当前 control plane 不具备 workflow 平台属性
- 它只是一次具体 profiling 决策过程的辅助面板

---

## 3. Failure Surface Audit

### 3.1 Coordination Failure

主要风险：
- 同一任务在 iteration 文档、Review、MiniMax 反馈、control inbox 中被多次重述
- 同一事实可能出现多个版本
- 没有 attempt 级标识，难以区分“当前修复轮次”和“历史失败轮次”
- control plane 可能记录了结论，但主流程文档未同步

直接后果：
- 重复劳动
- 任务丢失
- 错误反馈未被消费
- 决策口径漂移

### 3.2 State Consistency Failure

当前最脆弱的点是状态一致性。

失败面包括：
- `state.json` 已更新，但 `snapshot.md` 未重生成
- `TASK_LOG.md` 已记录通过，但 `state.json` 仍显示 blocked
- `inbox.md` 已采纳，但未提升到 `state.json`
- `snapshot.md` 显示“当前焦点”，但 iteration 已切换

控制层设计文档已经承认“无自动回流”，这意味着 stale state 不是异常，而是默认风险。

### 3.3 Rollback Failure

当前 rollback 机制不成体系。

已有能力：
- 代码层可通过 git 回退
- 部分文档可回看历史

缺失能力：
- 无法回退到某个完整 workflow state
- 无法回退到某个 control plane 决策截面
- 无法把“某次验收结果 + 某次状态快照 + 某个任务文档”作为同一 rollback unit 恢复

如果现在迁移 workflow，失败后最多只能回代码，回不到之前的工作流运行状态。

### 3.4 Governance Failure

治理缺口明确存在：

- 没有 workflow version entry rule
- 没有 workflow freeze rule
- 没有 workflow acceptance standard
- 没有 rollback trigger matrix
- 没有强制的 state reconciliation step
- 没有 control plane retirement rule

其中最后一点很关键：
- 你们昨天建立 control plane，今天已经认为体验差并准备移除
- 这说明 workflow 组件的引入与退役没有治理门槛

---

## 4. Future Workflow Fit Assessment

### 4.1 Type A: Control Console Workflow

#### Fit

中等。

原因：
- 当前已经有 `state.json` / `snapshot.md` 的雏形
- 人类确实需要更压缩的状态视图

#### Migration Cost

低到中。

#### Governance Strength

中等偏低。

如果只是继续维护当前 control plane，治理不会自动变强，因为它仍然依赖手工同步。

#### Rollback Compatibility

中等偏低。

当前 control plane 不是 authoritative event log，只是手工镜像。

#### Observability

中等。

它提升了局部可读性，但没有提升事实可追溯性。

#### Judgment

可作为只读 supervision layer，但不应继续保留当前这版 profiling-specific control plane 作为正式 workflow 组件。

### 4.2 Type B: Orchestrator Workflow

#### Fit

中等偏低。

原因：
- 当前 workflow 还没有稳定事件边界
- 任务 handoff 仍依赖人工

#### Migration Cost

高。

#### Governance Strength

理论上高，当前基础上实际偏低。

#### Rollback Compatibility

低。

#### Observability

如果强接 orchestration，表面上会变强，实质上只是把混乱输入机械化。

#### Judgment

当前不适合直接接 orchestrator。先接只会放大状态漂移。

### 4.3 Type C: Event-Driven Workflow

#### Fit

中等偏高。

原因：
- 当前最大问题正是 handoff 不可审计
- event-driven 模型能正面对齐这个结构缺口

#### Migration Cost

中到高。

#### Governance Strength

高。

#### Rollback Compatibility

高，前提是事件日志成为权威事实源。

#### Observability

高。

#### Judgment

这是推荐的目标形态。不是因为它最省事，而是因为它最符合当前问题的根因。

### 4.4 Type D: Chatroom Workflow

#### Fit

表面高，实质低。

#### Migration Cost

低。

#### Governance Strength

低。

#### Rollback Compatibility

低。

#### Observability

低。

#### Judgment

不建议。自由聊天会进一步放大上下文漂移、责任模糊、状态不可重建的问题。

### 4.5 Comparative Conclusion

推荐排序：

1. Event-Driven Workflow
2. Control Console Workflow
3. Orchestrator Workflow
4. Chatroom Workflow

但实施顺序应为：

1. 先修正 authority model
2. 再最小事件化
3. 再补只读 control console
4. 最后再决定是否引入 orchestrator

### 4.6 Transition Roadmap

以下路线不是完整实施计划，而是把推荐目标从“方向”补到“可执行过渡”。

#### Stage 0: Freeze Current Workflow

前置条件：
- 当前主流程文档可定位
- control plane 已被明确标记为实验层

交付物：
- 冻结版 `workflow_core.md`
- 一份退役说明，声明 control plane 不进入正式基线

验收标准：
- 新增 workflow 规则修改必须显式记入 `workflow_changelog`
- 不再向 `control/` 追加新能力

#### Stage 1: Establish Single Authority Model

前置条件：
- Stage 0 完成

交付物：
- 一份 authority matrix：规则谁说了算、状态谁说了算、验收谁说了算
- 一份 closure rule：task 完成条件、iteration 完成条件

验收标准：
- 任一状态变化都能回答“最终以哪个 artifact 为准”
- `workflow_core.md` 与 `CLAUDE.md` 不再对同一流程给出冲突性定义

#### Stage 2: Minimal Eventization

前置条件：
- authority model 已明确

交付物：
- `task_id`
- `attempt_id`
- `review_id`
- `acceptance_id`
- 最小 handoff record 模板

验收标准：
- 任一失败反馈都能追溯到具体 attempt
- 从 `TASK_LOG` 能区分“当前轮失败”与“历史轮失败”

#### Stage 3: Build Read-Only Console From Authoritative Facts

前置条件：
- 已有最小事件或最小 authoritative state

交付物：
- 新控制台或新摘要页
- 只读生成逻辑，不要求人工额外维护第二份状态

验收标准：
- 摘要是从 authoritative facts 自动生成
- 关闭摘要层不会影响主流程闭环

#### Stage 4: Decide Whether Orchestrator Is Necessary

前置条件：
- Stage 1-3 已稳定运行

交付物：
- 一份 orchestrator necessity review

验收标准：
- 若人工 relay 仍是主要瓶颈，再考虑 orchestrator
- 若只读 console 已足够，则不强行引入 orchestration

### 4.7 Next-Workflow Design Constraints

用户提出的下一轮 workflow 约束应直接纳入设计基线，而不是作为软性建议。

#### Constraint-01: 可被审查

含义：
- 每次 iteration 必须有明确输入、明确变更范围、明确验收标准、明确版本锚点
- 外部审查者不依赖口头背景，也能从 artifacts 重建“为什么改、改了什么、如何验收”

最低落地要求：
- iteration doc
- 对应 commit 或 tag
- 测试记录
- 通过 / 失败结论

#### Constraint-02: 可被解释

含义：
- 每次结构调整都必须能解释其因果链，而不是只给结果
- 每次失败都必须能解释它属于哪一轮尝试、为什么失败、是否已消费反馈

最低落地要求：
- 结构改动说明：原因 / 替代方案 / 为什么选当前方案
- 每轮修复有 attempt 级标识
- 验收失败有可追溯错误来源

---

## 5. Version and Rollback Governance Audit

### 5.1 Version Entry Rule

当前不存在显式 entry rule。

建议最小定义：
- 任一流程角色职责变化
- 任一 handoff 机制变化
- 任一 authoritative artifact 变化
- 任一验收闭环变化

满足以上任一条件，即视为 workflow 新版本。

按这个标准，`2026-04-14` 引入 control plane 已经构成 workflow version increment，但仓库中没有正式完成这次版本治理。

### 5.2 Freeze Rule

当前不存在显式 freeze rule。

建议最小定义：
- 引入新控制层前必须冻结当前主流程文档
- workflow migration 期间不得同时改动任务闭环与状态 authority
- 若新控制层连续一个工作日内出现“维护成本高于读取收益”，必须停止扩散

按这个标准，昨天的 control plane 应被视为一次未冻结条件下发生的实验性引入。

### 5.3 Rollback Unit

当前 rollback unit 不清晰。

建议最小 rollback unit 应包含：
- workflow rule doc version
- iteration doc version
- `TASK_LOG.md` 截面
- `CHANGELOG.md` 截面
- state snapshot 或 event log 截面
- 对应代码提交

当前实际只具备部分代码和部分文档回退能力，不具备完整 workflow rollback capability。

### 5.4 Rollback Trigger

当前没有显式触发器。

建议至少定义以下 trigger：
- 状态源冲突无法在单轮内 reconciled
- 交付闭环被新增层显著拉长
- 人工维护次数高于信息压缩收益
- 新层无法成为事实源，却要求人类持续维护
- workflow 组件上线后 24 小时内即出现退役意图

按这个标准，control plane 已经触发 retirement escalation 条件。

这里需要明确区分：
- rollback trigger / retirement trigger：表示“必须人工介入并决定是否退回或下线”
- rollback execution capability：表示“系统是否真的有能力自动或半自动执行回退”

当前系统的问题是：
- trigger 可以定义
- execution capability 仍然薄弱

因此本报告中“trigger 已触发”的含义是：
- 已触发人工退役/冻结提醒
- 不是系统具备了自动执行 rollback 的能力

### 5.5 Auditability

当前 audit trail 部分可见，但不可完整重建。

可见部分：
- 部分流程规则文档
- iteration 文档
- 测试日志与 changelog
- control plane 文件

不可重建部分：
- agent 间完整输入输出序列
- 用户中转时丢失的上下文
- 某条状态为什么被写入 `state.json`
- 某条 inbox 何时被视为 authoritative

### 5.6 Git Repository Rollback Audit

本节只审计 git 仓库事实，不讨论理想流程。

已核实事实：
- 当前仅有一个本地分支：`master`
- 当前仅有一个 tag：`v1.1.19-profiling-closeout`
- `v1.1.19-profiling-closeout` 与当前 `HEAD` 存在线性祖先关系
- `v1.1.19-profiling-closeout..HEAD` 之间共有 `9` 个提交
- 同一区间 `git diff --stat` 覆盖 `129` 个文件
- 当前工作树存在大量未提交变更：`git status --porcelain=v1` 共 `150` 条记录
- 其中已跟踪变更约 `90` 条，未跟踪文件约 `60` 条

这些事实直接意味着：
- 当前仓库没有把“每次 iteration = 一个干净可回滚版本单元”稳定落地
- 当前仓库没有把“每次版本迭代结束 = 一个正式 tag 或 release anchor”稳定落地
- 当前仓库存在大量生成产物、实验文件、归档文档与源码同时漂浮在工作树中

结论分两层：

#### 5.6.1 Git Theoretical Rollback

理论上可以：
- checkout 到旧 commit
- checkout 到唯一已知 tag `v1.1.19-profiling-closeout`

但这不等于 workflow 级 rollback capability。

#### 5.6.2 Workflow-Grade Rollback

当前不能证明以下命题成立：

> 每一次版本迭代之后，都能顺利回滚到上一版本。

原因不是 git 本身做不到，而是当前仓库状态不满足版本回滚前提：
- 工作树不干净
- 版本锚点不足
- 单个版本区间改动过宽
- 生成产物与源码版本边界不清

因此当前项目只具备“局部代码回退可能性”，不具备“稳定 iteration rollback 能力”。

### 5.7 Operational Recovery Capability

当前恢复能力较弱。

可以做到：
- 回看文档
- 回看代码
- 回看部分 profiling 证据

做不到：
- 恢复到某个稳定 workflow 运行状态
- 恢复到某次流程迁移前的完整控制面
- 自动证明回退后的状态与历史一致

### 5.8 Governance Judgment

版本治理与 rollback 治理当前不满足 workflow migration 前置条件。

---

## 6. Findings Summary

### 6.1 Confirmed Strengths

- 主流程角色已有文档化定义：至少 `workflow_core.md`、`CLAUDE.md`、`TASK_LOG.md` 可用于重建主闭环
- 实现前 Review 与实现后测试已形成最小闭环雏形：`workflow_core.md` 同时定义了 Review gate 与测试 gate
- 团队已经开始把 workflow 本身当成可审计对象，而不是隐形习惯
- 已有一定文档化基础，适合继续收敛，而不是从零搭工作流

### 6.2 Critical Contradictions

- `workflow_core.md` 声称是唯一主流程定义，但实际并非唯一 authority
- control plane 试图解决状态分散，却通过新增状态源进一步放大状态同步问题
- Human 既是决策者又是主要消息总线，这使控制权与转发工作混在一起
- 文档、状态、验收三套系统并存，但没有统一 closure rule

### 6.3 Migration Risks

- 当前直接接 orchestration 会把手工漂移固化为系统漂移
- 当前 control plane 若继续扩展，会持续消耗人工维护成本
- 若不先定义 rollback unit，任何 workflow migration 都是高风险不可逆实验
- 若不先 formalize handoff event，Observability 会停留在“有摘要、无事实”

### 6.4 Governance Gaps

- 缺少 workflow version entry rule
- 缺少 workflow freeze rule
- 缺少 workflow acceptance standard
- 缺少 rollback trigger
- 缺少 authoritative state model
- 缺少 control plane component retirement rule
- 缺少 iteration 级 git release anchor
- 缺少 clean working tree 作为版本收口条件

### 6.5 Control Plane Verdict

对昨天建立的 control plane，本报告结论是：

- 它只部分达成了“压缩视图可读性提升”
- 它未达成“减少复制粘贴和上下文传递成本”
- 它没有成为 authority source
- 它引入了新的手工维护链路
- 它当前更适合作为一次 profiling-specific experiment，而非正式 workflow 层

因此建议：
- 不将其继续升级为正式 workflow 层
- 将其判定为应退役的实验性控制层

---

## 7. Minimal Closing Actions

### P0

- 冻结当前主流程定义，以 `docs/skills/workflow_core.md` 作为唯一流程规则源
- 明确宣布当前 control plane MVP 不进入正式工作流基线
- 为 control plane 制定 retirement decision，并停止继续向其追加功能
- 定义唯一 authoritative running state，不允许 `TASK_LOG` / `state.json` / `snapshot.md` 并列为真相源

### P1

- 为每轮任务引入最小事件字段：`task_id`、`attempt_id`、`review_id`、`acceptance_id`
- 定义 workflow version entry / freeze / rollback rules
- 定义 task closure rule 与 iteration closure rule
- 把“用户中转”从隐式行为提升为显式 workflow event
- 定义 iteration freeze 时的 git 条件：clean tree、tag 或等价 release anchor、最小回滚验证

### P2

- 在 authority model 明确后，再设计新的 control console
- 新控制台应只读优先，不先要求人工额外维护
- 新控制台若存在，必须从 authoritative event/state 自动生成，而不是反过来成为新的手工状态源

---

## 8. Final Decision

### 8.1 Is the current workflow internally consistent?

否。

它具备最小执行闭环，但不具备内部一致的 authority model。

### 8.2 Is it ready for external workflow integration?

否。

当前直接接入外部 orchestration/control workflow 会放大现有冲突，而不是解决冲突。

### 8.3 Which target workflow type should be adopted next?

目标形态应选择 event-driven workflow。

但短期动作不是“立刻迁移”，而是：
- 先冻结
- 先收权
- 先事件化

### 8.4 Is rollback governance strong enough?

否。

当前 rollback 治理不足以支撑 workflow migration。

补充：
- 当前也不足以支撑“每次 iteration 后顺利回到上一版本”的工程承诺。

### 8.5 Project-Level Decision

本项目不应选择“保持现状，仅做轻微修补后直接集成新层”。

建议决策为：
- 冻结当前主流程版本
- 退役昨天引入的 control plane MVP
- 先修正 authority / version / rollback 治理
- 再进入下一轮 workflow model 重构

这是“先 refactor workflow，再谈 integration”，不是“继续叠层”。

---

## Appendix A. Artifact Verification Notes

### A.1 `workflow_core.md`

已核实关键内容：
- 自称“唯一主流程定义（Single Source of Truth）”
- 明确规定 Human / Codex / MiniMax 三方职责
- 明确规定 `MiniMax 运行测试`
- 明确规定 `用户转发`

### A.2 `2026-04-14-workflow-transformation-design.md`

已核实关键内容：
- 原始目标是“看清状态 / 一键压缩 / 减少复制粘贴”
- 明确声明“不做自动回流”
- `state.json` 的设计默认是 6 字段
- Baseline-Aware Variant 是在 6 字段之外增补字段

### A.3 `control/state.json`

已核实关键内容：
- 当前是 baseline-aware 运行态
- 缺少设计稿中的 `stage` / `progress` / `risks` / `last_updated`
- `status` 使用自由文本而非三态

### A.4 `control/snapshot.md`

已核实关键内容：
- 当前确有摘要功能
- 当前也包含长附录和整段 baseline summary
- 因此“可读性提升”与“维护成本高”可以同时成立，但净效益为负

### A.5 `scripts/generate_snapshot.py`

已核实关键内容：
- 直接依赖 `control/state.json` / `control/inbox.md`
- baseline 路径与文件名包含 `v1.2.0_baseline` 硬编码
- 输出内容包含大量 profiling-specific 文案

### A.6 Probe Dependencies

已核实关键内容：
- `scripts/probes/reduced_schema_chain_probe.py` 对 `control/state.json` / `control/inbox.md` 有真实依赖
- `scripts/probes/p1a_prompt_probe.py` 对 `control/inbox.md` 有真实依赖
- `scripts/probes/p1g_prompt_probe.py` 对 `control/inbox.md` 有真实依赖

因此：
- control plane 可退役
- 但退役前仍需同步清理 probe/script 侧依赖

### A.7 Git Rollback Facts

已核实关键内容：
- 当前分支：`master`
- 当前 tag 数量：`1`
- 唯一 tag：`v1.1.19-profiling-closeout`
- 该 tag 是当前 `HEAD` 的祖先
- 该 tag 到 `HEAD`：`9` 个提交
- 该 tag 到 `HEAD`：`129` 个文件改动
- 当前工作树：`150` 条 status 记录
- 其中已跟踪变更约 `90` 条，未跟踪文件约 `60` 条

因此：
- 当前不能把“上一版本”稳定定位为每轮 iteration 的标准回滚目标
