# DS Agent Team — Phase 4 Dependency / Import Hygiene 只读审查报告

---

## audit_id
`DS-AGENT-TEAM-HYGIENE-2026-05-15-001`

## team_mode_used
`true`

## reviewer_agents
| # | Agent 名称 | 审查范围 | 状态 |
|---|-----------|---------|------|
| 1 | Import Usage Reviewer | src/phase4/ 全部文件的 import 使用、重复、过期依赖 | 已完成 |
| 2 | Helper Consumer Reviewer | v1.2.9 解耦后 helper/wrapper/re-export 的消费者分析 | 已完成 |
| 3 | Test Compatibility Reviewer | tests/ 对 report_agent.py 私有函数、全局变量、wrapper 的依赖 | 已完成 |
| 4 | Scope Safety Reviewer | 清理项的风险分类（低风险 hygiene vs 业务逻辑触碰） | 已完成 |

## current_git_status_summary
```
Branch: work/v1.2.8
Modified:
  - CLAUDE.md
  - src/phase4/report_agent.py
Deleted:
  - audit/DS_Agent_Team_Review_Command.md
  - audit/adarian_long_term_architecture_plan_v0.3_phase1_draft_format_revised.md
New (untracked):
  - src/phase4/report_narrative.py
  - src/phase4/report_normalizer.py
  - src/phase4/report_title.py
  - tests/test_phase4_report_agent_decoupling.py
  - tests/test_phase4_report_normalizer.py
  - Multiple audit artifacts
```

## checked_files
```
src/phase4/__init__.py
src/phase4/report_agent.py
src/phase4/report_narrative.py
src/phase4/report_normalizer.py
src/phase4/report_prompts.py
src/phase4/report_title.py

tests/test_phase4_report_normalizer.py
tests/test_phase4_report_agent_decoupling.py
tests/test_report_product_contract.py
tests/test_report_markdown_grounding.py
tests/test_risk_assessment_directionality.py
tests/test_inflection_point_output_guard.py
tests/test_whitebox_artifact_shell.py
tests/test_run_dir_concurrency.py
```

## evidence_commands_summary

### Git 状态
```
 M CLAUDE.md
 M src/phase4/report_agent.py
?? src/phase4/report_narrative.py
?? src/phase4/report_normalizer.py
?? src/phase4/report_title.py
?? tests/test_phase4_report_agent_decoupling.py
?? tests/test_phase4_report_normalizer.py
```

### 关键符号 grep 结果摘要

| 符号 | 定义位置 | 消费者数量 | 跨文件引用 |
|------|---------|-----------|-----------|
| `_llm_generated_markdown` | report_agent.py:535 | 4 测试文件 + 1 解耦测试 | 大量读写 |
| `parse_llm_report_response` | report_agent.py:576 | report_narrative.py + tests | re-export via __init__.py |
| `generate_fallback_report` | report_agent.py:648 | 5 测试文件 + 内部 | re-export via __init__.py |
| `_normalize_saved_markdown` | report_normalizer.py:350 | report_agent.py + 3 测试文件 | re-export via report_agent.py |
| `_ensure_metadata_header` | report_title.py:111 | report_normalizer.py + 2 测试文件 | re-export via report_agent.py |
| `_normalized_report_title` | report_title.py:12 | report_title.py + 2 测试文件 | re-export via report_agent.py |
| `_normalize_report_title_line` | report_title.py:118 | report_normalizer.py 仅 | report_agent.py 导入了但从未使用 |
| `_has_required_five_chapter_sections` | report_normalizer.py:335 | report_agent.py 仅 | 无测试覆盖 |
| `_code_owned_risk_section` | report_normalizer.py:130 | report_agent.py + 2 测试文件 | re-export via report_agent.py |
| `METRIC_EXPLANATION_PREFILL` | report_prompts.py:288 | report_normalizer + report_agent + 3 测试文件 | 活跃 |
| `INTERNAL_CODE_OWNED_LABELS` | report_prompts.py:55 | report_normalizer + 1 测试文件 | 活跃 |
| `REPORT_SYSTEM_PROMPT` | report_prompts.py:303 | report_narrative + 1 测试文件 | 活跃 |

### compileall 结果
```
编译成功，无语法错误。
```

---

## SAFE_TO_REMOVE 清单（A 类）

以下项目有明确的 grep/AST 证据表明无消费者，删除不改变业务逻辑，不影响测试。

### A1. report_agent.py:51 — 移除 `_normalize_report_title_line` 导入
- **文件**: `src/phase4/report_agent.py`
- **行**: 51
- **内容**: `_normalize_report_title_line,` 从 `from .report_title import` 块中删除
- **证据**:
  - `_normalize_report_title_line` 在 report_agent.py 中仅出现 1 次（即该 import 行）
  - 函数体内零引用
  - 无任何测试通过 `report_agent._normalize_report_title_line` 访问
  - 解耦测试仅检查字符串 `"from .report_title import"` 存在，不检查具体导入符号
  - 函数仍可通过 `report_normalizer.py` 的独立导入正常使用
- **风险**: 零

### A2. report_agent.py:346-364 — 删除 `build_entity_distribution()` 函数
- **文件**: `src/phase4/report_agent.py`
- **行**: 346-364
- **内容**: 整个 `def build_entity_distribution(...)` 函数定义
- **证据**:
  - 全代码库唯一出现处即该定义
  - 零调用者（src/、tests/、main.py 均无）
  - 未在 `__init__.py` 中 re-export
  - 不在 `__all__` 中
- **风险**: 零

### A3. report_agent.py:723 — 删除 `_trajectory_description()` 函数
- **文件**: `src/phase4/report_agent.py`
- **行**: 723 附近
- **内容**: 整个 `def _trajectory_description(...)` 函数定义
- **证据**:
  - 全代码库唯一出现处即该定义
  - 零调用者
  - 未完成的 helper，从未接入 `generate_markdown_report`
- **风险**: 零

### A4. report_agent.py:865 — 删除 `_stance_summary_lines()` 函数
- **文件**: `src/phase4/report_agent.py`
- **行**: 865 附近
- **内容**: 整个 `def _stance_summary_lines(...)` 函数定义
- **证据**:
  - 全代码库唯一出现处即该定义
  - 零调用者
  - 疑似早期版本的遗留代码，已被 `_evolution_subject_structure_lines`、`_evolution_group_change_lines`、`_evolution_stage_lines` 取代
- **风险**: 零

### A5. report_agent.py:1100 — 移除重复的局部 `TickLog` 导入
- **文件**: `src/phase4/report_agent.py`
- **行**: 1100
- **内容**: `from src.schemas import TickLog`（在 `load_tick_logs()` 函数内部）
- **证据**:
  - `TickLog` 已在文件顶部第 29 行导入
  - 函数内部重新导入是冗余的
  - 模块级作用域中已有 `TickLog`
- **风险**: 零

### A6. __init__.py — 清理无外部消费者的 re-export（4 个符号）
- **文件**: `src/phase4/__init__.py`
- **内容**: 移除以下 4 个符号的 import 和 `__all__` 条目：
  - `build_full_report_context` — 无外部 `from src.phase4 import build_full_report_context`
  - `load_tick_logs` — 无外部 `from src.phase4 import load_tick_logs`
  - `parse_llm_report_response` — 无外部通过 `__init__.py` 路径导入
  - `generate_markdown_report` — 无外部通过 `__init__.py` 路径导入
- **证据**:
  - `main.py` 仅导入: `generate_report_with_llm`, `save_report`, `save_markdown_report`
  - 全代码库无 `from src.phase4 import build_full_report_context` 等模式
  - 这些函数仍在原模块中正常定义和使用，仅清理 re-export 层
- **注意**: 以下 6 个符号**必须保留**在 `__init__.py` 中：
  - `generate_report_with_llm`（main.py 调用）
  - `save_report`（main.py 调用）
  - `save_markdown_report`（main.py 调用）
  - `assess_risk`（main.py 通过 `from src.phase4 import` 导入）
  - `generate_fallback_report`（main.py 通过 `from src.phase4 import` 导入）
  - `identify_inflection_points`（保留以备外部使用）
- **风险**: 零（仅清理 re-export 层，不删除函数本身）

---

## KEEP_REQUIRED 清单（B 类）

以下符号虽然看起来像 wrapper/re-export，但当前测试或外部入口仍依赖，暂时必须保留。

### B1. `_normalize_saved_markdown` re-export
- **文件**: `src/phase4/report_agent.py:44`
- **消费者**:
  - `test_phase4_report_normalizer.py:40` — `assert report_agent._normalize_saved_markdown is _normalize_saved_markdown`
  - `test_phase4_report_agent_decoupling.py:10` — 同上
  - `test_report_product_contract.py:17` — 直接 `from src.phase4.report_agent import _normalize_saved_markdown`
  - `report_agent.py:1086,1089` — 内部调用

### B2. `_code_owned_risk_section` re-export
- **文件**: `src/phase4/report_agent.py:42`
- **消费者**:
  - `test_phase4_report_agent_decoupling.py:11` — identity 断言
  - `test_phase4_report_normalizer.py:5,94` — 直接导入和使用
  - `report_agent.py:993` — 内部调用

### B3. `_normalized_report_title` re-export
- **文件**: `src/phase4/report_agent.py:52`
- **消费者**:
  - `test_phase4_report_agent_decoupling.py:12` — identity 断言
  - `test_report_product_contract.py:18,211,218-221` — 直接 `from src.phase4.report_agent import _normalized_report_title`

### B4. `_ensure_metadata_header` re-export
- **文件**: `src/phase4/report_agent.py:49`
- **消费者**:
  - `test_phase4_report_agent_decoupling.py:13` — identity 断言
  - `test_report_product_contract.py:16,209` — 直接 `from src.phase4.report_agent import _ensure_metadata_header`

### B5. `_replace_report_metric_terms` re-export
- **文件**: `src/phase4/report_agent.py:46`
- **消费者**:
  - `test_phase4_report_normalizer.py:8,38,49` — identity 断言和直接使用
  - `test_inflection_point_output_guard.py:15,170` — 直接导入和使用

### B6. `_replace_reality_claims_about_inflection` re-export
- **文件**: `src/phase4/report_agent.py:45`
- **消费者**:
  - `test_phase4_report_normalizer.py:7,39` — identity 断言
  - `test_inflection_point_output_guard.py:14,154` — 直接导入和使用

### B7. `_llm_generated_markdown` 全局变量
- **文件**: `src/phase4/report_agent.py:535`
- **消费者**（4 个测试文件，大量读写）:
  - `test_report_markdown_grounding.py` — ~20 处读写（lines 175, 345-559）
  - `test_report_product_contract.py` — 5 处读写（lines 249-299）
  - `test_risk_assessment_directionality.py` — 4 处读写（lines 249-289）
  - `test_inflection_point_output_guard.py` — 4 处读写（lines 190-232）
  - `test_phase4_report_agent_decoupling.py:26` — `hasattr(report_agent, "_llm_generated_markdown")`
- **注意**: 这是最脆弱的依赖点，任何移除或重命名都会导致多个测试文件崩溃

### B8. `get_llm_client` 在 report_agent 命名空间中
- **文件**: `src/phase4/report_agent.py:28`
- **消费者**: `test_report_product_contract.py:242` — `monkeypatch.setattr(report_agent, "get_llm_client", ...)`
- **注意**: 当前通过 `from src.llm_client import get_llm_client` 自然满足

### B9. `_build_code_owned_report_contract_block` 在 report_agent.py 中
- **文件**: `src/phase4/report_agent.py:229`
- **消费者**:
  - `test_report_product_contract.py:14` — 直接导入
  - `test_risk_assessment_directionality.py:14` — 直接导入
  - `report_agent.py:568` — 内部作为回调传递
- **注意**: 该函数尚未提取到新模块，仍在 report_agent.py 本体中定义

### B10. `__init__.py` 主入口 re-export（6 个符号，必须保留）
- `generate_report_with_llm` — main.py:200 + 3 个测试文件
- `save_report` — main.py:208 + 2 个测试文件
- `save_markdown_report` — main.py:209 + 3 个测试文件
- `assess_risk` — main.py 导入 + 2 个测试文件
- `generate_fallback_report` — 5 个测试文件
- `identify_inflection_points` — 2 个测试文件 + report_narrative.py

### B11. 解耦测试对源代码字面字符串的检查
- **文件**: `tests/test_phase4_report_agent_decoupling.py:40-42`
- **内容**: 检查 report_agent.py 源码中是否包含 `"from .report_normalizer import"`、`"from .report_narrative import"`、`"from .report_title import"`
- **影响**: 只要保留至少一个来自每个模块的导入，这 3 个断言就不会被破坏

---

## NEEDS_CODEX_VERIFICATION 清单（C 类）

以下项目可能可删，但需要 Codex 通过 targeted tests / full tests 验证，不可直接人工判断。

### C1. re-export 身份断言的去重可能性
- **涉及符号**: `_normalize_saved_markdown`, `_code_owned_risk_section`, `_normalized_report_title`, `_ensure_metadata_header`, `_replace_report_metric_terms`, `_replace_reality_claims_about_inflection`
- **问题**: 这些符号在 report_agent.py 中被导入但从未直接调用（仅在内部通过其他路径调用），仅作为 re-export 供测试做 identity 断言
- **潜在清理方案**: 更新测试，使其直接从 report_normalizer/report_title 导入，然后从 report_agent.py 移除这些 re-export
- **需要验证**:
  - 修改 `test_phase4_report_agent_decoupling.py` 中的 identity 断言路径
  - 修改 `test_phase4_report_normalizer.py` 中的 re-export 断言
  - 修改 `test_report_product_contract.py` 中的直接导入路径
  - 确认 `report_agent.py` 内部对这些函数的调用不会中断（需确认内部调用路径是否依赖模块级名称）
- **风险**: 中等 — 需要协调测试更新

### C2. `_has_required_five_chapter_sections` 的测试覆盖缺口
- **符号**: `_has_required_five_chapter_sections` (report_normalizer.py:335)
- **问题**: 该函数被 report_agent.py 调用（line 1087），但无任何测试直接覆盖
- **需要验证**: 是否存在间接覆盖（通过 `save_markdown_report` -> `_normalize_saved_markdown` 的集成路径）
- **建议**: 在合并 HYGIENE_PATCH 之前运行 `pytest tests/test_report_markdown_grounding.py -v` 确认间接覆盖

### C3. `_metadata_header` 函数的导入保留判断
- **符号**: `_metadata_header` (report_title.py, report_agent.py:50)
- **问题**: report_agent.py 导入了此函数但仅在内部使用（line 1044），无测试直接访问 `report_agent._metadata_header`
- **需要验证**: 是否可将其从 report_agent.py 的导入中移除（因为它仅由 `_ensure_metadata_header` 内部调用，而 report_agent.py 调用的是后者）

### C4. `__init__.py` 中 `assess_risk`、`generate_fallback_report`、`identify_inflection_points` 的 re-export 必要性
- **问题**: 这些符号虽然在 `__init__.py` 中 re-export，但 main.py 是否直接使用 `from src.phase4 import assess_risk` 需要验证
- **需要验证**: 如果 main.py 不直接通过这些路径导入，可以从 `__init__.py` 移除，只保留 `generate_report_with_llm`、`save_report`、`save_markdown_report` 三个

---

## DO_NOT_TOUCH 清单（D 类）

以下元素涉及 prompt 语义、risk algorithm、schema、report contract、main.py/whitebox contract，严禁进入 hygiene patch。

### D1. Prompt 语义（report_prompts.py 全部内容）
- `REPORT_SYSTEM_PROMPT`（含所有子规则的 f-string 展开）
- `METRIC_EXPLANATION_PREFILL`
- `INTERNAL_CODE_OWNED_LABELS`
- `ENTERPRISE_PR_FORBIDDEN_PHRASES`
- `QUOTE_FABRICATION_PATTERNS`
- `RAW_METRIC_FIELD_NAMES`
- `FORBIDDEN_EQUIVALENT_PHRASES`
- `POLICY_BOUNDARY_FORBIDDEN_PHRASES`
- `NON_WHITELISTED_RISK_TYPE_EXAMPLES`
- `FIVE_CHAPTER_HEADINGS`
- `REPORT_USER_PROMPT_SUFFIX`
- `SIMULATION_DISCLAIMER`
- 以及所有其他 report_prompts.py 中定义的常量

### D2. Risk Algorithm（核心算法逻辑）
- `assess_risk()` — report_agent.py:440
- `select_primary_risk_types()` — report_agent.py:140
- `identify_inflection_points()` — report_agent.py:367
- 以及它们调用的所有内部 helper 函数

### D3. Report Contract / Schema
- `Phase4Output` 及其所有字段、validator
- `REPORT_TYPE`、`RISK_LEVEL_LABELS`、`RISK_TYPE_LABELS` 常量
- `report_meta` 构建逻辑
- `generate_fallback_report()` 的**逻辑**（re-export 本身可动，逻辑不可动）
- `parse_llm_report_response()` 的**逻辑**

### D4. Code-Owned Report Section
- `_code_owned_risk_section()` 的**逻辑**（report_normalizer.py:130）
- `_has_required_five_chapter_sections()` 的**逻辑**（report_normalizer.py:335）
- `_build_code_owned_report_contract_block()` 的**逻辑**（report_agent.py:229）

### D5. main.py / Whitebox Contract
- `main.py` 中对 phase4 的任何 import 路径
- `src/whitebox/` 中对 phase4 的任何 import 路径
- `generate_report_with_llm` 的签名和返回值契约

### D6. 禁止修改的文件
- `main.py`
- `src/schemas/`（全部）
- `src/whitebox/`（全部）
- `src/phase4/report_prompts.py`
- `config.py`
- `src/llm_client.py`

---

## risk_notes

1. **最高风险项**: `_llm_generated_markdown` 是可变模块级全局变量，4 个测试文件直接读写。任何 hygiene patch 不得触碰此变量。

2. **中等风险项**: 6 个 private re-export 符号被测试通过 identity 断言验证。如果未来要清理这些 re-export，需要同步更新 3 个测试文件中的导入路径。

3. **低风险项**: 5 个 A 类清理项（1 个未使用导入 + 3 个死函数 + 1 个重复导入）可以零风险执行。

4. **解耦测试的字面字符串检查**: `test_phase4_report_agent_decoupling.py` 检查源码中是否包含 `"from .report_normalizer import"` 等字符串。只要每个模块至少保留一个导入符号，这些检查就通过。

5. **__init__.py 过度导出**: 当前 10 个 re-export 中有 4 个无外部消费者，清理它们不会影响任何调用者。

6. **测试覆盖缺口**: `_has_required_five_chapter_sections` 有零直接测试覆盖，仅通过集成路径间接覆盖。

---

## recommended_hygiene_patch_scope

建议的 hygiene patch 范围仅限 **A 类**（SAFE_TO_REMOVE）项目：

| 序号 | 操作 | 文件 | 说明 |
|------|------|------|------|
| 1 | 移除导入符号 | `src/phase4/report_agent.py:51` | 从 `from .report_title import` 中删除 `_normalize_report_title_line,` |
| 2 | 删除死函数 | `src/phase4/report_agent.py` | 删除 `build_entity_distribution()` 函数定义 |
| 3 | 删除死函数 | `src/phase4/report_agent.py` | 删除 `_trajectory_description()` 函数定义 |
| 4 | 删除死函数 | `src/phase4/report_agent.py` | 删除 `_stance_summary_lines()` 函数定义 |
| 5 | 移除重复导入 | `src/phase4/report_agent.py:1100` | 删除 `load_tick_logs()` 内的 `from src.schemas import TickLog` |
| 6 | 清理 re-export | `src/phase4/__init__.py` | 移除 4 个无外部消费者的 re-export 符号及其 `__all__` 条目 |

**此 patch 的保证**:
- 零测试破坏
- 零业务逻辑变更
- 零 prompt 语义变更
- 零 risk algorithm 变更
- 零 schema 变更
- 零 main.py/whitebox contract 变更

---

## recommended_codex_prompt_boundary

以下边界定义了 Codex 可以验证的内容范围：

**Codex 可以执行**:
- 运行 `pytest tests/test_phase4_report_normalizer.py tests/test_phase4_report_agent_decoupling.py -v` 验证 A 类清理后测试全绿
- 运行 `pytest tests/test_report_markdown_grounding.py tests/test_report_product_contract.py -v` 验证无回归
- 运行 `.venv/bin/python -m compileall src` 验证语法

**Codex 不得执行**:
- 任何 B 类或 C 类项目的实际删除
- 任何对 report_prompts.py 的修改
- 任何对 risk algorithm 函数的修改
- 任何对 schemas/ 的修改
- 任何对 main.py 的修改
- `git add` / `git commit`
- 超出 A 类范围的任何代码修改

---

## final_verdict:

**HYGIENE_PATCH_RECOMMENDED**

### 统计
- **safe_to_remove_count**: 6（1 个未使用导入 + 3 个死函数 + 1 个重复导入 + 1 个 __init__.py 清理组）
- **keep_required_count**: 11
- **needs_codex_verification_count**: 4
- **do_not_touch_count**: 6 大类（含数十个子项）

### 推荐操作
仅执行 A 类 hygiene patch（6 项），在合并前运行:
```bash
.venv/bin/python -m compileall src
.venv/bin/python -m pytest tests/test_phase4_report_normalizer.py tests/test_phase4_report_agent_decoupling.py tests/test_report_markdown_grounding.py tests/test_report_product_contract.py -v
```

---

*报告生成时间: 2026-05-15*
*审查模式: 只读，未修改任何文件*
*审查分支: work/v1.2.8*
