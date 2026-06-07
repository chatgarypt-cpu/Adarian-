/agent team

# Code Reality Mapping Review — Adarian MVP v1.3.1

> 使用 skill: code-reality-review (v0.1)
> 审查精神：从真实代码出发；先描述，再评价；反对过度设计；反对代码粘稠。

## 审查目标

target_path: src/
target_files:
  - main.py
  - config.py
  - src/phase1/extraction.py
  - src/phase3/tick_simulation.py
  - src/phase3/risk_analyzer.py
  - src/phase3/parser.py
  - src/phase4/report_agent.py
  - src/phase4/report_narrative.py
  - src/phase4/report_prompts.py
  - src/phase4/report_normalizer.py
  - src/phase4/paths.py
  - src/whitebox/run_meta.py
  - src/llm_client.py
  - src/model_router.py
  - src/schemas/
  - legacy/phase4/legacy_analytics.py
  - legacy/phase4/legacy_generation.py
  - legacy/phase4/legacy_markdown.py
  - legacy/main_legacy.py

辅助参考:
  - tests/ (全部测试文件)
  - outputs/runs/test8_20260606_180754/ (最新 smoke 产出)
  - docs/iterations/active/v1.3.1_phase4_streamlining_and_entrypoint_unification_r1.md
  - tools/bypass_compare_phase3.py

## Reviewer 分工

5 个 agent 依次执行，每位阅读代码后输出发现给下一 agent。

### agent 1: code-reality-mapper
阅读 src/ 下所有代码，列出实际存在的文件、类、函数、调用链。只描述现状，不评价。

输出：code_reality_inventory.md
- 当前真实文件列表（含行数）
- 当前真实类/函数清单（含职责）
- 当前真实调用链
- 设计中提到但代码未实现的能力

### agent 2: boundary-reviewer
基于 agent 1 的发现，检查 SRP 合规性。重点关注：
- tick_simulation.py 1067 行 — 是否存在巨类/多职责混合？
- extraction.py 675 行 — Analyzer/Generator/Validator 边界是否清晰？
- report_agent.py 283 行 — 纯消费端是否真正隔离？
- model_router.py — 是否轻量（dict + 一层函数）？
- 各模块间是否有不应该存在的耦合

输出：code_reality_boundary.md
- 职责清晰的模块
- 职责粘稠的模块（含说明）
- 最小拆分建议（克制）
- 不建议现在拆分的内容

### agent 3: runtime-flow-mapper
基于 agent 1+2 的发现，画出 Adarian 端到端执行流程。
从 main.py 启动到输出保存，逐阶段检查实现完整性。

重点关注：
- LLM 调用链路（model_router → llm_client → init_llm_client → 各 phase）
- Phase 3 tick 模拟 → risk_analyzer → parser → Phase4 消费的完整数据流
- smoke test 中验证过的路径 vs 未覆盖路径

输出：code_reality_runtime_flow.md
- 真实 runtime flow 文字说明
- Mermaid 运行时流程图（含各 phase 调用关系）
- missing steps 列表

### agent 4: design-alignment-reviewer
对比 v1.3.1 迭代计划 vs 真实代码。按迭代计划的 Goal A-E 逐项检查：

Key checks:
1. Phase4 纯消费端：report_agent.py 是否真的不再调旧计算函数？simulation_dataset 是否是唯一数据源？
2. 入口归一：main.py 是否只做编排？build_run_paths/write_run_meta 是否已抽出？
3. Legacy 归档：legacy/ 是否与 src/ 完全隔离不互相引用？
4. 模型路由：model_router.py 是否只控制模型名不控制 params？.env 是否只放凭证？
5. 测试迁移：旧测试是否已切到 legacy 路径？新测试是否覆盖边界？
6. YAGNI：是否存在死代码/未使用的函数/参数？
7. KISS：是否存在过度复杂的实现？
8. 是否引入了迭代范围外的改动？

设计文档对照：docs/iterations/active/v1.3.1_phase4_streamlining_and_entrypoint_unification_r1.md

输出：code_reality_design_alignment.md
- 设计已实现
- 设计部分实现
- 设计未实现
- 实现偏离设计
- 本次范围外的改动

### agent 5: mermaid-synthesizer
汇总 agent 1-4 的所有发现，输出最终报告。

必须画的 Mermaid 图：
1. 文件依赖图（import/调用关系）
2. 类/职责图（需反映真实代码结构，不照抄示例）
3. 运行时流程图（端到端）
4. 设计 vs 实现差异图（dashed node = missing）

最终报告格式（code_reality_mapping_review.md）：

```markdown
# Code Reality Mapping Review：Adarian MVP v1.3.1

## 1. 审查结论
Verdict: PASS / PASS_WITH_FINDINGS / REPAIRABLE_HOLD / BLOCKING_HOLD / FAIL

## 2. team_mode / tool 使用情况

## 3. 真实代码结构（文件+类+函数+行数）

## 4. 真实运行路径（文字 + Mermaid）

## 5. Mermaid 图
### 5.1 文件依赖图
### 5.2 类职责图
### 5.3 运行时流程图
### 5.4 设计 vs 实现差异图

## 6. 低耦合审查
- 是否存在巨类？
- 是否存在多职责函数？
- 哪些逻辑粘稠？
- 必要拆分 vs 过度设计？

## 7. 设计一致性审查

## 8. 风险与问题
- Blocking Issues
- Repairable Issues
- Known Issues

## 9. 最小改进建议

## 10. 最终建议
```

## 输出质量协议（必读）

1. 必须使用 Write() 工具直接写入最终报告，禁止 inline editor
2. 写入后重新读取文件检查：无行号残留、无单词断裂、无表格断裂、无末尾截断
3. 必须包含 Verdict、Known Issues、改进建议、Next Step
4. 格式污染 → Verdict 降级为 REPAIRABLE_HOLD，不得标记 PASS

## 最终产出

将最终报告写入：outputs/code_reality_mapping_review.md
