# Control Agent v3→v4 Transitional Context Packet

> **文档类型**: 过渡期上下文包（Transitional Context Packet）
> **目标读者**: Control Agent（当前 Owner-Control 协作窗口）
> **用途**: 在 workflow_core.md v4.0 正式落盘前，供 Control Agent 临时按 v4.0 口径进行 gate、prompt 和 landing 判断
> **权威声明**: 本文件不是 workflow_core.md 的替代权威源。v4.0 正式落盘后以 `docs/skills/workflow_core.md` 为准。
> **生成日期**: 2026-05-19
> **生成方**: Hermes-PM（基于 R2 一致性修复草案 + 三线审查结果）
> **状态**: transitional / readonly / 不写入 docs/skills/

---

## 0. 快速定位：这份文件是什么、不是什么

**是**：
- Control Agent 在 v3→v4 过渡期的术语对照手册
- 帮助 Control Agent 用 v4.0 口径判断 gate、生成 prompt、评估 landing
- 基于已通过的 R2 草案和三线审查结论

**不是**：
- workflow_core.md v4.0 的正式替代
- Control Agent 的 system prompt 或指令文件
- 对任何 Agent 有约束力的权威规则
- Codex landing 的授权凭据

---

## 1. v3→v4 术语映射

| v3 术语 | v4.0 术语 | 变化说明 |
|---|---|---|
| DS Verify | DS Post-Execution Review（中的验证动作） | 不再作为独立流程节点；verify 是 Review 内部的 checks |
| DS Accept | DS Post-Execution Review（中的 acceptance_verdict 字段） | 不再作为独立流程节点；accept 是 Review 报告的结论字段 |
| DS Verify Report + DS Accept Report | DS Post-Execution Review Report（一份报告） | 两份合并为一份，包含 verify 结果 + acceptance_verdict |
| HOLD / FAIL | repairable_hold / blocking_hold | 细分为可返修阻断和硬阻断 |
| —（无对应概念） | PM Runtime | 新角色：任务中台，负责生成任务书草案、启动已批准任务、回收报告 |
| —（无对应概念） | Patch Loop | 新概念：原范围内小问题自动返修（默认最多 2 次） |
| —（无对应概念） | Patch Lane | 新概念：同版本补丁通道（原范围不变，追加修复） |
| —（无对应概念） | A0 / A1 / A2 批准模式 | A0=单次人工批准，A1=低风险自动批准，A2=DS预审后端到端执行包 |
| —（无对应概念） | workflow_core_compact.md / compact.yaml | 新派生文件：精简运行版 + 机器可读版，非权威源 |
| Hermes = PM Coordinator / 流程助手 | Hermes = PM Runtime | 职责升级：从上下文路由变为任务中台执行 |

---

## 2. v3→v4 路径映射

| v3 路径 | v4.0 路径 | 说明 |
|---|---|---|
| `audit/hermes_tasks/<task_id>/` | `audit/tasks/active/<task_id>/` | 旧路径标记为 legacy/transitional |
| `audit/pm_runtime_tasks/` | `audit/tasks/active/<task_id>/` | 统一到 active 下 |
| `owner_approval.md`（默认审批文件） | `task/approval.yaml`（标准审批记录） | 不再有默认审批文件名 |
| `docs/skills/ds_verify.md` | 内容合并到 DS Post-Execution Review 流程 | v3 验证规范文件需后续更新 |
| `docs/skills/ds_accept.md` | 内容合并到 DS Post-Execution Review 流程 | v3 验收规范文件需后续更新 |

**v4.0 新增路径**：
- `audit/tasks/active/<task_id>/ds/` — DS 报告和回执
- `audit/tasks/active/<task_id>/summary/` — 审查报告
- `audit/tasks/active/<task_id>/runtime/` — result.yaml、运行时记录
- `audit/tasks/active/<task_id>/logs/` — 运行日志
- `audit/tasks/active/<task_id>/scripts/` — relay_runner.py
- `audit/tasks/active/<task_id>/dispatch/` — dispatch.md + system_prompt.md

---

## 3. DS Verify / Accept → DS Post-Execution Review

**v3 流程**：
```
Codex Attempt → DS Verify（5阶段） → DS Accept（Hard/Soft Target 判定） → Closeout
```

**v4.0 流程**：
```
Codex Attempt → DS Post-Execution Review（一份报告，包含 verify checks + acceptance_verdict） → Owner-Control Closeout
```

**对 Control Agent 的影响**：
- 给 DS Team 的 prompt 不再说「请执行 DS Verify 然后 DS Accept」
- 改为「请执行 DS Post-Execution Review，输出包含 verify checks 结果和 acceptance_verdict」
- TASK_LOG 不再有单独的 verify_id 和 acceptance_id，改为 review_id

---

## 4. audit/hermes_tasks → audit/tasks/active/<task_id>

**对 Control Agent 的影响**：
- 迭代文档中引用任务产物路径时，使用 `audit/tasks/active/<task_id>/`
- 旧路径 `audit/hermes_tasks/` 仅作为历史引用存在，新任务不应再使用
- 当前过渡期（v4.0 未正式落盘前），`audit/tasks/active/` 已实际使用

---

## 5. PM Runtime 边界

PM Runtime 是 v4.0 新增的任务中台角色，当前由 Hermes 实现。

**PM Runtime 可以**：
- 根据 Owner/Control Agent 目标生成任务书草案
- 执行已批准任务
- 启动长程 relay（Claude Code via subprocess）
- 维护 heartbeat / progress 跟踪
- 回收 report / receipt / result 等产物
- 向 Owner-Control 汇总任务状态

**PM Runtime 不得**：
- 未经批准启动高风险任务
- 自行扩大任务权限
- 自动 closeout
- 修改项目源码
- git commit
- 把执行摘要伪装成最终 Gate

---

## 6. Hermes 通讯修复边界

Hermes-PM 可以在任务目录 `audit/tasks/active/<task_id>/` 下执行 task-local communication repair：

**允许范围**（路径白名单）：
- `scripts/` — 修复 relay_runner.py
- `runtime/` — result.yaml
- `logs/` — 日志
- `summary/` — 报告
- `ds/` 或 `dispatch/` — 结果回收文件

**允许动作**（仅限 5 类）：
1. 修复 relay_runner / stdout / JSON extraction / heartbeat / progress / result 写入问题
2. 重新提取已完成 agent 输出
3. 补写 runtime_note / process_issue
4. 生成 pm_runtime_summary
5. 在不改变任务目标、prompt、verdict 选项的前提下重试通讯通道

**禁止**：修改 src/、tests/、main.py、config.py、workflow_core.md、迭代文档、contracts

**硬规则**：
1. 修通讯不修源码
2. 修 relay 不修业务逻辑
3. 回收报告不修改结论
4. 标记 process_issue 不降级 blocker
5. 越界立即 HOLD 回 Owner-Control
6. 所有 repair 必须在 pm_runtime_summary 披露

---

## 7. Patch Loop vs Patch Lane

**Patch Loop（小问题自动返修）**：
- DS Post-Execution Review 发现小问题
- 问题在原版本范围内
- Codex 自动返修，默认最多 2 次
- 不创建新任务
- 返修后 DS 重新 Review

**Patch Lane（同版本补丁通道）**：
- 同版本内追加修复需求
- 原范围不变，追加具体修复目标
- 作为 Iteration Document 的 Patch Appendix
- 不创建新版本

**对 Control Agent 的影响**：
- Gate 判断时区分：这是 Patch Loop（小修）还是 Patch Lane（补丁）还是新版本
- HOLD 判定：repairable_hold → 走 Patch Loop；blocking_hold → 回 Owner-Control
- Patch Lane 需要 Control Agent 写 Patch Appendix 追加到迭代文档

---

## 8. Codex First Landing 前置条件

基于 C线（Landing Execution Plan Review）结论：

**第一批落盘**：仅覆盖 `docs/skills/workflow_core.md`

**前置条件**（必须全部满足）：
1. ✅ A线 R2 Structural Review — PASS（当前状态：PASS_WITH_MINOR_NOTES）
2. ⚠️ Control Agent 对齐 v4.0 口径（当前：B线判定 READY_AFTER_CONTROL_AGENT_PATCH）
3. ❌ Owner 明确批准 Codex landing（待批准）
4. ❌ Codex 完成全部静态检查（待执行）
5. ❌ DS Post-Landing path/reference review（待执行）

**禁止触碰**（23 项）：
- workflow_core_compact.md / compact.yaml
- 所有 Agent 指令文件（Control Agent / DS / Codex / Hermes）
- TASK_LOG.md / CHANGELOG.md
- 全部源码（src/、tests/、main.py、config.py）
- 迭代文档、审计文件

**Commit 策略**：no_commit_until_owner_confirmed（C0 模式）

---

## 9. 当前三线审查结论摘要

| 线 | task_id | verdict | 关键发现 |
|---|---|---|---|
| A线 | v4.0-workflow-r2-ds-review-01 | **PASS_WITH_MINOR_NOTES** | R2 草案结构完整，21/21 必检项通过。1 个格式缺陷（§10→§11 缺 `---` 分隔符），不阻塞落盘。team_mode=true, 5 reviewer |
| B线 | v4.0-workflow-rollout-readiness-01 | **READY_AFTER_CONTROL_AGENT_PATCH** | Control Agent 必须先对齐 v4.0 口径。若先落盘再补 Control Agent，会出现 v3/v4 口径分裂窗口期。14 项缺失产物，最小安全上线需 10 步 |
| C线 | v4.0-workflow-landing-execution-review-01 | **LANDING_PLAN_READY_WITH_CONDITIONS** | 第一批仅覆盖 `docs/skills/workflow_core.md`，23 个 forbidden 文件，commit_mode=no_commit_until_owner_confirmed。前提：A线 PASS + Owner 批准 |

**综合判断**：
- 三线无 hard blocker
- B线判定 Control Agent 必须先对齐 → 当前本 packet 即为对齐动作
- A线和C线均已就绪，等待 Control Agent 吸收 v4.0 口径后 Owner 决定是否 Codex landing

---

## 10. Archive / Context 文件路径索引

### 新命名结构

```
audit/tasks/active/workflow-v4-landing/
├── A-r2-review/            ← A线：R2 结构审查
├── B-rollout-readiness/    ← B线：上线准备度审查
├── C-landing-execution/    ← C线：落盘执行计划审查
├── control-context-packet/ ← Control Agent v3→v4 过渡上下文包
└── pm_runtime_summary.md   ← PM Runtime 执行摘要
```

### 权威源与草案

| 文件 | 路径 | 说明 |
|---|---|---|
| v3 现行权威 | `docs/skills/workflow_core.md` | v3.0，当前生效 |
| v4.0 R2 草案 | `audit/workflow_v4.0/workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md` | 6973 行，一致性已修复 |
| v4.0 执行计划 | `audit/workflow_v4.0/workflow_core_v4_r2_review_and_landing_execution_plan_revised_2026-05-19.md` | 三线审查设计 + dispatch prompt |

### 三线审查产物

| 线 | 报告 | 回执 |
|---|---|---|
| A线 | `audit/tasks/active/workflow-v4-landing/A-r2-review/ds/ds_review_report_workflow_core_v4_r2_2026-05-19.md` | `.../ds/ds_receipt.yaml` |
| B线 | `audit/tasks/active/workflow-v4-landing/B-rollout-readiness/summary/workflow_rollout_readiness_report_2026-05-19.md` | `.../runtime/result.yaml` |
| C线 | `audit/tasks/active/workflow-v4-landing/C-landing-execution/summary/workflow_landing_execution_plan_review_2026-05-19.md` | `.../runtime/result.yaml` |

### PM Runtime 汇总

| 文件 | 路径 |
|---|---|
| 执行摘要 | `audit/tasks/active/workflow-v4-landing/pm_runtime_summary.md` |
| Owner Directive | `audit/tasks/active/workflow-v4-landing/*/runtime/owner_directive_task_local_repair.md`（三线各一份） |

### v3 相关文件（过渡期参考）

| 文件 | 路径 |
|---|---|
| DS 前置审计规范 | `docs/skills/ds_pre_audit.md` |
| DS 验证规范（v3，待更新） | `docs/skills/ds_verify.md` |
| DS 验收规范（v3，待更新） | `docs/skills/ds_accept.md` |
| Codex 执行门禁 | `docs/skills/iteration_execution_guard.md` |
| 任务日志 | `docs/iterations/TASK_LOG.md` |
| 变更日志 | `docs/iterations/CHANGELOG.md` |
| 开发规范 | `CLAUDE.md` |

---

---

## 附录 A：v3→v4 关键概念差异速查

| v3 概念（Control Agent 已熟悉） | v4.0 对应 | 一句话变化 |
|---|---|---|
| Owner 人肉复制任务给 Agent | PM Runtime 生成任务书草案，Owner 批准后派发 | Owner 不再做人肉邮差 |
| Owner 人肉整理报告 | PM Runtime 回收报告并生成摘要 | Owner 不再手工整理 |
| DS Verify → DS Accept 两阶段 | DS Post-Execution Review 单报告 | 合并为一份报告 |
| HOLD / FAIL 两种阻断 | repairable_hold / blocking_hold | 区分可返修和硬阻断 |
| 没有 Patch 概念 | Patch Loop（返修）+ Patch Lane（补丁） | 小修不升级为新版本 |
| 没有批准分级 | A0/A1/A2 三级批准 | A1=低风险自动，A2=端到端执行包 |
| `audit/hermes_tasks/` | `audit/tasks/active/` | 新 canonical path |
| `owner_approval.md` | `task/approval.yaml` | 统一审批记录格式 |

---

## 附录 B：v3→v4 行为对齐 — Control Agent / Hermes PM 传达职责

v4.0 不仅是术语和路径变化，更是协作模式升级：**Owner 不再做人肉邮差，Control Agent 必须成为 Owner 的「可执行翻译器」**。

### B.1 Control Agent 必须明确告知 Owner

每次输出时，Control Agent 应让 Owner 一眼看到：

- 当前状态是什么
- 当前阶段是什么
- 当前 blocker 是什么
- 当前唯一下一步动作是什么
- 下一步由谁执行：Owner / Control Agent / Hermes / DS Team / Codex
- 是否需要 Owner 批准

### B.2 Control Agent 必须给出可执行文本，而非抽象建议

进入执行期后，不应只说「建议做 X」，而应直接给出可执行的 prompt：

- 下一步需要 Hermes 派发任务 → 完整 Hermes dispatch prompt
- 下一步需要 DS Team 审查 → 完整 DS Team prompt
- 下一步需要 Codex 落盘 → 完整 Codex execution prompt
- 需要 Owner 转发 → Owner 确认后给出可复制 prompt

### B.3 不应让 Owner 拼提示词、补上下文、猜顺序

Owner 的职责是方向判断、批准和最终 gate，不是人肉邮差或流程调度器。

### B.4 Control Agent 固定输出模板

进入执行期或 landing gate 时：

```
当前状态：
当前阶段：
当前 blocker：
唯一下一步：
执行方：
是否需要 Owner 批准：
如需转交其他 agent，完整 prompt 如下：
```

### B.5 Hermes PM 固定汇报模板

每次汇报时：

```
当前运行状态：
已完成任务：
阻塞任务：
产物路径：
是否需要 Owner 决策：
推荐的唯一下一步：
```

### B.6 Closeout 不等于完成

- Hermes completed ≠ closeout
- DS pass ≠ closeout
- Codex delivered ≠ closeout
- 所有执行结果必须由 Control Agent 转译为 Owner 可判断的下一步 |
