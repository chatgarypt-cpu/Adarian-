@skill karpathy-coding

use a workflow to: 通过 5 agent team 并发审查今日重构后的 Adarian MVP 系统架构，确认各层职责清晰、依赖方向正确、无死模块、无断链。

## 背景

今日（2026-06-07）做了三项重大重构：
1. **观测层收口** — 白盒 JSON 全部合入 run.log，whitebox/ 目录移除
2. **Phase 4 dataset-only** — Phase 4 所有函数改为只依赖 simulation_dataset.json，去除外部参数
3. **架构分层** — 分析层从 phase3/ 拆出独立的 src/analysis/，parser 从 phase3/ 提到 src/parser.py

## 审查目标

target_path: src/
target_files:
  - src/phase3/tick_simulation.py
  - src/phase3/__init__.py
  - src/analysis/risk_analyzer.py
  - src/analysis/inflection_detector.py
  - src/analysis/stance_analyzer.py
  - src/analysis/__init__.py
  - src/parser.py
  - src/phase4/report_narrative.py
  - src/phase4/report_agent.py
  - src/phase4/paths.py
  - src/whitebox/__init__.py
  - src/whitebox/run_meta.py
  - src/whitebox/token_tracker.py
  - src/display/__init__.py
  - src/display/run_log_writer.py
  - src/llm_client.py
  - src/utils/runtime_logger.py
  - main.py
  - tests/midPhaseTest.py
  - spec/dataset_fields.yaml

辅助参考:
  - docs/iterations/active/v1.3.2_risk_type_classification_expansion.md

forbidden:
  - docs/archive/

## Reviewer 分工（并发执行）

### Agent 1 — Code Reality Mapper

真实代码结构反向建模：

1. 逐文件读 target_files 列出的代码（不读没列出的）
2. 列出实际存在的类、函数
3. 说明每个类/函数当前负责什么
4. 找出真实调用链（import 链、函数调用链）
5. 注意以下层之间的依赖方向是否正确：
   - phase3/ → analysis/（正确：phase3 不依赖 analysis）
   - analysis/ → phase3/（正确：analysis 不依赖 phase3，只读 schemas）
   - parser.py → analysis/（正确：parser 调分析器）
   - parser.py → phase4/（正确：parser 不依赖 phase4）
   - phase4/ → 仅 dataset（正确：phase4 不依赖 phase3/analysis 类型）

输出文件：outputs/agent1_inventory.md

### Agent 2 — Responsibility Boundary Reviewer

职责边界检查：

1. 检查每个模块是否只负责一个变化原因（SRP）
2. 重点关注：
   - src/whitebox/ 各文件职责是否重叠（token_tracker / run_meta / dataset_spec_writer）
   - src/display/run_log_writer.py 是否真的只做"追加摘要"
   - src/parser.py 是否只做"编排聚合"
   - src/utils/runtime_logger.py 是否只做"运行时日志"
3. 标记职责粘稠点

输出文件：outputs/agent2_boundary.md

### Agent 3 — Runtime Flow Mapper

运行时流程检查：

1. 从 main.py 入口到 final_report 产出的完整端到端流程
2. 确认 dataset 流向：Phase3 → parser → dataset.json → Phase4
3. 确认 run.log 产生流程：RuntimeLogger 边跑边记 → append_run_summary 跑后追加
4. 确认异常捕获流程：sys.excepthook → run.log / threading.excepthook → run.log
5. 标记断链或数据不一致

输出文件：outputs/agent3_flow.md

### Agent 4 — Dependency & Import Checker

依赖关系检查：

1. 对 target_files 所有文件做全量 import 检查
2. 确认不存在循环依赖
3. 确认不存在 import 已删除的模块（如旧的 report_observer / artifact_check / build_full_report_context）
4. 确认 phase4/ 不导入 phase3/ 或 analysis/ 的任何模块（只读 schemas）
5. 确认 analysis/ 不导入 phase3/ 的任何模块（只读 schemas）

输出文件：outputs/agent4_deps.md

### Agent 5 — Mermaid Synthesizer

基于 Agent 1-4 的产出：

1. 文件依赖图
2. 模块职责图（含今日重构前后的对比）
3. 运行时流程图
4. 收敛所有发现到一份报告中

输出文件：outputs/code_reality_mapping_review.md

## 5a. 输出质量协议

最终报告必须：
- Verdict: PASS / PASS_WITH_FINDINGS / REPAIRABLE_HOLD / BLOCKING_HOLD / FAIL
- Known Issues / 风险与问题
- Blockers / Repairable Issues
- 最小改进建议
- 质量门禁：行号残留、单词断裂、表格断裂 → 降级为 REPAIRABLE_HOLD

## 完成条件

所有 5 个 output 文件生成，其中 Agent 5 的汇总报告包含 Verdict 和 Known Issues。
