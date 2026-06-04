# Demo 迭代计划 — v4.2.0 补 G5 产物完整性 Validator

> **演示 v4.2 四层模板的完整填写。**
> 场景：Control Agent 决策 → 补 G5 设计缺口（relay_runner 收尾校验 expected_outputs）

---

## 第 1 层：Owner Brief（人话摘要）

**1. 这轮干嘛？**
给 relay_runner 加一个收尾检查：跑完后自动验证 expected_outputs 文件存在且非空。

**2. 为什么现在做？**
G5 是 Control Agent 判定"Go2 前必须修"的唯一缺口，直接增强产物验收的可靠性。不做的话迁移后缺文件没人知道。

**3. 谁调度？谁执行？**
- 调度：Hermes
- 执行：Codex（单节点、高约束工程落盘）
- 审查：不需要

**4. 单节点还是多节点？**
single_node。一个 executor 搞定，不改其他模块。

**5. 会碰哪些文件？**
- `WorkflowBase/runner/relay_runner.py`（加一个函数 + 一行调用）

**6. 做完我看什么？**
- 语法检查通过
- 跑一次模拟 relay dispatch，确认 `outputs/expected_outputs_validation.json` 生成

**7. 什么情况必须停？**
- 改了 relay_runner.py 之外的文件
- expected_outputs 检查阻塞了正常的 executor 完成流程

---

## 第 2 层：Iteration Contract（迭代合同）

---

### 0. Record Protocol

```yaml
skill_loaded: template-v4.2-iteration-contract
record_type: iteration_plan
blocker_status: none
artifact_quality: not_checked
closeout_eligible: false
```

---

### 1. Version Info

| 字段 | 值 |
|------|-----|
| 版本号 | v4.2.0 |
| 基于 | v4.0 Reality Review |
| 日期 | 2026-06-04 |
| 状态 | approved |

---

### 2. Control Agent Decision

```yaml
control_agent: Hermes
owner_approval_required: false
task_level: M
```

---

### 3. Goal & Boundary

**做什么：** relay_runner 执行完成后，校验预期的产物文件存在且非空，结果写入 `outputs/expected_outputs_validation.json`。

**不做什么：**
- 不改 executor 逻辑

**允许路径：**
- `WorkflowBase/runner/relay_runner.py`

**禁止路径：**
- `WorkflowBase/runner/codex/`
- `WorkflowBase/runner/claude/`
- `WorkflowBase/registry/`
- `docs/`

---

### 4. Review / Audit

- [x] 不需要审查
- [ ] 需要 Team Review

---

### 5. File Change Scope

```yaml
新文件:
  - WorkflowBase/runner/relay_runner.py（改动）
修改:
  - WorkflowBase/runner/relay_runner.py
不碰:
  - 注册表、executor、docs 全部不改
```

---

### 6. Execution Strategy

| 字段 | 值 |
|------|-----|
| shape | single_node |
| executor | Codex |
| observer | true |
| dag_nodes | [] |

---

### 7. Verification

```yaml
expected_outputs:
  - 语法检查通过（python -m py_compile）
  - expected_outputs_validation.json 可正常写入
artifact_validation: true
capture_stdout: true
```

---

### 8. Runtime Evidence

```yaml
receipt: outputs/codex_receipt.yaml
result: runtime/result.json
logs: runtime/pane_capture.log
```

---

### 9. Acceptance & Closeout

**完成条件：**
- [x] `relay_runner.py` 语法检查通过
- [x] 模拟 run_task 收尾时正常输出 validation.json
- [x] 未碰禁止路径中的任何文件
- [x] 已有代码（G5 实现在 `_check_expected_outputs` 中）已在运行时验证

**收口记录：** summary/summary.md

---

### 10. Carry-over

G6（workflow_map.yaml 的 `--generate-map` 模式）已在 `drift_check.py` 中实现，无需额外迭代。
