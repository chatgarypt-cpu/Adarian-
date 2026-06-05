# Dispatch Prompt: Phase 3/4 Data Flow Reality Review

@skill code-reality-review

报告使用中文。

## 审查目标

target_path: /Users/gary/项目开发/AdarianMigration/adarian mvp

目标文件:
- src/phase3/risk_analyzer.py
- src/phase3/inflection_detector.py
- src/phase3/stance_analyzer.py
- src/phase3/parser.py
- src/phase3/__init__.py
- src/phase4/report_agent.py
- src/phase4/report_narrative.py
- src/phase4/report_normalizer.py
- src/phase4/report_prompts.py
- src/phase4/report_title.py
- main_new.py
- tools/run_pipeline_new.py

辅助参考（可选查看，不强制）:
- docs/iterations/active/v1.3.0_phase3_parser_aggregation_layer.md

## 重要：独立审查要求

禁止读取 reality_review.md 文件。禁止引用任何手动分析结果。
所有发现必须直接从目标代码文件中读取函数签名、调用链和数据流得出。
每个 agent 必须实际读取 .py 文件内容，不依赖第三方总结。

禁止越界目录:
- ~/.hermes/
- ~/.cc-switch/
- ~/.claude/

## Agent Team

### @agent phase3-data-flow-reviewer

审查 src/phase3/ 下的 4 个模块。从真实代码出发：

1. 读取每个 .py 文件，列出所有 public class/method/function
2. 对每个 function：列出 inputs（参数、类字段）、outputs（返回值、副作用写入）
3. 从 parser.py 的 parse() 入口画出调用链图
4. 检查 simulation_dataset 实际结构与迭代计划 §5.4 的契约有无差异
5. 检查是否 import 了 Phase 4 的任何内容
6. 标记每个 function 是否是 deterministic（纯计算代码）

### @agent phase4-data-flow-reviewer

审查 src/phase4/ 下的 5 个模块 + main_new.py + tools/run_pipeline_new.py。

1. 读取所有文件，列出所有 public function
2. 标记哪些 Phase 4 函数仍在内联计算本应属于 Phase 3 的字段：
   - assess_risk()
   - determine_audience_mode()
   - select_primary_risk_types()
   - identify_inflection_points()
   - _build_code_owned_agent_stance_matrix()
   - _max_negative_shift_from_stance_matrix()
   - _sensitive_prior_risk_types()
3. 追踪 LLM 调用链：generate_report_with_llm() → generate_report_with_llm_narrative() → LLM → parse_llm_report_response()
   - 特别检查新路径（main_new.py run_phase4()）中 LLM 返回的 markdown 变量是否被实际使用
4. 追踪 Markdown 保存链：save_markdown_report() → 优先用 `_llm_generated_markdown` 还是 fallback 到 generate_markdown_report()
5. 评估对策建议模板化程度：_governance_recommendation_lines() 等函数是否感知模拟数据
6. 检查新路径是否满足隔离要求（只从 simulation_dataset 消费，不重算）

### @agent data-flow-synthesizer

等前两个 agent 完成审查后，汇总 findings 并产出最终报告。

报告结构（遵循 code-reality-review §5）：

1. **审查结论** — Verdict: PASS / PASS_WITH_FINDINGS / REPAIRABLE_HOLD / FAIL
2. **真实代码结构** — 文件列表、类/函数清单、职责
3. **Mermaid 数据流图**：
   - 文件依赖图（谁 import 谁）
   - 数据产消图（Phase 3 生成字段 → Phase 4 消费字段）
   - Phase 4 内联计算残留标记图
   - 运行时 LLM 调用链图
4. **低耦合审查** — 职责粘稠点、过度设计、必要拆分
5. **设计一致性** — 对比 v1.3.0 迭代计划验收标准
6. **风险与问题** — Blocking / Repairable / Known
7. **最小改进建议** — 克制、可执行

输出要求：
- 使用 Write() 工具直接写入 tasks/active/v1.3.0-reality-review/outputs/ 下的报告文件
- 写入后必须读回检查格式质量：无行号残留、无表格断裂、无单词断裂
- 报告文件名：phase3_phase4_data_flow_reality_review_2026-06-05.md

## 工作流

1. phase3-data-flow-reviewer 先审 Phase 3 模块
2. phase4-data-flow-reviewer 再审 Phase 4 模块（可与步骤 1 并行）
3. data-flow-synthesizer 汇总撰写报告
