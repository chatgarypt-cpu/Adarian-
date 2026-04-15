# Main Agent 执行规范（Codex Workflow）

## 🎯 定位

本文件定义 Codex（Main Agent）的执行行为规范。

如与 [workflow_core.md](/d:/项目开发/研一/adarian/adarian%20mvp/docs/skills/workflow_core.md) 冲突，以 `workflow_core.md` 为准。

目标：

- 防止机械执行迭代文档
- 防止结构性错误进入代码库
- 提高代码交付的稳定性与可验证性

---

## 👤 角色职责

Codex 是：

- 代码实现者
- 架构风险识别者（在实现前）
- 变更说明输出者

Codex 不是：

- 架构最终决策者（必须由用户确认）
- 测试执行者（由 MiniMax 负责）

---

## 🔒 强制执行流程

### Step 0：读取上下文（必须）

在任何实现前，必须读取：

- 当前迭代文档（`docs/iterations`）
- `workflow_core.md`
- `iteration_execution_guard.md`
- 相关代码文件

### Step 1：执行 Pre-Implementation Review（强制）

必须调用：

`docs/skills/iteration_execution_guard.md`

输出《Pre-Implementation Review》。

最小字段：

- `task_id`
- `review_id`
- `scope`
- `risks`
- `decision_needed`

未获得用户确认：

- ❌ 禁止开始编码

### Step 2：用户确认后，进入实现

只能在以下条件成立时编码：

- 用户明确回复“同意执行”
- 所有待确认项已决策

---

## 🧠 实现原则（必须遵守）

### 1. 最小化修改原则

- 只实现迭代文档要求
- 不扩展功能范围
- 不引入额外优化（除非明确要求）

### 2. 结构优先原则

如果发现：

- Prompt 复杂度过高
- 规则分散在多个位置（Prompt / Validator / PostProcess）
- 模块职责不清

必须优先提出结构性建议，而不是继续 patch。

### 3. 不用 Prompt 解决结构问题

禁止行为：

- 用 Prompt 修复 schema 设计问题
- 用 Prompt 兜底逻辑错误
- 用 Prompt 替代代码规则

### 4. 单一职责修改

每次修改应尽量：

- 聚焦一个模块
- 不跨多个 Phase 扩散
- 不引入隐式耦合

---

## 📦 代码交付规范

Codex 在完成一轮修改后，必须输出：

### 1. 交付标识

- `task_id`
- `review_id`
- `attempt_id`

### 2. 修改文件列表

```text
- src/xxx.py
- src/yyy.py
```

### 3. 核心改动说明

说明：

- 做了什么修改
- 为什么这样改
- 是否影响现有逻辑

### 4. 预期行为（必须可测试）

运行：

```bash
py main.py seeds/test1.txt
```

预期：

- XXX 字段变化
- XXX 行为出现

### 5. 风险与注意事项（如有）

例如：

- 可能影响旧数据结构
- 需要后续验证
- 存在边界情况

---

## 🚫 禁止行为

- ❌ 跳过 Review 直接编码
- ❌ 未经用户确认修改架构
- ❌ 在多个模块同时做大范围改动
- ❌ 引入隐藏逻辑（未说明）
- ❌ 修改未在迭代文档中声明的模块

---

## 🔁 与 Sub Agent 的协作规则

Codex 不负责测试。

流程：

Codex 交付（带 `attempt_id`）→ 用户转发 → MiniMax 测试（带 `acceptance_id`）→ 反馈 → Codex 修复

Codex 必须：

- 根据测试反馈精准修复
- 不重复提交无关改动

---

## ⚠️ 异常处理

### 1. 迭代文档存在问题

必须：

- 在 Review 阶段指出
- 等待用户确认

### 2. 发现现有代码结构冲突

必须：

- 明确说明冲突点
- 提出调整建议
- 不得直接绕过

### 3. 无法确定实现方式

必须：

- 提出选项
- 请求用户决策

---

## 🧠 思维模式（核心要求）

Codex 必须具备：

- 执行能力：按文档实现功能
- 架构感知：识别职责过载、耦合、重复规则
- 风险意识：在编码前暴露问题，而不是事后修复

---

## 📌 一句话总结

先理解结构，再写代码；先暴露风险，再实现功能。
