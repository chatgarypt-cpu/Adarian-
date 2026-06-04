# DS Agent Team 前置审计报告 — v1.2.9 Phase 4 Report Agent Decoupling R0

## 1. 审计元数据

- **audit_id**: `audit-v1.2.9-01`
- **team_mode_used**: `true`
- **审计日期**: 2026-05-15
- **审计对象**: `docs/iterations/v1.2.9-Phase-4-Report-Agent-Decoupling-R0.md`
- **源码基线**: `f71f9af closeout: v1.2.8.1 risk assessment directionality patch`
- **审查范围**: 迭代文档可执行性、边界清晰度、allowed/forbidden files合理性、attempt拆分稳妥性、测试计划充分性

## 2. Reviewer Agents

本次审计启动 **5 个独立 reviewer agent** 并行审查：

| # | Reviewer | 审查领域 | 状态 |
|---|----------|---------|------|
| 1 | Architecture Boundary Reviewer | 拆分边界、三路拆分合理性、Façade可行性、函数依赖图 | ✅ 完成 |
| 2 | Import / Compatibility Reviewer | Import路径、`__init__.py`导出、测试兼容性、循环导入风险 | ✅ 完成 |
| 3 | Phase 4 Behavior Preservation Reviewer | final_report.json/MD契约、风险算法语义、Prompt语义、normalizer bug | ✅ 完成 |
| 4 | Test Plan Reviewer | 新增测试充分性、既有测试覆盖、smoke test、测试脆弱性 | ✅ 完成 |
| 5 | Scope Drift Reviewer | 范围边界、allowed/forbidden files、audit dirty tree、attempt边界 | ✅ 完成 |

## 3. DS Controller 综合裁决

### 3.1 Verdict

**CONDITIONAL_GO**

### 3.2 裁决理由

5 个 reviewer 一致给出 CONDITIONAL_GO。v1.2.9 的三路拆分方向（report_normalizer.py / report_narrative.py / report_title.py）在架构上是合理且必要的，迭代文档在目标定义、禁止变化和验收标准方面是完整且明确的。然而，存在以下必须在 Codex 执行前修正的阻断项：

1. **缺少精确的"函数→模块"迁移映射表**（5/5 reviewer 共识）。当前文档只有模块级别的"定位描述"，Codex 无法据此自主判断 15+ 个函数的精确归属。这会导致错误的迁移决策或函数遗漏。

2. **循环导入风险未解决**（Architecture + Import reviewer 共同确认）。`parse_llm_report_response()` 和 `generate_fallback_report()` 若迁到 `report_narrative.py` 将形成 `report_agent.py → report_narrative.py → report_agent.py` 的循环导入。`_code_owned_risk_section` 及其 5 个子函数若留在 facade 而被 normalizer 导入，同样形成循环。

3. **Section 6.3 禁止修改清单存在缺口**（Scope reviewer 确认）。主清单缺少 `report_prompts.py`、`config.py`、`src/llm_client.py`，与 attempt 级别子清单不一致。

4. **`_llm_generated_markdown` 全局变量归属未明确**（Test + Architecture reviewer 确认）。3 个既有测试文件直接操作此变量，若随 LLM 逻辑迁出会导致测试全部崩溃。

5. **attempt-01 边界内存在跨 attempt 函数调用**（Scope + Architecture reviewer 确认）。`_ensure_metadata_header()` 和 `_normalize_report_title_line()` 属于标题域（attempt-02），但被 normalizer pipeline（attempt-01）调用，边界处理方式未定义。

### 3.3 审查项裁决矩阵

| 审查维度 | Architecture | Import | Behavior | Test | Scope | 综合 |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| 三路拆分合理性 | ✅ | ✅ | ✅ | N/A | ✅ | **PASS** |
| Façade可行性 | ⚠️ | ✅ | N/A | N/A | N/A | **PASS with notes** |
| Import兼容性 | N/A | ⚠️ | N/A | ⚠️ | N/A | **PASS with fixes** |
| final_report.json契约 | N/A | N/A | ✅ | N/A | N/A | **PASS** |
| final_report.md五章结构 | N/A | N/A | ✅ | N/A | N/A | **PASS** |
| 风险算法语义 | ✅ | N/A | ✅ | N/A | N/A | **PASS** |
| Prompt语义 | N/A | N/A | ✅ | N/A | N/A | **PASS** |
| 模拟模拟极化指数bug | N/A | N/A | 🔴 | 🔴 | N/A | **BLOCKER** |
| Allowed/Forbidden files | N/A | N/A | N/A | N/A | 🔴 | **BLOCKER** |
| Attempt边界 | ⚠️ | N/A | N/A | ⚠️ | ⚠️ | **WARNING** |
| Smoke test | N/A | N/A | N/A | ⚠️ | N/A | **WARNING** |
| Scope drift防护 | N/A | N/A | N/A | N/A | ⚠️ | **WARNING** |

图例：✅ PASS | ⚠️ PASS with fixes | 🔴 BLOCKER | N/A 不适用

## 4. Hard Blockers

以下问题必须在 Codex 执行前解决，否则禁止进入 attempt-01：

### B1. 缺少精确的函数迁移映射表

**发现者**: Architecture Boundary Reviewer (B2)，5/5 reviewer 共识

**问题**: 迭代文档 Section 5.3 仅给出模块级别的"定位描述"和"承接/禁止"文本，未逐函数列出精确的迁移清单。`report_agent.py` 中共有 40+ 个函数，其中 15+ 个的归属在文档中缺乏明确分配。

**影响**: Codex 无法自主判断函数归属，将导致错误的迁移决策、函数遗漏或模块职责混乱。

**修正要求**: 在迭代文档中新增附录"函数→模块迁移映射表"，逐函数列出：
- 函数名 + 行号
- 目标模块（report_normalizer.py / report_narrative.py / report_title.py / report_agent.py）
- 迁移理由（一句话）

参考 Architecture Boundary Reviewer 报告第 7 节的完整映射表。

### B2. 循环导入风险：parse_llm_report_response / _code_owned_risk_section

**发现者**: Architecture Boundary Reviewer (B1)，Import/Compatibility Reviewer (B1)

**问题**:
- 路径 A：若 `parse_llm_report_response()` 迁到 `report_narrative.py`，它需要 `from .report_agent import assess_risk`，而 `report_agent.py` 需要 `from .report_narrative import generate_report_with_llm`，形成循环导入。
- 路径 B：若 `_code_owned_risk_section` 留在 `report_agent.py`，而 `_replace_risk_section_with_code_owned` 迁到 `report_normalizer.py`，则 normalizer 需要 `from .report_agent import _code_owned_risk_section`，形成反向依赖。

**影响**: 模块无法导入，代码无法运行。

**修正要求**:
- `parse_llm_report_response()` 和 `generate_fallback_report()` 必须留在 `report_agent.py`（facade），因为它们是编排函数，调用 facade 内部的风险计算。
- `_code_owned_risk_section` 及其 5 个依赖函数（`_risk_explanation`, `_conflict_focus_lines`, `_structural_risk_point_lines`, `_short_mid_term_risk_judgment`, `_risk_type_labels`）总计约 130 行，必须与 `_replace_risk_section_with_code_owned` 放在同一个模块。建议方案：全部迁入 `report_normalizer.py`。

### B3. Section 6.3 禁止修改清单缺口

**发现者**: Scope Drift Reviewer (B1)

**问题**: Section 6.3 主清单与 attempt 级别子清单不一致：
- `src/phase4/report_prompts.py` 在 attempt-01/02 禁止清单中，但不在 Section 6.3 主清单中
- `config.py` 未列入任何禁止清单
- `src/llm_client.py` 未列入任何禁止清单

**影响**: Codex 可能在拆分过程中修改这些关键基础设施文件。

**修正要求**: 在 Section 6.3 新增：
```
- src/phase4/report_prompts.py
- config.py
- src/llm_client.py
```

### B4. `_llm_generated_markdown` 全局变量归属

**发现者**: Test Plan Reviewer (B1)，Architecture Boundary Reviewer (W4)

**问题**: 此模块级全局变量在 `generate_report_with_llm()` 中写入，在 `save_markdown_report()` 中读取。3 个既有测试文件直接操作 `report_agent._llm_generated_markdown`。若随 LLM 逻辑迁到 `report_narrative.py`，所有既有测试崩溃。

**影响**: 3 个测试文件（test_report_product_contract.py, test_report_markdown_grounding.py, test_risk_assessment_directionality.py）共 15+ 处直接赋值将引发 AttributeError。

**修正要求**: `_llm_generated_markdown` 必须在 `report_agent.py` 中保留。`report_narrative.py` 中的叙事生成函数通过返回值传递 Markdown 字符串，由 facade 负责写入全局变量。

### B5. "模拟模拟极化指数"重复前缀 Bug 确认

**发现者**: Behavior Preservation Reviewer (B1)

**问题**: `_replace_report_metric_terms()` 中 `("极化指数", "模拟极化指数")` 的替换在已包含 "模拟极化指数" 的文本上会产生 "模拟模拟极化指数"。Bug 存在于 body 替换循环（line 468）和 appendix 替换（line 481）两处。

**影响**: final_report.md 中出现无意义的重复前缀，违反 closeout 验收条件（Section 8.6 item 11）。

**修正要求**: 在 `report_normalizer.py` 中使用 negative-lookbehind 正则 `re.sub(r'(?<!模拟)极化指数', '模拟极化指数', text)` 替代简单的 `str.replace()`。

## 5. Must Fix Before Codex

以下问题不阻塞 attempt-01 启动，但必须在 attempt-01 执行过程中解决：

### M1. Re-export 策略确认

**发现者**: Import/Compatibility Reviewer (W1)，Test Plan Reviewer (B5)，Architecture Boundary Reviewer (B3)

3 个既有测试文件的私有函数 import 在拆分后会断裂：
- `test_report_product_contract.py` 导入 `_normalize_saved_markdown`, `_ensure_metadata_header`, `_normalized_report_title`
- `test_phase4_markdown_metric_grounding.py` 导入 `_build_code_owned_agent_stance_matrix`, `_format_code_owned_inflection_points`

必须在 `report_agent.py` 中保留 re-export：
```python
from .report_normalizer import _normalize_saved_markdown, _has_required_five_chapter_sections
from .report_title import _ensure_metadata_header, _normalized_report_title, _normalize_report_title_line
```

### M2. attempt-01 边界：_ensure_metadata_header / _normalize_report_title_line 处理

**发现者**: Scope Drift Reviewer (W1)，Architecture Boundary Reviewer

`_normalize_saved_markdown()` pipeline 的 Step 1-2 调用了 `_ensure_metadata_header()` 和 `_normalize_report_title_line()`，这两个函数属于标题域（attempt-02 目标）。attempt-01 有两种处理方式：

**推荐方案**: attempt-01 将它们保留在 `report_agent.py`，`report_normalizer.py` 通过参数接收 phase4_output 并委托 facade 调用它们。attempt-02 再迁移。

### M3. code-owned 中文转述泄漏词表范围

**发现者**: Behavior Preservation Reviewer (W1)，Test Plan Reviewer (B3)，Scope Drift Reviewer (W1)

迭代文档 Section 5.2 提到 "扩展 code-owned / prompt 指令中文转述泄漏过滤"，但 `INTERNAL_CODE_OWNED_LABELS` 在 `report_prompts.py` 中（禁止修改文件）。存在设计矛盾。

**解决方案**: 在 `report_normalizer.py` 中新增本地常量 `CODE_OWNED_CHINESE_PARAPHRASE_PATTERNS`，包含中文转述泄漏模式（如 "请补充 risk_level_label"、"无法自行发明风险等级"），不修改 `report_prompts.py`。

### M4. Section 6.4 补充必须保持不变的条目

**发现者**: Scope Drift Reviewer (W3)

Section 6.4 需新增：
- `select_primary_risk_types()` 实现方式（keyword matching，不得升级为 signal source）
- `identify_inflection_points()` 算法与阈值（极化差值 > 0.1，不得升级为 multi-signal framework）
- `assess_risk()` 的信号逻辑与阈值常量（不得"顺手调参"）
- `INTERNAL_CODE_OWNED_LABELS` 常量内容（过滤词表扩展通过 normalizer 本地变量实现）

### M5. Codex 操作层面 audit/ 防护

**发现者**: Scope Drift Reviewer (Section 5)

在 Codex Execution Prompt (Section 12) 的 "执行前先记录" 前增加操作约束：
```
执行前确认：git status --short 输出中 audit/ 下文件状态为 [D] 或 [??]，
Codex 不得 git add 任何 audit/ 路径下的文件。
Codex 只允许 git add 6.1/6.2 授权的文件路径。
```

## 6. Nice to Have

以下建议不阻塞执行，但推荐在 closeout 前考虑：

| # | 建议 | 来源 |
|---|------|------|
| N1 | Smoke test 建议覆盖两种 audience_mode（如 test1 执法类 + test8 消费争议） | Test Plan Reviewer |
| N2 | 新增 normalizer 变换顺序的隔离测试，验证 10 步 pipeline 顺序正确 | Test Plan Reviewer |
| N3 | 死代码 `build_entity_distribution()` (L735) 可在本轮清理 | Architecture Reviewer |
| N4 | `generate_markdown_report()` 及 13 个模板 helper（~430行）标注为 R1 候选 `report_template.py` | Architecture Reviewer |
| N5 | 现有测试文件中直接操作 `_llm_generated_markdown` 的用法，建议在 closeout 时考虑重构为通过 facade 函数间接操作 | Test Plan Reviewer |
| N6 | closeout 时检查报告产物中是否出现 "模拟模拟极化指数" 和 "模拟模拟关键变化点"（虽然后者理论上不会出现，但建议预防性检查） | Behavior Reviewer |
| N7 | 3.3 节补充 "不修改 config.py" 和 "不修改 src/llm_client.py" | Scope Drift Reviewer |

## 7. Scope Drift Risks

以下风险点已识别并评估，本轮不构成 BLOCKER 但需持续关注：

| # | 风险点 | 可能性 | 当前防护 | 评估 |
|---|--------|:---:|---------|:---:|
| SD1 | Codex 在拆分时"顺手"改进 select_primary_risk_types() 的 keyword matching | 中 | Section 6.4 补充后（见 M4）可防护 | **已覆盖** |
| SD2 | Codex 在拆分时"顺手"升级 identify_inflection_points() 引入多信号 | 中 | Section 6.4 补充后（见 M4）可防护 | **已覆盖** |
| SD3 | Codex 在 closeout 时 git add 误伤 audit/ dirty tree | 中 | 操作约束补充后（见 M5）可防护 | **已覆盖** |
| SD4 | Codex 在 normalizer 扩展时修改 report_prompts.py | 低 | Section 6.3 补充后（见 B3）可防护 | **已覆盖** |
| SD5 | Codex 在 attempt-02 时重新修改 attempt-01 已完成的 normalizer | 低 | 串行 attempt 依赖 + git diff 回传要求 | **已覆盖** |
| SD6 | "风险计算逻辑可暂留"的"暂"字给 Codex 提供"也可以移走"的解读空间 | 低 | 建议改为"必须留在 report_agent.py，本轮不移出" | **措辞修正** |

## 8. Allowed Files Review

### 8.1 允许新增（Section 6.1）

5 个文件完整覆盖本轮需求，无遗漏：

- `src/phase4/report_narrative.py` ✅
- `src/phase4/report_title.py` ✅
- `src/phase4/report_normalizer.py` ✅
- `tests/test_phase4_report_agent_decoupling.py` ✅
- `tests/test_phase4_report_normalizer.py` ✅

### 8.2 允许修改（Section 6.2）

6 类文件基本完整。**建议新增**：
- `src/phase4/report_agent.py` — 已有，确认 ✅
- `src/phase4/__init__.py` — 已有，确认 ✅
- 文档类（迭代文档、TASK_LOG、CHANGELOG、dev_spec）— 已有，确认 ✅

### 8.3 禁止修改（Section 6.3）

**存在缺口，见 B3**。补充后的完整清单应为：

```
- main.py
- src/phase1/
- src/phase2/
- src/phase3/
- src/schemas/
- src/whitebox/
- src/utils/runtime_logger.py
- src/phase4/report_prompts.py    ← 新增
- config.py                        ← 新增
- src/llm_client.py                ← 新增
- seeds/
- outputs/
- smoke_logs/
- audit/
- README.md
- docs/workflow_core.md
- docs/skills/
- 产品侧 v0.3 文档原件
```

## 9. Forbidden Files Review

### 9.1 主清单与子清单一致性

| 文件 | Section 6.3 | attempt-01 | attempt-02 | Codex Prompt | 一致性 |
|------|:---:|:---:|:---:|:---:|:---:|
| main.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| src/phase1/ | ✅ | ✅ | ✅ | ✅ | ✅ |
| src/phase2/ | ✅ | ✅ | ✅ | ✅ | ✅ |
| src/phase3/ | ✅ | ✅ | ✅ | ✅ | ✅ |
| src/schemas/ | ✅ | ✅ | ✅ | ✅ | ✅ |
| src/whitebox/ | ✅ | ✅ | ✅ | ✅ | ✅ |
| src/phase4/report_prompts.py | ❌ 缺失 | ✅ | ✅ | ✅ | 🔴 不一致 |
| audit/ | ✅ | ✅ | ✅ | ✅ | ✅ |
| src/utils/runtime_logger.py | ✅ | N/A | N/A | ✅ | ⚠️ attempt级缺失 |

**修正**: Section 6.3 补充 `report_prompts.py`、`config.py`、`src/llm_client.py` 后，全链路一致。

### 9.2 必须保持不变（Section 6.4）

**存在缺口，见 M4**。补充后的完整清单应为：

```
- Phase 4 对外调用入口
- final_report.json 字段契约
- final_report.md 五章结构
- risk_level 四档枚举
- risk_level_label 映射
- primary_risk_types 现有逻辑
- select_primary_risk_types() 实现方式（keyword matching）    ← 新增
- identify_inflection_points() 算法与阈值（极化差值 > 0.1）   ← 新增
- assess_risk() 的信号逻辑与阈值常量                          ← 新增
- INTERNAL_CODE_OWNED_LABELS 常量内容                         ← 新增
- METRIC_EXPLANATION_PREFILL 语义
- REPORT_SYSTEM_PROMPT 语义
- RuntimeLogger 职责
- Whitebox artifact contract
```

## 10. Test Plan Review

### 10.1 新增测试充分性

| 测试文件 | 最小必须用例数 | 评估 |
|---------|:---:|------|
| test_phase4_report_normalizer.py | 8 条（7 项检查点 + 双前缀） | 必须覆盖：双前缀修复验证、code-owned 剥离、五章结构、指标术语、企业PR移除、引语伪造移除、风险段code-owned、中文转述泄漏过滤 |
| test_phase4_report_agent_decoupling.py | 10 条 | 必须覆盖：导出完整性、模块可导入性、端到端流程、既有import兼容、无循环导入、_llm_generated_markdown可访问、__init__.py导出不变 |

### 10.2 既有测试覆盖

4 个既有测试文件（40 条用例）覆盖了 normalizer pipeline、LLM prompt 注入、标题规范化、风险评估方向性、Markdown grounding 等关键路径。拆分后正常通过即为有效的回归证据。

### 10.3 Smoke Test

`test8` 作为 smoke 选择合理（历史一致性强）。建议 closeout 前至少覆盖两种 audience_mode。

### 10.4 验收流水线评估

```
attempt-01: py_compile + normalizer新测试 + markdown grounding回归 → 充分
attempt-02: py_compile + decoupling新测试 + 全量Phase 4回归      → 充分
closeout:   compileall + full tests + test8 smoke                → 充分
```

## 11. Final Recommendation

### 11.1 总体评估

v1.2.9 Phase 4 Report Agent Decoupling R0 迭代文档在**版本目标定义、边界划定、禁止变化和验收标准**方面是完整且清晰的。三路拆分（report_normalizer.py / report_narrative.py / report_title.py）的方向与 DS 前置审计的发现一致，attempt 串行策略（先 normalizer 后 narrative/title）合理降低了单次搬迁风险。

### 11.2 执行建议

1. **立即修正**: 解决 B1-B5 五个 hard blocker（补充迁移映射表、明确循环导入规避方案、修补 forbidden files 清单、明确全局变量归属、确认双前缀 bug 修复方案）。
2. **执行前确认**: 解决 M1-M5（re-export 策略、attempt 边界、中文泄漏词表、Section 6.4 补充、audit 操作防护）。
3. **允许进入 attempt-01**: 以上修正完成后，Control Agent 可将 Gate 从 CONDITIONAL_GO 更新为 GO。
4. **执行后验证**: 严格按 Section 8 验证计划执行，每个 attempt 完成后的 Execution Report（Section 10）必须完整回传。

### 11.3 建议 Gate 更新

```
- [ ] GO
- [x] CONDITIONAL_GO → 修正 B1-B5 + M1-M5 后 → GO
- [ ] HOLD
- [ ] FAIL
```

### 11.4 签字

本报告由 DS Agent Team 5 个独立 reviewer agent 并行审查、DS Controller 综合裁决生成。报告仅审查迭代文档的可执行性和风险，不重新设计版本边界，不替 Control Agent 做最终 gate。

---

*报告生成时间：2026-05-15*
*审计工具：DS Agent Team (5-reviewer parallel audit)*
*审查范围：v1.2.9 Phase 4 Report Agent Decoupling R0 — 前置审计*
