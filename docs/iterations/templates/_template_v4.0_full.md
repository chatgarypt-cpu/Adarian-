# 迭代计划模板 v4.1：Runtime-Aware / Agent-Orchestrated Edition

> 模板定位：适用于 A 线正式迭代、B 线目标驱动 DAG、workyb / Runtime 底座狗食测试。  
> 核心原则：不绑定具体模型名，绑定角色、边界、证据、回传协议与 closeout gate。  
> 继承关系：v4 = v3 + Lane Selector + Execution Profile + Runtime Dispatch + DAG Node Contract + Runtime Evidence + Promotion Gate。

---

## 0. Template Mode Selector

### 0.1 Lane

- [ ] A_LINE_FORMAL
- [ ] B_LINE_LIGHTWEIGHT_DAG
- [ ] WORKYB_RUNTIME
- [ ] DOCUMENT_GOVERNANCE
- [ ] DOGFOOD_TEST
- [ ] EXPERIMENT
- [ ] COURSEWORK

### 0.2 Execution Profile

- [ ] A_CONTROLLED_ITERATION  
  Design → Review → Execute → Review → Repair → Acceptance → Closeout

- [ ] B_GOAL_DRIVEN_DAG  
  Goal → Context Completion → DAG Nodes → AI Fix AI → Product Gate → Retrospective

- [ ] HYBRID_DOGFOOD_RUNTIME  
  A 线边界 + B 线 DAG 执行 + Runtime evidence closeout

### 0.3 Governance Weight

- [ ] light
- [ ] medium
- [ ] heavy

### 0.4 Model Binding

```text
本模板不绑定具体模型名。
只声明角色：
- Control Agent
- Orchestrator
- Executor
- Reviewer Team
- Repair Executor
- Owner-Control
```

---

## 1. Version / Task Info

- **版本号**：
- **版本名称**：
- **基于版本**：
- **task_id**：
- **review_id**：
- **attempt_id / node_id**：
- **acceptance_id**：
- **当前阶段**：exploration / planning / execution / validation / repair / closeout
- **状态**：draft / under_review / approved / executing / validating / repair / closed
- **Git Commit / Tag**：`待填写`

---

## 1.5 record_protocol

> **注：** 本模板的 record_protocol 嵌入到具体文件内容中（而非独立文件）。
> 填写迭代计划时，必须在头部声明以下元数据。
>
> record_protocol 是治理入口锁，不是内容合规判断。
> 声明 blocker_status=not_checked 是合法值，closeout_eligible 自动为 false。

```yaml
record_protocol:
  skill_loaded: template-v4-static | template-v4-dynamic | huihua-handoff | phase-retrospective | code-reality-review
  skill_version: 4.1
  record_type: iteration_plan | session_handoff | closeout_record | review_report
  blocker_status: none | present | not_checked
  artifact_quality: pass | pass_with_format_issues | not_checked
  closeout_eligible: true | false
```

### 三态字段定义

| 字段 | none | present | not_checked |
|------|------|---------|-------------|
| blocker_status | 已检查，无已知问题 | 存在已知阻塞，清单见 §Blockers | 未检查阻塞状态。closeout_eligible 自动为 false |
| artifact_quality | 交付物格式/内容通过检查 | 内容完整但有格式瑕疵 | 未检查交付质量 |
| closeout_eligible | 所有条件满足，可 closeout | false | false |

### 写入规则

1. 写迭代计划时必须声明 record_protocol
2. blocker_status 不允许为空字符串或非法枚举值
3. 不要求 blocker_status 必须为 none 或 present。not_checked 是合法值
4. closeout_eligible 不允许跳过

---

## 2. Control Agent Decision

### 2.1 Gate

- [ ] GO
- [ ] CONDITIONAL_GO
- [ ] HOLD
- [ ] FAIL

### 2.2 决策理由

```text
说明：
1. 本任务属于哪条产线；
2. 为什么可以 / 不可以进入执行；
3. 当前 hard blocker；
4. 是否需要前置审查；
5. 是否允许执行器落盘；
6. 是否需要 Owner-Control 额外确认。
```

### 2.3 执行前条件

```text
若 Gate = CONDITIONAL_GO，列出进入执行前必须满足的条件。
若 Gate = GO，可写：无额外前置条件。
```

---

## 3. Goal & Boundary

### 3.1 本轮主目标

```text
一句话说明本轮唯一主目标。
```

### 3.2 要解决的问题

```text
1.
2.
3.
```

### 3.3 不解决的问题

```text
1.
2.
3.
```

### 3.4 禁止变化

```text
1. 不扩大到下一版本。
2. 不修改未授权文件。
3. 不替 Owner-Control 做最终 gate。
4. 不把 review finding 自动升级为任务。
5. 不把 process success 误判为 task success。
```

---

## 4. Runtime Roles

### 4.1 Role Assignment

```yaml
control_agent:
orchestrator:
primary_executor:
reviewer_team:
repair_executor:
sidecar:
owner_control:
```

### 4.2 Role Boundaries

```text
Control Agent:
- 负责边界、任务卡、gate、closeout 建议。
- 不直接修改本地代码。

Orchestrator:
- 负责 dispatch、状态跟踪、result / receipt 回收。
- 不做最终 closeout。

Executor:
- 负责授权范围内的落盘、代码修改、测试执行。
- 不自行扩大 scope。

Reviewer Team:
- 负责只读审查、事实核查、风险发现。
- 不替 Owner-Control 做最终决策。

Owner-Control:
- 负责最终 gate、closeout、是否进入下一步。
```

---

## 5. Execution Profile Detail

## 5A. A_CONTROLLED_ITERATION

适用于：正式版本、底座关键链路、长期接口、权限 / result schema / artifact contract 等高影响任务。

### 5A.1 Flow

```text
Design
→ Pre-Review
→ Controlled Execution
→ Post-Execution Review
→ Repair Loop
→ Acceptance
→ Closeout
```

### 5A.2 Required Stages

```yaml
design_required: true
pre_review_required: true / false
controlled_execution_required: true
post_execution_review_required: true
repair_loop_allowed: true / false
max_repair_rounds:
owner_control_final_gate: true
```

### 5A.3 Repair Policy

```text
允许修：
1.
2.

必须 HOLD：
1.
2.
```

---

## 5B. B_GOAL_DRIVEN_DAG

适用于：课程作业、demo、MVP、实验项目、快速验证任务。

### 5B.1 Owner Goal

```text
描述 Owner 想要达成的目标，而不只是文件修改清单。
```

### 5B.2 Completion Target

- [ ] draft
- [ ] demo
- [ ] usable
- [ ] polished
- [ ] archive-ready
- [ ] promotion-ready

### 5B.3 DAG Nodes

```yaml
nodes:
  - node_id:                  # 对应 task_config.node_id
    role:                     # 执行角色名
    goal:                     # 节点目标
    input:                    # 输入文件/上下文清单
    output:                   # 预期产出物（对应 task_config.expected_outputs）
    allowed_scope:
    forbidden_scope:
    validation:
    dependency:               # 前置 node_id 列表
    receipt_required: true    # 执行后必须生成 node receipt
```

### 5B.4 AI Fix AI Loop

```yaml
ai_fix_allowed: true / false
max_rounds:
issue_packet_required: true / false
owner_escalation_conditions:
```

---

## 5C. HYBRID_DOGFOOD_RUNTIME

适用于：用当前工作流建设 / 测试工作流自身，例如 Relay Runtime、Skill Registry、MCP Registry、Artifact Registry、Handoff Writer。

### 5C.1 Dogfood Target

```text
本任务测试哪条工作流能力？
例如：
- Runtime → Codex dispatch
- Claude Code DAG review
- Skill / MCP Registry 落盘
- result / receipt 回收
- Code Reality Review
```

### 5C.2 Hybrid Rule

```text
目标和边界按 A 线控制；
盘点、审查、样张可用 B 线 DAG；
落盘和 closeout 按 Runtime / A 线证据标准验收。
```

### 5C.3 Dogfood Evidence

```text
必须证明：
1. 调度链路真实发生；
2. 执行器真实产生产物；
3. result / receipt 被回收；
4. 审查节点基于真实代码 / 真实产物；
5. Owner-Control 能基于 evidence closeout。
```

---

## 6. Artifact / Contract

### 6.1 当前结构

```text
列出当前文件 / 目录 / runtime artifact 结构。
```

### 6.2 目标结构

```text
列出本轮完成后的目标结构。
```

### 6.3 Contract Changes

```text
说明是否改变：
- 输入契约
- 输出契约
- result schema
- receipt schema
- artifact path
- permission model
- executor interface
```

### 6.4 Compatibility Strategy

```text
说明旧入口 / 旧字段 / fallback / shim 如何保持兼容。
```

---

## 7. File Change Scope

### 7.1 允许新增

```text
-
```

### 7.2 允许修改

```text
-
```

### 7.3 禁止修改

```text
-
```

### 7.4 必须保持不变

```text
-
```

### 7.5 删除文件

```text
无。
```

如需删除，必须逐项列出理由。

---

## 8. Coupling & Architecture Hygiene

### 8.1 Low-Coupling Check

```text
检查：
1. 是否新增硬编码 if/else；
2. 是否将多个执行器逻辑粘在同一主流程；
3. 是否引入 import cycle；
4. 是否破坏 fallback；
5. 是否把实现细节泄漏到 orchestration 层；
6. 是否符合 Single Change Responsibility；
7. 是否符合 OCP / LSP 方向。
```

### 8.2 Interface / Replacement Check

```text
如果本轮涉及 executor / registry / interface，必须说明：
1. 新增实现是否可替换；
2. 是否能通过统一 contract 调用；
3. 新实现失败时是否能统一回传；
4. 是否破坏旧实现；
5. 后续新增同类实现是否需要改主流程。
```

---

## 9. Runtime Dispatch Plan

### 9.1 Dispatch Mode

- [ ] single_executor
- [ ] readonly_review
- [ ] dag_team
- [ ] codex_landing
- [ ] runtime_smoke
- [ ] dogfood_runtime_test

### 9.2 Dispatch Mode Detail

#### observer_mode

控制执行器运行的可见性和人机交互策略。

```yaml
observer_mode: true                 # 是否打开执行器窗口
observer_attach: terminal_window    # terminal_window | none
permission_mode: human_takeover     # human_takeover | auto_bypass | record_only
permission_fallback:                # 当 human_takeover 超时时
  timeout_sec: 300
  action: hold                      # hold | abort | auto_approve
```

- `observer_attach=terminal_window`：打开 macOS Terminal.app 窗口，真实观察执行器（Gary 原则：可见、可接管、不盲猜）
- `permission_mode=human_takeover`：权限弹窗不自动点，写 permission_request.json、状态标记 WAITING_OWNER_PERMISSION，等人工处理（安全权限不可自动批准）
- `auto_bypass`：仅用于已知安全的 dogfood 测试

### 9.3 Dispatch Artifacts

```text
必须生成：
- task_config:
- dispatch.md:
- result.json / result.yaml:
- receipt.yaml:
- expected_outputs:
- runtime_summary:
```

### 9.3 Stop Conditions

```text
出现以下情况必须 HOLD：
1.
2.
3.
```

---

## 9A. Known Blockers

> **必须由 Owner-Control 或 Control Agent 逐项审核。**

与 record_protocol.blocker_status 联动：
- blocker_status=none → 本节可写"无已知阻拦项"或跳过
- blocker_status=present → 本节必须有至少一项
- blocker_status=not_checked → 本节写"未检查"，closeout_eligible 自动为 false

### 9A.1 已知阻塞

```text
1. （阻塞描述）
   影响范围：
   触发条件：
   已有尝试解决：
   是否在新 iteration 范围内解决：是 / 否
2.
```

### 9A.2 执行协议违规

```text
本次 Registry R0 DAG 执行中 inventory 节点走了 relay dispatch，
但 schema/assembly/validation/review/promotion 节点由 Hermes 直接执行，
未走 task 创建 → relay dispatch → receipt 回收的标准流程。

影响：
- DAG 执行证据链不完整
- 缺少 task_config / dispatch / result 文件
- 无法用 runtime evidence 证明链路真实发生

后续所有 DAG 节点必须严格按照以下流程执行：
1. 读迭代计划，确认节点 input/output
2. 创建 task_dir + dispatch/task_config.yaml + dispatch/prompt.md
3. relay runner dispatch
4. 回收 result.json + receipt
```

### 9A.2 遗留问题（从上一 iteration 带入）

```text
1. （上一轮 known issue，本轮仍未解决）
   延续理由：
   是否在本轮范围内：是 / 否
   如果否，下一个预期解决 iteration：
```

### 9A.3 不视为 blocker 的事项

```text
1. （已知但已决策不排除——如设计取舍、性能非阻塞、暂时兼容性约束）
   决策理由：
   决策者：
```

---

## 10. Verification Plan

### 10.1 Static Check

```bash

```

### 10.2 Import / Unit Test

```bash

```

### 10.3 Runtime Smoke

```bash

```

### 10.4 Artifact Check

```text
必须检查：
1.
2.
3.
```

### 10.5 Regression Check

```text
是否需要回归测试：
- [ ] 是
- [ ] 否

理由：
```

### 10.6 总报告

所有 DAG 节点完成后、closeout gate 前，PM Runtime（Hermes 编排层）必须：

1. 收齐所有节点 receipts
2. 注入 Reality Review 全文
3. 融合生成唯一 `execution_report.md`
4. 压 `summary/pm_runtime_summary.md`
5. 交 closeout gate

详见 skill：`pre-closedout-review` Step 4。

禁止用聊天摘要或口头总结替代总报告。

---

## 11. Runtime Evidence Requirement

```text
必须回收：
1. task_config path
2. dispatch path
3. result path
4. receipt path
5. changed files
6. expected output paths
7. validation commands
8. stdout / stderr / pane_capture path
9. heartbeat / progress path，如适用
10. permission dialog status，如适用
11. fallback_used，如适用
12. timeout status
13. forbidden files check
```

---

## 12. Agent Return Contract

### 12.1 Executor Return Format

```text
STATUS:
CHANGED_FILES:
DIFF_SUMMARY:
VALIDATION:
KNOWN_ISSUES:
RISK:
ARTIFACTS:
NEXT_STEP:
```

STATUS 值引用自 relay_runner FAILURE_CLASSIFICATIONS（工具级分类，在 relay_runner.py 定义，由 classify_result() 返回）：

| 状态 | 含义 | 典型原因 |
|------|------|---------|
| `agent_completed` | 成功完成 | returncode=0 + 产出物存在 |
| `agent_failed` | 执行器失败 | returncode≠0 / 运行时错误 |
| `environment_blocked` | 环境问题 | auth token 过期 / 命令不存在 / 文件系统错误 |
| `permission_blocked` | 权限阻塞 | sandbox 拒绝 / 权限不足 |
| `timeout_or_abort` | 超时或中止 | runtime 墙时 / Owner 手动中止 |
| `missing_receipt` | 收据文件缺失 | 产出物不存在 |
| `missing_report` | 报告缺失 | 报告文件不存在 |

非 agent_completed 状态需要 owner_control_required = true。

### 12.2 Reviewer Return Format

```text
STATUS:
SCOPE:
FINDINGS:
BLOCKERS:
RISKS:
RECOMMENDATIONS:
ARTIFACTS:
VERDICT:
NEXT_STEP:
```

### 12.3 DAG Node Receipt Format

```text
NODE_ID:
ROLE:
INPUTS:
ACTIONS:
OUTPUTS:
VALIDATION:
ISSUES:
DEPENDENCIES:
READY_FOR_NEXT:
```

---

## 13. Acceptance Target & Criteria

### 13.1 Hard Acceptance Target

```text
不满足任一项即 HOLD / FAIL：
1.
2.
3.
```

### 13.2 Soft Acceptance Target

```text
不满足可记录为 known issues：
1.
2.
3.
```

### 13.3 Pass

```text
1.
2.
3.
```

### 13.4 Pass with Known Issues

```text
允许的 known issues：
1.
2.
3.
```

### 13.5 Fail / Hold

```text
出现以下任一情况即 fail / hold：
1. 触碰 forbidden files。
2. 违反 artifact contract。
3. 扩大 scope。
4. 关键 runtime evidence 缺失。
5. 执行成功但无法证明任务完成。
```

---

## 14. Post-Execution Review

### 14.1 Review Scope

```text
Reviewer 只审查：
1.
2.
3.
```

### 14.2 Reviewer Must Not Do

```text
1. 不重新设计版本范围。
2. 不扩大架构。
3. 不把建议项自动升级为 blocker。
4. 不替 Owner-Control 做最终 gate。
```

### 14.3 Code / Reality Mapping Requirement

如涉及代码或 runtime 底座，必须回答：

```text
1. 真实代码结构是什么；
2. 真实调用链是什么；
3. 真实产物流是什么；
4. 设计中有但代码中没有的内容是什么；
5. 是否存在代码粘稠；
6. 是否需要现在修，还是进入 backlog。
```

### 14.4 Review Protocol Reference

本模板适用于 Team Review 流程（多 Agent 并行审查，当前使用 Claude Code agent team 模式）。已沉淀的审查协议：

| 审查流程 | skill / 手册 | 适用场景 |
|---------|-------------|---------|
| Post-Implementation Code Review | `post-implementation-code-review` skill | A 线迭代、底座代码审查 |
| Code Reality Review | `code-reality-review` skill（`~/.claude/skills/code-reality-review/`） | 并行审查 5 agent：Code Reality Mapper / Responsibility Boundary / Runtime Flow Mapper / Design Alignment / Mermaid Synthesizer |
| Relay Runtime Smoke | relay runner smoke 测试 | Runtime + executor 链路验证 |
| Dogfood Test | `dogfood` skill | 端到端产品验证 |

> **重要：** 派发审查时，prompt 里直接用 `@skill code-reality-review` 让 Claude Code 加载，不要自己重新定义审查角色和流程。
>
> Team Review 已知约束（2026-05-30）：
> - 使用 Write() 工具输出报告，不使用 inline editor（避免行号泄漏到报告中）
> - 输出后 read back 检查格式完整性
> - 报告使用中文

---

## 15. Closeout Record

```yaml
iteration:
task_id:
execution_profile:
lane:
governance_weight:
acceptance_result: pass / pass_with_known_issues / fail / hold
result_path:
receipt_path:
artifacts:
changed_files:
validation:
known_issues:
risk:
carry_over:
git_commit:
git_tag:
allow_next_version: true / false
next_step:
```

---

## 16. Promotion / Carry-over Discipline

### 16.1 Carry-over

```text
只记录必须延续的问题。
不要把所有 review finding 自动升级为下一版本任务。
```

### 16.2 Promotion Decision

适用于 B 线 / dogfood / experiment：

```text
是否成为正式资产候选：
- [ ] discard
- [ ] keep_as_B_asset
- [ ] promotion_candidate
- [ ] promote_after_review
```

理由：

```text

```

---

## 17. Notes

```text
本节只记录必要补充。
不要在这里扩展新需求。
不要把新想法伪装成 closeout requirement。
```
