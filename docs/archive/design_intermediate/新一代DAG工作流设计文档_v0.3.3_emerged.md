# workyb 新一代 DAG 工作流设计文档 v0.3.3（emerged）

> 版本：v0.3.3 · emerged  
> 日期：2026-05-29  
> 性质：哲学层 + 技术层的最终融合版  
> 融合来源：  
>   - `new_dag_workflow_design_synthesis_2026-05-26.md`（1055 行，哲学层 + 防漂移 + 17 原则）  
>   - `新一代DAG工作流设计文档_v0.3.2_emerged.md`（技术实现层）  
>   - 四份原始设计文件（v0.3 蓝图 / v0.2 §12 / 能力蓝图 / 归盘分析）  
>   - MiMo Team 4 Agent 并行审查报告（4 P0 + 8 P1 + 6 Gap 全部修复）  
> 审查情况：两份独立审查报告（relay runner 562 行 + 10 Agent 并审 230 行）+ MiMo Team 4 Agent 并行审查（227 行）交叉验证  
> 实战验证：relay runner 真实派发 + DeepSeek thinking-fixer + Xiaomi MiMo 全链路跑通

---

## §0. 一句话定义

不预设大架构，只定义小变化。每个节点只负责一个变化。用运行现场暴露问题，用 Code Reality 防止设计漂移。系统设计不是在抽象中完成的，而是在真实任务压力下长出来的。

---

## §1. 核心原则与设计约束

以下原则来自 2026-05-26 设计合成文档 + 软件工程 SOLID + 敏捷开发方法论，是本次 DAG 工作流所有技术决策的前提。

> **结构说明**：§1.1 的 15 条为设计硬约束；§1.2 的 SOLID 映射为参考（详见附录 A）；§1.3 为敏捷补充原则；§1.4 为节点设计检查清单。

### 1.1 设计原则（15 条，来自实战归盘）

```
1.  系统设计不是凭空抽象出来的，而是在真实任务中长出来的。
2.  不预先设计大系统，先跑最小闭环。
3.  一个 DAG 节点只负责一个变化（Single Responsibility Principle）。
4.  一个代码类只负责一个变化。
5.  Runtime 现场型小 bug，优先现场方 Hermes hotfix。
6.  结构性代码修复交 Codex。
7.  代码现实与架构审查交 DS Team。
8.  最终 closeout 只能由 Owner-Control 判断。
9.  Handoff 是连续工作状态账本，不是会话摘要。
10. 相近会话 handoff 默认增量合并，阶段 closeout 后才允许压缩重置。
11. 不靠 agent 自觉防漂移，要靠机制让正确路径成为阻力最小路径。
12. Code Reality Review 是防任务书幻想替代真实代码的硬门。
13. Skill / MCP / Hook 必须登记，否则能力资源会黑盒漂移。
14. 实验不污染主线，但好实验可以被 promotion 到正式工程资产。
15. 报告、receipt、result、pane_capture 是 evidence；口头 summary 不是 closeout。
```

### 1.2 SOLID 原则映射（参考，详见附录 A）

> 以下为 SOLID 五大原则在 DAG 工作流中的映射参考。其中 Single Responsibility 已作为 §1.1 #3 的硬约束，其余四项为设计指导。

| 原则 | DAG 工作流中的映射 |
|------|-------------------|
| **S — Single Responsibility** | 已作为 §1.1 #3：一个 DAG 节点只负责一个变化。 |
| **O — Open/Closed** | DAG manifest 支持新增节点类型而不修改已有节点。plugin chain 支持新增格式转换器而不改核心路由。 |
| **L — Liskov Substitution** | 任何 executor 应能在同一节点定义下互换而不破坏 DAG。 |
| **I — Interface Segregation** | 节点定义只暴露它需要的字段，不暴露无关的执行器细节。 |
| **D — Dependency Inversion** | 编排层依赖抽象接口（dispatch.yaml / receipt.yaml），不依赖具体的 agent 实现。 |

### 1.3 敏捷开发补充原则

> 以下 4 条为 §1.1 未覆盖的敏捷补充。YAGNI 和 KISS 已由 §1.1 #2 体现，不再重复。

| 原则 | DAG 中的含义 |
|------|-------------|
| **最小可验证版本** | 每个节点必须先跑通最小闭环再扩展。一个节点的第一个版本只写一个文件，不写一整个模块。 |
| **迭代交付** | 每步有 Done 条件。不在当前版本做下个版本的事。 |
| **反馈驱动** | 每个节点执行后必须产出 evidence（receipt / result / log），用于驱动下一步设计。卡住的节点就是最好的设计输入。 |
| **重构纪律** | Code Reality Review 之后才允许重构。不在修复 bug 的同时重构无关代码。 |

### 1.4 节点设计检查清单（每个新节点必须过）

> Karpathy 四约束的详细说明见 §3.3。SOLID 检查项见 §1.2 / 附录 A。

```
□ 这个节点只负责一个变化？（§1.1 #3 — Single Responsibility）
□ 这个节点现在真的有需求要做，还是"以后可能有用"？（YAGNI）
□ 有没有更简单的实现方式？（KISS）
□ 最小可验证版本是什么？能不能先跑一次看看？（MVP）
□ 跑完之后要留什么 evidence？（反馈驱动）
□ 这次改动有没有顺手修了没坏的东西？（Surgical Changes — §3.3）
□ 加入新 provider 是否需要改 DAG 引擎？（Dependency Inversion）
```

---

## §2. 防漂移架构（7 层）

每一层防一种漂移，每种漂移有特定对策机制：

| # | 漂移类型 | 防漂移机制 | 承载物 |
|---|----------|-----------|--------|
| 1 | **上下文漂移** — 跨会话断裂、scope 污染 | Memory Governance + Handoff | memory_registry.yaml / .session_handoff.md / handoff archive |
| 2 | **执行漂移** — 黑盒运行、长程失联 | Relay Runtime | heartbeat.json / heartbeat_history.jsonl / pane_capture.log / result.json |
| 3 | **现场漂移** — 任务现场不可接管 | tmux attach/detach | tmux session / pane capture / progress.yaml |
| 4 | **代码漂移** — 改超出范围、顺手重构 | allowed_files + git boundary | task card / Codex execution contract |
| 5 | **架构漂移** — 设计架构和实现脱节 | Code Reality Review | Mermaid 图 / 设计-实现差异表 |
| 6 | **能力漂移** — agent 能力边界不清 | Skill / MCP / Hook Registry | registry.yaml / 权限白名单 |
| 7 | **验收漂移** — 执行完成误判为版本完成 | DS Team + Owner-Control Gate | Gate 6-8 / receipt / result |

**核心逻辑：** 不靠 agent 自觉防漂移，靠机制让正确路径成为阻力最小路径。

---

## §3. 三层分离架构

### 3.1 架构图

```
┌────────────────────────────────────────────────────────┐
│                   编排层 Orchestration                    │
│  Hermes / PM Runtime                                   │
│  DAG manifest 解析 → 节点依赖排序 → 派发 → 回收         │
│  只关心：做什么、什么顺序、产出契约                        │
│  不关心：用什么模型、API 格式、鉴权方式                    │
│                                                        │
│  → 编排层→执行层：dispatch.yaml                           │
│  → 执行层→编排层：receipt.yaml + result.json              │
├────────────────────────────────────────────────────────┤
│                   执行层 Execution                        │
│  Relay Runner + tmux + Agent CLI                       │
│  会话管理 → 心跳监控 → 弹窗自动处理 → 产出回收            │
│  弹窗策略：ClaudeDialogHandler 5 类自动识别与响应          │
│  安全模型：--allowedTools + 路径白名单 + 命令白名单        │
│  ⛔ 不使用 --allow-dangerously-skip-permissions          │
│                                                        │
│  → 执行层→通讯层：provider_config + plugin chain          │
├────────────────────────────────────────────────────────┤
│                   通讯层 Communication                   │
│  CC Switch / format-fixer chain（plugin 注册表管理）      │
│  路由 + 鉴权 + 格式转换（fallback 才介入）                │
│  plugin 规范：error_trigger → on_error activation        │
│  provider 链：优先级排序 + 健康检测 + fallback 切换        │
│                                                        │
│  → 通讯层→外部：统一 Anthropic Messages API               │
└────────────────────────────────────────────────────────┘
```

### 3.2 三大底座

三层分离架构依赖三大底座提供运行承载：

| 底座 | 管什么 | 核心资产 | 防什么漂移 |
|------|--------|----------|-----------|
| **Memory Governance** | 上下文存储与恢复 | memory_registry.yaml / handoff / archive | 上下文漂移 |
| **Relay Runtime** | 运行现场管理 | tmux / heartbeat / pane / result | 执行漂移 + 现场漂移 |
| **Skill / MCP / Hook Registry** | 能力资源登记 | registry.yaml / 权限白名单 / 路径登记 | 能力漂移 |

**规则**：角色卡必须建立在三大底座之上，不能在底座未就绪时提前做角色卡管理。

### 3.3 节点设计的 Karpathy 四约束

每个 DAG 节点的 prompt 设计必须通过以下 4 条约束（在编节点 prompt 时自动加载 `/karpathy-coding` skill）：

```
1. Think Before Coding — 写代码前列假设，不明白就问
2. Simplicity First    — 函数能解决就别用类，常量能解决就别配配置系统
3. Surgical Changes    — 只动需求要求的行，不修没坏的东西
4. Goal-Driven Execution — 先定义"做成什么样算成功"，再动手
```

---

## §4. 七角色职责与现场优先原则

### 4.1 七角色分工

| 角色 | 层级 | 职责 | 行使者 |
|------|------|------|--------|
| **Owner** | 策略层 | 方向决策、Gate 裁决、终审 | 人 |
| **Control Agent** | 编排层 | 方案设计、边界定义、归盘中控 | Hermes |
| **Orchestrator** | 编排层 | 任务拆解、DAG 编排、派发调度 | PM Runtime |
| **Executor** | 执行层 | 节点执行、代码落盘、测试运行 | Claude Code / Codex |
| **Repair Agent** | 执行层 | AI 修复闭环（≤2 轮重试） | Claude Code / Hermes |
| **Reviewer** | 审查层 | Code Reality Review、架构-实现比对 | DS Team |
| **Infra** | 通讯层 | 会话管理、通讯转换、模型路由 | Relay Runner / CC Switch |

### 4.2 现场优先原则

谁最接近运行现场，谁优先处理现场型故障：

```
Runtime 现场型小 bug → Hermes hotfix（最接近现场）
结构性代码修复      → Codex / Claude Code
架构审查            → DS Team（从真实代码出发）
最终 gate           → Owner-Control
```

**Hermes 适合**：tmux 卡点 / dialog 自动处理 / heartbeat 异常 / 长任务保活 / 现场 smoke
**Codex 适合**：完整实现单元 / 多文件落盘 / 测试补强 / 结构化 patch
**DS Team 适合**：Code Reality Review / 低耦合审查 / 架构比对 / Mermaid 图
**Owner 适合**：判断 closeout / P0 裁决 / 升格判断

---

## §5. 九级 Gate 体系

| Gate | 名称 | 触发时机 | 裁决者 | 通过条件 | 驳回条件 |
|------|------|----------|--------|----------|----------|
| 0 | Context Gate | 上下文收集完 | Control Agent | 目标清晰、边界明确 | 关键信息缺失 |
| 1 | Plan Gate | 方案形成后 | Owner | 方案批准 | 方案驳回（含方向） |
| 2 | DAG Gate | 节点拆解完 | Owner/Control | 粒度合理、依赖正确 | 粒度过粗/过细 |
| 3 | Node Gate | 单节点产出后 | Orchestrator | 产出物存在、校验通过 | 文件缺失/超时 |
| 4 | AI Repair Gate | AI 修复后 | Repair Agent | pass / retry_once | escalate（超轮数） |
| 5 | Stage Gate | 阶段间过渡 | Control Agent | 阶段产物完整 | 质量不达标 |
| 6 | Product Gate | 最终成品后 | Owner | 成品通过 | 成品驳回 |
| 7 | Retro Gate | 归盘完成后 | Control Agent | 资产完整、workspace 已清理 | 资产缺失 |
| 8 | Promotion Gate | 升格判断 | Owner | 升格 A 线 | 归档 B 线 |

**验收防漂移**：报告、receipt、result、pane_capture 是 evidence；口头 summary 不是 closeout。最终 closeout 只能由 Owner-Control 判断。

---

## §6. 目录协议（10 层）

```
{{task_dir}}/
├── 00_task_brief.md              # 任务书（含 Karpathy 四约束检查点）
├── 01_dag_plan/                  # DAG 编排计划
│   ├── dispatch.yaml             # DAG manifest
│   └── receipts/                 # 节点回执
├── 02_probe/ ~ 07_product/       # 执行阶段（每层 input/output/receipt）
├── 08_retrospective/             # 归盘复盘
├── logs/                         # executor 日志
└── runtime/                      # 运行时（12+ 种文件）
```

---

## §6A. 核心模板 Schema（v0.4 模板定稿输入）

> 以下 4 个模板为 v0.4 的直接输入。来源：v0.3 蓝图 §12 + 能力蓝图 §8。

### 6A.1 最小任务书（task_brief）

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
  stage_gate:
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

### 6A.2 AI Fix Issue Packet

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
retry_limit: 2
owner_decision_required: true | false
```

### 6A.3 Node Receipt

```yaml
node_id:
executor:
status: completed | failed | gate_blocked
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

### 6A.4 Lane Context（记忆隔离）

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

---

## §7. 通讯层：fallback-only 插件链

> 本节摘要自 v0.3.2 §6，完整 YAML 配置和验证数据见 v0.3.2。

### 7.1 设计规则

通讯层是一个 filter chain，每个插件默认不激活，仅在检测到特定错误后 fallback 时启用。

```yaml
communication_layer:
  default_route: "cc_switch"

  plugins:
    - id: "thinking-fixer"
      enabled: on_error
      trigger_errors:
        - "content[].thinking must be passed back"
        - "unknown variant `system`"
      activation: fallback
      scope:
        providers: ["deepseek"]
        models: ["v4-pro", "v4-flash"]

  provider_chain:
    - provider: "xiaomi_mimo"
      priority: 1
    - provider: "deepseek"
      priority: 2
      plugins: ["thinking-fixer"]

  model_mapping:
    model_hint_fast: "mimo-v2.5-pro"
    model_hint_balanced: "deepseek-v4-pro"
    model_hint_cheap: "deepseek-v4-flash"
```

### 7.2 正常 vs Fallback

```
正常（MiMo / 无 thinking 问题）：
  Claude → CC Switch → Provider API → 200 ✅（fixer 不介入）

Fallback（DeepSeek 触发 thinking 400）：
  Claude → CC Switch → DeepSeek → 400 🔴
    ↓ 检测 trigger_error → 激活 thinking-fixer
  Claude → CC Switch → thinking-fixer → DeepSeek → 200 ✅
```

### 7.3 Thinking Fixer 生存周期

```
stopped → 首次请求 bypass → 检测到 trigger_error → on-demand 启动
→ 后续请求经过 fixer → 会话结束自动关闭
```

### 7.4 实战验证

| 指标 | 结果 |
|------|------|
| MiMo 直通（无 fixer） | ✅ 零延迟 |
| DeepSeek fixer 介入 | ✅ 6 轮连续 200 |
| 缓存命中率 | ✅ 100% |
| 无 fixer 时 | ❌ 400 thinking error |

---

## §8. DAG Manifest 定义

> 本节摘要自 v0.3.2 §8，完整节点定义见 v0.3.2。

### 8.1 节点定义

```yaml
dag:
  version: "1.0"

  nodes:
    - id: "probe"
      label: "探针验证"
      depends_on: []
      executor_config:
        agent: "claude"
        prompt_file: "dispatch/probe_prompt.md"
        model_hint: "fast"
        fallback:
          on_error: true
          fallback_model_hint: "balanced"
          retry_config:
            max_retries: 2
            retry_delay_sec: 10
      expected_outputs:
        - path: "{{task_dir}}/probe/report.md"
          validation: "exists"
      timeout_sec: 300
      priority: 1
      retry_policy:
        max_attempts: 3
        backoff: "exponential"
      resource_constraints:
        max_input_tokens: 10000
        max_output_tokens: 2000

    - id: "collection"
      label: "全量采集"
      depends_on: ["probe"]
      executor_config:
        agent: "claude"
        prompt_file: "dispatch/collect_prompt.md"
      fan_out:
        strategy: "split_input"
        split_on: "keywords"
      fan_in:
        strategy: "merge"
        merge_method: "dedup_and_concat"
```

### 8.2 编排层 ↔ 执行层接口契约

**编排层→执行层（dispatch.yaml）：**
```yaml
task_id: "probe-task-01"
node_id: "probe"
prompt: "请探针验证数据可采集性"
prompt_file: "dispatch/probe_prompt.md"
model_hint: "fast"
timeout_sec: 300
expected_outputs:
  - "{{task_dir}}/probe/report.md"
```

**执行层→编排层（receipt.yaml）：**
```yaml
node_id: "probe"
status: "completed"
started_at: "2026-05-29T15:00:00+08:00"
completed_at: "2026-05-29T15:05:00+08:00"
outputs:
  - path: "{{task_dir}}/probe/report.md"
    size_bytes: 12345
    validation: "pass"
repair_count: 0
verdict: "pass"
metadata:
  total_tokens: 5000
  model: "deepseek-v4-pro"
```

### 8.3 节点状态机

```
pending → ready → dispatched → running → completed → next node
                                    → failed → retry(≤2次) → running
                                             → hold(等待 Owner)
```

### 8.4 节点 prompt 设计规范

每个 DAG 节点的 prompt 必须通过 Karpathy 四约束检查（详见 §3.3）和 §1.4 节点设计检查清单。

---

## §9. Code Reality Review（审查门）

每个底座级模块在完成 R0/R1 后，必须固定做 Code Reality Review：

| 审查对象 | 触发时机 |
|----------|----------|
| Relay Runtime | ✅ R1 已完成 |
| Memory Governance | R0 完成后 |
| Skill / MCP / Hook Registry | R0 完成后 |
| PM Runtime | R0 完成后 |
| Handoff | R0 完成后 |
| Agent Team DAG | R0 完成后 |

审查方法论：
1. 不从任务书倒推代码——先读真实代码
2. 从真实文件、真实类、真实调用链出发
3. 画 Mermaid 图，再做设计-实现比对
4. 输出差异表 + 粘稠度判断
5. 给 verdict（PASS / PASS_WITH_FINDINGS / HOLD / FAIL）

---

## §10. Handoff 与 Memory 边界

| 层级 | 存什么 | 不存什么 | 更新策略 |
|------|--------|----------|----------|
| **Memory** | 长期偏好、项目惯例、工具环境、稳定原则 | 任务进度、临时决策 | 追加 + 更新，不做全量覆盖 |
| **Handoff** | 当前状态、下一步、未审批事项、blocker、活跃 task id | 完整报告、大段日志、pane_capture | 相近会话增量合并，closeout 后允许压缩重置 |
| **Archive** | 已 closeout 阶段的完整上下文 | 不存当前活跃任务 | 自动归档，保留路径不删除 |

**Context Recovery**：会话启动时自动搜索 handoff 文件和 archive，恢复"昨晚在干嘛"。

---

## §11. 演进路线与 Done 条件

### Phase 1：基础定稿（v0.4，本周）

| 行动 | Done 条件 |
|------|-----------|
| 目录协议定稿（10 层） | 新任务创建即生成完整目录骨架 |
| 核心模板定稿（§6A 四模板） | dispatch / receipt / issue_packet / lane_context 模板可直接使用 |
| 安全策略定稿（DialogHandler） | 无弹窗阻塞 relay runner |

### Phase 2：引擎与底座（v0.5-v0.6）

| 版本 | 行动 | Done 条件 |
|------|------|-----------|
| v0.5 DAG 引擎 | DAG manifest YAML 解析 + 串行派发 | 3 个串行节点端到端跑通 + 循环依赖检测 |
| v0.6 通讯层 | thinking-fixer on_error 模式 + plugin 注册表 | 6 轮回归测试通过 |

### Phase 3：并行与隔离（v0.7-v0.9）

| 版本 | 行动 | Done 条件 |
|------|------|-----------|
| v0.7 执行层 | ClaudeDialogHandler 5 类弹窗 ≥95% | clauderemote fallback 验证 |
| v0.8 Docker DAG POC | 隔离执行舱 | 1 个 L 级任务端到端跑通 |
| v0.9 多 Agent 协作 | fan-out/fan-in + 聚合 | 3 个并行节点 + 部分失败聚合策略验证 |

### Phase 4：正式版（v1.0）

| 行动 | Done 条件 |
|------|-----------|
| B 线全链路验收 | 端到端场景通过 |
| Code Reality Review 全覆盖 | 6 个底座模块审查完成 |

### 关键路径

```
v0.3.3（本文件）→ v0.4 → v0.5 → v0.6 → v0.7 → v0.8 → v0.9 → v1.0
可并行：v0.6（通讯层）↔ v0.7（执行层），需先声明接口契约（§8.2）
总估算：15-24 天（单人全职）
```

---

## §12. 实战验证记录

| 验证项目 | 结果 |
|----------|------|
| relay runner tmux 模式 | ✅ 正常启动/发 prompt/监心跳 |
| thinking-fixer（DeepSeek） | ✅ 6 轮连续 200 |
| Xiaomi MiMo 直通（无 fixer） | ✅ 出完整 227 行审查报告 |
| 4 Agent 并行审查（MiMo Team） | ✅ 4 维度并行产出 |
| Karpathy 四约束 | ✅ 节点 prompt 中应用 Think / Simplicity / Surgical / Goal-Driven |
| 弹窗自动处理 | ⚠️ 待 v0.4 模板定稿解决 |
| Memory Governance | 🔲 待启动 |

---

*本文件为哲学层（5 月 26 日设计合成文档）与技术层（v0.3.2）的最终融合版。15 条设计原则为硬约束，SOLID 与敏捷补充为参考指导，7 层防漂移架构为运行护栏，Karpathy 四约束为节点执行规范。*

---

## 附录 A：SOLID 原则在 DAG 工作流中的完整映射

> 以下为 §1.2 的展开版，供设计审查参考。SOLID 映射不计入核心原则计数。

| 原则 | 原始含义 | DAG 工作流中的映射 | 典型检查场景 |
|------|----------|-------------------|-------------|
| **S — Single Responsibility** | 一个类只应有一个变化原因 | 一个 DAG 节点只负责一个变化。Code Reality Review 检查每个类/函数是否承担多个变化原因。 | 节点是否混合了采集和清洗？ |
| **O — Open/Closed** | 对扩展开放，对修改关闭 | DAG manifest 支持新增节点类型而不修改已有节点。plugin chain 支持新增格式转换器而不改核心路由。通讯层允许新增 provider 而不改执行层。 | 新增 provider 是否需要改 DAG 引擎？ |
| **L — Liskov Substitution** | 子类型必须可替换其基类型 | 任何 executor（Claude Code / Codex / Hermes）应能在同一节点定义下互换而不破坏 DAG。修复 Agent 和原 Executor 应遵守相同的 message / output / receipt 契约。 | 换一个 executor 是否需要改 dispatch.yaml？ |
| **I — Interface Segregation** | 不应强迫依赖它不使用的方法 | 节点定义只暴露它需要的字段（prompt_file / expected_outputs / timeout），不暴露无关的执行器细节。executor 只看到 dispatch.yaml，不看到其它节点的内部状态。 | 节点 YAML 是否有从未使用的字段？ |
| **D — Dependency Inversion** | 依赖抽象而非具体实现 | 编排层依赖抽象接口（dispatch.yaml / receipt.yaml / result.json），不依赖具体的 agent 实现。通讯层依赖 plugin 接口定义，不依赖具体 provider。 | 换模型是否需要改编排层代码？ |
