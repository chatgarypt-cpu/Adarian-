# /ds-accept — DS 验收判定

## 定位

`/ds-verify` 完成后，对照迭代文档的 Hard / Soft Acceptance Target 做正式验收判定。

**不负责**：不直接把 iteration doc 状态改为 closed、不宣布允许进入下一版本、不替 Control Agent / User 做最终 Gate、不新增下一版本范围、不把 soft issue 自动升级为 blocker。

---

## 触发时机

`/ds-verify` 完成后。

---

## 输入

1. DS Verify Report
2. 当前 iteration document
3. Hard Acceptance Target
4. Soft Acceptance Target
5. Codex attempt report
6. DS Pre-Audit Report（如存在）

---

## 验收逻辑

```text
1. 任一 Hard Target 不满足 → fail / hold
2. 所有 Hard Target 满足，部分 Soft Target 不满足 → pass_with_known_issues
3. Hard / Soft Target 全部满足 → pass
```

---

## 可更新

DS Accept 可以更新：

```text
TASK_LOG.md
CHANGELOG.md
当前 iteration doc 的 acceptance section
```

---

## 输出

### Acceptance Report 最小字段

```text
task_id: task-vX.Y.Z-xxx
audit_id: audit-vX.Y.Z-01 / N/A
attempt_id: attempt-vX.Y.Z-01
acceptance_id: accept-vX.Y.Z-01
acceptance_result: pass / pass_with_known_issues / fail / hold
hard_targets: X/Y
soft_targets: X/Y
carry_over:
  - item 1
  - item 2
closeout_recommendation:
  - allow_closeout / hold / require_fix
```

---

## 格式要求

```text
acceptance_id: accept-vX.Y.Z-01
```

---

## 边界

DS Accept 只能输出：

```text
acceptance_result:
  pass
  pass_with_known_issues
  fail
  hold
```

最终 closeout 由 Control Agent / User 确认。

DS Accept 不得：

1. 直接把 iteration doc 状态改为 closed
2. 宣布允许进入下一版本
3. 替 Control Agent / User 做最终 Gate
4. 新增下一版本范围
5. 把 soft issue 自动升级为 blocker
