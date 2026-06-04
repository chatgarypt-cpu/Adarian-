# Safety Gate Follow-up Finding

> 记录时间: 2026-05-22
> 当前状态: recorded_for_followup — 不打断当前 Codex 主线

## Finding

```yaml
finding_id: safety_gate_missing_infrastructure_creation_lane
severity: P1
source_task: pm-runtime-communication-substrate-mvp
observed_blocker: NEEDS_VERSION_ISOLATION（2 次）
impact: approved new infrastructure task blocked because new files are untracked
current_workaround: manual_owner_override_codex_dispatch
recommended_fix: add infrastructure_creation_lane to adarian-iteration-safety-gate
```

## 根因

当前 `adarian-iteration-safety-gate` / Codex safety gate 默认假设：

```
Codex 任务 = 修改已有 tracked 文件
```

但本次通讯层 MVP 是：

```
Codex 任务 = 创建新的 PM Runtime infrastructure 文件
```

不是 taskbook 失败，是 safety gate 缺少合法任务类型。

## 后续补丁方向

safety gate 增加 execution_lane 分支：

```yaml
execution_lane:
  - existing_tracked_file_modification  # 当前默认
  - infrastructure_creation             # 新增
```

`infrastructure_creation` lane 规则：

1. allow new untracked files only under approved allowed_new_file_roots
2. require Owner approval
3. require DS/taskbook readiness if applicable
4. require created_files in Codex receipt
5. still enforce forbidden_files strictly
6. still forbid git commit
7. still require git status capture
8. if untracked files appear outside allowed roots, fail/hold
9. do not treat infrastructure_creation as generic write permission

## 边界

不要现在修。通讯层 MVP 实现完 + DS 验收后，单独开补丁任务。
