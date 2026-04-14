# Adarian MVP 开发流程指南（当前生效）

## 定位

本文档是 Adarian 的当前生效工作流，采用主从协作：

- Codex：主 Agent，负责代码实现
- MiniMax Claude Code：子 Agent，负责文件管理与测试验收
- 用户：任务决策与结果确认

如与其他流程文档冲突，以本文档和 `workflow_multiagents.md` 为准。

---

## 标准流程

```
1. 用户提出任务
        ↓
2. MiniMax 准备迭代文档并登记 TASK_LOG（开始）
        ↓
3. Codex 完成一轮代码改动并交付
        ↓
4. MiniMax 运行测试并给出通过/失败
        ↓
5. 失败则回传 Codex 继续修复（循环 3-4）
        ↓
6. 通过后 MiniMax 更新 TASK_LOG / CHANGELOG / 迭代文档状态
```

---

## Codex 交付要求

每轮交付给 MiniMax 时应明确：

- 修改文件
- 核心改动
- 预期行为
- 待验证风险（如有）

---

## MiniMax 测试职责

- 语法检查：`py -m py_compile src/<modified_file>.py`
- 端到端检查：`py main.py seeds/test1.txt`
- 按迭代文档验收
- 回传失败信息（可复现）
- 通过后维护项目文档与输出同步

---

## 核心原则

1. 文档驱动开发：改动必须有迭代文档依据
2. 最小化修改：只改任务范围内文件
3. 测试闭环：每轮改动都需 MiniMax 验收
4. 透明记录：TASK_LOG/CHANGELOG 必须同步

---

**文档版本**：v1.1.13
**最后更新**：2026-04-07
**变更记录**：
- v1.1.13：弃用 superpowers 流程，改为 Codex-MiniMax 主从测试闭环
