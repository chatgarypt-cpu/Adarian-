# /ds-verify — DS 后置验证

## 定位

Codex 完成 attempt 交付后，对照迭代文档执行五阶段验证。

**不负责**：不修改代码、不运行 test7（除非迭代文档声明为 hard gate）、不更新 TASK_LOG/CHANGELOG（由 `/ds-accept` 负责）。

---

## 触发时机

Codex 完成一次 attempt 交付后。

---

## 输入

1. Codex 交付说明
2. attempt_id
3. 当前 iteration document
4. 当前 git status
5. 当前 diff
6. 当前 run_dir（如已运行）

---

## Diff 基准

默认基准：`HEAD`。

若 Codex 已产生 commit，则必须使用本轮 iteration 开始前的 `base_commit`。

若 Codex 产生多个 commit，DS Verify 不得使用 `HEAD~1` 猜测基准，必须要求 Codex 提供本轮 iteration 开始前的 `base_commit`。

若无法确认 diff 基准，标记 `partial_fail / hold` 并要求 Control Agent 判断。

---

## 验证步骤

### Phase 1 — 静态检查

```bash
python -m py_compile main.py
python -m compileall src
```

若本版本声明新增 tests：

```bash
python tests/<declared_test>.py
```

### Phase 2 — Forbidden Files 检查

```bash
git diff --name-only <base_commit_or_HEAD>
```

对照 iteration doc §6.3 forbidden files。

若发现 forbidden files 被修改：
- 立即 hard_fail
- 不得继续包装为 pass_with_known_issues

### Phase 3 — Import 完整性检查

根据本版本声明执行 import 测试：

```bash
python -c "from src.phase1 import ..."
python -c "from src.phase1_entity_extraction import ..."
python -c "from src.whitebox import ..."
```

### Phase 4 — Smoke Test

```bash
python main.py seeds/test1.txt
```

若 iteration doc §8.4 声明 `test7` 为 hard gate，则必须执行：

```bash
python main.py seeds/test7.txt
```

### Phase 5 — Artifact Contract 检查

检查最新 run_dir：`outputs/runs/<latest_run_id>/`

必须核验：

```text
run_meta.json
run.log
timing_summary.json
entities_and_relations.json
social_graph.json
tick_logs.json
final_report.json
final_report.md
本版本新增 artifact
```

---

## 输出

```text
attempt_id
base_commit / diff 基准
modified files
forbidden files result
py_compile result
import result
smoke result
artifact result
overall_verify_result: all_pass / partial_fail / hard_fail
```

---

## 边界

DS Verify 不得：

1. 修改代码
2. 运行 test7（除非迭代文档声明为硬门槛）
3. 更新 TASK_LOG / CHANGELOG（那是 accept 阶段的事）
4. 对 forbidden files 做 soft fail
