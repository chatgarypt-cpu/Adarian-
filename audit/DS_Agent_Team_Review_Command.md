# DS Agent Team Review Command
# Task: Review audit documents against real code / artifacts evidence

你现在作为 DS Agent Team 主控，对 audit 目录下的三份规划 / 迭代文档进行审查。

## 0. Hard Requirement

team_mode_used 必须为 true。

你必须启动 DS Agent Team / 多 reviewer 并行审查，而不是单 agent 审查。

最低 reviewer 配置：

1. Reviewer A：源码一致性审查
   - 负责从真实代码出发，检查文档中的模块、函数、文件路径、职责边界是否与当前仓库一致。

2. Reviewer B：运行产物 / artifact 审查
   - 负责检查 outputs / run artifacts / whitebox / final_report / tick_logs 等真实产物是否支持文档判断。

3. Reviewer C：版本边界 / workflow 审查
   - 负责检查版本排期、scope freeze、禁止项、是否存在越界或跨阶段塞功能。

4. Reviewer D：Phase 1 Generation Governance 审查
   - 负责检查 LLM draft format、Parser / Compiler / Validator、ValidationReport、Repair Loop、Diff Guard 的规划是否合理，是否与当前 Phase 1 代码状态一致。

5. Reviewer E：Phase 4 Report Governance 审查
   - 负责检查 v1.2.8.1、报告可信度、风险等级、指标解释、拐点 / 模拟关键变化点、final_report / whitebox 相关规划是否与当前 Phase 4 代码和产物一致。

如果无法开启 team mode，请立即停止并报告：
team_mode_used=false
reason=...
不要伪装为多 reviewer 审查。

## 1. MCP / Repo Access Requirement

必须开启 MCP / 文件系统工具 / 代码检索能力，对真实仓库进行审查。

本次审查不能只看 audit 文档文字，必须从以下真实证据出发：

1. 代码证据
   - src/
   - src/phase1/
   - src/phase2/
   - src/phase3/
   - src/phase4/
   - src/whitebox/
   - main.py
   - tests/

2. 文档证据
   - audit/ 下的三份待审文档
   - docs/iterations/
   - docs/contracts/
   - docs/dev_spec.md
   - TASK_LOG.md
   - CHANGELOG.md

3. 运行产物证据
   - outputs/runs/ 下最近一次或最近几次 run_dir
   - final_report.md
   - final_report.json
   - tick_logs.json
   - whitebox_summary.json
   - whitebox/ 下的 detail artifacts
   - run_meta.json
   - timing_summary.json

如果某些路径不存在，必须如实记录，不得猜测。

## 2. Review Target

请审查 audit 目录下的三份文档。

重点应包括但不限于：

1. v1.2.8.1 Risk Assessment Directionality & Metric Explanation Patch
2. Adarian long-term architecture plan v0.3 / Phase 1 Draft Format revised
3. 另一个 audit 目录中的相关规划 / 产品侧文档 / 远期规划文档

请先列出你实际发现的三份文档路径与文件名。

如果 audit 目录下多于三份文档，请按最近修改时间和文件名判断目标文档，并说明选择依据。
如果少于三份，请停止并报告 missing documents。

## 3. Core Review Questions

请围绕以下问题审查。

### 3.1 文档是否与真实代码一致？

检查：

1. 文档中提到的文件是否真实存在。
2. 文档中提到的函数是否真实存在。
3. 文档中提到的产物是否真实存在。
4. 文档中对当前能力的描述是否夸大。
5. 文档中是否把 future hook 写成 current capability。
6. 文档中是否存在已经过时的路径、模块名或旧架构假设。

必须重点检查：

```text
src/phase4/report_agent.py
src/phase4/report_prompts.py
src/whitebox/
src/phase1/
src/schemas/
main.py
tests/
outputs/runs/<latest_run>/
```

### 3.2 v1.2.8.1 是否越界？

重点判断：

1. 是否仍然保持为 Phase 4 risk / metric explanation patch。
2. 是否越界进入完整 change point framework。
3. 是否越界进入微博数据接入 / situational_snapshot / input_arbitration。
4. 是否越界进入 Phase 1 Repair Loop。
5. 是否越界修改 schema 或 Phase 1-3。
6. external_risk_adjustment 是否已经被降级为 future hook。
7. prior_floor 是否有 risk_type 白名单边界。
8. max_negative_shift 缺失时是否采用 graceful degrade，而不是 hard fail 主链。
9. 产品侧 v0.3 是否只作为术语和 carry-over，而非本轮实现依据。

### 3.3 Phase 1 Draft Format 规划是否合理？

重点判断：

1. "JSON runtime authority + YAML/Markdown LLM-facing draft format"是否合理。
2. 是否避免了 JSON → YAML 全系统迁移。
3. 是否保持 EntityExtractionOutput canonical object 地位。
4. Parser / Compiler / Validator / ValidationReport / Targeted Repair Loop / Diff Guard 的顺序是否合理。
5. 是否存在 Repair Loop 早于 ValidationReport / pre_repair_snapshot / rollback 的风险。
6. 是否需要先做 P/C/V reality check。
7. 是否与当前 Phase 1 真实代码结构一致。
8. 是否有过度设计或阶段过细问题。

### 3.4 长期架构规划是否越界？

重点判断：

1. 动态态势感知是否被正确后移。
2. 微博数据能力审计是否没有抢跑。
3. situational_snapshot 是否仍是 contract / fixture 方向，而不是立即主链实现。
4. Input Arbitration 是否作为 future contract，而不是当前强依赖。
5. Parallel Run / Batch Synthesis 是否还停留在 contract 层。
6. 是否存在把产品端任务自动升级为工程实现的风险。
7. 是否存在 MCP / Web Search / 外部检索重新混入的风险。

### 3.5 版本排期是否合理？

请基于真实代码状态判断以下排期是否合理：

```text
v1.2.8.1
拐点识别可信度修复

v1.2.8.2
单轮 / 多轮 / 最终报告通用产物契约

v1.2.9.0
Phase 1 P/C/V Reality Check

v1.2.9.1
LLM Draft Format Policy

v1.2.9.2
Parser / Compiler / Validator Skeleton R0

v1.2.9.3
ValidationReport Contract

v1.2.9.4
Targeted Repair Loop R0

v1.2.9.5
Diff Guard & Fallback R0

v1.2.10
微博数据能力审计 + situational_snapshot 契约
```

请指出：

1. 哪些版本可以 GO。
2. 哪些版本应 CONDITIONAL_GO。
3. 哪些版本必须 HOLD。
4. 哪些版本应该合并、拆分或后移。
5. 是否存在未 closeout 就开启下一版本的风险。

## 4. Evidence Rules

每个 reviewer 的结论必须包含 evidence。

证据格式必须包含：

```text
evidence_type: code / artifact / doc / missing
path:
line_or_function_or_artifact:
finding:
impact:
```

禁止只写：

```text
看起来合理
建议优化
可能存在问题
```

必须说明证据来自哪里。

如果证据不足，请写：

```text
evidence_type: missing
path: ...
finding: cannot verify
impact: ...
```

## 5. Output Format

最终输出必须按以下结构：

```markdown
# DS Agent Team Review Report

## 0. Team Mode Confirmation

team_mode_used: true / false
reviewer_count:
reviewers:
- Reviewer A:
- Reviewer B:
- Reviewer C:
- Reviewer D:
- Reviewer E:

If team_mode_used=false, stop here.

## 1. Reviewed Documents

| File | Role | Found? | Notes |
|---|---|---|---|

## 2. Evidence Sources Checked

### Code Paths
| Path | Exists? | Notes |
|---|---|---|

### Artifact Paths
| Path | Exists? | Notes |
|---|---|---|

### Documentation Paths
| Path | Exists? | Notes |
|---|---|---|

## 3. Reviewer Findings

### Reviewer A — Code Consistency

| Finding ID | Severity | Evidence Type | Path | Finding | Impact | Recommendation |
|---|---|---|---|---|---|---|

### Reviewer B — Artifact Consistency

| Finding ID | Severity | Evidence Type | Path | Finding | Impact | Recommendation |
|---|---|---|---|---|---|---|

### Reviewer C — Version Boundary / Workflow

| Finding ID | Severity | Evidence Type | Path | Finding | Impact | Recommendation |
|---|---|---|---|---|---|---|

### Reviewer D — Phase 1 Generation Governance

| Finding ID | Severity | Evidence Type | Path | Finding | Impact | Recommendation |
|---|---|---|---|---|---|---|

### Reviewer E — Phase 4 Report Governance

| Finding ID | Severity | Evidence Type | Path | Finding | Impact | Recommendation |
|---|---|---|---|---|---|---|

## 4. Cross-reviewer Conflict Resolution

| Conflict | Reviewers | Resolution |
|---|---|---|

## 5. Gate Recommendation

Choose one:

- GO
- CONDITIONAL_GO
- HOLD
- FAIL

Final DS verdict:

```text
...
```

## 6. Required Patches Before Codex

Only list patches that are required before execution.

| Patch ID | Target Document | Required Change | Reason |
| -------- | --------------- | --------------- | ------ |

## 7. Non-blocking Suggestions

| Suggestion | Reason | Should become version scope? yes/no |
| ---------- | ------ | ----------------------------------- |

## 8. Final Next Action

Give exactly one recommended next action.

Allowed examples:

```text
Patch audit documents, then re-review.
Freeze v1.2.8.1 scope and generate Codex prompt.
Hold Phase 1 Repair Loop until P/C/V reality check.
Proceed with DS-reviewed v0.3 roadmap as planning baseline.
```

```

## 6. Severity Definition

Use these severities:

```text
BLOCKER:
必须修，否则不能执行。

HIGH:
强烈建议修，否则执行容易漂移或失败。

MEDIUM:
应记录，可能作为 patch 或 known issue。

LOW:
不阻塞，可作为后续优化。

INFO:
事实记录。
```

## 7. Important Constraints

1. 不要替 Control Agent 做最终 gate。
2. 不要把所有建议自动升级为 blocker。
3. 不要给 Codex 写执行 prompt。
4. 不要修改文件。
5. 不要重写规划文档。
6. 不要自行新增版本。
7. 不要把动态态势感知提前为当前实现任务。
8. 不要要求现在接 MCP / Web Search / RAG。
9. 不要把 YAML 作为 runtime authority。
10. 不要建议 JSON 全系统迁移。
11. 不要把产品端任务升级为工程任务。
12. 不要让 Repair Loop 早于 ValidationReport / pre_repair_snapshot / rollback policy。
13. 不要把单轮 run_report.md 误判为 final_report.md。

## 8. Final Reminder

本次审查的核心不是判断"规划是否好看"，而是判断：

```text
规划是否被真实代码和真实产物支持；
版本边界是否可执行；
是否存在隐藏越界；
是否能进入下一步 scope freeze。
```

请从证据出发，给出可复盘的 DS Agent Team verdict。
