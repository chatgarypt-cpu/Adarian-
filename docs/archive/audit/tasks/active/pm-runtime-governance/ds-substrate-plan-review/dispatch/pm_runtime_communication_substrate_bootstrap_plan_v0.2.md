# PM Runtime Communication Substrate Bootstrap Plan v0.2

> document_type: long_task_plan / DS review candidate  
> project: Adarian / 多智能体舆情推演系统 Workflow v4.0  
> plan_name: PM Runtime Communication Substrate Bootstrap Plan  
> version: v0.2  
> supersedes: `pm_runtime_communication_relay_bootstrap_plan_v0.1.md`  
> status: bootstrap candidate / not repository-landed / pending DS Team review  
> created_at: 2026-05-22  
> author: ChatGPT Control Agent  
> intended_reviewer: DS Team via Hermes / PM Runtime  
> owner_control_required: true  

---

## 0. Correction Notice

v0.1 存在一个关键设计错误：

```text
把“通讯层中台”误写成了一个 PM Runtime skill。
```

正确设计应为：

```text
通讯层中台 = 工程基座平台 / runtime substrate
skill = 该平台的操作说明、边界说明、使用规程
```

也就是说，通讯层不应被定义为：

```text
pm_runtime/skills/communication_relay/SKILL.md
```

而应被定义为一个实际可运行的基座平台，例如：

```text
pm_runtime/relay/
pm_runtime/runtime/
pm_runtime/transport/
```

可用 Python / Go / shell wrapper / CLI 方式实现。

Skill 文件只负责说明：

1. 什么时候使用该通讯层；
2. 如何创建任务；
3. 如何调用 runtime；
4. 如何监控状态；
5. 如何回收产物；
6. Hermes / Codex / Claude / DS 的权限边界；
7. 失败时如何 HOLD；
8. 什么不能做。

---

## 1. Executive Summary

当前 workflow_v4.0 的下一阶段主线应调整为：

```text
先做 PM Runtime 通讯层工程基座
→ 再配置 Hermes / Codex / Claude-DS 三类角色卡
→ 再用 skill / instruction 描述如何使用该基座
→ 上线第一版受限 bootstrap runtime
→ 用真实任务测试
→ 再逐步优化 gate / MCP / skills / workflow_core
```

本计划书主张：

```text
Communication Substrate First
```

不是：

```text
Communication Skill First
```

第一版目标不是把治理文档写完，而是建设一个最小可运行平台，解决：

1. 长程任务如何派发；
2. 任务如何在用户杀进程 / 会话断开后恢复；
3. task_id / status / artifact path 如何持久化；
4. Codex / Claude / DS Team / External Agent 如何共用一套任务生命周期；
5. report / receipt / summary 如何被回收；
6. runtime 行为如何可审计。

---

## 2. Current Evidence

根据 Hermes / PM Runtime relay context packet，当前 `relay_runner.py` 的真实状态是：

```text
任务内 subprocess relay 脚本
```

它由 Hermes-PM 通过 `execute_code + subprocess.Popen(start_new_session=True)` 启动，调用 Claude Code CLI，并负责写 heartbeat / progress、解析 Claude JSON 输出、提取 report 和 receipt。

当前它不是：

```text
不是全局 daemon
不是 workflow_core 组件
不是 Agent
不是最终 gate
```

当前已验证价值：

1. 能绕过长中文 dispatch 触发 terminal 安全扫描的问题；
2. 能以独立进程运行长程 Claude / DS 审查；
3. 能周期性写 heartbeat / progress；
4. 能提取 Claude JSON 输出；
5. 能从 permission_denial payload 中回收报告；
6. 能处理部分 JSON code block 包裹问题。

当前主要缺口：

1. task_id / timeout / max_turns / prompt 硬编码；
2. 每任务复制一份 relay_runner.py；
3. 无集中 task registry；
4. 无持久化任务注册表；
5. 会话断开后无法可靠恢复监控；
6. heartbeat / progress / result 格式不统一；
7. timeout 后 partial stdout / stderr 未保留；
8. stderr 未独立保存；
9. 失败分类过粗；
10. 无标准 executor profiles；
11. 无统一 recovery scan；
12. 无统一 task lifecycle；
13. 无平台级 CLI / API。

---

## 3. Core Design Distinction

### 3.1 Platform vs Skill

| 层级 | 是什么 | 例子 | 作用 |
|---|---|---|---|
| Communication Substrate | 工程基座平台 | Python / Go runtime、CLI、task registry、relay runner template | 真正执行、记录、恢复、回收 |
| Runtime Contract | 平台契约 | task schema、status enum、artifact paths、failure taxonomy | 保证平台输入输出稳定 |
| Operator Skill | 操作说明 | SKILL.md | 告诉 Hermes / PM Runtime 如何使用平台 |
| Role Instruction | 角色边界 | Hermes / Codex / DS / Claude role card | 规定谁能做什么、不能做什么 |
| Workflow Core | 治理总则 | workflow_core.md | 抽象原则，不承载实现细节 |

错误模式：

```text
把工程基座写成 skill。
```

正确模式：

```text
先定义 / 实现最小工程基座；
再写 skill 说明如何调用该基座。
```

### 3.2 Runtime Substrate 负责什么

Communication Substrate 应负责：

1. 创建 task_id；
2. 创建任务目录；
3. 写入 dispatch；
4. 写入 executor prompt / system prompt；
5. 启动下游执行进程；
6. 记录 pid / process group；
7. 写 heartbeat；
8. 写 progress；
9. 捕获 stdout / stderr；
10. 保存 raw output；
11. 解析 report / receipt；
12. 写 task registry；
13. 支持恢复扫描；
14. 支持 timeout / killed / missing receipt / partial output 分类；
15. 生成 runtime summary；
16. 将证据交回 Owner-Control。

### 3.3 Skill 只负责什么

后续的 `SKILL.md` 只应负责：

1. 平台使用 SOP；
2. 命令/配置入口说明；
3. 任务目录规范说明；
4. Hermes 可做 / 不可做边界；
5. task-local repair 边界；
6. 产物回收要求；
7. HOLD 条件；
8. 不把 runtime completed 误判为 closeout。

---

## 4. Target Product Definition

### 4.1 产品名建议

可选命名：

```text
PM Runtime Communication Substrate
PM Runtime Relay Platform
PM Runtime Task Relay Kernel
Hermes Relay Substrate
```

推荐：

```text
PM Runtime Communication Substrate
```

因为它强调这是工程基座，不是单一脚本，也不是 skill。

### 4.2 第一版形态

第一版可以是 Python 实现，不必上 Go。

建议形态：

```text
pm_runtime/
  relay/
    relay_runner.py
    task_registry.py
    recovery.py
    extractors.py
    failure_classifier.py
    cli.py
    templates/
      ds_dispatch_template.md
      codex_dispatch_template.md
  schemas/
    task_config.schema.yaml
    task_registry_entry.schema.yaml
  skills/
    relay_operator/SKILL.md
```

但为了避免过度工程化，v0.1 可以收缩为：

```text
pm_runtime/
  relay/
    relay_runner.py
    cli.py
    extractors.py
    recovery.py
  templates/
    task_config.yaml
  skills/
    relay_operator/SKILL.md
```

### 4.3 不建议一开始做

第一版不建议：

1. 全局 daemon；
2. Web dashboard；
3. 复杂队列系统；
4. 多进程任务调度池；
5. 跨机器分布式执行；
6. 复杂数据库；
7. 自动 git 操作；
8. 自动 closeout；
9. 自动修改 workflow_core；
10. 大型 schema 套娃。

---

## 5. Minimum Runtime Capabilities

v0.1 Communication Substrate 至少应具备：

### 5.1 Task Creation

输入：

```yaml
task_id: required_or_generated
task_domain: required
short_task: required
executor_type: claude | codex | ds_team | external_agent
task_level: S | M | L | patch
dispatch_path: required
system_prompt_path: optional
timeout_sec: optional
max_turns: optional
allowed_tools: optional
owner_control_required: true
```

输出：

```text
audit/tasks/active/<task_domain>/<short_task>/
```

### 5.2 Task Registry

必须写入：

```yaml
task_id: required
task_domain: required
short_task: required
executor_type: required
task_level: required
status: created | dispatched | running | waiting_input | blocked | failed | completed | recovered | cancelled
created_at: required
started_at: optional
last_heartbeat_at: optional
ended_at: optional
pid: optional
process_group: optional
dispatch_path: required
runtime_dir: required
report_paths: []
receipt_paths: []
summary_path: optional
known_issues: []
blockers: []
```

### 5.3 Process Launch

平台负责启动下游进程，例如：

```text
claude -p --allowedTools Read --output-format json
```

未来也可支持：

```text
codex ...
python ...
shell wrapper ...
external agent handoff ...
```

但 v0.1 可以先支持 Claude / DS relay。

### 5.4 Heartbeat / Progress / Result

建议统一结构化输出：

```text
runtime/heartbeat.json
runtime/progress.yaml
runtime/relay_state.yaml
logs/stdout.log
logs/stderr.log
logs/raw_output.json
summary/pm_runtime_summary.md
```

### 5.5 Recovery

平台必须支持：

```text
pm-runtime relay recover --task-id <task_id>
pm-runtime relay scan --domain <task_domain>
```

v0.1 可以先实现为脚本或手动命令，不要求 daemon。

恢复能力至少包括：

1. 根据 registry 找任务目录；
2. 根据 heartbeat 判断最后状态；
3. 根据 pid / process group 判断进程是否仍在；
4. 根据 report / receipt 文件判断是否产物已存在；
5. 根据 stdout / raw_output 尝试二次提取 report；
6. 生成 recovery summary；
7. 不修改 DS verdict；
8. 不 closeout。

### 5.6 Failure Classification

第一版应至少区分：

```text
agent_completed
agent_failed
permission_blocked
partial_output
json_parse_failed
no_output
timeout
process_killed
environment_blocked
missing_receipt
missing_report
artifact_path_missing
role_boundary_violation
```

---

## 6. Executor Profiles

Executor profile 不是独立通讯系统，而是 runtime substrate 的差异配置。

### 6.1 Claude / DS Team Profile

必须回收：

```yaml
report_path: required
receipt_path: recommended
acceptance_verdict: required_if_review
findings: required_if_review
process_issues: []
blockers: []
mcp_used: true | false | unknown
team_mode_used: true | false | unknown
```

禁止：

1. final closeout；
2. 修改文件；
3. 降级 blocker；
4. 把 scan 当 audit；
5. 不看真实路径就做 repository-level verdict。

### 6.2 Codex Profile

必须回收：

```yaml
changed_files: []
commands_run: []
test_results: []
diff_summary: required
receipt_path: required
handoff_path: recommended
commit_status: no_commit | committed | unknown
forbidden_files_touched: []
```

禁止：

1. auto commit；
2. scope expansion；
3. touching forbidden files；
4. claiming closeout；
5. treating environment blocker as code failure without evidence。

### 6.3 Hermes / PM Runtime Profile

必须回收：

```yaml
task_id: required
runtime_state: required
dispatch_path: required
receipt_paths: []
report_paths: []
summary_path: required
blockers: []
known_issues: []
next_recommendation: required
```

禁止：

1. final gate；
2. DS-level audit；
3. source code modification；
4. workflow authority modification；
5. git commit。

---

## 7. Role Cards After Platform

三张角色卡应在 Communication Substrate 的边界确定后配置。

### 7.1 Hermes / PM Runtime Role Card

围绕平台使用：

1. 如何创建 task；
2. 如何调用 relay platform；
3. 如何恢复任务；
4. 如何生成 summary；
5. 什么情况下 HOLD；
6. 什么情况下转 Owner-Control；
7. task-local repair 边界。

### 7.2 Codex Role Card

围绕执行回传：

1. 如何读 approved dispatch；
2. 如何遵守 allowed / forbidden files；
3. 如何输出 diff / commands / test results；
4. 如何写 receipt / handoff；
5. 如何声明 environment blocker；
6. 不 closeout。

### 7.3 Claude / DS Role Card

围绕审查回传：

1. 如何做 read-only review；
2. 如何输出 Chinese Markdown report；
3. 如何报告 team_mode / MCP；
4. 如何输出 acceptance_verdict；
5. 如何区分 scan / audit / verification；
6. 不修改文件，不 closeout。

---

## 8. Long-Term Roadmap

### Phase 0: DS Plan Review

目标：

```text
让 DS Team 审查本计划路线是否合理。
```

重点审查：

1. 是否正确区分 platform / skill；
2. 是否存在过度工程化；
3. 是否应 Python 先行还是 Go 先行；
4. 第一版能力是否足够；
5. 是否遗漏用户杀进程 / 会话断开恢复；
6. 是否限制了 Hermes 权限；
7. 是否需要更早配置 Codex / DS role card；
8. 是否应继续保留任务内 relay_runner 复制模式作为过渡。

### Phase 1: Runtime Contract Draft

目标：

```text
写 PM Runtime Communication Substrate 的最小 runtime contract。
```

产物可包括：

1. task lifecycle；
2. task config；
3. registry entry；
4. artifact paths；
5. failure taxonomy；
6. executor profiles；
7. recovery rules。

注意：这是平台契约，不是 skill。

### Phase 2: Python Runtime MVP

目标：

```text
实现 Python 版最小通讯层基座。
```

功能：

1. init task；
2. run claude relay；
3. write heartbeat/progress/state；
4. capture stdout/stderr；
5. extract report/receipt；
6. classify failure；
7. recover task；
8. generate summary。

### Phase 3: Operator Skill / Role Cards

目标：

```text
在平台 MVP 明确后，再写 skill 和 role cards。
```

产物：

1. relay_operator/SKILL.md；
2. Hermes / PM Runtime role card；
3. Codex role card；
4. Claude / DS role card。

### Phase 4: Bootstrap Online

目标：

```text
上线 PM Runtime v0.1 bootstrap。
```

只允许受限任务：

1. S-Level path check；
2. read-only review；
3. document landing；
4. small patch；
5. recovery simulation。

### Phase 5: Real Task Test Loop

用真实任务测试：

1. normal completion；
2. timeout；
3. user killed process；
4. missing receipt；
5. permission denied；
6. json parse failure；
7. wrong task domain；
8. artifact missing；
9. role boundary violation。

### Phase 6: Governance Hardening

根据真实失败补：

1. pre-action gate；
2. artifact path gate；
3. task domain gate；
4. MCP preflight；
5. DS team_mode enforcement；
6. Codex preflight；
7. YAML active maintenance；
8. anti-drift skill；
9. workflow_core repair。

### Phase 7: Maintainable Workflow OS

长期目标：

```text
可维护
可恢复
可审计
可回滚
可扩展
```

但不在 v0.1 追求一次性完成。

---

## 9. Boundary Rules

### 9.1 Platform Does Not Own Governance

Communication Substrate 只负责：

```text
执行通讯、状态、恢复、证据回收
```

它不负责：

```text
判断任务是否通过
批准版本完成
修改 DS verdict
修改 workflow_core
批准 Codex landing
```

### 9.2 Hermes Uses Platform, Does Not Become Platform Authority

Hermes 可以：

1. 调用 platform；
2. 监控 platform；
3. 执行 task-local repair；
4. 生成 runtime summary；
5. 披露 process issue。

Hermes 不能：

1. 修改 platform contract 的权力边界；
2. 自行扩权；
3. closeout；
4. 修改业务源码；
5. 修改 workflow authority；
6. git commit。

### 9.3 Skill Documents Platform Usage

Skill 不是 runtime 本体。

任何 `SKILL.md` 中出现的代码、命令、路径规范，都必须明确其性质：

```text
operator instruction / usage guide
```

不得把 skill 当成实际平台能力已存在的证据。

---

## 10. DS Team Review Request

### 10.1 Review Type

```text
read_only_architecture_plan_review
```

### 10.2 Required Questions

请 DS Team 审查：

1. v0.2 是否正确修复 v0.1 的“把通讯层误写成 skill”的问题？
2. Communication Substrate 作为工程基座平台是否是正确主线？
3. Python MVP 是否比 Go MVP 更适合当前 bootstrap 阶段？
4. task registry / recovery / stdout-stderr capture 是否是 v0.1 必需能力？
5. 是否应该继续保留任务内 relay_runner 复制模式作为过渡？
6. 是否存在过早平台化、过度工程化？
7. 是否遗漏 Codex / Claude / DS / Hermes 的关键 executor profile？
8. 是否需要更早引入 MCP / settings.local.json preflight？
9. 是否充分防止 Hermes 通过平台建设自我扩权？
10. 下一步应先写 runtime contract、Python MVP 任务卡，还是先写三张角色卡？
11. 是否存在 P0 blocker？

### 10.3 Expected DS Output

```yaml
review_type: read_only_architecture_plan_review
team_mode_used: true | false
mcp_used: true | false
scope_compliance: pass | issue
acceptance_verdict: pass | pass_with_known_issues | patch_required | hold | fail
findings:
  P0: []
  P1: []
  P2: []
  P3: []
process_issues: []
blockers: []
recommended_next_action: []
report_path: <required>
```

---

## 11. Hermes Dispatch Suggestion

Hermes 可将本计划交给 DS Team 审查。

建议任务信息：

```yaml
task_id: ds-review-pm-runtime-communication-substrate-plan-20260522
task_domain: pm-runtime-governance
task_level: M
mode: read_only_architecture_plan_review
executor: DS Team / Claude
owner_control_required: true
```

Required input files:

1. `PM Runtime Communication Substrate Bootstrap Plan v0.2`
2. `pm_runtime_relay_context_packet_2026-05-21.md`
3. `system_failure_analysis_2026-05-22.md`
4. `pm_runtime_skill_review_v0.1_2026-05-22.md`
5. `workflow_core_compact / workflow_compact YAML` if available
6. `pm_runtime_instruction_v0.1.3.md` if available

Forbidden actions:

1. Do not modify files.
2. Do not write code.
3. Do not update workflow_core.
4. Do not claim closeout.
5. Do not expand into Codex landing.
6. Do not treat missing files as nonexistent.

---

## 12. Recommended Immediate Next Step

若 Owner 认可本 v0.2 修正，下一步不是写 `communication_relay/SKILL.md`。

下一步应是让 DS Team 审查本计划。

若 DS Team 无 P0 blocker，则下一步应由 Control Agent 起草：

```text
PM Runtime Communication Substrate Runtime Contract v0.1
```

而不是先写 skill。

之后再进入：

```text
Python Runtime MVP task card
→ Codex implementation dispatch
→ Hermes bootstrap validation
→ role cards
→ operator SKILL.md
```

---

## 13. Final Position

通讯层不是 skill。

通讯层是 PM Runtime 的工程基座平台。

Skill 是人和 agent 使用该平台的操作手册。

当前最小正确路线是：

```text
先定义 runtime substrate
再定义 runtime contract
再实现 Python MVP
再写 operator skill 和角色卡
再上线 bootstrap
再用真实任务测试
再回修 gate / MCP / skills / workflow_core
```
