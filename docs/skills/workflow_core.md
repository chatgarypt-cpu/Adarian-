# Adarian MVP 核心开发工作流（Workflow Core）

## 🎯 定位

本文件是 Adarian 项目的唯一流程规则权威源。

- 规则权威源：`docs/skills/workflow_core.md`
- 运行状态权威源：当前 iteration 文档状态 + `docs/iterations/TASK_LOG.md` 验收记录
- 已退役组件：`control/` 与 `scripts/generate_snapshot.py` 只保留历史证据价值，不再参与现行流程

如与其他 workflow 文档冲突，以本文件为准。

---

## 👥 角色分工（固定）

- **用户（决策者）**
  - 定义任务
  - 审核方案
  - 决定是否进入下一阶段

- **Codex（Main Agent）**
  - 负责代码实现与修复
  - 必须遵循 iteration 文档执行
  - 必须先完成 `Pre-Implementation Review`
  - 必须在每轮交付中声明 `attempt_id`

- **MiniMax Claude Code（Sub Agent）**
  - 负责测试与验收
  - 负责更新 `TASK_LOG.md`、`CHANGELOG.md`、iteration 文档
  - 必须在验收记录中声明 `acceptance_id`

---

## 🔐 Authority Model

### Rule Authority

所有流程规则、gate、closeout 条件只由本文件定义。

### Runtime Authority

当前运行状态只看两类事实：

- iteration 文档中的状态字段
- `docs/iterations/TASK_LOG.md` 中最新的验收记录

以下内容不是现行状态源：

- `control/state.json`
- `control/inbox.md`
- `control/snapshot.md`
- 任何 probe 运行摘要

### No Authority Vacuum

若有人问“当前任务状态以什么为准”，答案必须总是：

1. 先看当前 iteration 文档状态。
2. 再看 `TASK_LOG.md` 中对应 `task_id` / `acceptance_id` 的最新验收结论。

---

## 🔗 协作通信机制

Agent 不直接对话，通过 repo artifacts + 用户中转协作：

- iteration 文档：`docs/iterations/vX.Y.Z_xxx.md`
- Codex `Pre-Implementation Review`：带 `review_id`
- Codex 交付：代码变更 + 修改说明 + `attempt_id`
- MiniMax 验收：`TASK_LOG.md` 记录 + `acceptance_id`

用户中转是现行机制的一部分，不是例外行为。

---

## 🧭 核心流程（强制闭环）

1. 用户确认一个 iteration 任务。
2. MiniMax 准备 iteration 文档，并写入 `task_id` 与开始状态。
3. Codex 读取 iteration 文档、本文件、`iteration_execution_guard.md` 和相关代码。
4. Codex 输出带 `review_id` 的 `Pre-Implementation Review`。
5. 用户确认 Review 结论。
6. Codex 实现一轮代码修改，并输出带 `attempt_id` 的交付说明。
7. MiniMax 运行测试，并写入带 `acceptance_id` 的验收记录。
8. 若失败，用户转发失败信息给 Codex，进入下一轮修复。
9. 若通过，MiniMax 更新 `TASK_LOG.md`、`CHANGELOG.md` 与 iteration 文档状态。
10. iteration closeout 前必须执行 [git_freeze_checklist.md](/d:/项目开发/研一/adarian/adarian%20mvp/docs/audit/workflow/git_freeze_checklist.md)。

---

## 🪪 Minimal Eventization

现行 workflow 的最小事件字段如下：

- `task_id`：iteration 级唯一任务标识
- `review_id`：一次实现前审查
- `attempt_id`：Codex 的一次交付轮次
- `acceptance_id`：MiniMax 的一次验收结论

最小要求：

- iteration 文档必须声明 `task_id`
- `Pre-Implementation Review` 必须声明 `review_id`
- 每次 Codex 交付必须声明 `attempt_id`
- `TASK_LOG.md` 验收记录必须声明 `acceptance_id`

如果失败反馈不能定位到具体 `attempt_id`，则视为闭环不完整。

---

## ⚠️ 实现前强制门禁

在任何编码开始前，Codex 必须执行：

`docs/skills/iteration_execution_guard.md`

未完成 Review：

- ❌ 不允许写代码
- ❌ 不允许提交修改

---

## 📦 Codex 交付规范

每轮代码交付必须包含：

- `task_id`
- `attempt_id`
- 对应 `review_id`
- 修改文件列表
- 每个文件的核心改动
- 预期可验证行为
- 已知风险或待验证点

---

## 🧪 MiniMax 验收职责

每轮交付后必须执行：

### 基础检查

`py -m py_compile src/<modified_file>.py`

### 端到端测试

`py main.py seeds/test1.txt`

### 验收记录最小字段

- `task_id`
- `attempt_id`
- `acceptance_id`
- `acceptance_result`
- `carry_over`

### 验收后操作

- 更新 `TASK_LOG.md`
- 更新 `CHANGELOG.md`
- 更新 iteration 文档状态

---

## ✅ Closure Rules

### Task Complete

只有当某个 `attempt_id` 已被 `acceptance_id` 明确标记为通过，任务才算完成。

### Iteration Complete

只有当以下条件同时成立，iteration 才算完成：

- 已有通过的验收记录
- 已声明 carry-over items
- 已准备 closeout record

---

## 🧊 Freeze And Rollback Governance

iteration closeout 必须遵守 [git_freeze_checklist.md](/d:/项目开发/研一/adarian/adarian%20mvp/docs/audit/workflow/git_freeze_checklist.md)。

最小 gate：

- iteration 文档状态已关闭
- `TASK_LOG.md` 已记录完成
- `CHANGELOG.md` 已更新
- 当前版本锚点和上一版本锚点明确
- 工作树干净

如果 `git status --porcelain=v1` 非空，或无法明确上一版本是谁，不得宣称“当前 iteration 可回滚”。

### Minimal Closeout Record

每次 closeout 至少记录：

```text
iteration: vX.Y.Z
task_id: task-vX.Y.Z-xxx
current_tag: iter-vX.Y.Z-closeout
previous_tag: iter-vX.Y.(Z-1)-closeout
acceptance: pass / pass_with_known_issues / fail
carry_over:
- item 1
- item 2
```

---

## 📄 文档更新规则

| 文档 | 更新触发 | 责任 |
|------|--------|------|
| `TASK_LOG.md` | 每轮验收结果 | MiniMax |
| `CHANGELOG.md` | 验收通过后 | MiniMax |
| iteration 文档 | 状态变化 / closeout | MiniMax |
| `dev_spec.md` | 架构变化 | MiniMax |

---

## 🚨 异常处理

### 1. iteration 文档不清晰

- 停止执行
- MiniMax 记录 `TASK_LOG`
- 等待用户澄清

### 2. 测试失败

- MiniMax 输出错误信息
- 必须附带 `attempt_id`
- 用户转发 Codex
- 进入下一轮修复

### 3. 文档与代码结构冲突

- Codex 必须在 Review 阶段指出
- 不允许直接按文档强行实现
- 必须等待用户确认

---

## 🧠 核心原则

1. **文档驱动开发**
   所有修改必须基于 iteration 文档。

2. **先审查再实现**
   必须先做带 `review_id` 的 `Pre-Implementation Review`。

3. **最小化修改**
   不做额外优化，不扩大范围。

4. **测试闭环**
   未经 MiniMax 验收，不算完成。

5. **透明记录**
   所有任务状态必须能落到 `task_id / review_id / attempt_id / acceptance_id`。

---

## 🔗 关联文档

| 文档 | 作用 |
|------|------|
| `iteration_execution_guard.md` | 实现前架构核对 |
| `main_agent_delivery.md` | Codex 行为规范，若冲突以本文件为准 |
| `subagent_test_and_docs.md` | MiniMax 职责细化，若冲突以本文件为准 |

---

## 📌 一句话总结

> 本文件定义规则，iteration 文档与 `TASK_LOG.md` 定义运行事实，control plane 已退役为历史证据。
