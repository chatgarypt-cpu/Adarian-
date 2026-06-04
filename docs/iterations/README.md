# 迭代计划目录

## 结构

```
docs/iterations/
  active/             ← 当前活跃的迭代计划
    v0.1.0-*.md
    ...
  archived/           ← 已 closeout 的历史迭代计划
    v1.x/
      v1.1.0_baseline.md
      ...
  templates/          ← 模板文件
    _template_v4.0.md
  TASK_LOG.md         ← 任务执行日志（长期维护）
  CHANGELOG.md        ← 版本变更日志（长期维护）
  README.md           ← 本文件
```

## 生命周期

| 状态 | 位置 | 说明 |
|------|------|------|
| 起草 | ~/Downloads/ | iteration-gate hook 自动扫描落盘 |
| 活跃执行 | active/ | 当前版本的迭代计划 |
| 已 closeout | archived/ | 对应版本已完工归档 |
| 模板 | templates/ | 用于创建新迭代计划 |

## 归档

创建 `archived/` 下对应版本号子目录，移入文档。

## 模板

| 文件 | 行数 | 定位 |
|------|------|------|
| `templates/_template_v4.2_iteration_contract.md` | ~56 | **主模板**：Control Agent + Artifact Contract + Runtime Evidence |
| `templates/_template_v4.0_full.md` | ~843 | 备选全量版：L-Level 架构变更、全链路 gate |

由 Control Agent 根据任务等级择一使用。

## 新计划自动落盘

`iteration-gate` hook 自动扫描 `~/Downloads/` 中匹配 `vX.Y.Z-*` 或 `iteration-*` 模式的文件，落盘到 `active/`。
