# _template_v4.2_iteration_contract.md — A 线默认模板

> 四层工作流：Owner Brief → Iteration Contract → Runtime Dispatch → Evidence / Closeout
> 本文件 = 第 1 层（人话）+ 第 2 层（合同）。第 3 层由 Hermes 自动生成，第 4 层由 runtime 自动回收。

---

## 第 1 层：Owner Brief（人话摘要）

> **给你的。30 秒看完。**

**1. 这轮干嘛？**
_{一句话目标}_

**2. 为什么现在做？**
_{背景 / 触发原因}_

**3. 谁调度？谁执行？**
- 调度：Hermes
- 执行：Codex / Claude Code
- 审查：（可省略）

**4. 单节点还是多节点？**
single_node / workflow_dag

**5. 会碰哪些文件？**
_{核心改动文件，3-5 个}_

**6. 做完我看什么？**
_{验收产物，1-3 个}_

**7. 什么情况必须停？**
_{触碰 forbidden files / 跨出 allowed_paths}_

---

## 第 2 层：Iteration Contract（迭代合同）

> **给 Control Agent + Hermes 读的。锁死目标、边界、验收。**

---

### 0. Record Protocol（记录协议）

```yaml
skill_loaded: <加载本模板时加载的 skill>
record_type: iteration_plan
blocker_status: none
artifact_quality: not_checked
closeout_eligible: false
```

---

### 1. Version Info（版本信息）

| 字段 | 值 |
|------|-----|
| 版本号 | v<major>.<minor>.<patch> |
| 基于 | v<prev> |
| 日期 | YYYY-MM-DD |
| 状态 | draft / approved / executing / done |

---

### 2. Control Agent Decision（调度决策）

```yaml
control_agent: Hermes
owner_approval_required: true | false
task_level: S | M | L
```

---

### 3. Goal & Boundary（目标与边界）

**做什么：** _{一句话}_

**不做什么：**
- _{明确排除的范围}_

**允许路径：**
- _{只改这些}_

**禁止路径：**
- _{绝对不能碰的}_

---

### 4. Review / Audit（审查）

- [ ] 不需要审查
- [ ] 需要 Team Review
  - 类型：read-only / full
  - 产出：{审查报告路径}

---

### 5. File Change Scope（文件改动）

```yaml
新文件:
  - <路径>
修改:
  - <路径>
不碰:
  - <特殊说明不改的>
```

---

### 6. Execution Strategy（执行策略）

| 字段 | 值 |
|------|-----|
| shape | single_node（默认）/ workflow_dag |
| executor | Codex / Claude Code |
| observer | true / false |
| dag_nodes | []（默认空，多目标才填） |

---

### 7. Verification（验证）

```yaml
expected_outputs:     # relay_runner 据此做产物检查
  - <路径>
artifact_validation: true
capture_stdout: true
```

---

### 8. Runtime Evidence（运行时证据）

```yaml
receipt: outputs/<executor>_receipt.yaml
result: runtime/result.json
logs: runtime/pane_capture.log
```

---

### 9. Acceptance & Closeout（验收收口）

**完成条件：**
- [ ] expected_outputs 全部存在
- [ ] 未碰禁止文件
- [ ] Owner 确认

**收口记录：** summary/summary.md

---

### 10. Carry-over（遗留项）

_{未解决的、后续处理的}_
