# Last Good Commit 定位报告

**调查时间**: 2026-04-22
**目标**: 找到"最后一个 test1 能完整跑通的 commit"，作为唯一恢复起点
**硬约束**: 禁止修改代码、禁止修 bug、禁止恢复架构

---

## 测试方法

从 HEAD 开始，按 git log 顺序逐个执行：
```
git checkout <commit>
py main.py seeds/test1.txt
```

---

## 测试结果

| Commit | Hash | Phase 1 | Phase 2 | Phase 3 | Phase 4 | 失败原因 |
|--------|------|---------|---------|---------|---------|----------|
| HEAD | 4227175 | FAIL | - | - | - | `No module named 'src.phase1'` |
| cd1ef0f | 4227175 | FAIL | - | - | - | `No module named 'src.phase1'` |
| 0a846d7 | 4227175 | FAIL | - | - | - | `No module named 'src.phase1'` |
| 461047b | 4227175 | FAIL | - | - | - | `No module named 'src.phase1'` |
| 163367d | 4227175 | FAIL | - | - | - | `No module named 'src.phase1'` |
| d9d9068 | 4227175 | FAIL | - | - | - | `No module named 'src.phase1'` |
| 25a384e | 4227175 | FAIL | - | - | - | `No module named 'src.phase1'` |
| **a8c95ea** | rollback | **PASS** | **PASS** | FAIL | - | `No module named 'src.phase3.context_builder'` |
| 4c52d2a | v1.1.19 | FAIL | - | - | - | LLM error: `model not found: qwen-turbo` (API 配置问题) |
| c3cdfe6 | v1.1.4 | FAIL | - | - | - | LLM error: `model not found: qwen-turbo` (API 配置问题) |

---

## 关键发现

### 1. 问题引入区间

**first_bad_commit**: `25a384e` ("chore: structure cleanup - archive historical files")

在 `25a384e` 之后（包含 25a384e 本身），所有 commit 的 `phase1_entity_extraction.py` 都包含：
```python
from src.phase1.orchestrator import run_phase1_orchestrator_from_file
```
但 `src.phase1/` 目录从未创建，导致 Phase 1 入口失败。

### 2. 第一个"接近成功"的 commit

**a8c95ea** ("On master: pre-manual-rollback-2026-04-22")

该 commit 是一个 merge commit，撤销了对 `phase1_entity_extraction.py` 的破坏性修改：
- 移除了 `from src.phase1.orchestrator import` 死代码
- 恢复了 `extract_entities_with_validation()` 直接实现
- 同时修改了 `config.py` 和 `speaker_selector.py`

**结果**: Phase 1 和 Phase 2 **PASS**，但在 Phase 3 入口失败（`src.phase3.context_builder` 不存在）

### 3. 更老的 commit 问题

更老的 commit（如 `4c52d2a`、`c3cdfe6`）使用的是 `qwen-turbo` 模型，该模型在当前 API 配置下不可用（返回 422），属于**运行环境问题**，不是代码问题。

---

## 结论

### last_good_commit

**a8c95ea** — "On master: pre-manual-rollback-2026-04-22"

- Phase 1: ✅ PASS
- Phase 2: ✅ PASS
- Phase 3: ❌ FAIL (`No module named 'src.phase3.context_builder'`)
- Phase 4: 未测试

### first_bad_commit

**25a384e** — "chore: structure cleanup - archive historical files"

### 问题引入区间

```
a8c95ea (rollback, good)
   ↓
25a384e (first_bad, 引入了 src.phase1.orchestrator 死导入)
   ↓
   ... (一系列失败 commits)
   ↓
4227175 HEAD (current, still broken)
```

### 结论说明

**没有找到任何一个"完整跑通 test1"的 commit**。

最接近的是 `a8c95ea`，它能完成 Phase 1 和 Phase 2，但在 Phase 3 入口就失败了（缺少 `src.phase3.context_builder` 等三个子模块）。

这是因为 Phase 3 的解耦目标（`context_builder`、`simulation_card`、`state_updater`）从未实现，源码中只是写上了 import 语句。

---

## 唯一结论

**last_good_commit: a8c95ea**
**first_bad_commit: 25a384e**

**当前源码不适合作为恢复起点**，因为即使在 a8c95ea，Phase 3 依赖的子模块也全部缺失，无法完成端到端运行。

**建议的下一步单一行动**: 以 a8c95ea 为基准，创建 `src/phase3/` 子模块（`context_builder.py`、`simulation_card.py`、`state_updater.py`），或者降级 Phase 3 到 a8c95ea 之前的旧单文件架构。
