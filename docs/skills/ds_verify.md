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

## Project Python Interpreter Rule

本项目在本地 Mac 工作区运行时，项目依赖安装在项目虚拟环境 `.venv` 中。

默认工作区：

```text
/Users/gary/项目开发/AdarianMigration/adarian mvp
```

默认 Python 解释器：

```bash
./.venv/bin/python
```

禁止默认使用：

```text
python
python3
/usr/bin/python3
```

原因：

```text
系统 Python 通常没有安装项目依赖，例如 pydantic。
如果使用系统 Python 执行 import / smoke，可能误报：
ModuleNotFoundError: No module named 'pydantic'
```

在本项目中，出现 `No module named 'pydantic'` 时，应优先判断为解释器环境错误，而不是源码错误。

在执行任何 Python 检查前，DS Team 必须先运行：

```bash
cd "/Users/gary/项目开发/AdarianMigration/adarian mvp"

./.venv/bin/python --version
./.venv/bin/python -c "import sys; print(sys.executable)"
./.venv/bin/python -c "import pydantic; print('pydantic=', pydantic.__version__)"
```

如果上述检查通过，后续所有 Python 命令统一使用：

```bash
./.venv/bin/python -m py_compile ...
./.venv/bin/python tests/xxx.py
./.venv/bin/python main.py seeds/test1.txt
```

如果 `./.venv/bin/python` 不存在、不可执行，或 `pydantic` 缺失：

```text
1. 标记为 environment_blocker。
2. 不得判定为源码回归。
3. 不得要求 Codex 修改源码。
4. 回传 venv 状态、解释器路径、缺失依赖。
5. 等待 Control Agent / User 决策。
```

DS Verify 输出中必须包含：

```text
environment_preflight:
  workspace:
  python_executable:
  python_version:
  pydantic_available: true / false
  status: pass / environment_blocker
```

结果分类规则：

```text
1. 如果 venv preflight 失败，overall_verify_result 不得直接写 hard_fail。
2. 应写 hold / blocked_by_environment。
3. failure_type = environment_blocker。
4. 如果 venv preflight 通过，但 import / shim / smoke 失败，才可以继续判断是否为 code_regression。
```

---

## 验证步骤

### Phase 0 — Environment Preflight

先执行 Project Python Interpreter Rule 中的 venv preflight。

只有 `environment_preflight.status = pass` 后，才允许进入静态检查、import test、smoke test。

### Phase 1 — 静态检查

```bash
./.venv/bin/python -m py_compile main.py
./.venv/bin/python -m compileall src
```

若本版本声明新增 tests：

```bash
./.venv/bin/python tests/<declared_test>.py
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
./.venv/bin/python -c "from src.phase1 import ..."
./.venv/bin/python -c "from src.phase1_entity_extraction import ..."
./.venv/bin/python -c "from src.whitebox import ..."
```

### Phase 4 — Smoke Test

```bash
./.venv/bin/python main.py seeds/test1.txt
```

若 iteration doc §8.4 声明 `test7` 为 hard gate，则必须执行：

```bash
./.venv/bin/python main.py seeds/test7.txt
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
environment_preflight:
  workspace:
  python_executable:
  python_version:
  pydantic_available: true / false
  status: pass / environment_blocker
failure_type: environment_blocker / code_regression / unknown / N/A
```

---

## 边界

DS Verify 不得：

1. 修改代码
2. 运行 test7（除非迭代文档声明为硬门槛）
3. 更新 TASK_LOG / CHANGELOG（那是 accept 阶段的事）
4. 对 forbidden files 做 soft fail
