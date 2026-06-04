# Adarian 当前工作流映射报告

> 报告生成日期：2026-05-15  
> 报告作者：工作流分析 Agent（Agent C）  
> 分析范围：v1.1.0 ~ v1.2.9 全量迭代记录 + 当前工作流规范 + Skill 定义 + 产品侧协议  
> 权威源依据：`docs/skills/workflow_core.md` v3.0（2026-05-06 生效）

---

## 一、工作流全景概览

Adarian 当前采用 **文档驱动、审计优先、最小落地** 的开发模式，核心原则为"慢审计，快落地"。项目将开发生命周期划分为五个阶段：**exploration → audit → execution → validation → closeout**，由四类角色分工协作。

**标准 Pipeline**（`workflow_core.md` 第 3 节）：

```
User/Owner → Control Agent → DS Pre-Audit → Scope Freeze → Codex Attempt → DS Verify → DS Accept → Control Agent/User Closeout
```

实际执行中并非每个版本都走完整流程。对于 documentation-only 版本（如 v1.2.0、v1.2.3）或 hotfix（如 v1.2.1.1），DS Pre-Audit 可跳过；对于涉及源码结构调整的版本（如 v1.2.5、v1.2.6、v1.2.7、v1.2.9），DS Pre-Audit 是强制环节。

---

## 二、各节点详细映射

### 2.1 User / Owner

**执行者**：Gary（项目 Owner）

**渠道**：Claude Code 对话界面

**实际做什么**：
- 提出版本需求与方向判断（从 TASK_LOG 可见，自 v1.1.x 时期起，Gary 通过 Claude Code 直接向 Agent 提出迭代任务）
- 审核 Control Agent（同样运行在 Claude Code 中的 Agent）产出的迭代文档
- 对高风险断点做 Owner-approved 决策（如 v1.2.8.1.1 中 "Owner-approved infra hotfix" 的并发 run_dir 修复）
- 最终批准 closeout，决定是否进入下一版本

**当前特点**：Gary 同时兼任 User、Owner 和实际上的 Control Agent 审批人三重角色。严格来说，User/Owner 和 Control Agent 在物理上是同一个 Claude Code 会话中的不同 prompt 人格，而非两个独立实体或系统。

---

### 2.2 Control Agent

**执行者**：理论上由 Claude Code 中扮演 Control Agent 人格的 Agent 执行，实际上就是 Gary 通过 Claude Code 手动操作

**渠道**：Claude Code

**实际做什么**（依据 `workflow_core.md` 第 6 节及迭代文档模板）：
1. **判断当前阶段**：exploration / audit / execution / validation / closeout
2. **编写正式迭代文档**：使用 `_template_v3.md` 模板，填写 12 个标准章节（Version Info、Control Agent Decision、Goal & Boundary、Audit Summary、Target Structure、File Change Scope、Execution Attempts、Verification Plan、Acceptance Target、Execution Report Requirement、Closeout Record、Notes）
3. **冻结版本边界**：声明 allowed files、forbidden files、non-goals
4. **决定是否需要 DS Pre-Audit**：涉及源码结构调整、schema 调整、main.py 链路调整等 7 类变更时必须触发
5. **采纳/不采纳 DS 建议**：在迭代文档 §4.1 中显式标注
6. **向 Codex 提供完整执行 Prompt**：即 iteration document 本身
7. **基于 DS Accept 与实际产物做最终 closeout**

**Control Agent 的 Gate 判断是人工判断**：每次版本迭代，Gary 需要手动判断本版本处于哪个阶段，手动填写迭代文档的 Gate 字段（GO/CONDITIONAL_GO/HOLD/FAIL），并给出决策理由。v1.2.9 中 Gate 为 CONDITIONAL_GO，理由是 DS 审计确认报告 agent 过胖但前置审计必须先完成。

**关键约束**（`workflow_core.md` 第 6 节）：
- 不得把最终 Gate 判断交给 DS
- 不得把迭代文档写作责任交给 Codex
- 不得在探索期过早 Execution Lock
- 未 closeout 当前版本不得开启下一版本
- 不得把 review findings 自动升级为下一版本任务

**输入**：User/Owner 需求 + 上一版本 closeout 状态 + 当前源码状态

**输出**：正式迭代文档（`docs/iterations/vX.Y.Z-<topic>.md`），包含 task_id、Gate、范围声明、执行指令、验收标准

---

### 2.3 DS Agent Team（三阶段审计）

DS Team 是 Adarian 工作流中最具结构化的节点。它分为三个独立阶段，每个阶段由不同的 Skill 文件定义，通过 Claude Code 中的 Agent 人格执行。

#### 2.3.1 /ds-pre-audit — 前置结构审查

**Skill 文件**：`docs/skills/ds_pre_audit.md`

**触发时机**：Control Agent 完成初版迭代文档，Gate 为 GO 或 CONDITIONAL_GO，且涉及源码结构/schema/main.py/phase package/whitebox/R1-R3/影响下游 Phase 的变更。

**输入**：
- 当前迭代文档（draft/under_review）
- 当前源码树（`src/` 下所有 `.py` 文件）
- `docs/dev_spec.md`
- `docs/iterations/TASK_LOG.md` 和 `CHANGELOG.md`
- 相关上一版本验收记录

**执行步骤**（`ds_pre_audit.md` 第 35-44 行）：
1. 读取迭代文档，提取目标结构、允许/禁止修改列表
2. 扫描 `src/` 下所有 `.py` 文件，建立文件清单
3. 追踪 `main.py` 的 import 链路，区分主链/legacy/独立工具
4. 搜索 whitebox 相关关键词，定位分散的观测逻辑
5. 检查 forbid 声明的文件是否确实存在且不应触碰
6. 评估循环 import 风险、shim 策略可行性
7. 输出结构化 DS Pre-Audit Report

**输出**：DS Pre-Audit Report，必须包含：audit_id、verdict（GO/CONDITIONAL_GO/HOLD/FAIL）、source tree facts、main chain dependency facts、allowed files check、forbidden files check、risk list、blockers、recommended execution scope、DS must not do。

**存放路径**：`audit/phase1大版本审计/vX.Y.Z-{topic}-{YYYY-MM-DD}.md` 或 `audit/workflow/` 或 `audit/general/`

**实际执行证据**：
- `audit/phase4大版本改造/DS_Agent_Team_Pre_Audit_Report_v1.2.9_2026-05-15.md`
- `audit/phase4大版本改造/DS_Agent_Team_Pre_Audit_Report_v1.2.8.1_2026-05-15.md`
- `audit/v1.2.6-ds-agent-team-review-2026-05-07.md`

#### 2.3.2 /ds-verify — 后置验证

**Skill 文件**：`docs/skills/ds_verify.md`

**触发时机**：Codex 完成一次 attempt 交付后。

**输入**：
- Codex 交付说明
- attempt_id
- 当前 iteration document
- 当前 git status
- 当前 diff
- 当前 run_dir（如已运行）

**验证步骤（五阶段，含 Phase 0 environment preflight）**：

| 阶段 | 内容 | 命令示例 |
|------|------|---------|
| Phase 0 | Environment Preflight | `.venv/bin/python --version` + pydantic check |
| Phase 1 | 静态检查 | `py_compile main.py` + `compileall src` |
| Phase 2 | Forbidden Files 检查 | `git diff --name-only <base_commit_or_HEAD>` 对照 §6.3 |
| Phase 3 | Import 完整性检查 | `from src.phase1 import ...` 等 |
| Phase 4 | Smoke Test | `.venv/bin/python main.py seeds/test1.txt` |
| Phase 5 | Artifact Contract 检查 | 核验 run_dir 下 9 个必备产物 |

**输出**：DS Verify Report，包含 attempt_id、base_commit、modified files、forbidden files result、py_compile result、import result、smoke result、artifact result、overall_verify_result（all_pass/partial_fail/hard_fail）、environment_preflight、failure_type。

**关键规则**：
- 发现 forbidden files 被修改时，立即 hard_fail，不得包装为 pass_with_known_issues
- 无法确认 diff 基准时标记 partial_fail/hold 并要求 Control Agent 判断
- Hook 不能替代 DS Verify

**实际执行证据**：
- `audit/phase4大版本改造/v1.2.7-attempt-01-ds-verify-2026-05-11.md`
- `audit/phase4大版本改造/v1.2.7-attempt-02-ds-verify-2026-05-11.md`

#### 2.3.3 /ds-accept — 验收判定

**Skill 文件**：`docs/skills/ds_accept.md`

**触发时机**：`/ds-verify` 完成后。

**输入**：
- DS Verify Report
- 当前 iteration document
- Hard Acceptance Target
- Soft Acceptance Target
- Codex attempt report
- DS Pre-Audit Report（如存在）

**验收逻辑**：
- 任一 Hard Target 不满足 → fail/hold
- 所有 Hard Target 满足，部分 Soft Target 不满足 → pass_with_known_issues
- Hard/Soft Target 全部满足 → pass

**输出**：Acceptance Report 最小字段：task_id、audit_id、attempt_id、acceptance_id、acceptance_result（pass/pass_with_known_issues/fail/hold）、hard_targets X/Y、soft_targets X/Y、carry_over、closeout_recommendation（allow_closeout/hold/require_fix）。

**可更新**：DS Accept 可以更新 TASK_LOG.md、CHANGELOG.md、当前 iteration doc 的 acceptance section。

**DS Accept 不得越权**：
- 不得直接把 iteration doc 状态改为 closed
- 不得宣布允许进入下一版本
- 不得替 Control Agent/User 做最终 Gate
- 不得新增下一版本范围
- 不得把 soft issue 自动升级为 blocker

**实际执行证据**：
- `audit/phase4大版本改造/DS_Agent_Team_Verify_Accept_Report_v1.2.9_2026-05-15.md`
- `audit/phase4大版本改造/DS_Agent_Team_Verify_Accept_Report_v1.2.8.1_2026-05-15.md`
- TASK_LOG 中每个版本的 acceptance record 明确标注了 acceptance_result

---

### 2.4 Codex 节点

**执行者**：Claude Code 中以 Codex 人格运行的 Agent

**执行方式**：
1. 读取 iteration document（由 Control Agent 编写）
2. 执行 `iteration_execution_guard.md` 中的脏树检查（区分 SOURCE_DIRTY_BLOCKER 与 DOC_DIRTY_ALLOWED）
3. 等待 User/Control Agent 确认
4. 在允许文件范围内执行代码修改
5. 运行自检级测试（py_compile、pytest、smoke test）
6. 回传 attempt report

**交付物**：attempt report，必须包含（`main_agent_delivery.md` 第 112-127 行）：
- task_id、audit_id/N/A、attempt_id
- actual_added_files、actual_modified_files、actual_deleted_files
- forbidden_files_touched: yes/no
- test_commands、test_results
- latest_run_dir/N/A
- artifact_check
- git diff --name-only output
- known_issues

**关键约束**：
- 只修改允许文件，不触碰 forbidden files
- 不自行扩大版本范围
- 不自行修改 TASK_LOG/CHANGELOG（除非 iteration doc 明确要求）
- 不自行 closeout
- 不自检级测试仅确认"交付具备进入 DS Verify 的最低条件"，验收级测试归 DS Verify
- attempt 默认串行执行（attempt-02 依赖 attempt-01 通过）

**实际执行证据**（从 TASK_LOG 可见）：
- v1.2.9：3 个 attempt（attempt-01、attempt-02、attempt-closeout），Codex 实际新增 5 个文件、修改 5 个文件，83 passed tests + test8 smoke
- v1.2.7：3 个 attempt（attempt-01、attempt-02、attempt-closeout-patch），16 targeted tests 全部通过
- v1.2.6：2 个 attempt（attempt-01、attempt-02），Codex 实际新增 8 个文件、删除 1 个文件、修改 3 个文件

---

### 2.5 产品侧

**当前是否有产品侧角色**：**是，但处于探索阶段。**

**证据**：
1. `audit/product_side_structured_delivery_protocol_v0.1_revised.md`（2026-05-13）：定义了产品侧结构化交付协议，核心原则是"一次性问题不走协议；可复用交付才走协议"。协议处于 draft/exploration 状态。
2. `audit/技术任务卡_风险类型信号映射与风险-对策映射表_v0.2.md`：产品侧向技术侧发出的结构化交付任务卡，属于 L-Level（将沉淀为长期参照规则）任务，主类型为 E 规则归纳型。
3. `audit/productside_review/` 目录：包含 `政府治理视角舆情风险分层与等级映射清单_v0.2.md`（5 个一级风险域、20 个二级风险类型，每类 12 个字段）和 `change_point_detection.py`（产品侧尝试的技术实现片段）。
4. `docs/product_inputs/optimized_inflection_point_definition_and_calculation_v0.1.md`：产品侧对模拟关键变化点定义和计算口径的输入。

**任务卡片传递方式**：产品侧通过 Markdown 任务卡（如 `技术任务卡_风险类型信号映射与风险-对策映射表_v0.2.md`）传递需求。任务卡包含任务背景、输入材料清单、任务等级/类型、交付物清单。目前传递渠道是文件系统（`audit/` 目录），尚未接入 git workflow。

**当前问题**：
- 产品侧与技术侧之间的对接仍不成熟：产品侧产出风险清单 v0.2，但技术侧 `select_primary_risk_types()` 仍依赖 keyword matching，未接入产品侧的风险分层体系
- 产品侧结构化交付协议仍为 draft，未正式生效
- 产品侧交付物存放路径不统一（`audit/productside_review/`、`docs/product_inputs/`、`audit/` 根目录）

---

### 2.6 Owner Gate（最终审批门）

**当前实现方式**：**完全手动，由 Gary 人工判断。**

Gate 机制在 workflow 中有两层：

**第一层：Control Agent Gate**（迭代文档 §2）
- 位于 Control Agent 决策中：GO / CONDITIONAL_GO / HOLD / FAIL
- 由 Gary（作为 Control Agent）在编写迭代文档时手动填写
- 需要给出决策理由（如 v1.2.9 的决策理由是 "DS 审计确认 report_agent.py 已约 1675 行，文件过胖"）

**第二层：Closeout Gate**（`workflow_core.md` 第 17 节）
- 版本 closeout 必须满足 6 个条件：DS Accept 已完成、Hard Acceptance Target 全部满足、TASK_LOG 已记录 acceptance_result、CHANGELOG 已记录版本变更、run_dir/artifact 证据完整、Control Agent/User 明确批准 closeout
- **最终 closeout 由 Control Agent/User 确认**
- 允许结果：closed/pass、closed/pass_with_known_issues、hold、fail

**是否自动化**：**否。** 没有任何自动化 Gate 判断。每次版本推进都需要 Gary 手动判断。Even DS Accept 的 closeout_recommendation 只是建议性质，不能替代 Owner 的最终审批。

**当前瓶颈**：Gary 是唯一的 Gatekeeper。当多个版本交错进行时（例如 v1.2.8.1 和 v1.2.8.1.1 在 closeout 时 v1.2.9 已开始执行），Gate 判断完全依赖 Gary 对全局状态的认知。

---

### 2.7 迭代文档生命周期

迭代文档是 Adarian 工作流的核心载体。生命周期如下：

```
draft → under_review → execution → closeout（最终状态改为 "closed"）
                       ↑                 ↑
                   (Control Agent)   (Control Agent / User)
```

**1. draft 阶段**：
- Control Agent（Gary）使用 `_template_v3.md` 模板创建迭代文档
- 文档按 `vX.Y.Z-<topic>.md` 命名，存放于 `docs/iterations/`
- 填写 Version Info、Control Agent Decision（含 Gate）、Goal & Boundary 等前 3 章

**2. under_review 阶段**：
- 如果本版本需要 DS Pre-Audit，文档提交给 DS Team 审查
- DS Pre-Audit 输出审计报告，Control Agent 在迭代文档 §4.1 中标注采纳/不采纳
- 如果不需要 DS Pre-Audit，直接进入 Scope Freeze

**3. execution 阶段**：
- Codex 读取 iteration document 执行
- 状态通常从 "under_review" 变为 "executing"
- 每个 attempt 完成后 Codex 回传 attempt report
- 如果 attempt 失败，可能需要 Control Agent 调整迭代文档后重新尝试

**4. closeout 阶段**：
- DS Accept 完成后，iteration doc 的 acceptance section 被更新
- Control Agent/User 确认后，状态改为 "closed"
- TASK_LOG 和 CHANGELOG 同步更新

**当前实例状态统计**（截至 v1.2.9）：
- closed：v1.2.0 ~ v1.2.8.1（约 15 个版本）
- pending DS verify：v1.2.8.1.1、v1.2.9

---

### 2.8 TASK_LOG / CHANGELOG

**TASK_LOG.md**（`docs/iterations/TASK_LOG.md`，约 2000 行）：
- **记录内容**：task_id、audit_id、attempt_id、acceptance_id、acceptance_result、carry_over、实际新增/修改/删除文件、测试结果、最新 run_dir
- **更新时机**：
  - Codex 完成 attempt 后在 TASK_LOG 中记录执行日志（如 v1.2.9 中 Codex 在 attempt_delivered 后追加记录）
  - DS Accept 完成后写入 acceptance record
  - Control Agent/User closeout 后更新最终状态
- **更新权限**：`workflow_core.md` 第 16.3 节规定 "DS Accept 可以写入 acceptance record"，Codex 也被允许在交付后写入执行记录（在 TASK_LOG 实际记录中可见大量 Codex 写入的条目）

**CHANGELOG.md**（`docs/iterations/CHANGELOG.md`，约 1500 行）：
- **记录内容**：版本主题、新增、修改、修复、兼容性、验收结果、已知遗留
- **更新时机**：每个版本 closeout 前更新
- **更新权限**：DS Accept 可以更新，Control Agent/User closeout 后最终确认

**实际观察**：Codex 也在写入 TASK_LOG 和 CHANGELOG。例如 v1.2.9 的 TASK_LOG 条目由 Codex 在 attempt 交付时写入，v1.2.7 的 CHANGELOG 条目也包含 Codex 写入的验收详情。这与 `workflow_core.md` 第 11 节 "Codex 不得自行修改 TASK_LOG/CHANGELOG，除非 iteration doc 明确要求" 存在一定张力 -- 实际上 iteration doc 通过声明 "Execution Report Requirement" 隐式授权了这些写入。

---

### 2.9 Closeout 机制

**负责人**：Control Agent / User（Gary）

**需要什么证据**（`workflow_core.md` 第 17 节）：
1. DS Accept 已完成
2. Hard Acceptance Target 全部满足
3. TASK_LOG 已记录 acceptance_result
4. CHANGELOG 已记录版本变更
5. run_dir/artifact 证据完整
6. Control Agent/User 明确批准 closeout

**实际 closeout 操作**（从 TASK_LOG 观察）：
1. DS Accept 完成后，acceptance_result 写入 TASK_LOG
2. Control Agent 在迭代文档 §11 Closeout Record 中填写最终结果
3. 状态改为 "closed"
4. 如果是 pass_with_known_issues，必须列出 carry_over、risk_level、next_version_candidate、是否阻塞下一版本

**未 closeout 的版本不得开启下一版本**（防漂移规则第 5 条）。但在实际执行中，存在灰色地带：例如 v1.2.8.1 刚 closeout，v1.2.8.1.1 和 v1.2.9 几乎同时开始执行。

---

### 2.10 Artifact / Evidence

**当前 Artifact 分类**：

| 类别 | 内容 | 存放路径 | 可追溯性 |
|------|------|---------|---------|
| 运行产物 | run_meta.json, run.log, timing_summary.json, entities_and_relations.json, social_graph.json, tick_logs.json, final_report.json, final_report.md, whitebox_summary.json | `outputs/runs/<run_id>/` | 按时间戳可追溯 |
| 白盒产物 | report_completeness.json, artifact_check.json | `outputs/runs/<run_id>/whitebox/` | 同 run_id 关联 |
| DS 审计报告 | Pre-Audit Report, Verify Report, Accept Report | `audit/phase4大版本改造/` 或 `audit/phase1大版本审计/` | 文件名含版本号和日期 |
| 迭代文档 | 正式迭代文档 | `docs/iterations/vX.Y.Z-<topic>.md` | 版本号索引 |
| 任务日志 | TASK_LOG.md, CHANGELOG.md | `docs/iterations/` | 按日期倒序 |
| 产品侧输入 | 风险分层清单、任务卡 | `audit/productside_review/`、`docs/product_inputs/` | 路径不统一 |
| Profiling 产物 | model_profiles.json, profile_summary.md, raw_logs | `profiling/output/` | profiling 独立目录 |

**可追溯性评估**：
- 运行产物通过 `run_id`（格式：`<seed_stem>_<YYYYMMDD_HHMMSS>`）或 `run_{microseconds}_{pid}` 可唯一追溯
- DS 审计报告通过 audit_id 关联到 task_id
- 版本间通过 CHANGELOG 和 carry_over 形成链路
- **缺失**：产品侧输入目前没有统一的 artifact ID 体系，无法稳定引用

---

### 2.11 Prompt 编写

**谁写 prompt**：
1. **业务 LLM Prompt**（如 Phase 1 Analyzer/Generator/Validator、Phase 3 Agent 发言、Phase 4 报告生成）：由 Codex 在 Control Agent 指定的范围内编写或修改。例如 `src/phase4/report_prompts.py` 中的 `FIVE_CHAPTER_HEADINGS`、`REPORT_SYSTEM_PROMPT` 等由 Codex 在 v1.2.7 中新增。
2. **迭代执行 Prompt**（即 iteration document 本身）：由 Control Agent（Gary）直接撰写。这是给 Codex 的执行指令。
3. **DS Team Prompt**：由 Skill 文件定义（`ds_pre_audit.md`、`ds_verify.md`、`ds_accept.md`），这些文件是 Control Agent/User 编写的规范。
4. **产品侧 Prompt**：产品侧提供的是"应该生成什么"的定义（如风险分层清单），而非技术 prompt。技术侧（Codex 或 Control Agent）负责转译为具体 prompt。

**如何确保一致性**：
- 通过 iteration doc 的禁止变化清单（§3.4）明确声明 "不改 schema 语义"、"不改 prompt 语义" 等，防止 Codex 擅自修改核心 prompt
- DS Pre-Audit 审查 iteration doc 中的 prompt 范围声明
- DS Verify 通过 forbidden files check 和 artifact contract check 验证 prompt 未被非法修改
- `report_prompts.py` 作为纯数据文件（AST 验证为无函数/类/导入/调用），但实际包含大量 prompt 常量

---

### 2.12 回执解析

**DS Team 如何解析 Codex 的交付**：
- DS Verify 阶段通过人工运行命令 + 人工读取输出来解析。这**不是自动化**过程。
- Codex 交付后，DS Team（同样是 Claude Code 中的 Agent 人格）读取 attempt report，然后逐阶段执行验证命令（py_compile、pytest、git diff、smoke test），将结果与 iteration doc 的 Hard/Soft Target 对照。
- 验证过程仍有自动化空间：Phase 1-5 的验证命令是可脚本化的，但目前依赖 DS Agent 逐一执行并解读结果。

**DS Accept 阶段**：DS Team 对照 Hard/Soft Acceptance Target 做人工判定。例如 v1.2.8.1 的 DS Accept 判定 acceptance_result 为 pass_with_known_issues，因为所有 Hard Target 满足但有 7 个 known issues 属于 Soft Target 范围。

---

### 2.13 下一步判断

**谁决定进入下一版本**：Control Agent / User（Gary）

**依据是什么**：
1. **DS Accept 的 closeout_recommendation**：推荐 allow_closeout / hold / require_fix
2. **carry_over 清单**：当前版本的已知遗留是否阻塞下一版本
3. **大版本路线图**：Phase 1 Generation Governance Major Track 规划（`audit/phase1大版本审计/Phase 1 Generation Governance Major Track 整体规划 v0.2.md`）定义了 v1.2.3 ~ v1.2.11 的版本路线
4. **当前产品侧需求**：如 v1.2.8.x 系列由产品侧对报告叙述质量的需求驱动
5. **DS 审计结论**：是否存在 hard blocker

**实际决策模式**：Gary 综合上述信息做人工判断。从版本演进路径看，v1.2.4→v1.2.5→v1.2.6→v1.2.7→v1.2.8→v1.2.9 的主线大体遵循了大版本路线图，但也根据产品侧需求插入了 v1.2.8.x 系列（报告叙述质量）。

---

## 三、节点映射分析表

| 节点类型 | 执行者 | 输入 | 输出 | 当前痛点 | 可中台化程度 |
|---------|-------|------|------|---------|------------|
| **User/Owner 需求输入** | Gary 人工 | 产品侧输入 + 运行结果 | 版本方向判断 | 需求分散在 audit/ 各个角落 | 低 -- 需要人的判断 |
| **Control Agent 版本决策** | Gary（通过 Claude Code） | 上一版本状态 + 路线图 | 迭代文档（含 Gate 判断） | Gary 是唯一决策者，无冗余 | 中 -- 版本状态可自动化追踪，Gate 建议可辅助生成，但最终决策需人工 |
| **DS Pre-Audit** | Claude Code DS Agent | 迭代文档 + 源码 | Pre-Audit Report | DS Agent 间审查质量一致性，对大型代码库的扫描深度 | 高 -- 源码扫描、import 链路、forbidden files 检查均可脚本化；verdict 建议可半自动 |
| **DS Verify** | Claude Code DS Agent | Codex attempt report + 源码 | Verify Report | 五阶段验证几乎全人工执行，耗时；无法并行验证多个 attempt | 高 -- 所有 6 个阶段（含 Phase 0）均可自动化脚本执行；结果解析需少量人工 |
| **DS Accept** | Claude Code DS Agent | Verify Report + Hard/Soft Targets | Accept Report | 对照 Hard/Soft Target 的判定依赖人工理解 | 中 -- Hard Target 检查可自动化（布尔判断），Soft Target 需人工 |
| **Codex 执行** | Claude Code Codex Agent | 迭代文档 | attempt report + 代码变更 | scope creep 风险（Codex 偶尔会修改 forbidden files 或越界设计）；dirty tree 阻塞 | 低 -- 代码实现天然需要人的监督 |
| **Codex 自检** | Claude Code Codex Agent | 代码变更 | test results | 自检命令不统一，依赖 iteration doc 声明 | 高 -- 可标准化为 pre-commit hook + CI 流水线 |
| **Iteration Doc 编写** | Gary（Control Agent） | 路线图 + 需求 | 迭代文档 | 文档写作耗时，模板部分章节重复填写 | 中 -- 模板可更自动化，但 Goal/Boundary 等需人工判断 |
| **TASK_LOG 更新** | Codex + DS Accept | 执行/验收结果 | 日志条目 | 多人写入格式不完全统一（Codex 写的条目 vs DS 写的条目） | 高 -- 可标准化为结构化表单写入 |
| **CHANGELOG 更新** | DS Accept + Control Agent | 版本变更 | 变更记录 | 格式半结构化（Markdown 表格 + 代码块混用） | 高 -- 可由版本 diff 自动生成初稿 |
| **Closeout Gate** | Gary 人工 | DS Accept + Artifacts + TASK_LOG | closeout 状态 | 完全依赖 Gary 判断，无自动化检查清单 | 中 -- 6 个条件中至少 4 个可自动化检查 |
| **产品侧输入** | 产品侧人员 | 业务需求 | 任务卡/风险清单 | 尚未建立稳定通道，产出物路径不统一，版本管理混乱 | 低 -- 需求定义天然需要人 |
| **产品侧→技术侧转译** | Gary（Owner） | 产品侧任务卡 | 迭代文档中的技术目标 | Gary 是唯一转译者，成为瓶颈 | 低 -- 需要理解两端语义 |
| **Prompt 编写/修改** | Codex（在 Control Agent 约束下） | 迭代文档中的 prompt 范围 | 业务 prompt 常量 | 多个 version 修改同一 prompt 文件，回滚困难 | 中 -- prompt 版本管理和 diff 可工具化 |
| **环境预检** | DS Verify Phase 0 | venv 状态 | environment_preflight report | 网络/认证/模型不可用频繁阻塞，浪费验证时间 | 高 -- 可完全自动化，作为 CI 前置步骤 |
| **并行 attempt 判断** | Control Agent | iteration doc 条件 | 并行许可 | 条件复杂（5 个条件），实际极少使用 | 中 -- 条件检查可自动化，但许可需人工 |

---

## 四、Gary 人工承担的关键节点

以下节点在当前工作流中完全或主要依赖 Gary 人工操作：

| 节点 | 承担程度 | 详细说明 |
|------|---------|---------|
| **Control Agent 全部职责** | 100% 人工 | Gate 判断、版本定位、迭代文档编写、采纳/不采纳 DS 建议、向 Codex 提供执行 Prompt、最终 Closeout -- 全部由 Gary 执行 |
| **Owner Gate / Closeout** | 100% 人工 | 最终审批完全依赖 Gary |
| **产品侧→技术侧转译** | 100% 人工 | 产品侧任务卡（如风险-对策映射表）需要 Gary 转译为技术侧迭代文档 |
| **工作流规范维护** | 100% 人工 | workflow_core.md、CLAUDE.md、Skill 文件的编写和维护 |
| **DS Team 调度** | 间接人工 | DS Team 虽然由 Claude Code Agent 执行，但需要 Gary 显式触发 `/ds-pre-audit`、`/ds-verify`、`/ds-accept` |
| **并行 attempt 许可** | 100% 人工 | 决定是否允许并行 attempt 需要 Gary 批准 |

---

## 五、可中台化节点

以下节点具有较高的自动化/半自动化潜力：

### 5.1 高可中台化（可完全自动化）
1. **DS Verify 执行**：6 个验证阶段（环境预检、静态检查、forbidden files、import 完整性、smoke test、artifact contract）均为确定性命令，可通过 CI pipeline 或 Hook 自动执行
2. **环境预检**：venv 状态、模型可用性、endpoint 可达性检查可前置为每次 attempt 的自动步骤
3. **Codex 自检**：py_compile、pytest、smoke 可标准化为 CI Step
4. **TASK_LOG 格式**：可由工具从 attempt report 自动生成结构化条目
5. **CHANGELOG**：可由 git diff 摘要 + 版本范围声明自动生成初稿

### 5.2 中可中台化（可半自动化，需人工审核）
1. **DS Pre-Audit**：源码文件清单、import 链路追踪、forbidden files 对照可自动化；但风险评估和 verdict 建议需人工
2. **DS Accept**：Hard Target 对照可自动化（布尔检查）；Soft Target 评估需人工
3. **Closeout Gate**：6 个条件中的 5 个可自动检查（DS Accept 状态、Hard Target 状态、TASK_LOG 记录、CHANGELOG 记录、artifact 完整性）；第 6 个（Control Agent 批准）需人工
4. **Iteration Doc 生成**：模板填充可自动化，但 Goal/Boundary、Gate 理由需人工

### 5.3 难以中台化（依赖人的判断）
1. **User/Owner 需求定义**：业务方向判断
2. **产品侧输入**：风险分层、对策体系的设计
3. **Codex 执行监督**：架构质量的最终判断
4. **产品侧→技术侧转译**：需要理解两端语义

---

## 六、当前工作流瓶颈

### 瓶颈 1：Gary 是单点瓶颈（贯穿全流程）
Gary 同时承担 User、Owner、Control Agent、产技转译者、DS Team 调度者、Closeout 审批者六个角色。所有版本的推进速度取决于 Gary 的处理带宽。当多版本交错推进时（如 v1.2.8.1 closeout 同时 v1.2.8.1.1 和 v1.2.9 并行开发），Gary 需要同时维护多个版本的状态认知。

**缓解方案**：将 DS Verify 的结果判定和 Hard Target 布尔检查自动化，减轻 Gary 的审查负担。建立版本状态仪表盘。

### 瓶颈 2：DS Verify 全人工操作（耗时最长）
DS Verify 五个阶段（不含 Phase 0）涉及多条命令的逐一执行和结果解读。一个版本的完整 DS Verify 可能涉及 10+ 次命令执行和多份报告的输出对比。v1.2.7 的 DS Verify 产生了 5 份独立报告（attempt-01 verify、attempt-02 verify、prompt quality review、test8 smoke、smoke rerun）。

**缓解方案**：将 DS Verify 的 5 个阶段整合为一个自动化脚本，输出结构化 JSON report，DS Agent 只需审核异常项。

### 瓶颈 3：产品侧与技术侧对接不稳定
产品侧有产出（风险分层清单 v0.2、任务卡等），但技术侧尚未完全接入。典型的例子是 `select_primary_risk_types()` 仍使用 keyword matching，而非产品侧定义的结构化信号。产品侧交付物路径不统一，版本管理无标准。

**缓解方案**：建立产品侧交付物的统一存放路径和版本号体系，建立产品侧 artifact 到技术侧迭代文档的引用链路。

### 瓶颈 4：环境不稳定消耗验证时间
从 TASK_LOG 可见，APIConnectionError、模型不可用、venv 依赖缺失等问题频繁出现（v1.2.4、v1.2.8.1.1 等版本均报告了此类问题）。DS Verify 中 Phase 0 环境预检虽然已经规范化，但环境问题仍导致完整的验证流程被阻塞。

**缓解方案**：将环境预检提升为每次 attempt 执行前的自动前置步骤，环境异常时不得进入 Codex 执行。

### 瓶颈 5：迭代文档写作耗时
完整的迭代文档（使用 _template_v3.md）需要填写 12 个章节，约 80% 的内容是结构性声明（Goal/Boundary、File Change Scope、Verification Plan 等）。目前的模板已经很完善，但仍需要人工逐项填写。

**缓解方案**：通过工具从上一版本迭代文档和当前 diff 自动生成初始迭代文档模板，Gary 只需修改决策性字段。

---

## 七、Workflow Event ID 体系追踪

当前 workflow v3 定义了四类事件 ID，实际执行情况如下：

| Event ID | 定义规范 | 实际执行情况 |
|----------|---------|------------|
| task_id | task-vX.Y.Z-\<topic\> | 所有迭代文档均已声明，格式一致 |
| audit_id | audit-vX.Y.Z-01 | DS Pre-Audit Report 已包含，但部分早期版本使用 review_id 替代（v1.2.5 及之前） |
| attempt_id | attempt-vX.Y.Z-01/02/... | Codex 交付说明中已声明，但部分版本 attempt_id 命名不统一（如 v1.2.8 的 "v1.2.8-five-chapter-markdown-fallback-patch"） |
| acceptance_id | accept-vX.Y.Z-01 | DS Accept Report 和 TASK_LOG 中已包含 |

**实际差距**：v1.2.5 之前（v1.1.x 系列）使用 review_id 替代 audit_id，存在历史遗留。v1.2.6 之后已全面对齐四类 ID。

---

## 八、总结

Adarian 当前工作流的核心特征是：**高度结构化、文档驱动、人工 Gate**。四角色分工（User/Owner、Control Agent、DS Team、Codex）在规范层面清晰，但在物理实现上全部运行在 Claude Code 的 Agent 人格中，Gary 通过 prompt 切换角色。

**最值得优先中台化的三项**：
1. **DS Verify 全流程自动化脚本**：将 6 个阶段整合为单一命令，输出结构化 JSON
2. **环境预检前置为 Codex 执行门控**：避免环境问题浪费版本迭代时间
3. **版本状态仪表盘**：让 Gary 能一眼看到所有版本的当前状态、阻塞项和 carry_over

**当前不推荐中台化的**：
- Control Agent 的 Gate 判断和最终 Closeout：需要人的业务理解
- 产品侧需求定义：天然需要人的判断
- Codex 执行的质量监督：代码架构判断需要人的审查
