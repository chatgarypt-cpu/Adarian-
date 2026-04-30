# Third Round Audit Checklist

## 0. Purpose

本文件用于第三轮审计。

审计目标不是再讨论设计是否合理，而是核实：

- freeze checklist 是否真的被执行
- control plane retirement plan 是否真的开始执行
- authority model 是否真的收口
- minimal eventization 是否真的开始落地

这是一份执行审计清单，不是建议文档。

---

## 1. Audit Outcome Levels

### Pass

规则已落盘，且执行证据存在。

### Partial Pass

规则已落盘，但只有部分执行证据。

### Fail

规则仍停留在文档层，没有可核实执行结果。

---

## 2. P0 Audit: Freeze Execution

### 2.1 Iteration Closed

检查项：
- [ ] 当前 iteration 文档状态已从进行中改为完成/关闭
- [ ] iteration closeout 时间已记录

证据来源：
- `docs/iterations/*.md`

失败判定：
- 仍显示 `进行中`
- 无 closeout 标记

### 2.2 TASK_LOG Complete

检查项：
- [ ] `TASK_LOG.md` 有开始记录
- [ ] `TASK_LOG.md` 有完成记录
- [ ] 验收结果已写明
- [ ] 已知遗留问题已明确声明是否 carry-over

证据来源：
- `docs/iterations/TASK_LOG.md`

### 2.3 CHANGELOG Updated

检查项：
- [ ] `CHANGELOG.md` 已反映本 iteration 的收口结果
- [ ] 变更边界与 iteration 文档一致

证据来源：
- `docs/iterations/CHANGELOG.md`

### 2.4 Clean Working Tree

检查项：
- [ ] `git status --porcelain=v1` 为空

证据来源：
- git 命令结果

失败判定：
- 任意已跟踪或未跟踪改动残留

### 2.5 Version Anchors Exist

检查项：
- [ ] current tag 已存在
- [ ] previous tag 可明确识别
- [ ] current tag 与 previous tag 已记录到 closeout record

证据来源：
- `git tag --sort=-creatordate`
- closeout record

### 2.6 Closeout Record Exists

检查项：
- [ ] 已生成最小 closeout record
- [ ] 包含 `iteration / current_tag / previous_tag / acceptance / carry_over`

证据来源：
- 指定 closeout 文档或 `TASK_LOG.md`

---

## 3. P0 Audit: Control Plane Retirement Execution

### 3.1 Freeze Achieved

检查项：
- [ ] `control/` 没有新增功能
- [ ] 没有新增脚本继续回写 `control/`

证据来源：
- 新提交 diff

### 3.2 Probe Dependencies Removed

检查项：
- [ ] `reduced_schema_chain_probe.py` 不再读写 `control/state.json` / `control/inbox.md`
- [ ] `p1a_prompt_probe.py` 不再写 `control/inbox.md`
- [ ] `p1g_prompt_probe.py` 不再写 `control/inbox.md`

证据来源：
- `rg -n "control/|state.json|inbox.md" scripts/probes`

失败判定：
- 任一 probe 仍依赖 `control/`

### 3.3 Runtime No Longer Depends on Control

检查项：
- [ ] 主流程运行脚本不再依赖 `control/`
- [ ] 删除或归档 `control/` 不会导致运行时报错

证据来源：
- 代码 grep
- 最小 smoke test

### 3.4 Retirement State Declared

检查项：
- [ ] 主流程文档已声明 control plane 退役
- [ ] `control/` 当前状态已标记为 archive 或 retired

证据来源：
- `workflow_core.md`
- 相关退役文档

---

## 4. P1 Audit: Authority Consolidation

### 4.1 Rule Authority Declared

检查项：
- [ ] `workflow_core.md` 明确声明自己是唯一规则权威源
- [ ] 其他文档不再给出冲突性主流程定义

证据来源：
- `workflow_core.md`
- `CLAUDE.md`
- 其他 workflow 文档

### 4.2 Runtime Authority Declared

检查项：
- [ ] 文档明确运行状态权威源是谁
- [ ] control plane 不再被视为现行状态源

证据来源：
- `workflow_core.md`
- 相关流程文档

### 4.3 No Authority Vacuum

检查项：
- [ ] 退役 control plane 后，仍能明确回答“当前状态以什么为准”

证据来源：
- 主流程文档
- 实际操作示例

---

## 5. P1 Audit: Minimal Eventization

### 5.1 Review ID

检查项：
- [ ] Codex 的 Pre-Implementation Review 已带 `review_id`

### 5.2 Attempt ID

检查项：
- [ ] Codex 每轮交付已带 `attempt_id`

### 5.3 Acceptance ID

检查项：
- [ ] MiniMax 验收记录已带 `acceptance_id`

### 5.4 Task ID

检查项：
- [ ] iteration / TASK_LOG / 交付记录之间存在统一 `task_id`

证据来源：
- iteration doc
- `TASK_LOG.md`
- 交付/验收记录

失败判定：
- 失败反馈仍无法归属到具体轮次

---

## 6. Evidence Package Required

第三轮审计必须附证据，不能只给判断。

最小证据包：
- [ ] `git status --porcelain=v1`
- [ ] `git tag --sort=-creatordate`
- [ ] 当前 iteration 文档状态截图或文本
- [ ] `TASK_LOG.md` 对应 closeout 记录
- [ ] `CHANGELOG.md` 对应版本记录
- [ ] probe 依赖 grep 结果
- [ ] `workflow_core.md` 中 authority 声明

---

## 7. Exit Criteria

只有当以下命题同时成立时，第三轮审计才能判定为 `Pass`：

- freeze checklist 已执行
- control plane 退役 Phase 2 已完成
- authority model 已正式收口
- minimal eventization 已出现最小落点

如果只有文档、没有执行证据，最高只能判 `Partial Pass`。

---

## 8. Final Question Set

第三轮审计结束时，必须能明确回答以下问题：

1. 当前 iteration 是否已经真实 closeout？
2. 当前版本和上一版本分别是谁？
3. 若现在回滚，是否有明确目标与验证路径？
4. control plane 是否已经不再参与运行时？
5. 当前 workflow 的规则权威源和运行状态权威源分别是谁？
6. 一条失败反馈能否定位到具体 attempt？
