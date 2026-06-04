# DS Agent Team Pre-Audit Report: v1.2.8.1

## 0. Team Mode

team_mode_used: true
reviewer_agents:
- Scope Reviewer
- Code Reality Reviewer
- Test & Verification Reviewer
- Risk Drift Reviewer
audit_id: audit-v1.2.8.1-01
target_doc: docs/iterations/v1.2.8.1-Risk-Assessment-Directionality-Metric-Explanation-Patch_repaired.md
repo_status_summary:
  branch: work/v1.2.8
  base_commit: df94ac0
  working_tree: clean (only audit artifacts untracked)
  target_doc_exists: yes (with _repaired suffix)
  all_required_source_files_exist: yes
  no_existing_change_point_detection: yes
  no_existing_external_risk_adjustment: yes

---

## 1. Executive Verdict

DS_verdict: CONDITIONAL_GO

One-line decision:
The iteration doc is well-scoped, code-aware, and directionally correct; two minor doc patches are needed before Codex execution to align assess_risk() call-site data flow with the documented plan.

Can Codex execute attempt-v1.2.8.1-01 now?
- yes_after_doc_patch

---

## 2. Source Tree Facts

- src/phase4/report_agent.py: exists (1504 lines)
- src/phase4/report_prompts.py: exists (358 lines, static-only, no imports/functions/classes)
- tests/test_report_product_contract.py: exists (399 lines, rich fixtures)
- tests/test_report_markdown_grounding.py: exists (564 lines, rich fixtures)
- tests/test_phase4_markdown_metric_grounding.py: exists (70 lines, lightweight)
- tests/test_schema_imports.py: exists (81 lines)
- docs/iterations/TASK_LOG.md: exists
- docs/iterations/CHANGELOG.md: exists

All required source files confirmed to exist.

---

## 3. Code Reality Findings

### 3.1 assess_risk() facts

- function_exists: yes
- signature: `def assess_risk(x_t_sequence: List[float], tick_logs: List[TickLog]) -> tuple:` (report_agent.py:729)
- call_sites:
  1. report_agent.py:215 — `_build_code_owned_report_contract_block()` (line 215)
  2. report_agent.py:887 — `parse_llm_report_response()` (line 887)
  3. report_agent.py:930 — `generate_fallback_report()` (line 930)
- current_inputs: ONLY `x_t_sequence` and `tick_logs`
- current_risk_direction_logic:
```python
final_x = x_t_sequence[-1]
final_pol = tick_logs[-1].global_metrics.polarization_index if tick_logs else 0
trend = final_x - x_t_sequence[0] if len(x_t_sequence) > 1 else 0

if final_x > 7.5 or (final_x > 7.0 and trend > 1.0):
    return RiskLevel.CRITICAL, ...
elif final_x > 6.5 or (final_x > 5.5 and final_pol > 0.5):
    return RiskLevel.HIGH, ...
elif final_x > 5.0 or (final_x > 4.5 and trend > 0.5):
    return RiskLevel.MEDIUM, ...
else:
    return RiskLevel.LOW, ...
```
- confirmed_directionality_issue: **yes**

The current logic has a clear directional blindness: it treats **high** final_x (stance mean) as high risk, and **low** final_x as low risk. In government sentiment governance, low stance mean (criticism, distrust), negative trend, high polarization, and key-group negative migration are the actual risk signals. The doc correctly identifies this.

### 3.2 report prompt / metric explanation facts

- report_prompts_exists: yes
- current_prompt_constants: 30+ prompt constants (FIVE_CHAPTER_HEADINGS, SIMULATION_DISCLAIMER, REPORT_SYSTEM_PROMPT, REPORT_USER_PROMPT_SUFFIX, GOVERNMENT_FACING_PERSPECTIVE_RULES, METRIC_BUSINESS_LABEL_MAP, etc.)
- best_location_for_METRIC_EXPLANATION_PREFILL: **src/phase4/report_prompts.py** — correct. The file is already static-only (verified by test_report_prompts_module_is_static_only), and houses all other prompt constants. Adding METRIC_EXPLANATION_PREFILL here is the natural choice.
- risk_of_LLM_generated_metric_explanation: **currently moderate** — the LLM generates the appendix/metric explanation section via `generate_markdown_report()` and `generate_report_with_llm()`. No code-owned prefill currently exists. The doc's plan to inject METRIC_EXPLANATION_PREFILL into the appendix via code-side concatenation is the correct mitigation.

### 3.3 data availability

- final_x_available: **yes** — `x_t_sequence[-1]` at all 3 call sites
- trend_available: **yes** — computable as `final_x - x_t_sequence[0]`
- final_pol_available: **yes** — `tick_logs[-1].global_metrics.polarization_index` at all call sites
- event_scale_available: **PARTIAL** — `extraction_output.event_scale` exists but assess_risk() does NOT currently receive it. However, all 3 call sites have access to `extraction_output`:
  - `_build_code_owned_report_contract_block()` at line 210: **YES**, receives extraction_output as param
  - `parse_llm_report_response()` at line 838: **YES**, receives extraction_output as param
  - `generate_fallback_report()` at line 906: **YES**, receives extraction_output as param
- event_controversy_available: **PARTIAL** — same situation as event_scale
- risk_type_labels_available: **yes** — `RISK_TYPE_LABLES` dict with 13 entries, code-owned, validated via Pydantic field_validator
- opinion_spreader_start_end_shift_available: **PARTIAL** — `_build_code_owned_agent_stance_matrix()` at line 594 already computes per-agent start-end stance deltas from tick_logs entries. However, there is **no existing mechanism** to reliably differentiate opinion_spreaders from event_entities within tick_logs entries. The doc correctly anticipates this (Section 7.2, requirement 7: "If tick_logs cannot stably distinguish opinion spreaders from event entities, max_negative_shift must graceful degrade").

---

## 4. Scope Compliance Review

allowed_files_ok: **yes** — The allowed modification list is precise and minimal: report_agent.py, report_prompts.py, 3 existing test files, iteration doc, TASK_LOG, CHANGELOG. Only new file allowed: test_risk_assessment_directionality.py.

forbidden_files_ok: **yes** — Phase 1-3, schemas, whitebox, main.py, seeds, workflow docs, product v0.3 originals all correctly forbidden.

single_attempt_ok: **yes** — The changes are concentrated in assess_risk() logic + METRIC_EXPLANATION_PREFILL + terminology mapping. No Phase 1-3 changes, no schema changes, no new runtime artifacts. Single attempt is appropriate.

M_Level_ok: **yes** — This is correctly scoped as an M-Level patch: it fixes a blocking directionality bug and adds stable metric explanation. It does not introduce new architecture, new phases, new data sources, or breaking schema changes.

---

## 5. Doc-Code Mismatch Matrix

| # | Item | Doc Says | Code Reality | Severity | Required Action |
|---|------|----------|-------------|----------|-----------------|
| 1 | assess_risk() signature | implied to take event_scale, event_controversy, risk_type_labels | current signature is `(x_t_sequence, tick_logs)` — only 2 params | **MUST_PATCH_BEFORE_CODEX** | Doc must clarify: either (A) extend assess_risk() signature to also accept extraction_output, or (B) add a wrapper that reads event_scale/event_controversy from extraction_output before calling. The 3 call sites all have extraction_output available, so option (B) is the minimum-change path. |
| 2 | assess_risk() receives prior_floor inputs | event_scale / event_controversy "可作为 prior_floor" | assess_risk() currently has no access to event_scale/event_controversy | **MUST_PATCH_BEFORE_CODEX** | Same as item 1 — the data flow needs to be explicitly specified. |
| 3 | max_negative_shift calculation | "以 opinion spreaders 首尾累计负向迁移为准" | `_build_code_owned_agent_stance_matrix()` already computes per-agent start-end deltas but doesn't isolate negative shifts or return max | **ACCEPTABLE_KNOWN_ISSUE** | Codex will need to implement the helper; the doc's graceful-degrade requirement (Section 7.2, item 7) provides sufficient guardrails. |
| 4 | external_risk_adjustment | "仅作为 future hook" | zero traces in codebase — confirmed no existing implementation | **NO_ISSUE** | Clean state for future hook documentation. |
| 5 | METRIC_EXPLANATION_PREFILL location | report_prompts.py | report_prompts.py is static-only, houses 30+ prompt constants | **NO_ISSUE** | Perfect fit. |
| 6 | risk_type_labels whitelist | "仅限当前已有稳定白名单" | 13 entries in RISK_TYPE_LABELS in schemas/phase4.py | **NO_ISSUE** | Stable whitelist exists. |
| 7 | assess_risk() risk_level_label mapping | LOW→低风险, MEDIUM→中风险, HIGH→高风险, CRITICAL→重大风险 | RISK_LEVEL_LABELS in schemas/phase4.py:11-16 matches exactly | **NO_ISSUE** | |
| 8 | assess_risk() LLM non-involvement | "LLM 不负责生成风险等级" | risk_level is computed code-side at all 3 call sites, then injected into LLM prompt via CODE_OWNED_REPORT_CONTRACT block; final markdown is replaced with code-owned risk section via `_replace_risk_section_with_code_owned()` | **NO_ISSUE** | Current architecture already enforces code-owned risk_level. |
| 9 | final_report.md appendix insertion point | "由代码侧拼接进入 final_report.md 附录 / 数据说明" | `generate_markdown_report()` lines 1354-1368 have the appendix section with "### 模拟口径说明" and "### 数据来源边界" | **NO_ISSUE** | Clear insertion point exists at the appendix. |
| 10 | change_point_detection.py non-existence | "不新增 change_point_detection.py" | File does not exist — confirmed | **NO_ISSUE** | |

---

## 6. Test Plan Review

Recommended required commands:

```bash
.venv/bin/python -m py_compile src/phase4/report_agent.py src/phase4/report_prompts.py
.venv/bin/python -m pytest tests/test_report_product_contract.py tests/test_report_markdown_grounding.py -v
.venv/bin/python -m pytest tests/test_phase4_markdown_metric_grounding.py tests/test_schema_imports.py -v
git diff --check -- src/phase4/report_agent.py src/phase4/report_prompts.py tests/test_report_product_contract.py tests/test_report_markdown_grounding.py tests/test_phase4_markdown_metric_grounding.py "docs/iterations/v1.2.8.1-Risk-Assessment-Directionality-Metric-Explanation-Patch.md"
```

Smoke recommendation: **optional**

Reason: Smoke requires live LLM API calls and is environment-dependent. The APIConnectionError/502 handling protocol in the doc (Section 7.2, execution requirements) is correct: record as environmental blocker, do not judge code failure. Smoke should be a closeout gate, not a Codex execution gate. The targeted unit tests with fixtures are sufficient for code correctness verification.

### Test Matrix

| Test Type | Command | Priority | Existing Coverage |
|-----------|---------|----------|-------------------|
| py_compile | `py_compile src/phase4/report_agent.py src/phase4/report_prompts.py` | HARD GATE | N/A |
| targeted pytest (directionality) | `pytest tests/test_risk_assessment_directionality.py -v` | HARD GATE | **New file needed** |
| regression pytest (existing) | `pytest tests/test_report_product_contract.py tests/test_report_markdown_grounding.py -v` | HARD GATE | Comprehensive (399+564 lines) |
| lightweight regression | `pytest tests/test_phase4_markdown_metric_grounding.py tests/test_schema_imports.py -v` | HARD GATE | Lightweight (70+81 lines) |
| optional smoke | `python main.py seeds/test8.txt` | SOFT GATE | N/A |
| artifact check | manual inspect final_report.json / final_report.md | SOFT GATE | N/A |

### Existing Fixture Reusability

The fixtures in test_report_product_contract.py and test_report_markdown_grounding.py are rich and reusable:
- `_extraction()` — creates EntityExtractionOutput with configurable event_scale/event_controversy
- `_tick()` — creates TickLog with configurable polarization_index
- `_entry()` — creates AgentEntry with configurable stance values
- `_phase2_output()` — creates Phase2Output

These can be directly reused or lightly adapted for the new test_risk_assessment_directionality.py.

### Doc Acceptance Command Accuracy

The acceptance commands in Section 7.2 and Section 8 reference `.venv/bin/python`. The doc should note this is the project virtualenv path and may need adjustment per environment. This is a minor note, not a blocker.

---

## 7. Risk Drift Review

hard_blockers: **none**

scope_drift_risks:
1. **LOW RISK** — assess_risk() signature expansion could inadvertently pull in broader refactoring. Mitigation: the doc explicitly states "保持 risk_level enum 不变" and "保持 risk_level_label 中文映射不变".
2. **LOW RISK** — max_negative_shift implementation could overreach into Phase 3 territory if it tries to modify tick_logs structure. Mitigation: Section 6.3 explicitly forbids Phase 3 changes, and Section 7.2 item 7 requires graceful degrade.
3. **LOW RISK** — METRIC_EXPLANATION_PREFILL injected into LLM prompt could inadvertently influence LLM behavior. Mitigation: Section 11.2 specifies code-side concatenation into appendix, not prompt injection.

must_not_do_for_codex:
1. Must NOT add change_point_detection.py — confirmed absent from codebase; doc correctly forbids
2. Must NOT modify Phase 1-3 — doc correctly forbids
3. Must NOT modify schema — doc correctly forbids
4. Must NOT add external_risk_adjustment as real data source — doc correctly gates this to future hook only
5. Must NOT let LLM generate risk_level_label — current architecture already enforces this; doc reinforces
6. Must NOT let LLM generate metric explanation — doc correctly requires code-owned prefill
7. Must NOT implement full v0.3 five-category change point framework — doc correctly positions v0.3 as carry-over only
8. Must NOT add whitebox/change_point_evidence.json — confirmed absent; doc correctly forbids

---

## 8. Required Patch Before Codex

Two minimal doc patches are required:

### Patch 1: Clarify assess_risk() data flow (§10.1 and §7.2)

**Problem**: The doc describes assess_risk() computing `prior_floor` from `event_scale`/`event_controversy`, but the current function signature `assess_risk(x_t_sequence, tick_logs)` does not receive `extraction_output`. The doc should specify the concrete signature change.

**Recommended patch** — Add to §7.2 (execution requirements), after item 1:

```text
1a. assess_risk() signature SHALL be extended to accept extraction_output as a
    keyword-only optional parameter:
    def assess_risk(x_t_sequence, tick_logs, *, extraction_output=None) -> tuple
    This is the minimum-change path: all 3 call sites already have extraction_output
    in scope. event_scale and event_controversy SHALL be read from
    extraction_output when available.
```

### Patch 2: Clarify max_negative_shift data source (§10.1 and §7.2 item 6)

**Problem**: The doc says "以 opinion spreaders 首尾累计负向迁移为准" but doesn't specify which data structure to read from. The code already has `_build_code_owned_agent_stance_matrix()` which computes per-agent start-end deltas.

**Recommended patch** — Add to §10.1, after the `max_negative_shift` line:

```text
max_negative_shift SHALL be computed by reusing the logic in
_build_code_owned_agent_stance_matrix() to obtain per-agent initial_stance and
final_stance, then taking max(0, initial - final) across all agents. If fewer
than 2 tick_logs with entries exist, or if no agent appears in both start and
end ticks, max_negative_shift SHALL return None and be ignored in assess_risk().
```

These are the **only** doc patches required. No full rewrite.

---

## 9. Codex Readiness

codex_readiness: READY_AFTER_DOC_PATCH

### Codex Execution Scope

```
exact attempt_id: attempt-v1.2.8.1-01

allowed files:
  src/phase4/report_agent.py      — assess_risk() fix, prior_floor, max_negative_shift helper,
                                    external_risk_adjustment future hook, terminology mapping
  src/phase4/report_prompts.py    — METRIC_EXPLANATION_PREFILL constant
  tests/test_risk_assessment_directionality.py  — NEW: targeted directionality tests
  tests/test_report_product_contract.py         — update/add risk directionality assertions
  tests/test_report_markdown_grounding.py       — update/add metric explanation grounding
  tests/test_phase4_markdown_metric_grounding.py — update as needed
  docs/iterations/v1.2.8.1-Risk-Assessment-Directionality-Metric-Explanation-Patch.md
  docs/iterations/TASK_LOG.md
  docs/iterations/CHANGELOG.md

forbidden files:
  src/phase1/** src/phase2/** src/phase3/**
  src/schemas/**
  src/whitebox/**
  main.py
  seeds/**
  docs/dev_spec.md
  workflow 文档
  产品侧 v0.3 文档原件

required tests:
  - py_compile: src/phase4/report_agent.py src/phase4/report_prompts.py
  - pytest: tests/test_risk_assessment_directionality.py (NEW)
  - pytest: tests/test_report_product_contract.py tests/test_report_markdown_grounding.py (regression)
  - pytest: tests/test_phase4_markdown_metric_grounding.py tests/test_schema_imports.py (regression)

required execution report fields:
  1. 实际修改文件清单
  2. 实际新增文件清单
  3. 实际删除文件清单 (expected: none)
  4. assess_risk() 修复摘要
  5. prior_floor 规则摘要
  6. max_negative_shift 计算摘要
  7. external_risk_adjustment future hook 记录方式
  8. METRIC_EXPLANATION_PREFILL 插入方式
  9. 术语映射实现位置
  10. 测试命令与结果
  11. 是否跑 smoke
  12. 最新 run_dir
  13. artifact check 结果
  14. risk_level before/after 样例对比
  15. 是否触碰 forbidden files (expected: no)
  16. git diff 摘要
  17. carry_over
```

---

## Appendix A: Reviewer Individual Verdicts

### Scope Reviewer

scope_verdict: **GO**

Rationale: The iteration is correctly scoped as M-Level. It fixes a blocking directionality bug without expanding into architecture territory. The allowed/forbidden file lists are correct. The v0.3 product-side change point rules are correctly positioned as carry-over, not implementation. Single attempt is appropriate.

### Code Reality Reviewer

code_reality_verdict: **CONDITIONAL_GO**

confirmed_code_facts:
- assess_risk() exists at report_agent.py:729 with confirmed directionality issue
- All 3 call sites have access to extraction_output with event_scale/event_controversy
- report_prompts.py is static-only and is the correct location for METRIC_EXPLANATION_PREFILL
- RISK_TYPE_LABELS whitelist with 13 entries is stable
- _build_code_owned_agent_stance_matrix() already provides per-agent start-end deltas
- No external_risk_adjustment or change_point_detection traces exist

uncertain_code_facts:
- Whether max_negative_shift can stably differentiate opinion_spreaders from event_entities in all seed scenarios (doc correctly requires graceful degrade)

doc_code_mismatches:
- assess_risk() signature/data flow needs clarification (see Patch 1 in §8)
- max_negative_shift data source needs specification (see Patch 2 in §8)

required_doc_patch_before_codex:
- Patch 1: Clarify assess_risk() signature extension
- Patch 2: Specify max_negative_shift computation from existing stance matrix

### Test & Verification Reviewer

test_verdict: **CONDITIONAL_GO**

Rationale:
- All acceptance commands are syntactically valid
- Existing test fixtures are rich and reusable
- New test_risk_assessment_directionality.py is justified and doesn't fragment existing tests
- The doc correctly prioritizes modifying existing tests over creating new ones
- APIConnectionError/502 protocol is correctly specified
- Smoke test is correctly positioned as optional/soft gate

Conditions:
- Patch 1 & 2 must be applied before tests can be written (test fixtures depend on final assess_risk() signature)

### Risk Drift Reviewer

drift_verdict: **GO**

hard_blockers: none

scope_drift_risks: 3 low-risk items identified (see §7), all with adequate doc mitigations

must_not_do_for_codex: 8 items listed (see §7), all covered by doc's explicit prohibitions

The doc's defense against scope creep is strong: §3.3 lists 21 "不解决的问题", §3.4 lists 10 "禁止变化", §6.3 lists 13 "禁止修改" categories, and §13.2 lists 6 "不实现" items for change point framework.

---

## Appendix B: Summary of Findings

| Dimension | Verdict | Blockers |
|-----------|---------|----------|
| Scope | GO | none |
| Code Reality | CONDITIONAL_GO | 2 minor doc patches |
| Test & Verification | CONDITIONAL_GO | dependent on patches |
| Risk Drift | GO | none |
| **DS Final** | **CONDITIONAL_GO** | **2 doc patches before Codex** |

The v1.2.8.1 iteration document is well-constructed, code-aware, and appropriately scoped. The two identified doc-code mismatches are minor and addressable with targeted patches to §7.2 and §10.1. Once patched, the document is ready for Codex execution of attempt-v1.2.8.1-01.
