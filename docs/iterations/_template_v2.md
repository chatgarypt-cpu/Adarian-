# 迭代记录：vX.X.X - <迭代标题>

## 📍 版本信息
- **版本号**：vX.X.X
- **任务 ID**：task-vX.X.X-xxx
- **基于版本**：vX.X.X
- **迭代日期**：YYYY-MM-DD
- **Git Commit**：`待填写`
- **状态**：🚧 进行中

---

## 🎯 本次迭代目标

### 问题描述
- 当前存在的问题：
- 影响范围：
- 是否为结构性问题（是/否）：

---

### 解决目标
- 本次希望达成的效果：
- 是否允许 breaking change：
- 本次是否涉及架构调整（是/否）：

---

## 🪪 Workflow Event IDs

- **Review ID**：`review-vX.X.X-01`
- **Attempt ID（最新）**：`attempt-vX.X.X-01`
- **Acceptance ID（最新）**：`accept-vX.X.X-01`

---

# 🧠 架构变更说明（新增关键模块）

### 当前结构问题
- 描述职责过载 / 耦合 / 冗余点

---

### 目标结构（本次之后）
列出模块划分：

- Module A：
- Module B：
- Module C：

---

### 本次迭代涉及层级（必须勾选）

- [ ] Entity Extractor
- [ ] Group Planner
- [ ] Persona Writer
- [ ] Assembler / Rules Engine
- [ ] Phase 2
- [ ] Phase 3

👉 必须明确：**这次只改哪一层**

---

# 🔄 数据流变化（新增关键模块）

### 旧流程
（简述旧数据流）

---

### 新流程（本次迭代后）
（简述新数据流）

---

### 兼容性说明

- [ ] 完全兼容
- [ ] 部分变更（需说明）
- [ ] 不兼容（需迁移）

说明：

---

# 📦 字段职责迁移（新增关键模块）

### 从 LLM 移除（改为代码处理）
- 字段：
- 原因：

---

### 保留在 LLM
- 字段：

---

### 延后生成（未来阶段处理）
- 字段：

---

# 📋 文件变更清单

### 新增文件
- `src/...`

---

### 修改文件
- `src/...`
  - 修改说明：

---

### 删除文件（如有）
- `src/...`

---

### 未修改文件（明确列出）
- `src/...`

---

# 🔧 详细修改指令（给 Codex）

Pre-Implementation Review 输出必须带 `task_id` 与 `review_id`。

每轮 Codex 交付必须带 `attempt_id`。

每轮 MiniMax 验收必须带 `acceptance_id`。

## 任务 1：
**目标**：

**输入**：

**输出**：

**实现要求**：

---

## 任务 2：
（同上结构）

---

## 任务 N

---

# 🔒 实现约束（非常重要）

- 不允许跳过 Pre-Implementation Review
- 不允许用 Prompt 修复结构问题
- 不允许扩展未声明范围
- 优先保证结构正确，其次优化生成质量

---

# ✅ 验收标准（MiniMax 使用）

## 模块级验收

- [ ] 功能是否实现
- [ ] 是否符合架构划分
- [ ] 是否引入额外耦合

---

## 行为验收

运行：

```bash
py main.py seeds/test1.txt
```

---

# 🧊 Closeout Record

```text
iteration: vX.X.X
task_id: task-vX.X.X-xxx
current_tag: iter-vX.X.X-closeout
previous_tag: iter-vX.X.(X-1)-closeout
acceptance: pass / pass_with_known_issues / fail
carry_over:
- item 1
```
