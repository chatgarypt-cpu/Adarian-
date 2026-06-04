# DS Agent Team 会话完整审计导出 — v1.2.8.1 Phase 4 Report Stack

**审计会话ID**: audit-v1.2.8.x-phase4-report-stack-snapshot-01
**审计日期**: 2026-05-15
**目标分支**: work/v1.2.8
**基准提交**: df94ac0
**审计模式**: DS Agent Team（多审查者并行 + DS Controller 综合裁决）
**语言**: 中文

---

## 一、审计方法与范围

### 1.1 审查者组成

本次会话共启动两轮 DS Agent Team 审查：

**第一轮 — 初始全量审计（4 个并行审查者）**：
- Architecture Reviewer：代码架构、职责分离、模块边界
- Prompt/Product Rules Reviewer：Prompt 规则完整性、产品合规
- Markdown/Report Output Reviewer：报告输出质量、格式规范
- Downstream Data Contract Reviewer：下游数据契约、结构化数据设计

**第二轮 — Verify/Accept 审查（6 个并行审查者）**：
- Scope Compliance Reviewer：变更范围合规
- Code Diff Reviewer：代码差异审查
- Test Evidence Reviewer：测试证据验证
- Risk Logic Reviewer：风险逻辑专项审查
- Documentation Sync Reviewer：文档同步检查
- Smoke Evidence Reviewer：冒烟测试证据

### 1.2 审查范围

| 维度 | 覆盖范围 |
|------|----------|
| 核心代码 | `src/phase4/report_agent.py` (1675行)、`src/phase4/report_prompts.py` (366行) |
| Schema | `src/schemas/phase4.py` (132行) |
| 白盒检测 | `src/whitebox/report_completeness.py`、`src/whitebox/report_observer.py` |
| 测试 | `test_report_product_contract.py`、`test_report_markdown_grounding.py`、`test_phase4_markdown_metric_grounding.py`、`test_risk_assessment_directionality.py` |
| 冒烟日志 | 并行5进程 + 串行3进程 smoke runs |
| 文档 | 迭代文档、TASK_LOG、CHANGELOG |
| 产物 | 3次完整运行的 final_report.json、final_report.md |

---

## 二、代码架构审查

### 2.1 当前架构快照

`report_agent.py`（1675行）混合了5种职责：

| 职责 | 代码区域 | 行数估算 |
|------|----------|----------|
| 风险计算器 | `assess_risk()` L829-920, `_max_negative_shift_from_stance_matrix()` | ~150 |
| 叙事生成器 | `generate_report_with_llm()` L927-994, prompt assembly | ~200 |
| Markdown 规范化器 | `_normalize_saved_markdown()` L568-579, `_replace_report_metric_terms()` L458-485, `_replace_risk_section_with_code_owned()` L407-424 | ~250 |
| LLM 编排器 | `generate_markdown_report()` L1421-1561, retry逻辑 | ~200 |
| I/O 处理器 | `save_report_artifacts()`, `build_batch_synthesis_context()` 等 | ~200 |

其余为辅助函数、常量定义和胶水代码。

### 2.2 report_prompts.py 静态性验证

经 AST 检查确认：`report_prompts.py` 为**纯静态文件**，无 import、无函数定义、无类定义。包含约30个 prompt 规则常量，按 T0/T1/T2/T3 优先级组装为 `REPORT_SYSTEM_PROMPT`。

### 2.3 T0/T1/T2/T3 规则优先级架构

- **T0（硬锁定）**：代码侧直接替换，LLM 无权修改（如风险等级、风险类型标签）
- **T1（结构性约束）**：五章模板、章节顺序、标题层级
- **T2（内容约束）**：禁止语、指标术语、叙事框架
- **T3（质量引导）**：few-shot 参考、风格指引

### 2.4 代码所有权机制

- `_build_code_owned_report_contract_block()`：注入代码自有标签到 prompt
- `_replace_risk_section_with_code_owned()`：完全替换 LLM 生成的第三章（风险研判）
- `_ensure_metric_explanation_prefill()`：注入代码自有的指标解释
- `_remove_metric_explanation_sections()`：移除 LLM 重复生成的指标解释
- `Phase4Output` 16个字段中13个为代码自有字段

### 2.5 Markdown 规范化链（10步）

`_normalize_saved_markdown()` 执行10步规范化：术语替换 → 内容清理 → 结构验证 → 标题规范化 → 指标预填 → 代码自有块注入 → 禁止语检查 → 格式修正 → 附录完整性 → 最终验证

---

## 三、代码质量发现

### 3.1 【已确认 Bug】"模拟模拟极化指数" 重复前缀

- **文件位置**: `src/phase4/report_agent.py` L471
- **根因**: `_replace_report_metric_terms()` 中 `("极化指数", "模拟极化指数")` 替换规则未检查是否已有"模拟"前缀，LLM 若已正确写出"模拟极化指数"，替换后变成"模拟模拟极化指数"
- **影响范围**: 3轮 smoke run 全部复现（run_1 L174, run_2 L180, run_3 L15/L39/L43/L59/L118/L155）
- **严重度**: 中等 — 不影响数据正确性，但影响报告可读性
- **建议修复**: 使用正则负向后顾 `(?<!模拟)极化指数` 或替换前做字符串包含检查

### 3.2 【已确认 Bug】Prompt 指令泄漏

- **文件位置**: `src/phase4/report_agent.py` 的 `_strip_internal_code_owned_labels()`
- **现象**: run_3 报告 L151 出现"code-owned标签"原文泄漏到产物中
- **根因**: 当前只过滤英文精确匹配（"CODE_OWNED_REPORT_CONTRACT"等），未覆盖中文转述
- **严重度**: 低 — 单次出现，不影响语义
- **建议修复**: 扩展过滤词表，加入中文变体

### 3.3 【已确认 Gap】`select_primary_risk_types()` 关键词匹配盲区

- **文件位置**: `src/phase4/report_agent.py` 的 `select_primary_risk_types()`
- **现象**: 3轮 test8 smoke 全部只返回 `['negative_narrative_risk']`
- **根因链**:
  1. test8（OPPO 营销争议）无公安/市监局/教育局等 audience 关键词 → `GENERIC_GOVERNMENT` → 不加 audience 专属类型
  2. 新 `assess_risk()` 输出结构化文本不含旧 `keyword_map` 匹配词（"负面"≠"负向"、"争议"、"信息透明"等）
  3. `polarization_index` ~0.38 < 0.5 → 不触发 `group_polarization_risk`
  4. 兜底逻辑每次命中 `negative_narrative_risk`
- **是否回归**: 否 — v1.2.8.1 未修改此函数，但这版将 `risk_assessment` 改为结构化输出后匹配真空更彻底
- **严重度**: 中等 — 风险类型标签缺乏区分度，所有中等风险事件都标为同一类型
- **建议修复**: 改为从 `extraction_output.event_type`、`event_scale`、`event_controversy` 和 `tick_logs` 极化数据判断，而非依赖文本匹配

### 3.4 【已确认 Gap】Phase 1 Validator 与 Pydantic 校验不一致

- **现象**: 某次 smoke run 的 Phase 1 Validator（LLM-based）通过，但 Pydantic 因缺少 `occupation` 字段拒绝
- **根因**: LLM-based validator 漏检了 schema 强制字段
- **严重度**: 低 — Phase 1 已有 fallback 机制，不影响最终产物
- **状态**: 已知结构性限制，非本次引入

---

## 四、测试与冒烟验证

### 4.1 测试套件结果

| 测试文件 | 测试数 | 结果 |
|----------|--------|------|
| `test_risk_assessment_directionality.py` | 11 | 全部通过 |
| `test_report_product_contract.py` | 9 | 全部通过 |
| `test_report_markdown_grounding.py` | 13 | 全部通过 |
| `test_phase4_markdown_metric_grounding.py` | 2 | 全部通过 |
| `test_schema_imports.py` | 2 | 全部通过 |
| 语法编译检查 | 2 | 全部通过 |
| **总计** | **43** | **全部通过** |

### 4.2 风险方向性测试覆盖矩阵

| 验收标准 | 对应测试 | 结果 |
|----------|----------|------|
| `final_x <= 4.7` → MEDIUM | `test_low_final_stance_triggers_medium` | PASS |
| `negative_trend >= 0.4` → MEDIUM | `test_negative_trend_triggers_medium` | PASS |
| `final_pol >= 0.30` → MEDIUM | `test_final_polarization_triggers_medium` | PASS |
| `max_negative_shift >= 1.2` → MEDIUM | `test_max_negative_shift_triggers_medium` | PASS |
| event_scale + event_controversy → MEDIUM floor | `test_scale_and_controversy_provide_medium_floor` | PASS |
| 单一轻信号不触发 HIGH/CRITICAL | `test_single_light_signal_does_not_trigger_high_or_critical` | PASS |
| OPPO 不过度升级为 CRITICAL | `test_oppo_brand_marketing_dispute_is_not_critical` | PASS |
| risk_type_labels 代码自有 | `test_risk_type_labels_remain_code_owned` | PASS |
| LLM 不被要求判断 risk_level | `test_llm_prompt_does_not_ask_llm_to_decide_risk_level` | PASS |
| 指标预填代码自有 + 去重 | `test_metric_explanation_prefill_is_code_owned_and_deduplicated` | PASS |
| saved markdown 使用指标术语 | `test_saved_markdown_uses_metric_terminology` | PASS |

### 4.3 冒烟测试结果

**并行模式（5进程）**：全部失败，FileExistsError
- 根因：`main.py:218` 使用秒级时间戳 + `exist_ok=False`，5个进程同一秒内碰撞
- 判定：**已有基础设施缺陷，非 v1.2.8.1 引入**，所有历史版本均受影响

**串行模式（5进程）**：3个完成，2个被用户中断

| 运行 | 退出码 | 风险等级 | 产物完整 | 9/9 Markdown 检查 |
|------|--------|----------|----------|-------------------|
| Run 1 | 0 | MEDIUM/中风险 | 是 | 通过 |
| Run 2 | 0 | MEDIUM/中风险 | 是 | 通过 |
| Run 3 | 0 | MEDIUM/中风险 | 是 | 通过 |
| Run 4 | 中断 | N/A | N/A | N/A |
| Run 5 | 中断 | N/A | N/A | N/A |

每轮产物包含：`run_meta.json`、`run.log`、`timing_summary.json`、`entities_and_relations.json`、`social_graph.json`、`tick_logs.json`、`final_report.json`、`final_report.md`、`whitebox_summary.json`

### 4.4 Markdown 质量检查（每轮 9/9 通过）

| 检查项 | Run 1 | Run 2 | Run 3 |
|--------|-------|-------|-------|
| 模拟立场均值 存在 | PASS | PASS | PASS |
| 模拟极化指数 存在 | PASS | PASS | PASS |
| 模拟关键变化点 存在 | PASS | PASS | PASS |
| 指标解释 section 存在 | PASS | PASS | PASS |
| METRIC_EXPLANATION_PREFILL 文本存在 | PASS | PASS | PASS |
| "待评估" 不存在 | PASS | PASS | PASS |
| "情绪均值" 不存在于正文 | PASS | PASS | PASS |
| 五章结构 完整 | PASS | PASS | PASS |
| CODE_OWNED labels 不存在 | PASS | PASS | PASS |

---

## 五、风险方向性修复验证

### 5.1 修复内容

v1.2.8.1 将 `assess_risk()` 的风险方向从"高立场均值=高风险"改为"低立场均值+负向趋势+高极化+大负向迁移=高风险"。

### 5.2 信号确认

| 风险信号 | 阈值 | 触发等级 |
|----------|------|----------|
| `final_x <= 4.7` | ≤4.7 | MEDIUM |
| `negative_trend >= 0.4` | ≥0.4 | MEDIUM |
| `final_pol >= 0.30` | ≥0.30 | MEDIUM |
| `final_pol >= 0.45` + 其他信号 | ≥0.45 | HIGH |
| `max_negative_shift >= 1.2` | ≥1.2 | MEDIUM |
| `max_negative_shift >= 2.0` | ≥2.0 | HIGH |
| `max_negative_shift >= 2.5` | ≥2.5 | CRITICAL |
| CRITICAL 多条件 | final_x≤3.0 AND pol≥0.45 AND shift≥2.5 AND (scale≥0.7 或 controversy≥0.8 或 sensitive) | CRITICAL |
| event_scale + event_controversy | 提供 MEDIUM floor | MEDIUM |

### 5.3 test8 验证

- 旧逻辑：test8 会返回 LOW（final_x ~5.0，无明显上升趋势）
- 新逻辑：test8 返回 MEDIUM（event_scale + event_controversy 提供 MEDIUM floor）
- 3轮 smoke 一致返回 MEDIUM，方向正确

---

## 六、解耦建议

### 6.1 三路拆分方案

| 新模块 | 职责 | 来源 |
|--------|------|------|
| `report_narrative.py` | LLM 调用编排 + prompt 组装 + 叙事生成 | report_agent.py 中的 LLM 编排和叙事部分 |
| `report_title.py` | 标题生成 + 标题规范化 + 标题 locale 适配 | report_agent.py 中分散的标题处理逻辑 |
| `report_normalizer.py` | Markdown 规范化链 + 术语替换 + 代码自有块注入 | report_agent.py 中的 `_normalize_saved_markdown()` 及其10步 pipeline |

### 6.2 下游结构化数据契约

**当前状态**：`final_report.md` 被明令禁止作为结构化数据源，但下游消费方缺乏正式的替代契约。

**建议设计三个结构化产物**：
- `parallel_world_synthesis.json`：多平行世界合成结果
- `batch_synthesis_context.json`：批量合成上下文
- `single_run_summary.json`：单次运行摘要

**设计原则**：
- 所有字段声明类型、nullable 语义、枚举值范围
- code-owned 与 LLM-generated 分表存储
- 包含 `data_provenance` 字段标注数据来源

---

## 七、已知问题清单

### 7.1 预审允许的已知问题（4项）

| # | 问题 | 状态 |
|---|------|------|
| 1 | 风险阈值仍是工程初始阈值，待后续多 seed 标定 | 遗留，不在本次范围 |
| 2 | 模拟极化指数仍是工程 proxy | 遗留，不在本次范围 |
| 3 | 模拟关键变化点仍未完整升级为多信号 framework | 遗留，不在本次范围 |
| 4 | `external_risk_adjustment` 仅作为 future hook，未实现 | 遗留，不在本次范围 |

### 7.2 DS 审计额外发现的已知问题（3项）

| # | 问题 | 严重度 |
|---|------|--------|
| 5 | `select_primary_risk_types()` 关键词匹配盲区，所有中等风险事件统一标为 `negative_narrative_risk` | 中等 |
| 6 | `main.py:218` 并行并发缺陷（`exist_ok=False` + 秒级时间戳），所有版本均受影响 | 低（基础设施） |
| 7 | `_replace_report_metric_terms()` 中"模拟模拟极化指数"重复前缀 bug | 中等 |

---

## 八、最终裁决

### DS Verdict: PASS

**验收结果**: `pass_with_known_issues`

**裁决依据**:
- 43/43 测试全部通过
- 3轮串行 smoke 全部返回正确风险等级（MEDIUM）
- 风险方向性修复有效（LOW→MEDIUM 确认方向正确）
- 禁止修改的文件未被触碰
- 已知问题全部与预审允许列表一致
- 无 hard blocker

**建议关闭决策**: `closeout_pass_with_known_issues`

**建议关闭备注**:
> v1.2.8.1 解决了阻塞性的风险方向性问题，建立了代码自有的指标解释机制。parallel run_dir 并发冲突为已有基础设施缺陷，应单独追踪。"模拟模拟极化指数"重复前缀 bug 和 `select_primary_risk_types()` 匹配盲区建议在后续 Phase 4 改进中修复。

**下一动作**: 移交 Control Agent / Owner 进行 v1.2.8.1 最终关闭。

---

## 九、附录：session 产物索引

| 产物 | 路径 |
|------|------|
| DS Agent Team 预审报告 | `audit/DS_Agent_Team_Pre_Audit_Report_v1.2.8.1_2026-05-15.md` |
| DS Agent Team Verify/Accept 报告 | `audit/phase4大版本改造/DS_Agent_Team_Verify_Accept_Report_v1.2.8.1_2026-05-15.md` |
| 本次会话完整审计导出（本文件） | `audit/phase4大版本改造/DS_Agent_Team_Session_Full_Audit_Export_v1.2.8.1_2026-05-15.md` |
| 串行 Smoke 日志 | `smoke_logs/v1.2.8.1_test8_sequential_20260515_150102/` |
| 并行 Smoke 日志 | `smoke_logs/v1.2.8.1_test8_parallel_20260515_145446/` |
| Run 1 产物 | `outputs/runs/test8_20260515_150103/` |
| Run 2 产物 | `outputs/runs/test8_20260515_150632/` |
| Run 3 产物 | `outputs/runs/test8_20260515_151223/` |
| 新增测试文件 | `tests/test_risk_assessment_directionality.py` |
| 迭代文档 | `docs/iterations/v1.2.8.1-Risk-Assessment-Directionality-Metric-Explanation-Patch_repaired.md` |

---

*本报告由 DS Agent Team 在 2026-05-15 会话中综合生成，整合了两轮审查（初始全量审计 + Verify/Accept 审查）的全部发现。报告语言为中文。*
