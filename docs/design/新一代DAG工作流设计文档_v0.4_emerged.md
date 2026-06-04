# workyb 新一代 DAG 工作流设计文档 v0.4（emerged）

> **版本**：v0.4 · 定稿  
> **日期**：2026-05-29  
> **性质**：v0.3.3 模板升级 + 协议落地 + 安全策略定稿  
> **来源**：v0.3.3 §6A / v0.3 蓝图 §12 / 能力蓝图 §3§9 / v0.3.2 §5§8  
> **定位**：将 v0.3.3 设计中的模板从骨架升级为带类型标注和完整示例的 schema，将 Handoff / Context Recovery / fan-in / 安全策略等协议从草案定稿为可执行规范

---

## 0. 定义

v0.4 的核心价值是**模板定稿与协议落地**——将 v0.3.3 中停留在骨架阶段的 5 个核心模板（task_brief / issue_packet / node_receipt / lane_context / dispatch.yaml）补全为带类型标注、必填/可选标记和完整示例的正式 schema，同时将 Handoff、Context Recovery、fan-in 聚合、安全策略四套协议从设计草案升级为可直接执行的定稿规范，使 DAG 工作流从"可讨论"进入"可跑通"状态。

---

## 1. 设计原则继承

v0.4 完整继承 v0.3.3 的以下设计资产，不在本文档重复全文：

- **15 条设计原则**（v0.3.3 §1.1）：系统从真实任务中长出、不预设大系统、一节点一变化、现场优先 hotfix、结构修复交 Codex、Code Reality Review、closeout 只由 Owner-Control 判断、Handoff 是连续账本、靠机制不靠自觉等
- **7 层防漂移架构**（v0.3.3 §2）：上下文漂移(Memory+Handoff) → 执行漂移(Relay Runtime) → 现场漂移(tmux) → 代码漂移(allowed_files) → 架构漂移(Code Reality Review) → 能力漂移(Skill/MCP/Hook Registry) → 验收漂移(DS Team+Owner Gate)
- **3 层分离架构**（v0.3.3 §3）：编排层 Orchestration / 执行层 Execution / 通讯层 Communication
- **7 角色定义**（v0.3.3 §4）：Owner / Control Agent / Orchestrator / Executor / Repair Agent / Reviewer / Infra
- **9 级 Gate 体系**（v0.3.3 §5）：Context → Plan → DAG → Node → AI Repair → Stage → Product → Retrospective → Promotion
- **Memory / Handoff / Archive 三层边界**（v0.3.3 §10）：Memory 存长期偏好、Handoff 存当前状态、Archive 存已 closeout 阶段
- **Karpathy 4 约束**（v0.3.3 §3.3）：Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution

---

## 2. v0.4 范围与 Done 条件

### 2.1 范围

v0.4 覆盖以下新增内容：

| 模块 | 来源 | 状态 |
|------|------|------|
| 5 个核心模板定稿（A 章） | v0.3.3 §6A 升级 | 定稿 |
| 目录协议定稿（B 章） | v0.3.3 §6 升级 | 定稿 |
| Handoff 协议（C 章） | v0.3.3 §6C 草案 | 定稿 |
| Context Recovery 协议（D 章） | 新增 | 定稿 |
| fan-in 聚合协议（E 章） | 新增 | 定稿 |
| 安全策略定稿（F 章） | v0.3.3 §6F 草案 | 定稿 |
| 推荐 Skill 清单（G 章） | 能力蓝图 §3§9 | 定稿 |
| Repair Agent 规范（H 章） | v0.3.3 §7 草案 | 定稿 |
| Code Reality Review 规范（I 章） | v0.3.3 §8 草案 | 定稿 |

### 2.2 Done 条件

- [x] 5 个模板均有类型标注、必填/可选标记、枚举定义、完整示例
- [x] 目录协议包含 runtime/ 16 文件清单与 logs/ 3 文件清单
- [x] Handoff 协议包含 7 节章节结构、2 种模式、9 项 Writer 补丁方向
- [x] Context Recovery 协议包含 5 步恢复流程、3 级优先级、Fallback 策略
- [x] fan-in 聚合协议包含 5 种策略、3 种部分失败策略、冲突解决流程
- [x] 安全策略包含 4 层安全机制、5 类弹窗处理表、执行上下文白名单
- [x] Skill 清单包含 10 项 Skill 总表及核心流程与关键规则
- [x] Repair Agent 包含触发条件、修复流程、AI 可修复 vs 必须上报边界
- [x] Code Reality Review 包含 5 步方法论、8 项输出物、4 级裁决枚举

---

## 3. 核心模板定稿

> 本章将 v0.3.3 §6A 的 4 个模板升级为完整 schema，新增类型标注、必填/可选标记、完整示例。新增 dispatch.yaml 模板（来自 v0.3.2 §8.2）。

### 3.1 最小任务书（task_brief）

**格式说明**：YAML frontmatter 格式，存储于 `{{task_dir}}/00_task_brief.md`。YAML frontmatter 块以 `---` 包裹，后接 Markdown 正文描述任务目标与约束。

**字段定义：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | 是 | 任务唯一标识，格式 `task-YYYYMMDD-NNN` |
| `lane` | enum(`A`\|`B`\|`tooling`\|`coursework`\|`experiment`) | 是 | 工作线标识 |
| `project_id` | string | 是 | 所属项目标识 |
| `task_type` | enum(`coursework`\|`demo`\|`pipeline`\|`validation`\|`experiment`) | 是 | 任务类型 |
| `owner_goal` | string | 是 | Owner 的原始目标描述 |
| `deliverables` | list[string] | 是 | 预期交付物清单 |
| `deadline` | string | 否 | 截止时间，ISO 8601 格式或自然语言 |
| `completion_target` | enum(`draft`\|`demo`\|`usable`\|`polished`\|`archive-ready`) | 是 | 完成度目标 |
| `non_goals` | list[string] | 否 | 明确不做的事 |
| `context_status.enough` | boolean | 是 | 上下文是否足够 |
| `context_status.missing_questions` | list[string] | 否 | 上下文不足时待追问的问题 |
| `plan.summary` | string | 否 | 方案摘要 |
| `plan.recommended_path` | string | 否 | 推荐路径 |
| `plan.alternatives` | list[string] | 否 | 备选方案 |
| `plan.owner_approval_required` | boolean | 是 | 是否需要 Owner 审批（默认 true） |
| `dag.nodes` | list[string] | 否 | DAG 节点 ID 列表 |
| `agent_team.required` | boolean | 是 | 是否需要 agent team |
| `agent_team.roles` | list[string] | 否 | 所需角色列表 |
| `quality_gates.*` | enum(`pass`\|`hold`\|`skip`) | 否 | 各级 Gate 状态（9 级） |
| `memory_scope.read` | list[string] | 否 | 允许读取的记忆路径 |
| `memory_scope.write` | list[string] | 否 | 允许写入的记忆路径 |
| `memory_scope.forbidden` | list[string] | 否 | 禁止触碰的记忆路径 |
| `handoff.report_path` | string | 否 | 报告路径 |
| `handoff.receipt_path` | string | 否 | 回执路径 |
| `handoff.retrospective_path` | string | 否 | 归盘路径 |

**完整示例（探针数据可采集性）：**

```yaml
---
task_id: "task-20260529-001"
lane: B
project_id: "adarian-data-viz"
task_type: validation
owner_goal: "探针验证 Adarian 平台公开课程评价数据的可采集性"
deliverables:
  - "probe_report.md — 字段可得性与样本质量评估"
  - "sample_records.csv — 5 条小样本记录"
deadline: "2026-05-30T18:00:00+08:00"
completion_target: demo
non_goals:
  - "不做全量采集"
  - "不做数据清洗"

context_status:
  enough: true
  missing_questions: []

plan:
  summary: "用 MCP fetch 采集 Adarian 公开评价页，判断字段结构与反爬风险"
  recommended_path: "MCP fetch → 字段提取 → 小样本验证 → 报告"
  alternatives:
    - "Selenium 采集（需额外环境配置）"
  owner_approval_required: true

dag:
  nodes: ["probe"]

agent_team:
  required: false
  roles: []

quality_gates:
  context_gate: "pass"
  plan_gate: "pass"
  dag_gate: "pass"
  node_gate: "hold"
  ai_repair_gate: "hold"
  stage_gate: "hold"
  product_gate: "hold"
  retrospective_gate: "hold"
  promotion_gate: "hold"

memory_scope:
  read: ["资产/项目惯例/数据采集规范.md"]
  write: ["资产/B线经验/采集探针lesson.md"]
  forbidden: ["资产/A线/workflow_core/**"]

handoff:
  report_path: ""
  receipt_path: ""
  retrospective_path: ""
---
```

### 3.2 AI 修复问题包（issue_packet）

**字段定义：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `issue_id` | string | 是 | 问题唯一标识，格式 `issue-YYYYMMDD-NNN` |
| `source_node` | string | 是 | 产出问题的节点 ID |
| `reviewer` | string | 是 | 发现问题的审查者角色 |
| `executor_to_fix` | string | 是 | 负责修复的执行器标识 |
| `problem_type` | enum | 是 | 问题分类（见下方枚举） |
| `evidence` | list[string] | 是 | 问题证据路径（日志、截图、错误输出） |
| `expected_fix` | string | 是 | 期望修复结果的描述 |
| `allowed_scope` | list[string] | 否 | 允许修复触碰的文件/目录 |
| `forbidden_scope` | list[string] | 否 | 禁止触碰的文件/目录 |
| `retry_limit` | integer | 是 | 最大重试次数（默认 2） |
| `owner_decision_required` | boolean | 是 | 超过重试次数是否需要 Owner 裁决 |

**`problem_type` 枚举值：**

| 值 | 说明 |
|----|------|
| `file_not_found` | 预期输出文件未生成 |
| `empty_output` | 输出文件存在但内容为空 |
| `format_error` | 输出格式不符合契约（JSON 解析失败、CSV 列错位等） |
| `timeout` | 节点执行超时 |
| `permission_denied` | 权限不足（路径写入、命令执行） |
| `logic_error` | 输出内容逻辑错误（数据不一致、字段缺失） |

**完整示例：**

```yaml
issue_id: "issue-20260529-001"
source_node: "probe"
reviewer: "Orchestrator"
executor_to_fix: "claude-code@relay-01"
problem_type: file_not_found
evidence:
  - "runtime/registry_events.jsonl"
  - "runtime/pane_capture.log"
expected_fix: "在 {{task_dir}}/02_probe/output/ 下生成 report.md"
allowed_scope:
  - "{{task_dir}}/02_probe/**"
forbidden_scope:
  - "{{task_dir}}/03_collection/**"
  - "资产/A线/**"
retry_limit: 2
owner_decision_required: true
```

### 3.3 节点回执（node_receipt）

**字段定义：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `node_id` | string | 是 | 节点标识 |
| `executor` | string | 是 | 执行器标识 |
| `status` | enum | 是 | 执行状态（见下方枚举） |
| `started_at` | string | 否 | 开始时间，ISO 8601 |
| `completed_at` | string | 否 | 完成时间，ISO 8601 |
| `input_files` | list[string] | 否 | 实际使用的输入文件 |
| `output_files` | list[object] | 否 | 输出文件列表（含 path、size_bytes、validation） |
| `actions_taken` | list[string] | 是 | 已执行动作列表 |
| `commands_run` | list[string] | 否 | 已运行的命令列表 |
| `issues_found` | list[string] | 否 | 发现的问题 |
| `issues_fixed` | list[string] | 否 | 已修复的问题 |
| `remaining_issues` | list[string] | 否 | 未修复的问题 |
| `needs_owner_decision` | boolean | 是 | 是否需要 Owner 决策 |
| `next_recommendation` | string | 否 | 下一步建议 |
| `repair_count` | integer | 否 | 已修复轮数 |
| `verdict` | enum(`pass`\|`fail`\|`hold`) | 否 | 验收裁决 |
| `metadata` | object | 否 | 运行元数据（见下方子结构） |

**`status` 枚举值：**

| 值 | 说明 |
|----|------|
| `completed` | 正常完成，产出物通过校验 |
| `failed` | 执行失败（超时、崩溃、产出校验不通过） |
| `gate_blocked` | 被 Gate 驳回，等待修复或 Owner 裁决 |
| `skipped` | 依赖未满足或主动跳过 |
| `timeout` | 执行超时 |

**`metadata` 子结构：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_tokens` | integer | 总 token 消耗 |
| `model` | string | 实际使用的模型名称 |
| `provider` | string | 实际使用的 provider 名称 |
| `runtime_seconds` | integer | 实际运行秒数 |
| `dialog_events` | integer | 弹窗事件次数 |

**完整示例：**

```yaml
node_id: "probe"
executor: "claude-code@relay-01"
status: completed
started_at: "2026-05-29T15:00:00+08:00"
completed_at: "2026-05-29T15:04:32+08:00"
input_files:
  - "{{task_dir}}/02_probe/input/target_urls.txt"
output_files:
  - path: "{{task_dir}}/02_probe/output/report.md"
    size_bytes: 2048
    validation: "pass"
  - path: "{{task_dir}}/02_probe/output/sample_records.csv"
    size_bytes: 512
    validation: "pass"
actions_taken:
  - "MCP fetch 目标页面 3 次"
  - "字段提取与结构化"
  - "小样本 CSV 生成"
commands_run:
  - "python3 scripts/field_extract.py"
issues_found: []
issues_fixed: []
remaining_issues: []
needs_owner_decision: false
next_recommendation: "进入 03_collection 阶段，按关键词分批采集"
repair_count: 0
verdict: pass
metadata:
  total_tokens: 4800
  model: "mimo-v2.5-pro"
  provider: "xiaomi_mimo"
  runtime_seconds: 272
  dialog_events: 0
```

### 3.4 工作线上下文（lane_context）

**字段定义：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `lane_id` | enum | 是 | 工作线标识（见下方枚举） |
| `project_id` | string | 是 | 项目标识 |
| `task_id` | string | 是 | 任务标识 |
| `node_id` | string | 是 | 当前节点标识 |
| `agent_role` | enum(`Owner`\|`Control`\|`Orchestrator`\|`Executor`\|`RepairAgent`\|`Reviewer`\|`Infra`) | 是 | 当前 agent 角色 |
| `native_identity` | string | 是 | agent 原生标识（如 `claude-code`、`hermes`） |
| `project_overlay` | string | 否 | 项目叠加身份（如 `adarian-data-viz`） |
| `memory_read_scope` | list[string] | 否 | 允许读取的记忆路径 glob |
| `memory_write_scope` | list[string] | 否 | 允许写入的记忆路径 glob |
| `forbidden_memory_scope` | list[string] | 否 | 禁止触碰的记忆路径 glob |
| `context_packet_path` | string | 否 | 上下文包文件路径 |
| `evidence_paths` | list[string] | 否 | evidence 文件路径列表 |
| `promotion_policy` | string | 否 | 经验升格策略（`auto_candidate` / `manual_only` / `forbidden`） |

**`lane_id` 枚举说明：**

| 值 | 说明 | 记忆范围 |
|----|------|----------|
| `A` | A 线正式工程资产 | A 线 workflow_core、role card、release 资产 |
| `B` | B 线轻量生产（demo/pipeline/experiment） | B 线 task 目录、B 线经验沉淀 |
| `tooling` | 工具链维护与脚本开发 | 工具链资产、脚本库 |
| `coursework` | 课程作业 | 课程作业专属目录、课程资料 |
| `experiment` | 独立实验（不计入主线） | 实验目录，实验结束后可废弃 |

**记忆填写规则：**

1. `memory_read_scope` 只填当前任务实际需要读取的路径，使用 glob 模式
2. `memory_write_scope` 只填当前任务被授权写入的路径
3. `forbidden_memory_scope` 必须显式列出禁止路径，尤其是其他 lane 的记忆
4. B 线节点默认禁止读写 A 线资产，除非 `promotion_policy` 为 `auto_candidate` 且路径在白名单内
5. 经验升格链：`node lesson → task retrospective → project lesson_candidate → B 线 asset → Owner-Control 审查 → A 线资产`

**示例：**

```yaml
lane_context:
  lane_id: B
  project_id: "adarian-data-viz"
  task_id: "task-20260529-001"
  node_id: "probe"
  agent_role: Executor
  native_identity: "claude-code"
  project_overlay: "adarian-data-viz"
  memory_read_scope:
    - "资产/项目惯例/数据采集规范.md"
    - "资产/B线经验/采集探针lesson.md"
  memory_write_scope:
    - "资产/B线经验/采集探针lesson.md"
  forbidden_memory_scope:
    - "资产/A线/**"
    - "资产/workflow_core/**"
    - "{{other_task_dir}}/**"
  context_packet_path: "{{task_dir}}/runtime/context_packet.yaml"
  evidence_paths:
    - "{{task_dir}}/02_probe/output/report.md"
  promotion_policy: "manual_only"
```

### 3.5 调度派发（dispatch.yaml）

**格式说明**：存储于 `{{task_dir}}/01_dag_plan/dispatch.yaml`，由编排层生成，执行层消费。

**字段定义：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | 是 | 所属任务标识 |
| `node_id` | string | 是 | 当前节点标识 |
| `prompt` | string | 否 | 内联 prompt 文本（与 `prompt_file` 二选一） |
| `prompt_file` | string | 否 | prompt 文件路径（与 `prompt` 二选一） |
| `model_hint` | enum(`fast`\|`balanced`\|`cheap`) | 是 | 模型选择提示，通讯层据此路由 |
| `timeout_sec` | integer | 是 | 节点超时秒数 |
| `expected_outputs` | list[string] | 是 | 预期输出文件路径列表 |
| `lane_context` | object | 否 | 工作线上下文（见 3.4） |

**`model_hint` 说明：**

| 值 | 通讯层映射 | 适用场景 |
|----|-----------|----------|
| `fast` | `mimo-v2.5-pro` | 探针、轻量采集、快速验证 |
| `balanced` | `deepseek-v4-pro` | 一般执行、报告生成 |
| `cheap` | `deepseek-v4-flash` | 大批量低精度任务 |

**完整示例：**

```yaml
task_id: "task-20260529-001"
node_id: "probe"
prompt: "请探针验证 Adarian 平台公开课程评价数据的可采集性"
prompt_file: "dispatch/probe_prompt.md"
model_hint: "fast"
timeout_sec: 300
expected_outputs:
  - "{{task_dir}}/02_probe/output/report.md"
  - "{{task_dir}}/02_probe/output/sample_records.csv"
```

---

## 4. 目录协议定稿

> 本章将 v0.3.3 §6 的目录协议升级为完整规范，包含每个目录的用途、必选/可选文件、runtime/ 16 文件清单、logs/ 3 文件清单、阶段目录标准结构。

### 4.1 目录总览

```
{{task_dir}}/
├── 00_task_brief.md
├── 01_dag_plan/
├── 02_probe/
├── 03_collection/
├── 04_cleaning/
├── 05_samples/
├── 06_final_assets/
├── 07_product/
├── 08_retrospective/
├── logs/
└── runtime/
```

### 4.2 各目录用途与文件清单

| 目录 | 用途 | 必选文件 | 可选文件 |
|------|------|----------|----------|
| `00_task_brief.md` | 任务书：目标、边界、Gate 状态、记忆范围 | 任务书 YAML frontmatter | Markdown 正文 |
| `01_dag_plan/` | DAG 编排计划与全局回执 | `dispatch.yaml` | `receipts/` 子目录 |
| `02_probe/` | 探针阶段：验证数据可采集性、字段可用性 | `input/`、`output/`、`receipt.md` | `dispatch.md` |
| `03_collection/` | 采集阶段：全量或分批数据采集 | `input/`、`output/`、`receipt.md` | `dispatch.md` |
| `04_cleaning/` | 清洗阶段：数据清洗、去重、格式化 | `input/`、`output/`、`receipt.md` | `dispatch.md` |
| `05_samples/` | 样张阶段：样张生成与 Gate 确认 | `input/`、`output/`、`receipt.md` | 按 `<node_id>/` 细分 |
| `06_final_assets/` | 最终资产：图表、PDF、代码产物 | `output/` | `receipts/` |
| `07_product/` | 成品整合：最终交付物组装 | `output/` | `product_receipt.md` |
| `08_retrospective/` | 归盘复盘：经验沉淀与升格候选 | `retrospective.md` | `skill_candidates.md`、`promotion_candidates.md` |
| `logs/` | 执行层日志（见 4.4） | 见 4.4 | -- |
| `runtime/` | 运行时状态（见 4.3） | 见 4.3 | -- |

### 4.3 runtime/ 子目录（16 文件完整清单）

| # | 文件 | 格式 | 说明 |
|---|------|------|------|
| 1 | `heartbeat.json` | JSON | 存活心跳，每 30s 更新，字段：`timestamp`、`seq`、`state`、`node_id` |
| 2 | `heartbeat_history.jsonl` | JSONL | 心跳历史记录，每行一条心跳快照 |
| 3 | `progress.yaml` | YAML | 进度文件（统一格式），字段：`current_node`、`completed_nodes`、`total_nodes`、`percent`、`eta` |
| 4 | `progress.md` | Markdown | 进度文件（legacy 兼容），人类可读格式 |
| 5 | `session.yaml` | YAML | tmux 会话信息，字段：`session_name`、`pane_id`、`pid`、`created_at` |
| 6 | `task_state.yaml` | YAML | 全量运行时状态，字段：`task_id`、`phase`、`active_node`、`gate_states`、`last_updated` |
| 7 | `result.json` | JSON | 最终结果，字段：`task_id`、`verdict`、`outputs`、`summary`、`completed_at` |
| 8 | `pane_capture.log` | 文本 | pane 文本快照，tmux pane 滚动缓冲区内容 |
| 9 | `registry_events.jsonl` | JSONL | 事件审计链，每行含 `event_type`、`timestamp`、`node_id`、`detail`，支持 14 种 `failure_classification` |
| 10 | `failure_classification.yaml` | YAML | 失败分类定义，枚举所有 failure 类型及其描述 |
| 11 | `pre_action_check.yaml` | YAML | 执行前安全检查结果，字段：`check_id`、`allowed`、`reason`、`paths_checked` |
| 12 | `blocker_report.md` | Markdown | 阻塞报告，描述当前阻塞原因与建议解锁方式 |
| 13 | `owner_decision_request.yaml` | YAML | Owner 决策请求，字段：`request_id`、`node_id`、`question`、`options`、`urgency` |
| 14 | `owner_decision_record.yaml` | YAML | Owner 决策记录，字段：`request_id`、`decision`、`reason`、`decided_at` |
| 15 | `abort_report.yaml` | YAML | 异常中止报告，字段：`reason`、`node_id`、`last_state`、`evidence` |
| 16 | `recovery_summary.md` | Markdown | 恢复摘要，从异常中恢复后的状态总结与下一步 |

### 4.4 logs/ 子目录（3 文件）

| 文件 | 格式 | 说明 |
|------|------|------|
| `executor.log` | 文本 | 执行器主日志，记录所有 executor 的 stdout/stderr 输出，含时间戳 |
| `tmux_capture.log` | 文本 | tmux 会话捕获日志，记录 tmux pane 的完整交互历史 |
| `dialog_history.jsonl` | JSONL | 弹窗处理历史，每行含 `timestamp`、`dialog_type`、`action_taken`、`auto_resolved` |

### 4.5 阶段目录标准结构（02~07）

每个阶段目录（02_probe 至 07_product）遵循统一的三件套结构：

```
{{stage_dir}}/
├── input/          # 输入契约
│   └── (上游产物的软链接或拷贝)
├── output/         # 产出物
│   └── (本阶段输出文件)
└── receipt.md      # 执行回执（YAML frontmatter + 可选 Markdown 正文）
```

**input/ 填充规则：** 由编排层在派发前生成，包含上游节点的 output 产物路径（软链接优先，硬拷贝兜底）。

**output/ 填充规则：** 由执行器在执行过程中生成，文件路径必须在 dispatch.yaml 的 `expected_outputs` 中声明，Gate 校验时检查文件是否存在且非空。

**receipt.md 规则：** YAML frontmatter 包含 3.3 node_receipt 的全部必填字段；由执行器在节点完成后自动生成；无 receipt 的节点视为 `failed`。

### 4.6 08_retrospective/ 内容规范

| 文件 | 类型 | 必选 | 说明 |
|------|------|------|------|
| `retrospective.md` | Markdown | 是 | 归盘报告：产物清单、时间线、卡点、修复经验、工作流经验 |
| `skill_candidates.md` | Markdown | 否 | 可复用 skill 候选列表 |
| `promotion_candidates.md` | YAML | 否 | B→A 升格候选列表，每条含 `type`、`description`、`owner_decision` |
| `workflow_lessons.md` | Markdown | 否 | 工作流经验教训 |

### 4.7 目录生成规则

1. 新任务创建时，编排层自动生成完整目录骨架（00~08 + logs + runtime）
2. 阶段目录内的 `input/`、`output/` 子目录必须预先创建（空目录）
3. `receipt.md` 在节点执行完成后由执行器写入
4. `runtime/` 下的文件由执行器自动管理，编排层只读
5. `logs/` 下的文件由执行层自动写入，禁止编排层直接修改
6. 任务 closeout 后，整个 `{{task_dir}}` 保留不删除，归入 archive

---

## 5. 安全策略定稿

### 5.1 安全模型总则

执行层**禁止**使用 `--allow-dangerously-skip-permissions`。采用以下四层安全机制：

| 安全层 | 机制 | 作用 |
|--------|------|------|
| 工具层 | `--allowedTools` | 仅允许声明在白名单中的工具 |
| 路径层 | 路径白名单 | 写路径限 `outputs/` + `runtime/`；读路径限 `task_dir` + 声明资产目录 |
| 命令层 | 命令白名单 | Bash 仅允许 `ls`、`cat`、`head`、`tail`、`python3`、`mkdir -p` |
| 弹窗层 | ClaudeDialogHandler | 五类弹窗自动识别与响应，拒绝未知弹窗 |

### 5.2 五类弹窗处理表（ClaudeDialogHandler）

| 弹窗类型 | 识别依据 | 处理策略 | 安全校验 |
|----------|----------|----------|----------|
| TRUST | "Do you trust" / "Are you sure" | 自动接受 | 无（信任对话框） |
| FILE_CREATION | "Do you want to create" | 匹配 `expected_outputs` 后自动批准 | 路径白名单 + basename 解析 |
| BASH_PERMISSION | Bash 命令安全对话框 | 匹配命令白名单后自动批准 | Shell 注入检测 + 路径校验 |
| PERMISSION | "Do you want to proceed?" / 文件写入 | 检查目标路径 | 路径白名单 + 签名去重 |
| OTHER_CONFIRMATION | 未知弹窗 | **HOLD**（等待 Owner） | 人工介入 |

### 5.3 预授权执行上下文

```yaml
execution_context:
  permissions:
    write_paths:
      - "{{task_dir}}/outputs/*"
      - "{{task_dir}}/runtime/*"
    read_paths:
      - "{{task_dir}}/**"
      - "资产/**"
    bash_commands:
      - "ls"
      - "cat"
      - "head"
      - "tail"
      - "python3"
      - "mkdir -p"
  forbidden:
    dangerous_flags:
      - "--allow-dangerously-skip-permissions"
    bash_patterns:
      - "rm -rf"
      - "sudo"
      - "chmod 777"
      - "curl | bash"
      - "> /dev/null 2>&1"
    write_outside_task: true
    read_outside_declared: true
```

### 5.4 clauderemote 模式

当 tmux 交互出现 ClaudeDialogHandler 无法自动处理的弹窗时，激活 clauderemote 模式：

1. 检测到不可自动处理的对话框（OTHER_CONFIRMATION 类型）
2. 自动执行 `/clauderemote on`
3. 将所有交互选项转为纯字母选择（`[A][B][C]`），避免误触
4. 记录 fallback 日志至 `runtime/registry_events.jsonl`

### 5.5 安全边界检查清单

```yaml
security_boundary_checklist:
  write_paths:
    rule: "仅限 outputs/ 和 runtime/ 子目录"
    validator: ArtifactDetector
    fail_action: "reject_write + log"
  bash_whitelist:
    rule: "仅限 ls / cat / head / tail / python3 / mkdir -p"
    validator: BashPermissionValidator
    fail_action: "reject_command + HOLD"
  read_scope:
    rule: "限 task_dir 及声明资产目录"
    validator: path_prefix_match
    fail_action: "reject_read + log"
  forbidden_ops:
    - "rm -rf"
    - "sudo"
    - "chmod 777"
    - "curl | bash"
    - "写入 task_dir 外部路径"
    - "修改 A 线资产"
    - "访问 .env 或 credentials 文件"
  fail_action: "escalate_to_owner"
```

---

## 6. Handoff 协议

### 6.1 定义

Handoff 是**连续工作状态账本**，不是会话摘要，不是日报。它记录的是"下一个会话启动时需要知道的一切"。

```text
上一轮已有成果 / 决策 / 文件索引 / 未完成问题
+
本轮新增成果 / 新发现 / 新问题 / 新待办 / 新风险
=
下一轮启动所需上下文
```

核心语义是 **accumulate working state**，不是 replace latest summary。

### 6.2 两种模式

| 模式 | 触发条件 | 行为 | 写入方式 |
|------|----------|------|----------|
| **Continuous**（默认） | 相近会话连续推进同一任务 | 增量合并，保留上一轮未完成事项和关键路径 | `handoff-writer.py`（默认 merge/append） |
| **Milestone** | 阶段真正 closeout，Owner 确认 | 旧 handoff 归档，生成压缩 baseline | `handoff-writer.py --replace`（显式） |

**选择逻辑：**

```text
Owner 确认 closeout? ──Yes──→ Milestone Reset Mode
        │                        ↓
        No                   归档旧 handoff
        │                    生成压缩 baseline
        ↓
  Continuous Mode（增量合并）
```

### 6.3 推荐章节结构（7 节）

每个 `.session_handoff.md` 必须包含以下 7 个章节：

```markdown
# Session Handoff — YYYY-MM-DD HH:MM → HH:MM（~XhYm）

## 1. 当前状态
一句话说明当前在做什么、处于哪个 Gate 阶段。

## 2. 本轮完成
- 完成了哪些节点 / Gate
- 产出了哪些 evidence（receipt / result / report 路径）

## 3. 待 Owner 审批
- 等 Owner 拍板的事项清单
- 每项附简要说明和推荐裁决

## 4. 下一步
- 明确优先级排序
- 分工建议（哪个角色执行哪个节点）

## 5. 关键决策记录
- 做了什么决策、为什么做这个、不做那个
- 决策者和决策时间

## 6. 关键文件索引
- 报告、receipt、result、pane_capture、review_report 等路径
- 只存路径，不存内容

## 7. 已知问题 / Blockers
- 下一轮必须知道的问题
- 未修复的 known issues
- 升级路径（自修 / 需 Owner 介入）
```

### 6.4 Handoff Writer R0 补丁方向（9 项）

| # | 补丁项 | 说明 |
|---|--------|------|
| 1 | 增加 `--replace` flag | 显式触发全量替换模式 |
| 2 | 默认 merge/append | 不带 flag 时自动增量合并 |
| 3 | replace 必须显式 | 不能隐式全量覆盖 |
| 4 | 即使 replace 也要 archive | 替换前自动归档旧 handoff |
| 5 | 写完自动调用 `session-end-stamp.py` | 记录会话结束时间戳 |
| 6 | 输出 update summary | 写入后打印本次变更摘要 |
| 7 | 不做过重 `write_file` 拦截 | 不拦截系统写入，只规范 handoff 写入路径 |
| 8 | 不做复杂语义合并 | 合并策略为追加 + 章节对齐，不做 AI 语义去重 |
| 9 | 不做状态管理平台 | handoff 就是文件，不做数据库 / 服务化 |

**设计原则：让正确路径成为阻力最小路径。**

```text
问题：write_file 更顺手，handoff-writer.py 更正确，但正确路径阻力更高。
对策：默认 merge + 自动 archive + 自动 end-stamp，让 handoff-writer 成为最省事的选择。
```

### 6.5 不应存入 Handoff 的内容

| 不存 | 原因 | 正确做法 |
|------|------|----------|
| 完整报告全文 | 手册膨胀，上下文浪费 | 存路径引用 |
| 大段日志 | 噪声淹没信号 | 存日志文件路径 |
| 已解决 bug 的完整过程 | 已关闭，无需延续 | 存 verdict + commit hash |
| 完整审查正文 | DS Team review 已有独立文件 | 存 review_report 路径 |
| 完整 pane_capture | 运行时快照，体积大 | 存 pane_capture.log 路径 |

**规则：引用路径，不替代证据本体。**

### 6.6 文件格式与路径规则

```yaml
文件名: .session_handoff.md
位置:   {{task_dir}}/.session_handoff.md
编码:   UTF-8
格式:   Markdown（YAML frontmatter 可选）

archive 路径:
  目录: {{task_dir}}/08_retrospective/handoff_archive/
  命名: handoff_YYYY-MM-DD_HHMM.md
  规则: --replace 时自动归档，归档后原文件清空重建
```

---

## 7. Context Recovery 协议

### 7.1 触发条件

首轮 LLM 调用自动触发 Context Recovery，无需手动干预。

```text
首轮 LLM 调用
  → 自动触发 Context Recovery Pipeline
  → 注入恢复上下文到 LLM 会话
```

### 7.2 恢复流程（5 步）

```
Step 1: 记录开始时间
  → 写入 ~/.hermes/.session_start
  → 格式: ISO 8601（如 2026-05-29T23:00:00+08:00）

Step 2: 注入时间上下文
  → 当前时间 + 会话已耗时
  → 用于 LLM 判断时间压力和优先级

Step 3: 搜索 handoff 文件
  → 查找 {{task_dir}}/.session_handoff.md
  → 找到则解析 7 章节结构
  → 注入为"会话进度恢复"上下文

Step 4: 搜索 archive 文件
  → 查找 {{task_dir}}/08_retrospective/handoff_archive/ 最近一条
  → 按文件名时间戳倒序取最新
  → 注入为"上一轮会话存档"上下文

Step 5: 注入到 LLM 上下文
  → 按优先级合并注入
  → 标记来源（handoff / archive / memory）
```

### 7.3 恢复优先级

```text
优先级从高到低:

1. handoff（.session_handoff.md）
   → 当前活跃任务的连续状态
   → 最新、最相关

2. archive（handoff_archive/ 最近一条）
   → 上一阶段的完整归档
   → 用于补充 handoff 未覆盖的历史上下文

3. memory（memory_registry.yaml）
   → 长期偏好、项目惯例、工具环境
   → 稳定上下文，不频繁变化
```

**合并规则：**

| 层级 | 发现时 | 未发现时 |
|------|--------|----------|
| handoff | 作为主恢复源注入 | 跳过，降级到 archive |
| archive | 作为补充源注入 | 跳过，降级到 memory |
| memory | 始终注入（稳定的长期上下文） | 正常，不报错 |

### 7.4 Fallback 行为

```yaml
fallback_policy:
  when_handoff_not_found:
    action: "降级到 archive"
    log: "WARN: .session_handoff.md not found, falling back to archive"
    inject_flag: true

  when_archive_not_found:
    action: "仅注入 memory + 时间上下文"
    log: "WARN: no handoff archive found, using memory only"
    inject_flag: true

  when_all_empty:
    action: "冷启动模式"
    log: "INFO: cold start — no handoff, no archive, no memory"
    inject_flag: true  # LLM 知道自己是冷启动，会主动询问关键上下文
```

---

## 8. fan-in 聚合协议

### 8.1 概述

fan-in 聚合发生在多个并行节点（fan-out）完成之后，将多个执行结果合并为单一产出物，传递给下游节点。配置位于 DAG manifest 的 `fan_in` 字段。

### 8.2 聚合策略

| 策略 | 适用场景 | 行为 |
|------|----------|------|
| `merge` | 同类数据合并 | 按字段对齐合并，去重后拼接 |
| `dedup_and_concat` | 采集类任务 | 去重后顺序拼接，保留唯一项 |
| `vote` | 多 Agent 审查 | 多数一致的结果胜出，分歧项标记 |
| `best_of` | 质量择优 | 按评分指标选最优单一结果 |
| `sequential_append` | 日志 / 事件流 | 按完成时间顺序拼接，不去重 |

**DAG manifest 配置示例：**

```yaml
nodes:
  - id: "collection"
    fan_in:
      strategy: "merge"
      merge_method: "dedup_and_concat"
      dedup_key: "url"
      output_format: "fan_in_receipt.yaml"
```

### 8.3 部分失败策略

| 策略 | 行为 | 适用场景 |
|------|------|----------|
| `fail_fast` | 任意节点失败，立即终止聚合，上报 Owner | 关键路径节点，不容忍缺失 |
| `continue` | 跳过失败节点，聚合成功节点的结果，标记缺失 | 采集类任务，部分缺失可接受 |
| `retry_then_continue` | 失败节点自动重试（最多 2 轮），仍失败则 continue | 非关键但高价值节点 |

**配置示例：**

```yaml
fan_in:
  strategy: "merge"
  partial_failure: "continue"
  retry_config:
    max_retries: 2
    retry_delay_sec: 10
  min_success_ratio: 0.6
```

### 8.4 冲突解决

**路径冲突（同名文件）：** 自动重命名 `report.md → report_nodeA.md / report_nodeB.md`，不覆盖、不静默丢弃，在 `fan_in_receipt.yaml` 中记录所有路径。

**内容冲突（同 key 不同值）：** 生成 `conflict_report.md`，记录所有冲突项及来源节点和值，提交 Owner 决策（Gate 3 → `escalate_to_owner`），不做自动覆盖。

**冲突解决流程：**

```
fan-out 节点完成
  → 聚合层扫描产出物
  → 检测路径冲突 → 自动重命名 + 记录
  → 检测内容冲突 → 生成 conflict_report.md + 升级到 Owner
  → 无冲突 → 正常聚合输出
```

### 8.5 聚合输出格式

聚合完成后产出 `fan_in_receipt.yaml`：

```yaml
fan_in_receipt:
  node_id: "collection"
  aggregation_strategy: "merge"
  aggregated_at: "2026-05-29T16:30:00+08:00"

  source_nodes:
    - node_id: "collect_A"
      status: "completed"
      output_path: "{{task_dir}}/03_collection/collect_A/report.md"
    - node_id: "collect_B"
      status: "completed"
      output_path: "{{task_dir}}/03_collection/collect_B/report.md"
    - node_id: "collect_C"
      status: "failed"
      error: "timeout"
      skipped: true

  aggregated_output:
    path: "{{task_dir}}/03_collection/merged_output.md"
    item_count: 142
    dedup_removed: 18

  conflicts:
    path_conflicts: 0
    content_conflicts: 0

  partial_failure:
    total_nodes: 3
    succeeded: 2
    failed: 1
    success_ratio: 0.67
    policy_applied: "continue"
    meets_min_ratio: true

  verdict: "pass"
  needs_owner_decision: false
```

---

## 9. 推荐 Skill 清单

### 9.1 十项 Skill 总表

| # | Skill 名称 | 用途 | 输入 | 输出 | 适用任务层级 |
|---|-----------|------|------|------|-------------|
| 1 | MCP 探针式采集 | 公开网页/平台数据采集探针 | URL / 关键词 / 平台列表 | `probe_report.md`、`sample_records.csv`、`field_availability.md` | 节点级 |
| 2 | 数据集质量闸门 | 采集完成后、清洗前数据可用性检查 | 采集产出文件（CSV/JSON） | `gate_verdict.yaml`（pass/repair_required/fail/downgrade） | 阶段级 |
| 3 | 可视化样张 Gate | 图表/PDF/PPT 样张先出再批量 | 数据集 + 变量组合 + 图表类型 | `sample.png`、`sample_note.md`、`owner_gate_request.md` | 节点级 |
| 4 | 图文解释型 PDF | 课程作业/数据分析图文报告 | 数据 + 图表 + 文字解释 | `final_report.pdf`（图占70%-80%，文字20%-30%） | 任务级 |
| 5 | 章节冻结式论文构建 | 课程论文/复杂报告 | 各章节源文件 | `src_docx/`、`frozen_pdf/`、`manifest.yaml`、`build/final_document.pdf` | 任务级 |
| 6 | DAG Node Dispatch | 编排层给执行 Agent 派发节点任务 | 节点定义 YAML | `dispatch.yaml`（含 node_id/executor/input/output/gate） | 编排级 |
| 7 | Lightweight Receipt | 节点执行完必有轻量回执 | 节点执行结果 | `receipt.yaml`（含 input_files/output_files/actions/issues） | 节点级 |
| 8 | B 线归盘 | 任务结束后沉淀可复用经验 | 全部产物 + 时间线 + 卡点 | `retrospective.md`、`skill_candidates.md`、`promotion_candidates.md` | 任务级 |
| 9 | Lane Context Isolation | 切换工作线时生成隔离 context packet | lane/project/task/node 标识 | `lane_context.yaml`（含 memory_read/write/forbidden scope） | 系统级 |
| 10 | Status-First Reporting | 先报状态再解释，降低延迟感 | 运行时状态 / 完成状态 | 运行中：task_id/elapsed/heartbeat_seq；完成后：exit_code/classification/report_path | 编排级 |

### 9.2 核心流程与关键规则

**Skill 1 — MCP 探针式采集**

```yaml
core_process: "平台探测 → 字段可得性判断 → 小样本采集 → 脚本生成 → 批量采集 → 质量闸门 → 解析修复"
key_rules:
  - "不先写死爬虫"
  - "先用 MCP/search/fetch 做结构探针"
  - "小样本字段稳定后再批量采"
  - "批量后必须跑质量门"
  - "字段大面积异常先修解析器，不急着清洗补救"
output_format: "probe_report.md + sample_records.csv + field_availability.md + source_risk.md"
```

**Skill 2 — 数据集质量闸门**

```yaml
core_process: "关键字段填充率 → 标题/时间/来源链接检查 → 字段错位检测 → 重复率 → 样本状态分布 → 数值可解析率 → 图表支撑力判断"
key_rules:
  - "标题/时间/来源三项任一缺失即 repair_required"
  - "重复率 > 30% 降级"
  - "关键字段填充率 < 70% 即 fail"
output_format: "gate_verdict.yaml (pass | repair_required | fail | downgrade)"
```

**Skill 3 — 可视化样张 Gate**

```yaml
core_process: "先定变量组合 → 再定图表类型 → 出样张 → Gate 五问 → Owner 裁决"
gate_questions:
  - "这张图回答什么问题？"
  - "变量组合是否讲得出故事？"
  - "读者是否一眼看懂主结论？"
  - "是否存在误导或解释成本过高？"
  - "是否值得进入正式图组？"
output_format: "sample.png + sample_note.md + owner_gate_request.md"
```

**Skill 4 — 图文解释型 PDF**

```yaml
core_process: "图表准备 → 文字解释编写 → 版式编排 → 样张 Gate → 批量渲染"
key_rules:
  - "每页一张大图"
  - "图占 70%-80%，文字占 20%-30%"
  - "文字只补充解释，不和图争主角"
output_format: "final_report.pdf"
```

**Skill 5 — 章节冻结式论文构建**

```yaml
core_process: "各章节独立编写 → 单章冻结为 PDF → manifest 声明构建顺序 → 组装 final_document"
key_rules:
  - "源文件保持可编辑（DOCX 是源码）"
  - "章节产物按阶段冻结（PDF 是冻结产物）"
  - "最终交付只做组装（final_document 是 release）"
output_format: "src_docx/ + frozen_pdf/ + manifest.yaml + build/final_document.pdf"
```

**Skill 6 — DAG Node Dispatch**

```yaml
core_process: "解析 DAG manifest → 按依赖排序 → 生成 dispatch.yaml → 派发给 executor"
key_fields:
  - "node_id / node_type / lane / project_id / task_id"
  - "executor / input / allowed_actions / forbidden_actions"
  - "output / receipt_required / owner_gate / memory_scope"
output_format: "dispatch.yaml"
```

**Skill 7 — Lightweight Receipt**

```yaml
core_process: "节点执行完成 → 填写最小字段 → 写入 receipts/ 目录"
key_rules:
  - "每个 B 线节点执行完必须有回执"
  - "口头 summary 不是 receipt"
min_fields: "node_id / executor / input_files / output_files / actions_taken / commands_run / issues / owner_decision_needed / next_recommendation"
output_format: "receipt.yaml"
```

**Skill 8 — B 线归盘**

```yaml
core_process: "产物清单 → 时间线 → 卡点 → 修复经验 → 工作流经验 → Owner 决策模式 → 可复用模板 → 可沉淀 skill → 升格候选"
key_rules:
  - "报告/receipt/result/pane_capture 是 evidence"
  - "口头 summary 不是 closeout"
  - "归盘完成后才允许 handoff 压缩重置"
output_format: "retrospective.md + skill_candidates.md + promotion_candidates.md"
```

**Skill 9 — Lane Context Isolation**

```yaml
core_process: "按 lane/project/task/node 检索上下文 → 只注入必要记忆 → 禁止无关项目污染 → 任务结束后写回 lesson_candidate"
key_rules:
  - "节点不应共享未批准的局部失败/偏好"
  - "项目经验不能自动污染其他课程"
  - "B 线经验不能自动污染 A 线"
  - "可复用经验必须归盘后再升格"
output_format: "lane_context.yaml"
```

**Skill 10 — Status-First Reporting**

```yaml
core_process: "运行中先报状态字段 → 完成后先报结果字段 → 再补解释"
running_fields: "task_id / elapsed / heartbeat_seq / runtime_state / next_check"
completed_fields: "exit_code / classification / report_path / receipt_path / next_action"
key_rules:
  - "状态汇报三元素：进度 + 产出 + 决策"
  - "声音只是体验补丁，不是主动调度核心"
output_format: "inline status block (非独立文件)"
```

---

## 10. Repair Agent 规范

### 10.1 角色定义

| 字段 | 值 |
|------|-----|
| 角色名 | Repair Agent |
| 层级 | 执行层 |
| 职责 | AI 修复闭环：诊断 Issue → 生成修复指令 → 重试裁决 |
| 行使者 | Claude Code / Hermes |
| 对应 Gate | Gate 4 — AI Repair Gate |
| 裁决权 | pass / retry_once / escalate_to_owner |

### 10.2 触发条件

节点产出物未通过预期校验时触发，包括：文件不存在（`expected_outputs` 路径无文件）、文件为空（0 字节）、格式错误（YAML/JSON 解析失败、PDF 损坏）、内容校验失败（字段缺失、结构不完整）。

### 10.3 修复流程

```
节点完成 → 校验产出
  → pass → Gate 3 通过，进入下一节点
  → fail → Repair Agent 诊断 Issue
           → 生成 Issue Packet
           → Executor 重试（retry_once）
           → 再次校验
             → pass → Gate 3 通过
             → fail → 二次重试（累计 ≤ 2 轮）
                      → 仍失败 → escalate_to_owner
```

**三裁决枚举：**

| 裁决 | 含义 | 后续动作 |
|------|------|----------|
| `pass` | 修复成功，产出通过校验 | 进入下一节点 |
| `retry_once` | 需要再试一次（≤ 2 轮上限） | 生成新 Issue Packet，Executor 重试 |
| `escalate_to_owner` | 超出修复轮数或方向错误 | 生成 `owner_decision_request.yaml`，等待人工介入 |

### 10.4 AI 可修复 vs 必须上报边界

**AI 可修复（Repair Agent 自行处理）：**

| # | 问题类型 | 典型表现 |
|---|---------|---------|
| 1 | 字段解析错误 | CSV 列错位、JSON key 拼写错误 |
| 2 | 格式错误 | YAML 缩进错误、Markdown 格式破损 |
| 3 | 路径错误 | 文件名大小写、子目录缺失 |
| 4 | 图表标签错误 | 标签重叠、坐标轴标签缺失 |
| 5 | PDF 溢出 | 文字溢出边界、图片尺寸超限 |
| 6 | 报告结构缺口 | 章节缺失、目录未生成 |
| 7 | Receipt 字段缺失 | 必填字段为空、状态未填写 |
| 8 | 小型代码 bug | 变量名拼写、导入缺失、语法错误 |
| 9 | 样张局部修复 | 字体替换、颜色调整、边距修正 |

**必须上报 Owner（escalate_to_owner）：**

| # | 问题类型 | 典型表现 |
|---|---------|---------|
| 1 | 任务目标变更 | 分析主题方向变化 |
| 2 | 分析方向变更 | 结论方向需反转 |
| 3 | 图表变量组合变更 | 需更换 X/Y 轴变量或新增维度 |
| 4 | 数据源更换 | 需换采集源或更换数据集 |
| 5 | 新增/删除核心产物 | 需加新图或删已有章节 |
| 6 | 扩展权限 | 需访问 task_dir 外部路径或新增 Bash 命令 |
| 7 | 修改 A 线资产 | 触及 `workflow_core/`、`role_card/` 等 |
| 8 | 高风险自动化 | 批量删除、网络请求外发、凭据使用 |

### 10.5 落地计划

```yaml
landing_plan:
  phase: "Phase 2 (v0.5)"
  dependency: "DAG manifest 引擎就绪后"
  done_definition: "一个真实节点的 Repair Loop 端到端跑通"
  done_criteria:
    - "节点产出 fail → 触发 Repair Agent"
    - "Repair Agent 生成 Issue Packet"
    - "Executor 重试 → 产出通过 → Gate 3 pass"
    - "完整记录 retry_count / diagnosis / repair_instruction"
  milestone: "v0.5 + 1 个真实节点修复闭环"
```

### 10.6 Issue Packet 格式参考

```yaml
issue_packet:
  issue_id: ""
  source_node: ""
  reviewer: "repair_agent"
  executor_to_fix: ""
  problem_type: ""
  evidence: ""
  expected_fix: ""
  allowed_scope: []
  forbidden_scope: []
  retry_limit: 2
  owner_decision_required: false
  current_retry: 0
  diagnosis: ""
  repair_instruction: ""
```

---

## 11. Code Reality Review 规范

### 11.1 核心判断

```text
任务书里说已经这样设计
≠
代码里真的这样实现
```

Code Reality Review 不从任务书倒推代码，而是从真实代码出发，防止 AI 工作流中的"文字闭环"——任务卡写得很漂亮，Agent 回传说完成，Owner 看到报告觉得差不多，但真实代码已经变成另一个东西。

### 11.2 审查方法论（五步）

| 步骤 | 动作 | 原则 |
|------|------|------|
| 1 | **读真实代码** | 不从任务书倒推，先读真实文件、真实类、真实函数 |
| 2 | **描述真实系统** | 从真实调用链、真实 runtime artifact flow 出发描述现状 |
| 3 | **画 Mermaid 图** | 用可视化表达真实架构，而非设计中的理想架构 |
| 4 | **与设计比对** | 将 Mermaid 图与设计文档逐模块对比，找出差异 |
| 5 | **输出差异表** | 输出设计-实现差异、代码粘稠度判断、拆分建议 |

### 11.3 必须输出物（8 项）

| # | 输出物 | 说明 |
|---|--------|------|
| 1 | 真实文件清单 | 实际存在于磁盘的文件列表（非设计文档中声明的） |
| 2 | 真实类/函数职责 | 每个类和函数实际承担的职责（非设计文档中描述的） |
| 3 | 真实调用链 | 模块间实际的调用关系和数据流向 |
| 4 | 真实 runtime artifact flow | 运行时实际产出的文件、路径和时序 |
| 5 | Mermaid 图 | 基于真实代码绘制的架构图和调用图 |
| 6 | 设计-实现差异表 | 设计文档声称 vs 代码实际实现的逐项对比 |
| 7 | 代码粘稠度判断 | 低耦合 vs 高粘稠（是否因变化原因未隔离导致改动牵连） |
| 8 | 拆分建议 | 哪些模块需要拆分、哪些只是 R2 backlog |

### 11.4 固定审查目标表

底座级模块完成 R0/R1 后，必须执行 Code Reality Review：

| # | 审查模块 | 触发时机 | 当前状态 |
|---|---------|----------|---------|
| 1 | Relay Runtime | R1 完成后 | **已完成**（verdict: PASS_WITH_FINDINGS） |
| 2 | Memory Governance | R0 完成后 | 待启动 |
| 3 | Skill / MCP / Hook Registry | R0 完成后 | 待启动 |
| 4 | PM Runtime | R0 完成后 | 待启动 |
| 5 | Handoff | R0 完成后 | 待启动 |
| 6 | Agent Team DAG | R0 完成后 | 待启动 |

### 11.5 裁决枚举

| 裁决 | 含义 | 后续动作 |
|------|------|----------|
| **PASS** | 设计与实现一致，无显著差异 | 进入下一阶段 |
| **PASS_WITH_FINDINGS** | 主体一致，存在需记录的发现 | 记录 findings，进入 R1.1 backlog |
| **HOLD** | 存在需要补充或修正的问题 | 暂停推进，修复后重新审查 |
| **FAIL** | 设计与实现严重脱节 | 回退，重新实现后再次审查 |

**已有审查参考**：Relay Runtime R1 的 Code Reality Review 裁决为 `PASS_WITH_FINDINGS`，findings 包括 `clauderemote` 状态记录不一致、`dialog_handling` 字段可能为空、`ArtifactDetector` 职责偏重待 R2 拆分等（详见 v0.3.3 附录 / synthesis doc section 8.3）。

---

## 12. 演进路线

### 12.1 v0.4 Done 标记

| 模块 | 状态 | Done 证据 |
|------|------|-----------|
| 核心模板定稿（5 个 schema） | **已完成** | 本文档第 3 章 |
| 目录协议定稿 | **已完成** | 本文档第 4 章 |
| Handoff 协议定稿 | **已完成** | 本文档第 6 章 |
| Context Recovery 协议定稿 | **已完成** | 本文档第 7 章 |
| fan-in 聚合协议定稿 | **已完成** | 本文档第 8 章 |
| 安全策略定稿 | **已完成** | 本文档第 5 章 |
| 推荐 Skill 清单定稿 | **已完成** | 本文档第 9 章 |
| Repair Agent 规范定稿 | **已完成** | 本文档第 10 章 |
| Code Reality Review 规范定稿 | **已完成** | 本文档第 11 章 |

### 12.2 后续路线

| 版本 | 核心目标 | 关键交付 |
|------|----------|----------|
| **v0.5** | DAG 引擎可执行 | DAG manifest 解析引擎、3 个串行节点端到端跑通、循环依赖检测 |
| **v0.6** | 通讯层 fallback 链 | thinking-fixer on_error 模式、plugin 注册表、6 轮回归测试 |
| **v0.7** | 执行层弹窗策略 | ClaudeDialogHandler 5 类弹窗 ≥95%、clauderemote fallback |
| **v0.8** | Docker DAG POC | 隔离执行舱、1 个 L 级任务端到端跑通 |
| **v0.9** | 多 Agent 协作 | fan-out/fan-in 实战、部分失败聚合策略验证 |
| **v1.0** | 正式版 | B 线全链路端到端验收、Code Reality Review 全覆盖 |

---

## 13. 与 v0.3.3 差异清单

以下为 v0.4 相对于 v0.3.3 的全部新增内容：

| # | 新增内容 | 对应章节 | v0.3.3 状态 |
|---|---------|----------|-------------|
| 1 | `task_brief` 完整 schema（类型标注 + 枚举 + 示例） | 3.1 | v0.3.3 §6A 骨架 |
| 2 | `issue_packet` 完整 schema + 6 种 `problem_type` 枚举 | 3.2 | v0.3.3 §6A 骨架 |
| 3 | `node_receipt` 完整 schema + 5 种 `status` 枚举 + `metadata` 子结构 | 3.3 | v0.3.3 §6A 骨架 |
| 4 | `lane_context` 完整 schema + 5 种 `lane_id` 枚举 + 记忆填写规则 | 3.4 | v0.3.3 §6A 骨架 |
| 5 | `dispatch.yaml` 模板（来自 v0.3.2 §8.2） | 3.5 | v0.3.2 草案，未纳入 v0.3.3 |
| 6 | 目录协议：runtime/ 16 文件完整清单 | 4.3 | v0.3.3 §6 部分清单 |
| 7 | 目录协议：logs/ 3 文件完整清单 | 4.4 | v0.3.3 §6 未列出 |
| 8 | 目录协议：阶段目录三件套标准结构 + 生成规则 | 4.5-4.7 | v0.3.3 §6 仅列出目录名 |
| 9 | Handoff 协议：7 节章节结构 | 6.3 | v0.3.3 §6C 草案 |
| 10 | Handoff 协议：Continuous / Milestone 双模式 | 6.2 | v0.3.3 仅 Continuous |
| 11 | Handoff 协议：Writer R0 补丁方向（9 项） | 6.4 | v0.3.3 未列出 |
| 12 | Context Recovery 协议（全新） | 第 7 章 | v0.3.3 无 |
| 13 | fan-in 聚合协议（全新） | 第 8 章 | v0.3.3 无 |
| 14 | 安全策略：4 层安全机制 + 5 类弹窗处理表 | 5.1-5.2 | v0.3.3 §6F 草案 |
| 15 | 安全策略：预授权执行上下文 + 安全边界检查清单 | 5.3-5.5 | v0.3.3 §6F 草案 |
| 16 | 安全策略：clauderemote 模式集成 | 5.4 | v0.3.3 未集成 |
| 17 | 推荐 Skill 清单：10 项 Skill 总表 + 核心流程与关键规则 | 第 9 章 | 能力蓝图 §3§9 散落 |
| 18 | Repair Agent 规范：触发条件 + 修复流程 + AI/Owner 边界 | 第 10 章 | v0.3.3 §7 草案 |
| 19 | Code Reality Review 规范：5 步方法论 + 8 项输出物 + 4 级裁决 | 第 11 章 | v0.3.3 §8 草案 |
| 20 | 演进路线：v0.4 Done 标记 + v0.5-v1.0 路线图 | 第 12 章 | v0.3.3 §11 部分 |

---

# v0.4.1 Amendment：两层 DAG 范式（2026-06-02 R1.0 狗食验证后补入）

> v0.4 原稿假设一个 DAG 节点 = 一个 executor session。R1.0 狗食验证后发现这个假设在实践中会迫使 Hermes 开多个 tmux session 来管理节点内多 subtask 的依赖关系。修正为两层 DAG 范式。

## 修正内容

### 问题

原 v0.4 设计：当 DAG 节点内部有多个子任务（如 6 个补丁 + 1 个交叉引用），且子任务之间存在依赖关系时，Hermes DAG 调度层需要为每个 subtask 独立创建 relay dispatch → 独立 tmux session。导致：
- 多个 tmux 窗口同时弹出，用户无法同时关注
- 子任务间依赖需要在 Hermes 层的 node_dependency 中管理，但同一节点内不应该再拆
- 没有复用 Claude Code 原生就有的多 agent 编排能力

### 修正：两层 DAG

```text
第一层：Hermes DAG（Goal 层调度）
  职责：Goal 级依赖管理、产出回收、Repair Agent、fan-in 验收
  执行单元：每个节点 = 一次 relay dispatch = 一个 tmux session
  
  第二层：Claude Code workflow（节点内 subtask 调度）
  职责：节点内多 agent 的依赖管理、并行执行、内部合成
  执行单元：workflow 脚本内的多个 agent
  激活条件：prompt 中包含 "workflow" 关键词
```

### 选择规则

| 场景 | 用一层 | 用两层 |
|------|--------|--------|
| 节点只有 1 个任务 | 单次 relay dispatch | — |
| 节点有 2+ 个独立子任务 | 可以但可能不清晰 | workflow，内部并行 |
| 子任务有依赖链（A→B→C） | 不要开多个 tmux | workflow 管理内部 DAG |
| 子任务并行（A∥B→C） | 同上 | workflow 管理并发 |
| 需要输出合成汇总 | 外部 fan-in | workflow 内置 |

### 对现有章节的影响

| 章节 | 影响 | 动作 |
|------|------|------|
| §3 核心模板 | dag.nodes 字段含义不变（仍为 Hermes DAG 的节点列表） | 不修改 |
| §5 安全策略 | 安全隔离适用于 Hermes DAG 节点层，workflow 内部 agent 共享节点级的 execution_context | 不修改 |
| §8 fan-in 聚合 | 适用于 Hermes DAG 节点产出，不适用于 workflow 内部产出 | 补充说明 |
| §10 Repair Agent | 适用于节点级校验失败，workflow 内部 agent 失败由 Claude Code 自行处理 | 补充说明 |

本次 amendmend 仅补充两层范式，不修改原文档任何章节。下次主要版本迭代（v0.5）时将其正式纳入正文结构。/Users/gary/项目开发/workyb/资产/workyb workflow_dag/新一代DAG工作流设计文档_v0.4_emerged.md
