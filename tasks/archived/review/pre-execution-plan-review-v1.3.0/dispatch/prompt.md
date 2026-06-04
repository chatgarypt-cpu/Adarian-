# Pre-Execution Plan Review — v1.3.0 parser 聚合层方案审查

> 审查模式：agent-team（3 reviewer + 1 synthesis）
> 审查目标：`docs/iterations/active/v1.3.0_phase3_parser_aggregation_layer.md`
> 参考现状：`tasks/archived/review/adarian-source-reality-review/outputs/code_reality_review.md`

---

@skill pre-execution-plan-review

## 审查目标

审查迭代计划 `docs/iterations/active/v1.3.0_phase3_parser_aggregation_layer.md` 的质量，从代码实际现状出发，不参考过时设计文档。

### 前期阅读（所有 agent 必须先读）

1. `tasks/archived/review/adarian-source-reality-review/outputs/code_reality_review.md` — 了解当前代码库的全景、Phase 4 的职责模糊点、Phase 3 的现状
2. 迭代计划本身 — 目标和边界

### 关键上下文

- 当前代码基线：8ea3f27（workflow v4.3 baseline）
- Phase 4 report_agent.py 中 assess_risk() / identify_inflection_points() / stance 计算 是 code-owned 确定性算法，住在 Phase 4 但本质属于 Phase 3
- Parser 是纯聚合层，零 LLM、零计算、零格式判断
- Phase 3 新增子模块是迁移式重建（不是从 Phase 4 搬代码）
- 不删除、不修改 Phase 4 现有代码

### 分 agent 任务

@agent plan-scope-checker
检查 scope 完整性和边界。重点关注：
- 是否有遗漏的改动范围？
- Non-goals 是否真正确认了不改的东西？
- 是否与代码现状一致？

@agent plan-design-smell-detector
检查设计气味。重点关注：
- Parser 是否真的是纯聚合（没有计算/LLM/格式判断混入）
- 子模块的 SRP 是否干净
- OCP：通过新增扩展而非修改现有
- LSP：Parser 输出能否替代 Phase4Output 的 code-side 部分
- 红线：不得 import Phase 4 内部函数

@agent plan-verifiability-checker
检查可验证性。重点关注：
- 验收标准是否可测试？
- bypass 验证策略是否可执行？
- 测试覆盖是否充分？

@agent plan-surgical-precision-checker
检查手术精度。重点关注：
- 禁止修改的 21 个文件是否防护到位？
- 是否有暗示的 adjacent 改动风险？
- 是否可能偷偷改到 Phase 4 的代码？

@agent plan-review-synthesis
汇总三位 reviewer 的发现，做事实核查和上下文矛盾检测。
使用 Write() 工具写报告到 `outputs/plan_review_report.md`，禁止 inline editor。
