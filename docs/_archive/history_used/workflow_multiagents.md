# Adarian MVP 开发流程指南（主从协作版）

## 定位

本文档定义 Adarian 项目的多 Agent 协作流程、角色边界和交付闭环。

核心参数定义见 [dev_spec.md](./dev_spec.md) 第3章「核心参数定义手册」。

---

## 角色分工（固定）

本项目采用固定主从协作，不使用“任意 Agent 任意任务”模式。

- 用户（决策者）：提出需求、确认验收结果、决定是否进入下一轮
- Codex（Main Agent）：负责代码实现与修复，按迭代文档完成具体改动
- MiniMax Claude Code（Sub Agent）：负责项目文件管理、运行测试、记录 TASK_LOG/CHANGELOG、反馈测试结果

---

## 协作通信介质

Agent 之间不直接对话，通过 repo 文件和用户转述协作：

```
迭代文档 → docs/iterations/vX.Y.Z_xxx.md
Codex 代码交付 → src/*.py（及必要说明）
MiniMax 测试结论 → docs/iterations/TASK_LOG.md（并由用户回传给 Codex）
```

---

## 核心流程（强制闭环）

```
1. 用户确认迭代任务
        ↓
2. MiniMax 准备/维护迭代文档与 TASK_LOG（开始状态）
        ↓
3. Codex 实现一轮代码修改
        ↓
4. Codex 交付给 MiniMax（变更文件 + 修改意图 + 预期行为）
        ↓
5. MiniMax 运行测试并给出通过/失败结论
        ↓
6. 失败：MiniMax反馈问题 → Codex继续修复（回到步骤3）
        ↓
7. 通过：MiniMax更新 TASK_LOG/CHANGELOG，执行同步与收尾
```

说明：每一次 Codex 代码输出后，必须先交由 MiniMax 测试；未通过不得直接判定任务完成。

---

## Codex 交付规范（每轮）

每轮代码完成后，Codex 交付内容至少包含：

- 修改文件列表
- 每个文件的核心改动点
- 预期可验证行为（MiniMax据此测试）
- 已知风险/待验证点（如有）

---

## MiniMax 验收职责

MiniMax 在每轮接收 Codex 交付后负责：

- 运行语法检查：`py -m py_compile src/<modified_file>.py`
- 运行端到端测试：`py main.py seeds/test1.txt`
- 按迭代文档逐项验收
- 失败时整理可复现错误信息并回传 Codex
- 通过后更新 `TASK_LOG.md`、`CHANGELOG.md`、迭代文档状态

---

## 文档更新规则

| 文档 | 更新触发条件 | 责任角色 |
|------|-------------|---------|
| `docs/iterations/TASK_LOG.md` | 任务开始、每轮测试结论、任务完成 | MiniMax |
| `docs/iterations/CHANGELOG.md` | 代码变更验收通过后 | MiniMax |
| `docs/dev_spec.md` | 架构/参数定义变化时 | MiniMax（根据 Codex 改动同步） |
| `docs/iterations/vX.Y.Z_xxx.md` | 状态变化或验收补充 | MiniMax |

---

## 异常处理

### 迭代文档不清晰
暂停执行，由 MiniMax 记录到 TASK_LOG，用户澄清后继续。

### 测试失败
MiniMax 输出失败项与错误信息，用户回传 Codex，进入下一轮修复。

### 迭代文档与 dev_spec 冲突
以 dev_spec 为准，MiniMax 记录冲突并通知用户修正文档。

---

## 常用命令

| 命令 | 用途 |
|------|------|
| `py main.py seeds/test1.txt` | 运行端到端模拟 |
| `py -m py_compile src/xxx.py` | Python 语法检查 |

---

**文档版本**：v1.1.13
**最后更新**：2026-04-07
**变更记录**：
- v1.1.13：固定主从协作（Codex 写码 + MiniMax 测试验收），新增“每轮交付-测试-反馈”闭环
- v1.1.12：重构为多 Agent 协作模式，去掉 superpowers 流程，改为产出物驱动
