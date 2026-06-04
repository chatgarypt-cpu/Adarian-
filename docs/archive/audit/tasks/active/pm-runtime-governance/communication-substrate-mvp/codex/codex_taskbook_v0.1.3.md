# v0.1.3 Stdout Artifact Recovery + Readonly Review Yolo Lane

## 新增规则

### readonly_review_yolo_lane

审查类任务允许 yolo 写权限，但边界锁死：
```yaml
# 允许 yolo 写入
allowed_write_scope:
  - 当前 task_dir/summary/**
  - 当前 task_dir/runtime/**
  - 当前 task_dir/logs/**

# 禁止 yolo 写入
forbidden_write_scope:
  - src/**
  - tools/**
  - docs/skills/**
  - workflow_core*
  - workflow_compact*
  - .claude/**
  - .codex/**
  - .hermes/**
  - .git/**
  - dependency files
```

### 适用条件

可以 yolo：
- 只读审查任务
- 写入仅限 task_dir 内
- 不修改源码/workflow/safety gate
- 不安装依赖、不 commit、不 closeout

不可以 yolo：
- 源码实现
- 安全门修改
- workflow_core/compact 修改
- 角色卡修改
- 跨 task_dir 写文件
- 扩大 sandbox
- git 操作

### stdout artifact recovery

当 returncode=0 但 required artifacts 缺失且 stdout 包含报告内容时：
1. 分类为 missing_receipt / missing_report（已在 v0.1.2 实现）
2. recovery 从 stdout 提取报告内容
3. 写入 task_dir 内 recovered_report.md / recovered_receipt.yaml
4. registry 记录 recovery
5. 标记为 trivial_recovery

## 改动范围

- 规则定义（本文）
- task_config 增加 approval_mode / yolo_write_scope 字段
