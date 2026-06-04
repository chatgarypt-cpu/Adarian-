# Adarian MVP 开发流程指南

## 定位

本文档是 Adarian 项目的**开发流程指南**，聚焦于"如何使用 superpowers 工作"。

**核心参数定义见 [dev_spec.md](./dev_spec.md) 第3章「核心参数定义手册」**

---

## 工作流程

本项目使用 superpowers 进行流程管理：

| 阶段 | 使用 superpower | 产出 |
|------|----------------|------|
| 需求探索 | `superpowers:brainstorming` | 设计文档 |
| 生成计划 | `superpowers:writing-plans` | 实现计划 |
| 执行实现 | `superpowers:executing-plans` | 代码修改 |
| 验证完成 | `superpowers:verification-before-completion` | 验证报告 |
| 代码审查 | `superpowers:requesting-code-review` | 审查结果 |

---

## 标准开发流程

```
1. 用户提出需求
        ↓
2. brainstorming（探索需求）
        ↓ 产出：docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md
3. writing-plans（生成实现计划）
        ↓ 产出：docs/superpowers/plans/YYYY-MM-DD-<topic>-plan.md
4. executing-plans（执行计划）
        ↓
5. 记录到 TASK_LOG / CHANGELOG
        ↓
6. verification-before-completion（验证）
        ↓
7. requesting-code-review（审查）
```

---

## 执行规范

### 1. 接收计划

阅读实现计划（来自 writing-plans 产出），明确：
- 本次修改的文件范围
- 验收标准
- 预计时间

### 2. 执行修改

- 按计划执行代码修改
- 遵循最小化修改原则
- 新增函数必须包含文档注释（Why 说明）

### 3. 验证

每次修改后必须验证：
```bash
# Python 语法检查
py -m py_compile src/<modified_file>.py

# 端到端运行
py main.py seeds/test1.txt
```

### 4. 记录

- 在 `TASK_LOG.md` 中记录任务开始和完成
- 在 `CHANGELOG.md` 中追加变更记录
- 更新 `docs/iterations/vX.Y.Z_xxx.md` 状态为"✅ 已完成"

---

## 版本命名规范

### 格式

`vX.Y.Z`

| 级别 | 说明 |
|------|------|
| X（主版本） | 重大架构变更 |
| Y（次版本） | 功能迭代 |
| Z（修订号） | Bug 修复、小优化 |

### 当前版本

```
v1.1.9 - MVP 阶段（微观涌现验证）
```

详细版本历史：[CHANGELOG.md](./iterations/CHANGELOG.md)

---

## 核心原则

1. **文档驱动开发**：所有修改必须基于迭代文档
2. **最小化修改**：只改必须改的，不做顺手优化
3. **向后兼容**：除非明确标注 Breaking Change
4. **透明化记录**：所有操作必须在 TASK_LOG 中留痕
5. **遇到不清晰立即提问**：不要猜测用户意图
6. **文档同步**：每次迭代完成后必须检查并更新相关文档

---

## 文档维护规则

### 文档体系

```
README.md              ← 交接入口（任何人第一眼看的）
    ↓
dev_spec.md           ← 【唯一权威信息源】架构、参数定义、版本变更
    ↓
dev_workflow.md       ← 开发流程指南
    ↓
CHANGELOG.md          ← 版本变更历史
    ↓
TASK_LOG.md           ← 开发任务日志
    ↓
docs/iterations/      ← 各版本详细文档
```

### 文档更新责任矩阵

| 文档 | 更新触发条件 | 记录内容 | 责任人 |
|------|------------|---------|--------|
| **README.md** | 项目结构、运行命令、版本信息变化 | 更新结构、核心概念、版本号 | 执行 agent |
| **dev_spec.md** | 架构/参数定义变化 | 在变更记录表中追加一行，修订相关章节 | 执行 agent |
| **CHANGELOG.md** | 任何代码变更 | 追加变更说明（新增/修改/修复） | 执行 agent |
| **TASK_LOG.md** | 任务开始/完成 | 记录开始/完成状态、遇到的问题 | 执行 agent |
| **dev_workflow.md** | 工作流程变化 | 更新流程、命令、自检清单 | 执行 agent |

### dev_spec.md 变更记录表格式

当 dev_spec.md 发生变更时，在文件顶部的变更记录表追加一行：

```markdown
| 日期 | 版本 | 变更内容 | 变更者 |
|------|------|---------|--------|
| 2026-03-30 | v1.1.9 | 新增第3章「核心参数定义手册」 | Claude |
```

### 文档版本同步

所有文档顶部的版本号必须与 dev_spec.md 保持一致。

**版本号检查**：每次任务完成前，检查相关文档的版本号是否需要更新。

---

## 异常处理

---

## 异常处理

### 迭代文档不清晰

停止执行，记录到 TASK_LOG，等待用户澄清。

### 代码修改导致测试失败

停止执行，记录问题，初步分析原因，向用户报告。

---

## 自检清单

每次任务完成前检查：

**代码层面**
- [ ] 我已阅读并理解实现计划的所有要求
- [ ] 我只修改了计划中列出的文件
- [ ] 我为所有新增/修改的函数添加了注释（包含 Why）
- [ ] 我运行了 `py main.py seeds/test1.txt` 验证

**文档层面**
- [ ] 我检查了 dev_spec.md 是否需要更新（架构/参数变更？）
- [ ] 如果 dev_spec.md 变更，我已更新变更记录表
- [ ] 我更新了 CHANGELOG（追加本次变更）
- [ ] 我更新了 TASK_LOG（记录开始和完成）
- [ ] 我更新了 README.md（如果项目结构变化）

**同步层面**
- [ ] 我同步了 outputs 到百度云
- [ ] 我同步了 CHANGELOG 到百度云

---

## 常用命令

| 命令 | 用途 |
|------|------|
| `py main.py seeds/test1.txt` | 运行 test1 模拟 |
| `py -m py_compile src/xxx.py` | 检查 Python 语法 |

---

**文档版本**：v1.1.9
**最后更新**：2026-03-30
**变更记录**：初始版本（整合文档维护规则）
