# 迭代记录：vX.X.X - title

## 1. Version Info

- **版本号**：vX.X.X
- **版本名称**：Title
- **基于版本**：vX.X.X - <Previous Title>
- **当前阶段**：exploration / audit / execution / validation / closeout
- **状态**：draft / under_review / approved / executing / validating / closed
- **task_id**：task-vX.X.X-<topic>
- **audit_id**：audit-vX.X.X-01
- **attempt_id**：
  - attempt-vX.X.X-01
  - attempt-vX.X.X-02
- **acceptance_id**：accept-vX.X.X-01
- **Git Commit / Tag**：`待填写`

---

## 2. Control Agent Decision

### Gate

- [ ] GO
- [ ] CONDITIONAL_GO
- [ ] HOLD
- [ ] FAIL

### 决策理由

```text
填写 Control Agent 的版本判断。

必须说明：
1. 为什么本版本可以 / 不可以进入执行；
2. 当前是否存在 hard blocker；
3. 是否需要 DS 前置审查；
4. 是否允许 Codex 开始落盘。
````

### 执行前条件

```text
若 Gate = CONDITIONAL_GO，列出进入执行前必须满足的条件。
若 Gate = GO，可写：无额外前置条件。
```

---

## 3. Goal & Boundary

### 3.1 本版本主目标

```text
一句话说明本版本主目标。
```

---

### 3.2 本版本要解决的问题

```text
1. 
2. 
3. 
```

---

### 3.3 本版本不解决的问题

```text
1. 
2. 
3. 
```

---

### 3.4 禁止变化

本轮明确禁止：

```text
1. 不改 schema 语义。
2. 不改 prompt 语义。
3. 不改核心业务逻辑。
4. 不改未声明模块。
5. 不删除历史入口。
6. 不扩大到下一版本任务。
```

可按本版本实际情况补充具体文件和模块。

---

## 4. Audit Summary & DS Review Scope

### 4.1 DS Pre-Audit Summary

* **是否经过 DS 前置审查**：是 / 否
* **DS Verdict**：GO / CONDITIONAL_GO / HOLD / FAIL / N/A

DS 关键发现：

```text
1.
2.
3.
```

Control Agent 采纳：

```text
1.
2.
3.
```

Control Agent 不采纳：

```text
1.
2.
3.
```

需要 Codex 注意的风险：

```text
1.
2.
3.
```

---

### 4.2 DS Review Scope

DS 验收时只审查以下区域：

```text
1. Scope Compliance
   - Codex 是否只做了本轮声明的事。
   - 是否越界进入下一版本。

2. File Diff Compliance
   - 是否只修改允许文件。
   - 是否触碰 forbidden files。

3. Import / Shim Integrity
   - 新入口是否可导入。
   - 旧入口是否继续兼容。

4. Artifact Contract
   - 运行产物是否按契约生成。
   - 新增产物路径和字段是否符合文档。

5. Behavior Preservation
   - 是否改变业务行为。
   - 是否修改 schema / prompt / selector / report generation 等禁止区域。

6. Documentation Sync
   - TASK_LOG / CHANGELOG / dev_spec / iteration doc 是否同步。
```

---

### 4.3 DS Must Not Do

DS / 验收 Agent 不负责：

```text
1. 不重新设计版本范围。
2. 不扩大架构。
3. 不把建议项自动升级为 blocker。
4. 不要求进入下一版本。
5. 不替 Control Agent 做最终 gate 判断。
```

---

## 5. Target Structure / Artifact Contract

### 5.1 当前结构

```text
列出当前结构。
```

---

### 5.2 目标结构

```text
列出本版本完成后的目标结构。
```

---

### 5.3 兼容策略

```text
说明旧入口、旧字段、旧产物如何兼容。

例如：
- 旧入口保留 shim。
- 旧 import 路径继续可用。
- 新 package 承载真实实现。
- 旧文件只做 re-export。
```

---

### 5.4 运行产物变化

如本版本涉及运行产物变化，填写：

```text
outputs/runs/<run_id>/
  ...
```

如不涉及，写：

```text
本版本不改变运行产物契约。
```

---

### 5.5 Whitebox / Observability 产物变化

如涉及 whitebox，填写：

```text
outputs/runs/<run_id>/
  whitebox_summary.json
  whitebox/
    ...
```

白盒边界：

```text
whitebox 只能观察、检查、汇总、验证；
不能生成；
不能决策；
不能改变模拟行为；
不能替代 RuntimeLogger；
不能成为 runtime authority。
```

---

## 6. File Change Scope

### 6.1 允许新增

```text
- path/to/new_file.py
```

---

### 6.2 允许修改

```text
- path/to/file.py
  - 修改说明：
```

---

### 6.3 禁止修改

```text
- path/to/forbidden_file.py
```

禁止规则：

```text
除非 Control Agent 明确改写本迭代文档，否则 Codex 不得修改本节文件。
```

---

### 6.4 必须保持不变

```text
- 业务输出契约：
- schema 字段语义：
- prompt 内容：
- selector 策略：
- report generation 语义：
- RuntimeLogger 职责：
```

---

### 6.5 删除文件

```text
无。
```

如确需删除，必须明确列出：

```text
- path/to/delete.py
  - 删除理由：
```

未在本节列出的文件不得删除。

---

## 7. Execution Attempts

### 7.1 Execution Mode

* [ ] Single Attempt
* [ ] Two-Attempt Workflow
* [ ] Multi-Attempt Workflow

选择理由：

```text
说明为什么分阶段 / 不分阶段。
```

---

### 7.2 attempt-vX.X.X-01：<Attempt Name>

目标：

```text
```

允许修改：

```text
```

禁止修改：

```text
```

执行要求：

```text
1.
2.
3.
```

验收命令：

```bash
python -m py_compile ...
python tests/...
python main.py seeds/test1.txt
```

通过条件：

```text
1.
2.
3.
```

---

### 7.3 attempt-vX.X.X-02：<Attempt Name>

目标：

```text
```

允许修改：

```text
```

禁止修改：

```text
```

执行要求：

```text
1.
2.
3.
```

验收命令：

```bash
python -m py_compile ...
python tests/...
python main.py seeds/test1.txt
```

通过条件：

```text
1.
2.
3.
```

---

### 7.4 Attempt Dependency

```text
- attempt-02 是否依赖 attempt-01 通过：
- 是否允许并行：
- 是否允许两个 attempt 同时修改 main.py：
- 如果 attempt-01 fail，attempt-02 是否必须停止：
```

---

## 8. Verification Plan

### 8.1 静态检查

```bash
python -m py_compile ...
```

---

### 8.2 Import / Unit Test

```bash
python tests/...
```

---

### 8.3 Smoke Test

```bash
python main.py seeds/test1.txt
```

---

### 8.4 Regression Test

```bash
python main.py seeds/test7.txt
```

是否作为硬门槛：

* [ ] 是
* [ ] 否

原因：

```text
```

---

### 8.5 Artifact Check

必须检查：

```text
1. run_dir 是否生成。
2. run.log 是否生成。
3. timing_summary.json 是否生成。
4. run_meta.json 是否生成。
5. tick_logs.json 是否生成。
6. final_report.json 是否生成。
7. final_report.md 是否生成。
8. 本版本新增产物是否生成。
```

---

## 9. Acceptance Target & Criteria

### 9.1 Hard Acceptance Target

不满足任一项即 fail / hold：

```text
1.
2.
3.
```

---

### 9.2 Soft Acceptance Target

不满足可记录为 pass_with_known_issues：

```text
1.
2.
3.
```

---

### 9.3 Pass

```text
1.
2.
3.
```

---

### 9.4 Pass with Known Issues

允许的 known issues：

```text
1.
2.
3.
```

---

### 9.5 Fail / Hold

出现以下任一情况即 fail / hold：

```text
1. smoke test 失败。
2. 触碰 forbidden files。
3. 改变业务输出契约。
4. 修改 schema / prompt / selector / report generation 等禁止区域。
5. 发现当前源码事实与迭代文档冲突，且无法在本轮边界内解决。
```

---

## 10. Execution Report Requirement

Codex 完成后必须回传：

```text
1. 实际新增文件清单
2. 实际修改文件清单
3. 实际删除文件清单
4. 每个 attempt 的执行结果
5. 测试命令与结果
6. 最新 run_dir
7. artifact 检查结果
8. 是否触碰 forbidden files
9. 是否改变业务输出契约
10. git diff 摘要
11. carry_over
12. risk level：LOW / MEDIUM / HIGH
```

---

## 11. Closeout Record

```text
iteration: vX.X.X
task_id: task-vX.X.X-<topic>
audit_id: audit-vX.X.X-01
attempt_id:
- attempt-vX.X.X-01
- attempt-vX.X.X-02
acceptance_id: accept-vX.X.X-01
acceptance_result: pass / pass_with_known_issues / fail / hold
git_commit: 待填写
git_tag: 待填写
carry_over:
- item 1
- item 2
是否允许进入下一版本：是 / 否
下一版本建议：
```

---

## 12. Notes

```text
本节只记录必要补充说明。
不要在这里扩展新需求。
不要把 review finding 自动升级为下一版本任务。
```

````

这版 v3 的核心是：

```text
v3 = v2 + Gate + Audit Scope + Attempt + Acceptance Target + Closeout
````


