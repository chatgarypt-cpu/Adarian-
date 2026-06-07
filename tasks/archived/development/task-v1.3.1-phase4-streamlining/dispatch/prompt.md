use a workflow to: execute v1.3.1 — Phase4 Streamlining & Entrypoint Unification

@skill karpathy-coding

执行依据：docs/iterations/active/v1.3.1_phase4_streamlining_and_entrypoint_unification_r1.md

这是一个 5-Goal DAG，Goal 之间有依赖链（A→B→C→D→E）。按顺序执行，每个 Goal 完成后自我验收再进下一个。

---

## Goal A — Legacy Archive Landing（🔁 部分已完成，只补剩余文件）

**状态：** `legacy/__init__.py`、`legacy/phase4/__init__.py`、`legacy/phase4/legacy_analytics.py` 已存在，**不要重写**。

**还缺（只创建下面三个文件）：**
- 新建 `legacy/main_legacy.py`（当前 main.py 完整复制，import 改为 `from legacy.phase4.legacy_generation import generate_report_with_llm`）
- 新建 `legacy/phase4/legacy_generation.py`（旧生成全路径）
- 新建 `legacy/phase4/legacy_markdown.py`（旧 markdown）

函数归属见迭代计划 §A.3。

**验收：**
```bash
.venv/bin/python -m py_compile legacy/main_legacy.py legacy/phase4/*.py
```

**红线：** legacy 不依赖 clean src.phase4，保留旧函数。已存在的文件不要碰。

---

## Goal B — Clean Phase4 Consumer Cleanup（删除）

**变化理由：** src.phase4 应只做纯消费端。

**做什么：** 从 report_agent.py 删除旧计算函数和全局变量，只保留纯 consumer 函数。

**文件变更：**
- 修改 `src/phase4/report_agent.py` — 删除旧函数、_llm_generated_markdown、__main__ block、dead imports
- 修改 `src/phase4/__init__.py` — 只导出 5 个 consumer 符号

保留/删除清单见迭代计划 §B.3-§B.4。

**重点：**
- `save_markdown_report(markdown=...)` 必须强制显式 markdown，删除 fallback
- `parse_llm_report_response` 只保留 dataset 路径，删除 dataset=None 分支
- `_build_code_owned_report_contract_block` 只保留 dataset 路径，删除 else-branch
- `report_narrative.py` 签名确认，不反向依赖 legacy

**验收：**
```bash
.venv/bin/python -m py_compile src/phase4/report_agent.py src/phase4/__init__.py src/phase4/report_narrative.py
```

---

## Goal C — Entrypoint Unification & Function Extraction（替换+抽取）

**变化理由：** 产品应只有一个主入口；main.py 只做编排。

**做什么：** main_new.py → main.py；将工具函数抽到对应模块。

**文件变更：**
- 新建 `src/phase4/paths.py`（接收 build_run_paths）
- 新建 `src/whitebox/run_meta.py`（接收 write_run_meta / write_whitebox_summary / write_whitebox_artifacts）
- 修改 `src/phase4/report_narrative.py`（接收 _build_report_context_new）
- 修改 `main.py`（基于 main_new.py，删除 _run_bypass_comparison，横幅 Adarian v1.3.1）
- 归档 main_new.py

**验收：**
```bash
.venv/bin/python -m py_compile main.py src/phase4/paths.py src/whitebox/run_meta.py
```

---

## Goal D — Tests / Tools Import Migration（import 替换）

**变化理由：** 旧计算函数已移入 legacy，import 必须更新。

**文件变更：** 12 个 tests/tools 文件的 import 从 `src.phase4` → `legacy.phase4`。

详见迭代计划 §D.2 文件清单。新增 4 个测试文件：
- `tests/test_phase4_pure_consumer_boundary.py`
- `tests/test_phase4_no_legacy_compute_at_runtime.py`
- `tests/test_phase4_export_shape.py`
- `tests/test_phase4_legacy_shielded_e2e.py`

**验收：**
```bash
.venv/bin/python -m pytest tests/test_phase4_new_consumer_wiring.py tests/test_phase_package_imports.py -v
.venv/bin/python -m pytest tests/test_phase4_pure_consumer_boundary.py -v
.venv/bin/python -m pytest tests/test_phase4_export_shape.py -v
.venv/bin/python -m pytest tests/test_phase4_no_legacy_compute_at_runtime.py -v
.venv/bin/python -m pytest tests/test_phase4_legacy_shielded_e2e.py -v
```

---

## Goal E — Runtime Verification

**变化理由：** 证明一切正常。

执行验证清单（迭代计划 §E.1）：
1. Static compile → `py_compile` + `compileall`
2. Product main smoke → `python main.py seeds/test8.txt`
3. Field provenance check → `final_report.json.risk_level == simulation_dataset.risk_verdict.level`
4. No-legacy-compute runtime check → monkeypatch legacy 函数为 raise，跑 main.py
5. Legacy-shielded E2E smoke → import hook 阻断 legacy，跑 main.py
6. Export shape check → `src.phase4.__all__` 精确等于 5 个导出
7. Boundary grep checks → no legacy imports in clean source
8. Bypass dev tool check → `tools/bypass_compare_phase3.py seeds/test8.txt`
9. Tests suite → `pytest tests/ --ignore=docs -v`

---

## 全局红线

- 不得修改 src/phase1/、src/phase2/、src/phase3/、src/schemas/
- 不得修改 src/phase4/report_prompts.py、report_normalizer.py、report_title.py
- 不得在 clean source（src/phase4、main.py）中 import legacy
- 不得实装 20 类风险 taxonomy

## 回传要求

回传 `outputs/execution_receipt.md`，包含：
1. 每个 Goal 的执行结果与证据
2. 实际新增/修改/删除文件清单
3. main.py entrypoint 变更摘要
4. src.phase4 public API shape
5. 每条验证命令与结果
6. 最新 run_dir、simulation_dataset.json / final_report.json / final_report.md 路径
7. 是否触碰 forbidden files
8. 是否 clean source import legacy
9. known issues / carry-over
