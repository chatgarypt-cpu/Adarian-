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

### Project Python Interpreter Rule

如果 DS Verify Report 中：

```text
environment_preflight.status = environment_blocker
```

或出现由解释器环境导致的依赖缺失，例如：

```text
ModuleNotFoundError: No module named 'pydantic'
```

则：

```text
1. acceptance_result 不得直接写 fail。
2. 应写 hold / blocked_by_environment。
3. failure_type = environment_blocker。
4. 不得要求 Codex 修改源码。
5. 必须回传 venv 状态、解释器路径、缺失依赖。
```

只有当 venv preflight 通过，且 import / shim / smoke 仍失败时，才可以继续判断是否为 code_regression。

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
environment_preflight:
  workspace:
  python_executable:
  python_version:
  pydantic_available: true / false
  status: pass / environment_blocker
failure_type: environment_blocker / code_regression / unknown / N/A
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
