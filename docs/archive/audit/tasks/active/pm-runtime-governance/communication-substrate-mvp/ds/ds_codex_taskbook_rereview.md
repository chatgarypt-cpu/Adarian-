# DS Team 快速复审报告：PM Runtime Communication Substrate MVP Codex Taskbook v0.2

> **复审类型**: `pre_implementation_taskbook_re_review`
> **复审日期**: 2026-05-22
> **复审团队**: DS Team (Claude Code) — 2 Agent Team Mode (P0-Repair-Verification / P1-Repair-Verification)
> **MCP 使用**: true
> **审查对象**: `audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/dispatch/codex_taskbook.md` v0.2
> **上游审查**: DS Team v0.1 审查（9 P0 / 8 P1 / 7 P2 / 6 P3）

---

## 0. 复审结论

```yaml
acceptance_verdict: pass_with_known_issues
codex_readiness: ready
```

**v0.2 任务书已具备 Codex dispatch 条件。** 所有 9 项 P0 和 8 项 P1 发现均已完整修复。2 项残留 P3 问题（并发模型未显式声明、task_config 路径轻微歧义）不阻塞 MVP 执行，可作为 known_issues 在 Codex receipt 中记录。

---

## 1. 复审方法

### 1.1 Agent Team 组成

| 角色 | 审查维度 | 状态 |
|------|---------|------|
| P0-Repair-Verification | 9 项 P0 修复验证 + 合同对齐 | 完成 |
| P1-Repair-Verification | 8 项 P1 修复验证 + Hermes 补充项 + 模板继承 | 完成 |

### 1.2 审查材料

| 文件 | 路径 | 状态 |
|------|------|------|
| Taskbook v0.2 | `audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/dispatch/codex_taskbook.md` | 已读取 |
| Runtime Contract v0.1 | `audit/workflow_v4.0/hermes pm context/pm_runtime_communication_substrate_runtime_contract_v0.1.md` | 已读取 |
| 前次 DS 审查报告 | `audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/ds/ds_codex_taskbook_review.md` | 已读取 |
| YAML v0.3.3 | `docs/skills/workflow_v4.0/workflow_core/workflow_compact_v0.3.3.yaml` | 已读取 |
| dispatch.template.yaml | `tools/pm_runtime/templates/dispatch.template.yaml` | 已读取 |
| receipt.template.yaml | `tools/pm_runtime/templates/receipt.template.yaml` | 已读取 |

---

## 2. P0 修复验证（9/9 全部通过）

### P0-1: forbidden_files 严重不完整 → **已修复**

v0.1 状态：CLAUDE.md、.venv/**、pyproject.toml、requirements.txt 未受保护

v0.2 §7 现在完整列出：
- `CLAUDE.md`
- `.venv/**`
- `pyproject.toml`
- `requirements.txt` / `requirements*.txt`
- `docs/dev_spec.md`
- `docs/workflow_changelog.md`
- `docs/skills/**` / `docs/skills/workflow_v4.0/**`
- `workflow_compact.yaml` / `workflow_compact_v0.3.3.yaml`
- `.claude/**` / `.codex/**` / `.hermes/**` / `.git/**`
- `tools/**` （带 `!tools/pm_runtime/**` 例外）
- `audit/tasks/active/**` （带 `!communication-substrate-mvp/**` 例外）
- 附加明确禁止操作列表

**结论：通过。禁止文件从 9 项扩展到 22+ 项，覆盖所有关键资产。**

### P0-2: allowed_files 不完整 → **已修复**

v0.1 状态：`tools/pm_runtime/__init__.py` 缺失

v0.2 §6 现在明确列出：
- `tools/pm_runtime/__init__.py`
- `tools/pm_runtime/relay/__init__.py`（额外补充）
- 对 `tools/__init__.py` 设置 HOLD 规则：Codex 必须报告 `HOLD_TOOLS_PARENT_PACKAGE_REQUIRED` 并询问 Owner

**结论：通过。包初始化文件已纳入 allowlist，父包问题有明确的 HOLD 升级路径。**

### P0-3: runtime_state 枚举偏差 → **已修复**

v0.1 状态：YAML 30 个值 vs taskbook 21 个值，缺失 9 个

v0.2 §11.2 现在包含全部 30 个 runtime_state 值，之前缺失的 9 个全部到位：
`not_started`, `running`, `completed`, `failed`, `timeout`, `partial_output_recovered`, `artifact_missing`, `environment_blocked`, `hold_required`

§11.3 "Bad Smell Note" 显式承认 runtime_state 与 task_status 的重叠（running/completed/failed），并指示 Codex 实现兼容性、记录为 known_issue、不得自行重新设计枚举。

**结论：通过。枚举完全对齐 YAML v0.3.3，设计坏味道有明确的处理策略。**

### P0-4: artifact schema 全面缺失 → **已修复**

v0.1 状态：零字段定义，Codex 将自创格式

v0.2 §10 为全部 9 种 artifact 提供完整字段级定义：
- §10.1 `pre_action_check.yaml`：20 个字段（对齐 Contract §7.2）
- §10.2 `registry_events.jsonl`：13 个字段 + 枚举约束（actor/event_type）
- §10.3 `blocker_report.md`：12 个字段
- §10.4 `owner_decision_request.yaml`：17 个字段 + 5 个 available_options
- §10.5 `owner_decision_record.yaml`：11 个字段
- §10.6 `abort_report.yaml`：完整 schema
- §10.7 `recovery_summary.md`：含 recovery_type 枚举
- §10.8 `task_config.yaml`：完整模板，含 paths/runtime_control/scope/executor_options 子字段
- §10.9 `pm_runtime_summary.md`：17 个必填节

**结论：通过。所有 artifact 的字段级 schema 已嵌入，Codex 可直接依此生成。**

### P0-5: abort_report.yaml 缺失 → **已修复**

v0.1 状态：Contract §9.4 强制要求，taskbook artifact 列表未列出

v0.2 §9 Required Runtime Artifacts 中已包含 `runtime/abort_report.yaml`。
§10.6 提供完整 schema：task_id, session_id, round_id, abort_reason, abort_requested_by, abort_approved_by, abort_time, partial_output_preserved, stdout_partial_path, stderr_partial_path, raw_output_partial_path, next_recommendation, owner_control_required。

**结论：通过。**

### P0-6: failure classification 未引用 → **已修复**

v0.1 状态：14 种失败类型完全缺失

v0.2 §13 Failure Classification 列出全部 14 种类型：agent_completed, agent_failed, permission_blocked, sandbox_denied, partial_output, json_parse_failed, no_output, timeout_or_abort, process_killed, environment_blocked, missing_receipt, missing_report, artifact_path_missing, role_boundary_violation。

每条分类必须包含 evidence、confidence、classified_by、requires_independent_review 字段。
明确规则：`role_boundary_violation` 不得由 Hermes 自清。
§8.2 relay_runner.py 职责 11 显式引用 "classify failure using §17"（现为 §13）。

**结论：通过。**

### P0-7: no_heartbeat_timeout_sec=180s 过紧 → **已修复**

v0.1 状态：Codex 启动基线 120-136s，仅剩 14-30s 余量

v0.2 §10.8 task_config 模板和 §12 Runtime Control 均设置 `no_heartbeat_timeout_sec: 300`。
§12 包含明确理由："set to 300s to avoid false timeout during Codex startup, given observed Codex baseline of ~120-136s"。

**结论：通过。300s 确保启动基线后至少 2 个 heartbeat 周期完成。**

### P0-8: receipt schema 严重不匹配 → **已修复**

v0.1 状态：缺少 11 个 YAML receipt_contract 必填字段

v0.2 §20 Layered Receipt Contract 采用分层模型：
- §20.1 Base Required Fields：对齐 receipt.template.yaml 全部必填字段（task_id, task_title, executor, started_at, completed_at, elapsed_sec, status, verdict, team_mode_used, mcp_used, input_files, output_files, modified_files, commands_run, known_issues, blockers, next_recommendation, report_path, receipt_path, summary_path, run_dir, diff_summary, process_issues）
- §20.2 Codex Extension Fields：平台特定字段（changed_files, test_results, handoff_path, commit_status, forbidden_files_touched, runtime_contract_deviations, python_interpreter）
- §20.3 Verdict Values：约束为 5 个允许值，明确 Codex 不得写 closeout

**结论：通过。分层 receipt 模型清晰对齐通用模板并保留 Codex 扩展。**

### P0-9: cli.py 和 relay_runner.py 零行为规范 → **已修复**

v0.1 状态：只有要点列表

v0.2 §8 提供详细行为规范：
- §8.1 cli.py：4 个子命令（init/run/recover/summary）各有 Input/Behavior 步骤/Outputs/Exit codes 完整定义
- §8.2 relay_runner.py：14 项职责 + 完整状态转换图（created → pre_action_checking → launching → healthy_running → {7 种结果状态} → {4 种终态}）
- §8.3 extractors.py：5 个函数签名（含参数和返回类型）+ JSONL 处理规则
- §8.4 recovery.py：5 项 must-implement + 4 项 must-not + recovery 类型区分

**结论：通过。Codex 有足够信息确定性实现每个模块。**

---

## 3. P1 修复验证（8/8 全部通过）

### P1-1: blocker_report 无字段 schema → **已修复**

v0.2 §10.3：12/12 Contract 字段完整定义（task_id 到 owner_control_required）。

### P1-2: owner_decision_request/record 无 schema → **已修复**

v0.2 §10.4（17 字段）+ §10.5（11 字段）：28/28 Contract 字段完整定义。

### P1-3: pm_runtime_summary 无节定义 → **已修复**

v0.2 §10.9：17/17 Contract 必填节枚举，含显式 "PM Runtime summary is not closeout"。

### P1-4: task_config 模板字段不足 → **已修复**

v0.2 §10.8：完整 4 层嵌套（paths/runtime_control/scope/executor_options），所有子字段已展开。

### P1-5: demo 范围模糊 → **已修复**

v0.2 §18：明确 "local_echo executor" 为默认，sandbox 路径解析为 `audit/tasks/.../sandbox/**`，提供 5 项 demo 验证清单。Real Codex 集成在 local demo 通过后测试。

### P1-6: rerun model 缺失 → **已修复**

v0.2 §14：round_id、parent_round_id、rerun_reason、rerun_config_delta 全部到位，含 registry event 追加规范。

### P1-7: docs/dev_spec.md 和 workflow_changelog.md 未受保护 → **已修复**

v0.2 §7：两个文件均已列入 forbidden_files glob 列表。

### P1-8: workflow_compact.yaml 仅散文禁止 → **已修复**

v0.2 §7：`workflow_compact.yaml` 和 `workflow_compact_v0.3.3.yaml` 均已列入 forbidden_files glob 列表。

---

## 4. Hermes 补充项验证（2/2 全部通过）

### A-1: R2 L0-L3 权限分级定义 → **已修复**

v0.2 §15 包含完整 L0-L3 表格，每级有明确的允许/禁止列：

| 级别 | 名称 | 允许 | 禁止 |
|------|------|------|------|
| L0 | 只读回收 | 读 dispatch/receipt/result，生成 summary | 启动新任务、重试执行、修改任务书、改变状态 |
| L1 | 状态修复 | 标记 stalled/incomplete/failed/hold，生成缺失原因说明和 summary | 自动重跑、补写执行方 receipt、替 DS/Codex 生成验收结论、改 failed 为 completed |
| L2 | 同权限重试 | 修复执行通道、同权限重新启动、要求补交 receipt | 改 task_id/goal/executor/读写范围/output/failure_policy、绕过安全扫描 |
| L3 | 任务方案变更 | — | 任何涉及改目标/执行对象/读写范围/验收条件/forbidden files 必须回 Owner 重新批准 |

默认 `runtime_allowed_level: L1`，L2 需 Owner 批准，L3 始终需 Owner 重新批准。

### A-2: HOLD 输出要求 → **已修复**

v0.2 §16 包含 8 项 HOLD 后必须输出的内容：
1. result.yaml
2. pm_runtime_summary.md
3. failure_type
4. existing_artifacts: []
5. missing_artifacts: []
6. l3_touched: true | false
7. recommended_next_action
8. waiting_for_owner_control: true

PM Runtime 不得在 HOLD 后自动继续。

---

## 5. 模板继承检查

### 5.1 Dispatch 模板继承 → **通过**

v0.2 §2-3 建立了清晰的继承链：
```
dispatch.template.yaml (R2 通用基线)
  ↓
Runtime Contract v0.1 (长程 runtime 扩展)
  ↓
This Codex Taskbook v0.2 (具体执行合同)
```

§3 Dispatch Compatibility Block 完整映射了 dispatch.template.yaml 的 17+ 基线字段。
§2.3 包含冲突解决规则：`HOLD_TEMPLATE_CONTRACT_CONFLICT → return_to: Owner-Control`。

### 5.2 Receipt 模板继承 → **通过**

v0.2 §20 采用分层 receipt 模型：基类字段对齐 receipt.template.yaml，Codex 扩展字段独立分区。不另起互不兼容格式。

---

## 6. CLI 和 relay_runner 可执行性评估

### 6.1 CLI 行为规范

| 子命令 | 输入 | 行为步骤 | 输出 | 退出码 | 评估 |
|--------|------|---------|------|--------|------|
| init | --config | 7 步 | 3 文件 | 0/2/3/4/1 | 充分 |
| run | --task-dir | 10 步 | 多文件 | 0/5/6/7/1 | 充分 |
| recover | --task-dir | 6 步 | recovery_summary | 0/6/7/1 | 充分 |
| summary | --task-dir | 5 步 | pm_runtime_summary.md | 0/1 | 充分 |

### 6.2 relay_runner 状态机

状态转换图覆盖从 `created` 到 4 种终态（summary_written/rerun_required/recovered/aborted）的完整路径，含 7 种中间结果状态的分类处理。Codex 可确定性实现。

**结论：CLI 和 relay_runner 行为规范对 Codex 实现足够。**

---

## 7. 残留问题评估

### 7.1 P3-A：并发模型未显式声明

v0.2 未包含显式声明："v0.1 supports one task execution at a time; concurrent task execution is out of scope."

**评估**：可接受。MVP 被描述为 "minimal"，无任何并发特性提及。建议 Owner 在最终批准时追加一行澄清，但不应阻塞 Codex dispatch。

```yaml
p3_concurrency_assessment:
  acceptable_for_mvp: true
  recommendation: "建议在 task_config.yaml 模板或 §5 Source Placement 追加一行：v0.1 MVP 支持单任务执行，并发任务执行不在范围内。"
```

### 7.2 P3-B：task_config 路径歧义

v0.2 在多个位置引用 `task_config.yaml`：
- §5：模板放在 `tools/pm_runtime/templates/`
- §6 allowed_files：`tools/pm_runtime/templates/task_config.yaml`
- §8.1 cli.py init：`--config <task_config.yaml>`
- §9：`dispatch/task_config.yaml`
- §10.8：标题为 `dispatch/task_config.yaml`

存在轻微歧义：模板位置（`tools/pm_runtime/templates/task_config.yaml`）与实例化落盘位置（`dispatch/task_config.yaml`）的关系未显式说明。

**评估**：可接受但有改进空间。Codex 可通过上下文推断：模板在 templates/，实例化在 dispatch/。建议追加一行澄清但不阻塞 dispatch。

```yaml
p3_task_config_path_assessment:
  acceptable_for_mvp: true
  needs_clarification: true
  recommendation: "建议在 §10.8 追加注释：tools/pm_runtime/templates/task_config.yaml 为可复用模板；dispatch/task_config.yaml 为按任务实例化的配置。"
```

### 7.3 其他残留 P2/P3 问题

| # | 问题 | 状态 | 阻塞? |
|---|------|------|-------|
| P2-1 | `communication-substrate-mvp/**` glob 仍较宽泛 | 部分解决（附加禁止操作） | 否 |
| P2-4 | 任务书/Runtime Contract 自身保护仅散文级 | 可接受 | 否 |
| P2-6 | Hermes 16 禁止项未逐条枚举 | 引用 Contract §12.3 | 否 |

以上 P2 残留均不阻塞 Codex 执行，可在 v0.2.1 修补。

---

## 8. 过程问题

| # | 问题 | 严重度 |
|---|------|--------|
| 1 | MCP filesystem 和 Agent Team 已按要求使用 | — |
| 2 | 审查严格保持只读，未修改任何文件 | — |
| 3 | Agent Team 由 2 名 reviewer 组成（P0-Repair-Verification / P1-Repair-Verification），符合任务书要求 | — |
| 4 | 两个 Agent 独立审查结论一致：全部 P0/P1 均已修复 | — |

---

## 9. 阻塞项

**无阻塞项。**

---

## 10. 建议下一步

```yaml
recommended_next_action:
  - action: owner_final_approval
    description: "Owner 最终审批 v0.2 任务书"
    priority: immediate
  - action: hermes_copy_to_iterations
    description: "Hermes 将批准的任务书复制到 docs/iterations/v0.1.0-pm-runtime-communication-substrate-mvp.md"
    priority: after_owner_approval
  - action: codex_dispatch
    description: "触发 Codex safety gate 执行实现"
    priority: after_hermes_copy
  - action: ds_post_execution_review
    description: "Codex 返回后 DS Team 验证实现"
    priority: after_codex_execution
```

---

## 11. 复审元数据

```yaml
review_id: ds-rereview-pm-runtime-communication-substrate-taskbook-v0.2-20260522
review_date: 2026-05-22
executor: DS Team (Claude Code)
review_type: pre_implementation_taskbook_re_review
team_mode_used: true
team_composition:
  - P0-Repair-Verification
  - P1-Repair-Verification
mcp_used: true
mcp_tools:
  - mcp__filesystem__read_text_file
readonly: true
file_modification: none
git_commit: none
input_files:
  - audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/dispatch/codex_taskbook.md
  - audit/workflow_v4.0/hermes pm context/pm_runtime_communication_substrate_runtime_contract_v0.1.md
  - audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/ds/ds_codex_taskbook_review.md
  - docs/skills/workflow_v4.0/workflow_core/workflow_compact_v0.3.3.yaml
  - tools/pm_runtime/templates/dispatch.template.yaml
  - tools/pm_runtime/templates/receipt.template.yaml
target_report_path: audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/ds/ds_codex_taskbook_rereview.md
target_receipt_path: audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/ds/ds_rereview_receipt.yaml
```
