# Pre-Execution Plan Review — v1.3.1 Phase4 Streamlining 方案审查

> 审查模式：agent-team（4 reviewer + 1 synthesis）
> 审查目标：`docs/iterations/active/v1.3.1_phase4_streamlining_and_entrypoint_unification.md`
> 参考现状：`src/phase4/report_agent.py`（1309行，当前混合体）

---

@skill pre-execution-plan-review

## 审查目标

审查迭代计划 `docs/iterations/active/v1.3.1_phase4_streamlining_and_entrypoint_unification.md` 的质量。

### 项目背景

这是一个"剥离+归档"版本：
- **v1.3.0** 已完成 Phase3 分析能力抽离（risk_analyzer, inflection_detector, stance_analyzer, parser），bypass 对比通过
- **v1.3.0.1** 已修复新路径 wiring
- **v1.3.1** 的目标是清理残留：让 Phase4 成为纯消费端，移除旧计算函数，归一入口

### 关键上下文

1. Phase4 report_agent.py 当前 1309 行，混合了旧内联计算函数（assess_risk, identify_inflection_points, determine_audience_mode 等）和新消费函数（save_report, parse_llm_report_response with dataset, _build_code_owned_contract_block with dataset 等）
2. Phase3 已有等价模块：RiskAnalyzer, InflectionDetector, StanceAnalyzer, SimulationDatasetParser
3. 方案将旧计算函数移入 legacy/ 目录，Phase4 只保留消费功能
4. main_new.py → main.py，旧 main.py → legacy/main_legacy.py
5. bypass 对比从 main.py 运行时移除，保留为 dev 诊断工具

### 分 agent 任务

@agent plan-scope-checker
检查范围完整性和边界。重点关注：
- 方案是否遗漏了需要清理的旧函数/import？
- src/phase4/report_agent.py 中是否有应该移入 legacy 但未被方案的函数？
- 不做的内容（§2.4 禁止变化）是否与实际可能发生的范围膨胀相符？
- 输入：迭代计划文档 + 读 report_agent.py 的 def/class 清单做交叉验证

@agent plan-design-smell-detector
检查设计气味和架构正确性。重点关注：
- SRP：Phase4 从"半计算半消费"变为"纯消费"——这个 SRP 落地是否彻底？有没有残留的计算函数方案说保留但实际仍有计算？
- OCP：通过新增 consumer 而非修改 Phase3 来扩展——新架构是否符合？
- _build_phase4_output_from_simulation_dataset() 是"字段映射"还是"隐式计算"？读代码确认
- 方案声称保留的 markdown 段落构建函数（_scale_description 等）——它们是纯格式化还是隐式计算？读代码判断
- legacy/ 目录的引用不会被旧 import 链意外触发吧？
- 红线：Phase4 新代码不得 import legacy 目录

@agent plan-verifiability-checker
检查可验证性和完成条件。重点关注：
- 方案说"final_report.json 中 risk_level 来自 simulation_dataset"——如何验证这个 claim？
- 编译检查是必要的，但不够——有没有办法写一个快速脚本验证 Phase4 运行时没有调用任何旧函数？
- 验证标准（§2.7）是否可操作？
- bypass 从 main.py 移除后，有没有可能遗漏回归？

@agent plan-surgical-precision-checker
检查手术精度和文件级影响分析。重点关注：
- 1309 行→250 行的裁剪，有没有牵一发动全身的 import 风险？
- tools/bypass_compare_phase3.py 的 import 改到 legacy——确定 legacy/phase4/__init__.py 的导出符号完全覆盖旧 report_agent 的导出？
- main.py 被替换后，其他引用 main.py 的脚本/文档/CI 是否需要更新？
- 方案说"不修改"的文件中，有没有间接被影响的？

@agent plan-review-synthesis
汇总四位 reviewer 的发现，做事实核查和上下文矛盾检测。
使用 Write() 工具写报告到 `outputs/plan_review_report.md`，禁止 inline editor。

写入后读回文件，检查：无行号残留、无单词断裂、无表格错位。
