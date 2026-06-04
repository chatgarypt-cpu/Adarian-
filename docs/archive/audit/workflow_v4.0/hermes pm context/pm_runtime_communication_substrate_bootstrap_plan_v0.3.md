# PM Runtime Communication Substrate Bootstrap Plan v0.3

> document_type: long_task_plan / DS review patch candidate  
> project: Adarian / 多智能体舆情推演系统 Workflow v4.0  
> plan_name: PM Runtime Communication Substrate Bootstrap Plan  
> version: v0.3  
> supersedes: `pm_runtime_communication_substrate_bootstrap_plan_v0.2.md`  
> review_basis: DS Team architecture review verdict = patch_required  
> status: bootstrap candidate / not repository-landed / pending Owner-Control gate  
> created_at: 2026-05-22  
> author: ChatGPT Control Agent  
> owner_control_required: true  

---

## 0. v0.3 Purpose

v0.2 的方向正确，但 DS Team 审查给出 `patch_required`，指出 7 项 P0 blocker。v0.3 用于吸收这些 P0/P1 修正，并加入 Owner-Control 新增的关键判断：

```text
PM Runtime 通讯层必须以“独立进程 + task session 维持 + 健康监控 + 可恢复”为核心。
不能用单次 120s 调用或固定内层 timeout 来管理 Codex / Claude 这类长程任务。
```

v0.3 仍然坚持：

```text
Communication Substrate First
```

但补齐四个关键安全原则：

1. Pre-action Gate 前置；
2. Runtime Contract 先于 Platform 实现；
3. 独立进程与任务会话维持；
4. 证据保真与防篡改。

---

## 1. Accepted DS Review Findings

v0.3 接受 DS Team 对 v0.2 的核心判断：

```text
方向正确，但不能进入 Runtime Contract 起草前，必须修复 P0/P1。
```

重点吸收以下 P0：

1. YAML 目录策略不一致；
2. Pre-action Gate 不应推迟到 Phase 6；
3. Task Registry status 与 YAML task_status 不对齐；
4. Timeout 时 partial output 保留机制缺失；
5. Phase 2-3 间存在权威真空；
6. Task Registry 缺少防篡改机制；
7. Recovery 缺少证据保真约束。

v0.3 也吸收 Owner-Control 新增 runtime 判断：

```text
Codex / Claude 等长程执行端必须由独立进程承载。
同一个 task 下应尽量维持 session，不应每次修补/确认都重启冷启动。
```

---

## 2. Core Correction: Independent Process + Persistent Task Session

### 2.1 Why Single 120s Calls Are Invalid

Hermes 普通工具调用常受短时超时限制，例如 120s。  
但 Codex / Claude Code 的首次启动、上下文加载、仓库扫描、模型响应都可能天然超过 120s。

因此，不能把长程任务设计成：

```text
Hermes 普通调用 Codex/Claude
→ 120s 超时
→ 进程被杀
→ 再次冷启动
→ 重复等待
```

这种模式会导致：

1. 首次加载成本反复发生；
2. 修补任务无法继承上下文；
3. 确认/阻塞点一出现就丢失进程；
4. 长程任务状态不可恢复；
5. 用户体验退化为反复等待；
6. runtime 无法建立真正的 task session。

### 2.2 Required Runtime Model

PM Runtime Communication Substrate 必须采用：

```text
Hermes / PM Runtime
→ 启动独立 relay supervisor process
→ relay supervisor 管理 executor process/session
→ task registry 持久化 session 状态
→ heartbeat/progress/result 持续写盘
→ Owner-Control / Hermes 可 attach / recover / inspect
```

最小进程模型：

```text
pm_runtime relay start <task_config>
  → creates task_id
  → creates task directory
  → writes registry append-only event
  → starts supervisor process
  → supervisor starts executor process/session
  → supervisor writes heartbeat/progress/logs
```

### 2.3 Task Session Concept

每个长程任务必须有：

```yaml
task_id: required
session_id: required
executor_type: claude | codex | ds_team | external_agent
supervisor_pid: optional
executor_pid: optional
process_group: optional
session_state: initialized | running | waiting_input | blocked | completed | failed | recovered | aborted
created_at: required
last_heartbeat_at: optional
last_progress_at: optional
last_observed_output_at: optional
```

Session 的目标：

1. 同一任务内避免反复冷启动；
2. 允许修补/确认后继续；
3. 支持 recover / attach；
4. 支持区分 running、waiting_input、blocked、failed；
5. 保留完整 stdout / stderr / raw output。

---

## 3. Runtime Control: Health-Based, Not Hard Timeout-Based

### 3.1 Hard Timeout Is Not Primary Control

固定 `timeout=1500` 或类似硬超时只能作为 emergency guard，不能作为主调度策略。

错误模式：

```text
任务到达固定时间 → 强制 kill
```

正确模式：

```text
监控进程健康
→ 判断是否有进展
→ 判断是否阻塞
→ 生成 blocker report
→ 请求 Owner-Control 决策
→ 必要时 abort
```

### 3.2 Runtime Control Contract

建议配置：

```yaml
runtime_control:
  mode: health_based
  heartbeat_interval_sec: 30
  progress_check_interval_sec: 120
  no_heartbeat_timeout_sec: 180
  no_progress_review_sec: 600
  owner_review_after_sec: 1800
  emergency_max_wall_time_sec: null
  abort_requires_owner: true
  preserve_partial_output_on_abort: true
```

字段含义：

| 字段 | 作用 |
|---|---|
| heartbeat_interval_sec | 生命体征写入频率 |
| progress_check_interval_sec | 进展检查频率 |
| no_heartbeat_timeout_sec | 判断 supervisor/executor 是否可能失联 |
| no_progress_review_sec | 进入 suspected_blocked 的阈值 |
| owner_review_after_sec | 长任务阶段性回报，不自动 kill |
| emergency_max_wall_time_sec | 可选兜底保险，不是主控 |
| abort_requires_owner | 默认中止需 Owner-Control 批准 |
| preserve_partial_output_on_abort | 中止前必须保存 partial output |

### 3.3 Blocker Report Instead of Silent Kill

当任务疑似阻塞时，runtime 应生成：

```text
runtime/blocker_report.md
```

最低字段：

```yaml
task_id:
session_id:
runtime_state: suspected_blocked | waiting_input | permission_blocked | no_progress
elapsed_seconds:
last_heartbeat_at:
last_progress_at:
stdout_growth:
stderr_tail:
suspected_blocker:
recommended_actions:
  - continue
  - attach
  - request_owner_decision
  - repair_permissions
  - recover_partial_output
  - abort
owner_control_required: true
```

---

## 4. Execution Modes

Communication Substrate 不是只服务 Claude / DS，也不是强行把 Codex 变成手动工具。

v0.3 定义两类候选执行模式，但 Codex 具体模式仍等待 spike 结果。

### 4.1 Managed Relay Session Mode

适用对象：

```text
Claude / DS Team / 长程审查 agent
```

特征：

1. PM Runtime 可启动独立进程；
2. supervisor 负责监控；
3. stdout/stderr 可捕获；
4. heartbeat/progress/result 持久化；
5. 可 recover / attach；
6. 可按 health-based control 处理阻塞。

### 4.2 Managed Codex Session Mode — Pending Spike

适用对象：

```text
Codex CLI / codex exec / Codex local executor
```

状态：

```text
pending verification spike
```

必须验证：

1. Codex CLI 是否可非交互运行；
2. 首次启动是否超过普通工具调用限制；
3. 是否能通过独立进程维持 session；
4. 是否能捕获 stdout/stderr/exit code；
5. 是否能在同一 task 下继续修补；
6. 是否可避免每次 cold start；
7. 是否需要人工 approval；
8. approval 出现时是否可进入 waiting_input，而不是杀进程；
9. 是否能生成 receipt / diff / changed_files；
10. 是否能被 health-based monitor 管理。

v0.3 不预设 Codex 一定手动，也不预设一定可 fully managed。

候选结论：

```text
managed_codex_session_feasible
manual_confirmed_codex_required
codex_cli_unavailable
codex_requires_additional_design
unsupported_hold
```

### 4.3 Manual Transport Fallback

在 managed Codex 尚未验证前，允许保留人工搬运作为 fallback：

```text
Owner 手动搬运 prompt / report / receipt
```

但 manual transport 不应成为最终目标，只是 bootstrap 兜底。

---

## 5. Pre-Action Gate Must Move to Phase 0/1

### 5.1 Why Gate Cannot Wait

v0.2 将 pre-action gate 放到 Phase 6 是错误时序。  
四连失败已经证明：角色越界、产物未落盘、domain 路由错误、MCP 工具上下文缺失，都是 action 前可检查的问题。

v0.3 将 Pre-Action Gate 提前到 Phase 0/1，并纳入 Runtime Contract。

### 5.2 Minimum Pre-Action Gate

每次 PM Runtime 执行 Adarian 相关动作前，必须落盘一份 pre-action record：

```text
runtime/pre_action_check.yaml
```

最低字段：

```yaml
task_id:
action_type: create_task | launch_executor | recover_task | classify_failure | produce_summary
intended_executor:
task_domain:
artifact_expected: true | false
artifact_target_paths: []
role_boundary_checked: true
allowed_by_role: true | false | unclear
needs_ds_team: true | false | unclear
needs_owner_approval: true | false | unclear
mcp_or_tool_preflight_required: true | false
result: pass | hold
hold_reason: optional
```

如果 `result = hold`，不得继续启动 executor。

---

## 6. Directory Policy and YAML Alignment

### 6.1 Canonical Directory Policy

v0.3 采用两级目录：

```text
audit/tasks/active/<task_domain>/<short_task>/
```

原因：

1. 更适合按任务域归档；
2. 便于区分 pm-runtime-governance、workflow-governance、source-code 等；
3. 已被当前 PM Runtime 实践使用；
4. 能降低所有任务平铺在 task_id 下的混乱。

### 6.2 YAML Must Be Updated

如果 YAML 当前使用：

```text
audit/tasks/active/<task_id>/
```

则需在后续 YAML patch 中改为两级目录，或增加兼容别名。

v0.3 不直接修改 YAML，但将其列为 Runtime Contract 前置决策：

```text
directory_policy_decision: two_level_domain_short_task
yaml_patch_required: true
```

---

## 7. Status Model: task_status + runtime_state

### 7.1 Task Status Must Align with YAML

顶层 `task_status` 应对齐 YAML / workflow compact 的正式状态，例如：

```text
proposed
approved
running
completed
failed
hold
closed
archived
```

如果 YAML 枚举最终不同，以 YAML patch 后的正式枚举为准。

### 7.2 Runtime State Captures Operational Details

运行细节不混入顶层 task_status，而放入 `runtime_state`：

```text
created
dispatch_ready
launching
healthy_running
slow_but_progressing
waiting_input
permission_blocked
suspected_blocked
partial_output
missing_receipt
missing_report
recovering
recovered
aborted
```

这样避免 platform 写入的状态值与 workflow_compact 校验冲突。

---

## 8. Evidence Preservation and Anti-Tamper Registry

### 8.1 Append-Only Registry

Registry 不应只保存当前状态，必须保存 append-only event log：

```text
runtime/registry_events.jsonl
```

每次状态变化写一行：

```json
{
  "event_id": "...",
  "task_id": "...",
  "session_id": "...",
  "timestamp": "...",
  "actor": "hermes|runtime|owner|codex|ds|control",
  "event_type": "created|launched|heartbeat|progress|blocked|recovered|summary_written",
  "from_status": "...",
  "to_status": "...",
  "reason": "...",
  "evidence_paths": []
}
```

当前状态可以由事件流派生，也可以缓存到：

```text
runtime/task_state.yaml
```

但缓存不能替代 append-only log。

### 8.2 Recovery Must Preserve Original Evidence

Recovery 规则：

1. 不覆盖原始 stdout/stderr/raw output；
2. 不删除原始 failure result；
3. 二次提取产物必须另存；
4. recovery summary 必须标注 recovered；
5. 非 trivial recovery 需要 Owner-Control approval；
6. recovered ≠ normal completed；
7. recovery 不得修改 DS verdict；
8. recovery 不得 closeout。

### 8.3 Partial Output Must Always Be Preserved

无论 timeout、abort、process killed、permission blocked，runtime 都必须尽力保存：

```text
logs/stdout.partial.log
logs/stderr.partial.log
logs/raw_output.partial.json
runtime/abort_or_timeout_report.yaml
```

---

## 9. Phase Plan v0.3

### Phase 0: Bootstrap Safety Baseline

目标：

```text
在写 Runtime Contract 前，先锁定安全基线。
```

必须完成：

1. 接受 DS review 的 patch_required；
2. 确认两级目录策略；
3. 确认 status/runtime_state 双层模型；
4. 确认 pre-action gate 前置；
5. 确认 append-only registry；
6. 确认 recovery evidence preservation；
7. 确认独立进程 + task session 是 P0 要求；
8. Codex spike 继续作为旁路证据，不阻塞本阶段。

产物：

```text
PM Runtime Communication Substrate Bootstrap Plan v0.3
```

### Phase 1: Runtime Contract v0.1

必须包含：

1. task config contract；
2. task directory contract；
3. task_status / runtime_state；
4. independent process/session contract；
5. health-based runtime control；
6. pre-action check contract；
7. task registry append-only log；
8. stdout/stderr/raw output preservation；
9. recovery evidence preservation；
10. executor profiles；
11. PM Runtime core forbidden items appendix；
12. MCP / settings preflight minimum;
13. Codex execution mode marked pending spike result。

注意：角色卡核心禁止项必须在 Phase 1 固化，避免 Phase 2-3 权威真空。

### Phase 2: Python MVP Task Card

只有 Runtime Contract v0.1 被 Owner-Control 接受后，才写 Python MVP 任务卡。

任务卡必须限制：

1. Python MVP；
2. 不做 daemon；
3. 不做 dashboard；
4. 不做 distributed queue；
5. 不做 auto closeout；
6. 不做 auto git commit；
7. 不修改 workflow_core；
8. 不触碰业务源码；
9. 先支持 Claude/DS managed relay；
10. Codex managed session 根据 spike 结果决定是否纳入。

### Phase 3: Python MVP Implementation

MVP 最小模块建议：

```text
pm_runtime/relay/
  cli.py
  relay_runner.py
  extractors.py
  recovery.py
```

v0.1 可暂缓独立：

```text
failure_classifier.py
task_registry.py
```

这些可先内联，避免过早模块化。

必须实现：

1. init task；
2. launch independent supervisor/executor；
3. write pre_action_check；
4. write append-only registry event；
5. write heartbeat/progress；
6. capture stdout/stderr；
7. preserve partial output；
8. classify minimal failures；
9. recover / inspect；
10. generate pm_runtime_summary。

### Phase 4: Operator Skill + Role Cards

平台 MVP 明确后，再写：

1. relay_operator/SKILL.md；
2. Hermes / PM Runtime role card；
3. Codex role card；
4. Claude / DS role card。

Skill 只说明如何使用平台，不是平台本体。

### Phase 5: Bootstrap Online Test Loop

用真实小任务测试：

1. normal completion；
2. slow but progressing；
3. no heartbeat；
4. no progress；
5. permission blocked；
6. missing receipt；
7. timeout / abort with partial output；
8. recovery；
9. wrong domain；
10. artifact path missing；
11. role boundary violation；
12. Codex managed / manual mode according to spike result。

### Phase 6: Governance Hardening

在真实测试后，再逐步增强：

1. deeper gate；
2. MCP matrix；
3. anti-drift skill upgrade；
4. YAML active maintenance；
5. workflow_core repair；
6. router calibration；
7. milestone stewardship；
8. optional dashboard。

---

## 10. Codex Spike Integration Rule

当前 Codex spike 仍在运行。v0.3 不等待 spike 完成，但明确：

```text
Codex execution mode remains pending evidence.
```

Codex spike 结果出来后，不重写 v0.3 主体，而是追加：

```text
Codex Execution Mode Patch Note
```

可能结论：

1. Codex 可 managed session；
2. Codex 可 non-interactive exec 但需严格 sandbox；
3. Codex 需要 manual confirmation；
4. Codex 当前环境不可用；
5. 需要更多测试。

该 patch note 将影响 Runtime Contract v0.1 的 executor profile，而不是推翻 Communication Substrate First 主线。

---

## 11. DS Review Follow-up

v0.3 不需要立即再次 DS Team 大审，除非 Owner-Control 判断 P0 修复仍不充分。

建议处理方式：

1. Owner-Control 先检查 v0.3 是否完整吸收 P0；
2. 若接受，进入 Runtime Contract v0.1 起草；
3. Runtime Contract 完成后，再交 DS Team 做 focused review。

---

## 12. Acceptance Criteria for v0.3

v0.3 可进入 Runtime Contract 起草，当且仅当：

1. Pre-action Gate 已前置；
2. independent process + persistent task session 被列为 P0；
3. health-based runtime control 替代 hard timeout 主控；
4. partial output preservation 被列为必需；
5. append-only registry 被列为必需；
6. recovery evidence preservation 被列为必需；
7. task_status / runtime_state 双层模型被接受；
8. 两级目录策略被明确；
9. Hermes forbidden items 必须进入 Runtime Contract 附录；
10. Codex execution mode 明确 pending spike；
11. skill 被明确为 operator manual，不是 platform；
12. 不进入代码实现，直到 Runtime Contract 被接受。

---

## 13. Final Position

v0.3 的核心结论：

```text
PM Runtime v0.1 的第一性问题不是“怎么写更多 skill”，
而是“如何建立一个不会丢任务、不会污染证据、不会反复冷启动、不会自我扩权的通讯基座”。
```

因此：

```text
独立进程是必需项；
task session 维持是必需项；
health-based control 是必需项；
append-only evidence 是必需项；
pre-action gate 是必需项；
hard timeout 只能是 emergency guard；
skill 只能是 operator manual；
closeout 仍然回 Owner-Control。
```
# PM Runtime Communication Substrate v0.3 — Codex Execution and Owner Decision Relay Patch Note

> document_type: patch_note / runtime_evidence_appendix  
> parent_plan: `pm_runtime_communication_substrate_bootstrap_plan_v0.3.md`  
> patch_version: v0.3.1-appendix  
> status: bootstrap evidence patch / not repository-landed  
> created_at: 2026-05-22  
> author: ChatGPT Control Agent  
> evidence_sources:
> - `hermes_codex_workflow_verification_spike_summary.md`
> - `owner_decision_relay_test_summary.md`
> owner_control_required: true  

---

## 0. Patch Purpose

本补丁用于将 Codex workflow verification spike 与 Owner Decision Relay test 的结果追加到 PM Runtime Communication Substrate v0.3 计划中。

本补丁不重写 v0.3 主体，不授权代码实现，不授权 Codex landing。

本补丁只用于修正两个关键问题：

```text
1. Codex execution mode 不再保持完全 unknown；
2. Owner Approval Relay 应升级为 Owner Decision Relay。
```

---

## 1. Evidence Summary

### 1.1 Codex Managed Execution Feasibility

Hermes spike 已验证：

```yaml
codex_cli_available: true
codex_exec_available: true
readonly_noninteractive_result: pass
workspace_write_result: pass
approval_required_observed: false
stdout_capturable: true
stderr_capturable: true
exit_code_capturable: true
receipt_feasible: true
recommended_execution_mode:
  - managed_codex_exec
```

结论：

```text
Codex 可作为 Communication Substrate 的 managed executor candidate。
```

但该结论不等于：

```text
Codex integration approved
Codex landing approved
Codex can modify workflow assets without Owner-Control gate
```

---

## 2. Codex Execution Mode Update

### 2.1 Previous v0.3 Status

v0.3 原状态：

```text
Codex execution mode: pending spike result
```

### 2.2 Updated Status

基于 spike 结果，更新为：

```text
Codex execution mode: managed_codex_exec candidate
```

推荐执行模式：

```text
executor_type: codex
execution_mode: managed_codex_exec
launch_mode: independent_subprocess
output_mode: jsonl
sandbox_mode:
  - read-only for review / inspection
  - workspace-write + --add-dir for controlled write
```

### 2.3 Supported Command Patterns

已验证命令形态：

```bash
codex exec --sandbox read-only --skip-git-repo-check --ephemeral --json "<prompt>"
```

```bash
codex exec --sandbox workspace-write --skip-git-repo-check --ephemeral --add-dir <sandbox_path> --json "<prompt>"
```

### 2.4 Required Runtime Support

Communication Substrate 必须支持：

1. JSONL stdout parsing；
2. stderr capture；
3. exit_code capture；
4. structured receipt extraction；
5. startup overhead accounting；
6. sandbox mode recording；
7. `--add-dir` scope recording；
8. task-local artifact path validation；
9. changed_files / commands_run / test_results / diff_summary 回收；
10. no-closeout boundary。

---

## 3. Codex Startup Overhead

### 3.1 Observed Overhead

三次 Codex exec 测试，即使是极小任务，也耗时约 121–136 秒。

观察原因包括：

1. 启动开销；
2. 多次 reconnection；
3. model initialization；
4. context loading。

### 3.2 Design Implication

Codex 不应由 Hermes 普通短时调用直接管理。

Communication Substrate 必须采用：

```text
independent subprocess
task session
health-based monitoring
recovery-capable task registry
```

### 3.3 Timeout Implication

Codex 的 timeout 设计必须包含启动基线成本。

不得使用：

```text
120s tool call timeout
```

作为 Codex 任务完成判断。

建议 Runtime Contract 增加：

```yaml
executor_startup_baseline:
  codex_exec_sec: 120
  claude_exec_sec: TBD
```

并将其用于：

```text
owner_review_after_sec
no_progress_review_sec
emergency_max_wall_time_sec
```

---

## 4. Sandbox Findings

### 4.1 Observed Behavior

测试覆盖：

| Mode | Result |
|---|---|
| read-only + read file | silent pass |
| workspace-write + --add-dir write | silent pass |
| read-only + delete attempt | OS sandbox denied |
| interactive approval popup | not observed |

### 4.2 Key Finding

Codex 的权限边界不一定表现为交互式确认弹窗。

实际观察到：

```text
OS-level sandbox denial
```

而不是：

```text
interactive approval_required prompt
```

因此 Runtime Contract 不能只建模 approval_required。

---

## 5. Owner Approval Relay → Owner Decision Relay

### 5.1 Rename Required

原概念：

```text
Owner Approval Relay
```

应改为：

```text
Owner Decision Relay
```

原因：

```text
中台要处理的不是单一 approval prompt，而是所有需要 Owner 判断的 runtime decision events。
```

### 5.2 Covered Event Types

Owner Decision Relay 至少覆盖：

```text
approval_required
sandbox_denied
permission_blocked
waiting_input
scope_violation
unclear_policy
missing_receipt
recovery_requires_approval
```

### 5.3 Required Event Record

当出现 decision-needed event 时，runtime 应写入：

```text
runtime/owner_decision_request.yaml
```

最低字段：

```yaml
task_id:
session_id:
request_id:
executor:
event_type:
requested_action:
affected_files: []
observed_result:
agent_message:
risk_level:
allowed_scope: []
forbidden_scope: []
available_options:
  - approve_with_scope
  - reject
  - abort_task
  - request_safer_alternative
  - ask_for_more_context
recommended_action:
owner_control_required: true
```

### 5.4 Required Decision Record

Owner 决策后，runtime 应写入：

```text
runtime/owner_decision_record.yaml
```

最低字段：

```yaml
task_id:
session_id:
request_id:
owner_decision:
decision_source:
decision_time:
approved_scope: []
rejected_scope: []
notes:
next_runtime_action:
```

---

## 6. One-Shot Subprocess Limitation

### 6.1 Finding

当前 `subprocess.run()` 一次性 stdin 架构无法支持运行中双向追问。

不可行或受限的 Owner decision options：

```text
ask_for_more_context
approve_with_modified_scope
```

因为当前进程无法在运行中修改 sandbox 参数或重新打开 stdin 对话。

### 6.2 Current Feasible Options

当前 one-shot 模式下可行：

```text
reject
abort_task
approve_with_scope via rerun
request_safer_alternative via rerun
```

### 6.3 Required Runtime Design

Runtime Contract 必须显式区分：

```text
in_session_action
rerun_required_action
unsupported_action
```

建议规则：

| Owner Decision | Current One-Shot Support | Required Handling |
|---|---|---|
| reject | supported | record and stop |
| abort_task | supported | terminate and record |
| ask_for_more_context | not supported | mark rerun_or_manual_required |
| approve_with_modified_scope | not live-supported | start round_2 with new config |
| request_safer_alternative | rerun required | start round_2 with safer prompt |

---

## 7. Round-Based Rerun Model

由于当前 one-shot subprocess 不支持运行中修改，Communication Substrate 应引入 round model：

```yaml
task_id: same
session_id: may_change
round_id: round_1 | round_2 | round_3
parent_round_id: optional
rerun_reason:
rerun_config_delta:
evidence_from_previous_round:
```

适用场景：

1. sandbox_denied 后扩大或缩小 scope；
2. Owner request safer alternative；
3. missing receipt 后要求 structured receipt rerun；
4. Codex 输出不合格后按同一任务修补；
5. permission issue 修复后重跑。

规则：

```text
rerun 不是新任务；
rerun 是同一 task 下的新 round。
```

所有 round 必须进入 append-only registry。

---

## 8. Codex Executor Profile Patch

Runtime Contract 中 Codex profile 应更新为：

```yaml
executor_type: codex
supported_modes:
  - managed_codex_exec
sandbox_modes:
  - read-only
  - workspace-write
required_flags:
  - --skip-git-repo-check
  - --ephemeral
  - --json
recommended_scope_control:
  - --add-dir for write tasks
stdout_format: jsonl
required_captures:
  - stdout
  - stderr
  - exit_code
  - jsonl_events
required_receipt_fields:
  - executor
  - mode
  - changed_files
  - commands_run
  - test_results
  - exit_code
  - sandbox_mode
  - stdout_path
  - stderr_path
  - known_issues
forbidden:
  - final_closeout
  - auto_commit_without_explicit_owner_approval
  - touching_forbidden_files
  - treating_sandbox_denied_as_success
  - suppressing stderr / stdout evidence
```

---

## 9. Runtime Contract Required Changes

The future `PM Runtime Communication Substrate Runtime Contract v0.1` must include:

1. `managed_codex_exec` execution mode；
2. Codex JSONL parser requirement；
3. executor startup baseline field；
4. Owner Decision Relay；
5. decision event types；
6. decision request / decision record schemas；
7. round-based rerun model；
8. sandbox_denied as first-class failure / decision event；
9. one-shot subprocess limitation notice；
10. distinction between `completed`, `blocked`, `recovered`, and `rerun_required`。

---

## 10. Gate Status

This patch note supports the following gate update:

```yaml
codex_spike_status: completed
codex_managed_executor_candidate: true
owner_decision_relay_status: validated_with_simulated_and_real_sandbox_denied_event
runtime_contract_patch_required: true
v0.3_main_plan_rewrite_required: false
next_step: draft_runtime_contract_v0.1_after_owner_acceptance
```

---

## 11. Final Boundary

This patch note does not authorize:

1. Codex landing；
2. source modification；
3. workflow_core modification；
4. automatic approval；
5. automatic closeout；
6. bypassing sandbox；
7. destructive testing outside sandbox。

Final decision remains with Owner-Control.
