# DS Team 工作流治理路径摸底报告

## 1. 扫描摘要

- **扫描时间**: 2026-05-18 15:30-16:00 CST
- **task_id**: workflow-governance-path-inventory-r0
- **review_id**: audit-path-inventory-2026-05-18-01
- **文件总数**: 72（去重后唯一文件路径）
- **MCP 使用情况**: 已使用 mcp__filesystem__directory_tree, mcp__filesystem__get_file_info, mcp__filesystem__read_text_file, mcp__filesystem__search_files
- **Agent Team 使用情况**: 已启用 — Reviewer A (Categories 2/3/6/8/12) + Reviewer B (Categories 4/5/9/10/11/13) + Lead Reviewer (Categories 1/7 + 合成)
- **扫描方法**: 仅只读审计，未修改任何文件

---

## 2. 路径清单

### 2.1 Category 1 — workflow_core.md

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| docs/skills/workflow_core.md | true | tracked | constitution | 唯一流程规则权威源 v3.0，2026-05-06 ratified | 规范版本，含全部 21 节，使用 .venv/bin/python |
| docs/workflow_core.md | true | tracked | historical | workflow_core.md 的旧分支版本 | **内容不同**：使用裸 python3 替代 .venv/bin/python，缺少 §11.1（Dirty Tree Gate Granularity）、§12（Internal Model Endpoint Preflight Rule）、§13（Project Python Interpreter Rule）。章节编号也不一致（§12-21 vs §14-19）。建议标记为过时。 |

**结论**：存在 2 个 workflow_core.md 副本，根目录 `docs/workflow_core.md` 为旧分支版本，与权威版本内容不一致。

### 2.2 Category 2 — Workflow Authority 文件

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| docs/skills/workflow_core.md | true | tracked | constitution | 唯一流程规则权威源 | 已在 Cat 1 列出 |
| docs/workflow_core.md | true | tracked | historical | 旧版 workflow authority（已过时） | 与权威版内容不一致 |
| CLAUDE.md | true | tracked | agent_instruction | 项目指令，第3行声明 workflow_core.md 为唯一权威源 | 含 Workflow Authority Notice |
| docs/skills/iteration_execution_guard.md | true | tracked | skill | Codex 执行门禁策略 | 引用 workflow_core.md 为权威源 |
| docs/skills/main_agent_delivery.md | true | tracked | skill | Codex 角色边界定义 | 引用 workflow_core.md 为权威源 |
| docs/dev_workflow.md | true | tracked | workflow_guide | 开发工作流指南 | 辅助性文档，引用 dev_spec.md |
| docs/workflow_changelog.md | true | tracked | log | 工作流迭代变更日志 | 自 v1.1 (2026-03-26) 起 |
| docs/audit/workflow/workflow_governance_refactor_acceptance_package.md | true | tracked | audit | 工作流治理重构验收包 | 状态 partial_done |

### 2.3 Category 3 — docs/skills/ 全部文件

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| docs/skills/workflow_core.md | true | tracked | constitution | 核心工作流权威 | 25KB，v3.0 |
| docs/skills/iteration_execution_guard.md | true | tracked | skill | Codex 迭代执行安全门禁 | 6.8KB |
| docs/skills/main_agent_delivery.md | true | tracked | skill | Codex 交付行为规范 | 4.7KB |
| docs/skills/ds_pre_audit.md | true | tracked | skill | DS 前置审计 | 2.0KB |
| docs/skills/ds_verify.md | true | tracked | skill | DS 五阶段交付验证 | 5.0KB |
| docs/skills/ds_accept.md | true | tracked | skill | DS 正式验收判定 | 2.6KB |

**总计**：6 个 skill 文件（排除 .DS_Store），全部为工作流相关，全部 tracked。

### 2.4 Category 4 — DS Team 审计 / 审查文件

**docs/skills/ 中的 DS 技能文件（已在 Cat 3 列出）：**
- docs/skills/ds_pre_audit.md
- docs/skills/ds_verify.md
- docs/skills/ds_accept.md

**.claude/SKILLS.md**

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| .claude/SKILLS.md | true | tracked | agent_instruction | DS Team 技能索引，列出 ds-pre-audit/ds-verify/ds-accept 及已退役技能 | 交叉引用 docs/skills/*.md |

**audit/phase4大版本改造/ 中的 DS 审计报告（21+ 文件）：**

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| audit/phase4大版本改造/DS_Agent_Team_Pre_Audit_Report_v1.2.8.1_2026-05-15.md | true | tracked | audit | v1.2.8.1 Phase 4 DS 前置审计报告 | |
| audit/phase4大版本改造/DS_Agent_Team_Pre_Audit_Report_v1.2.9_2026-05-15.md | true | tracked | audit | v1.2.9 Phase 4 DS 前置审计报告 | |
| audit/phase4大版本改造/DS_Agent_Team_Session_Full_Audit_Export_v1.2.8.1_2026-05-15.md | true | tracked | audit | v1.2.8.1 全量审计导出 | |
| audit/phase4大版本改造/DS_Agent_Team_Verify_Accept_Report_v1.2.8.1_2026-05-15.md | true | tracked | audit | v1.2.8.1 DS 验证+验收报告 | |
| audit/phase4大版本改造/DS_Agent_Team_Verify_Accept_Report_v1.2.9_2026-05-15.md | true | tracked | audit | v1.2.9 DS 验证+验收报告 | |
| audit/phase4大版本改造/DS_Agent_Team_Dependency_Hygiene_Audit_v1.2.9_2026-05-15.md | true | tracked | audit | v1.2.9 依赖卫生审计 | |
| audit/phase4大版本改造/v1.2.6-ds-agent-team-review-2026-05-07.md | true | tracked | audit | v1.2.6 DS Agent Team 审查 | |
| audit/phase4大版本改造/v1.2.6-ds-audit-receipt-recovery-2026-05-11.md | true | tracked | audit | v1.2.6 R3 receipt recovery | |
| audit/phase4大版本改造/v1.2.7-attempt-01-ds-verify-2026-05-11.md | true | tracked | audit | v1.2.7 attempt 1 DS 验证 | |
| audit/phase4大版本改造/v1.2.7-attempt-02-ds-verify-2026-05-11.md | true | tracked | audit | v1.2.7 attempt 2 DS 验证 | |
| audit/phase4大版本改造/v1.2.7-phase4-report-product-governance-sprint-ds-review-2026-05-11.md | true | tracked | audit | v1.2.7 Phase 4 产品治理审查 | |
| audit/phase4大版本改造/v1.2.7-prompt-quality-review-2026-05-11.md | true | tracked | audit | v1.2.7 prompt 质量审查 | |
| audit/phase4大版本改造/v1.2.7-test8-smoke-test-ds-report-2026-05-11.md | true | tracked | audit | v1.2.7 test8 smoke 报告 | |
| audit/phase4大版本改造/v1.2.7-test8-smoke-rerun-after-risk-contract-patch-2026-05-11.md | true | tracked | audit | v1.2.7 risk contract patch 后重跑 | |
| audit/phase4大版本改造/v1.2.8-iteration-readiness-ds-review-2026-05-12.md | true | tracked | audit | v1.2.8 迭代就绪审查 | |
| audit/phase4大版本改造/v1.2.8-iteration-readiness-ds-review1-2026-05-12.md | true | tracked | audit | v1.2.8 迭代就绪审查 v2 | |
| audit/phase4大版本改造/v1.2.8-metric-system-technical-audit-2026-05-13.md | true | tracked | audit | v1.2.8 指标系统技术审计 | |
| audit/phase4大版本改造/v1.2.8.x-inflection-point-definition-and-calculation-report-2026-05-15.md | true | tracked | audit | 拐点定义与计算报告 | |
| audit/phase4大版本改造/Phase4_Roadmap_DS_AgentTeam_Review_2026-05-11.md | true | tracked | audit | Phase 4 roadmap DS 审查 | |

**audit/phase1大版本审计/ 中的 DS 审计文件：**

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| audit/phase1大版本审计/DS_AgentTeam_审计_大版本总体规划v0.1_2026-05-01.md | true | tracked | audit | Phase 1 大版本总体规划审计 | |
| audit/phase1大版本审计/Phase 1 Generation Governance Major Track 整体规划 v0.2.md | true | tracked | audit | Phase 1 生成治理总体规划 | |
| audit/phase1大版本审计/ds-workflow-v3-proposal-2026-05-06.md | true | tracked | audit | DS workflow v3 建议书 | |
| audit/phase1大版本审计/v1.2.4-closeout-audit-2026-05-06.md | true | tracked | audit | v1.2.4 closeout 审计 | |
| audit/phase1大版本审计/v1.2.5.2-acceptance-note-2026-05-07.md | true | tracked | audit | v1.2.5.2 验收说明 | |

**其他 DS 审计文件：**

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| audit/DS_Agent_Team_Review_Report_2026-05-14.md | true | untracked | audit | DS Agent Team 5-reviewer 并行审查报告 v1.2.8 | |
| audit/repo_hygiene_closeout_2026-05-01.md | true | tracked | audit | 仓库卫生 closeout 记录 | |
| docs/iterations/v1.2.5-attempt-01-ds-acceptance-review.md | true | tracked | audit | v1.2.5 attempt 1 DS 验收审查 | |
| docs/iterations/v1.2.5-attempt-02-ds-acceptance-review.md | true | tracked | audit | v1.2.5 attempt 2 DS 验收审查 | |
| docs/audit/workflow/workflow_audit_report_review.md | true | tracked | audit | 工作流审计报告审查 | |
| docs/audit/workflow/workflow_governance_refactor_acceptance_package.md | true | tracked | audit | 工作流治理重构验收包 | |
| audit/hermes_tasks/workflow-governance-path-inventory-control-r0/ds_audit.md | true | untracked | audit | control group 路径摸底审计报告（已有） | 独立 control-review-agent 产出，88+ 条目 |
| audit/hermes_tasks/workflow-governance-path-inventory-control-r0/ds_receipt.yaml | true | untracked | protocol | control group 结构化 receipt | |

### 2.5 Category 5 — Codex 执行 / 交接 / 回执文件

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| docs/skills/iteration_execution_guard.md | true | tracked | skill | Codex 迭代执行安全门禁 | 嵌入 Codex 执行协议 |
| docs/skills/main_agent_delivery.md | true | tracked | skill | Codex 交付行为规范 | 定义 Codex 角色边界和交付协议 |
| docs/_archive/history_used/2026-04-08_phase1_prompt_benchmark_handoff.md | true | tracked | historical | Phase 1 prompt benchmark 交接文档 | 唯一的独立 handoff 文件 |
| audit/hermes_tasks/hermes-agent-call-capability-check-r0/mock_receipt.json | true | untracked | protocol | Hermes mock receipt（首次 relay 测试） | |
| audit/hermes_tasks/hermes-agent-call-capability-check-r0/mock_receipt_raw.json | true | untracked | protocol | Hermes raw mock receipt（max_turns=1 错误） | |
| audit/hermes_tasks/hermes-agent-call-capability-check-r0/mock_upgrade_receipt.json | true | untracked | protocol | Hermes upgrade mock receipt（Read tools 测试） | |

**说明**：无独立的 Codex 执行模板文件或回执模板文件。Codex 协议嵌入在 `iteration_execution_guard.md` 和 `main_agent_delivery.md` 中。mock receipt 文件仅存在于 Hermes 能力检查目录下（全部 untracked）。

### 2.6 Category 6 — 迭代文档模板

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| docs/iterations/_template.md | true | tracked | template | v1 迭代模板 | emoji 风格标题，字段：版本信息、修复目标、文件变更列表 |
| docs/iterations/_template_v2.md | true | tracked | template | v2 迭代模板 | 增加 task_id、workflow event IDs、acceptance targets（hard/soft）、forbidden files |
| docs/iterations/_template_v3.md | true | tracked | template | v3 迭代模板（当前） | 正式编号章节，含 Control Agent Decision gate（GO/CONDITIONAL_GO/HOLD/FAIL）、attempt_id 追踪、结构化 closeout 标准 |

**说明**：三个模板版本清晰递增，无重叠混淆。全部 tracked。

### 2.7 Category 7 — TASK_LOG / CHANGELOG

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| docs/iterations/TASK_LOG.md | true | tracked | log | 任务执行日志，时间倒序 | 最新条目：2026-05-15 v1.2.9 Phase 4 Report Agent Decoupling R0 Closeout |
| docs/iterations/CHANGELOG.md | true | tracked | log | 版本变更日志 | 最新条目：v1.2.9 (2026-05-15) Closeout |

**说明**：两份文件均活跃维护，tracked，内容一致且最新。TASK_LOG.md 引用 `BENCHMARK_LOG.md`（该文件不存在，见 Cat 13）。

### 2.8 Category 8 — Hook 配置 / Hook 策略文件

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| .claude/settings.json | true | tracked | hook | Claude Code 项目级 Hook 配置 | 仅含 PreCommit hooks：Python 语法检查（py_compile + compileall）+ 禁止文件提醒（echo 方式，非强制拦截） |
| .claude/settings.local.json | true | untracked | hook | 本地权限 allowlist | 含 Read/Bash/mcp__filesystem__* 权限配置。无 hook 定义 |

**说明**：无独立的 hook 策略文档（hook*.md）。settings.json 中的 PreCommit 禁止文件检查为 echo 提醒，非强制性阻塞。无 PostCommit、PreRequest 或其他 hooks。.

### 2.9 Category 9 — Hermes / Relay / Dispatch 文件

**audit/hermes_tasks/ 完整目录结构：**

**子任务 1：hermes-agent-call-capability-check-r0/**

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| audit/hermes_tasks/hermes-agent-call-capability-check-r0/capability_report.md | true | untracked | audit | Hermes Agent 调用能力检查报告 | 评估 Hermes 调度 Claude Code 子代理的能力 |
| audit/hermes_tasks/hermes-agent-call-capability-check-r0/mock_receipt.json | true | untracked | protocol | 首次 relay 测试 receipt | claude -p piped-data 执行 receipt |
| audit/hermes_tasks/hermes-agent-call-capability-check-r0/mock_receipt_raw.json | true | untracked | protocol | raw mock receipt（max_turns=1 错误） | |
| audit/hermes_tasks/hermes-agent-call-capability-check-r0/mock_upgrade_receipt.json | true | untracked | protocol | upgrade mock receipt（Read tools 测试通过） | 证明通过 settings.local.json allowlist 可解锁 Read tool |
| audit/hermes_tasks/hermes-agent-call-capability-check-r0/mock_upgrade_result.md | true | untracked | protocol | upgrade mock relay 测试结果报告 | |
| audit/hermes_tasks/hermes-agent-call-capability-check-r0/mock_relay_result.md | true | untracked | protocol | mock relay 测试结果报告 | PASS，2 turns，$0.185 |

**子任务 2：workflow-governance-path-inventory-control-r0/**

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| audit/hermes_tasks/workflow-governance-path-inventory-control-r0/ds_audit.md | true | untracked | audit | control group 独立审计报告 | 88+ 条目 |
| audit/hermes_tasks/workflow-governance-path-inventory-control-r0/ds_receipt.yaml | true | untracked | protocol | control group 结构化 receipt | |

**子任务 3：workflow-governance-path-inventory-r0/**（当前任务目录）

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| audit/hermes_tasks/workflow-governance-path-inventory-r0/ds_dispatch.md | true | untracked | protocol | Hermes-PM 任务调度书 | 定义 13 类扫描范围 |
| audit/hermes_tasks/workflow-governance-path-inventory-r0/ds_system_prompt.md | true | untracked | protocol | DS Team 系统约束 | 只读、MCP 强制、子代理强制 |
| audit/hermes_tasks/workflow-governance-path-inventory-r0/relay_runner.py | true | untracked | protocol | Python 子进程 relay 运行器 | 心跳/进度监控 |
| audit/hermes_tasks/workflow-governance-path-inventory-r0/relay_progress.md | true | untracked | protocol | relay 进度日志 | stage=init |
| audit/hermes_tasks/workflow-governance-path-inventory-r0/relay_heartbeat.txt | true | untracked | protocol | relay 心跳时间戳 | stage=claude_running, 90s |
| audit/hermes_tasks/workflow-governance-path-inventory-r0/subprocess_relay_result.json | true | untracked | protocol | 子进程 relay 结果（超时） | timeout 280s |
| audit/hermes_tasks/workflow-governance-path-inventory-r0/subprocess_relay_summary.md | true | untracked | protocol | 子进程 relay 执行摘要+失败分析 | 诊断：TIMEOUT_CONFIG_INSUFFICIENT |
| audit/hermes_tasks/workflow-governance-path-inventory-r0/ds_raw_result.json | true | untracked | protocol | DS raw result（空/1行） | 终端 dispatch 失败残留 |

**关键发现**：全部 17 个 Hermes/Relay/Dispatch 文件均为 untracked（未纳入 git）。文件记录了从 capability-check → mock-relay-test → upgrade-relay-test → path-inventory-dispatch 的递进过程。path-inventory-r0 子进程 relay 在 280s 超时。

此项目外未发现 `~/.hermes/skills/adarian/` 目录。

### 2.10 Category 10 — Product-side 协议文件

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| audit/product_side_structured_delivery_protocol_v0.1_revised.md | true | tracked | protocol | 产品侧结构化交付协议 v0.1 revised | 835 行，定义 M-Level/L-Level 任务类型、交付阶段、DS Team 规则、验收矩阵 |
| audit/productside_review/change_point_detection.py | true | untracked | unknown | 变化点检测 Python 脚本 | 产品侧分析工具 |
| audit/productside_review/技术任务卡_风险类型信号映射与风险-对策映射表_v0.2.md | true | untracked | protocol | 风险类型信号映射与风险-对策映射表 v0.2 | |
| audit/productside_review/政府治理视角舆情风险分层与等级映射清单_v0.2.md | true | untracked | protocol | 政府治理视角舆情风险分层与等级映射清单 v0.2 | |
| audit/phase4大版本改造/Adarian_Report_Product_Contract_PRD_v0.1.md | true | tracked | protocol | Adarian 报告产品合同 PRD v0.1 | |
| audit/phase4大版本改造/Adarian_模拟关键变化点_产品解释规则与计算口径建议_v0.3.md | true | tracked | protocol | 产品解释规则与计算口径建议 v0.3 | |
| docs/contracts/phase1-output-contract-freeze-v1.2.3.md | true | tracked | protocol | Phase 1 输出合同冻结 | 产品侧协议 |

### 2.11 Category 11 — Closeout / Acceptance / Handoff 模板

**无独立的 closeout/acceptance/handoff 模板文件。这些结构嵌入在迭代模板中：**

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| docs/iterations/_template_v3.md | true | tracked | template | 含结构化 closeout 标准 | §Closeout 段包含 closeout_status/decision/blocks_next_version |
| docs/iterations/_template_v2.md | true | tracked | template | 含 acceptance targets | hard/soft acceptance targets |

**实际 closeout/acceptance 实例：**

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| audit/repo_hygiene_closeout_2026-05-01.md | true | tracked | audit | 仓库卫生 closeout 记录 | |
| audit/phase1大版本审计/v1.2.4-closeout-audit-2026-05-06.md | true | tracked | audit | v1.2.4 closeout 审计 | |
| audit/phase4大版本改造/v1.2.7-closeout-record-patch-2026-05-12.md | true | tracked | audit | v1.2.7 closeout record patch | PASS verdict |
| audit/phase1大版本审计/v1.2.5.2-acceptance-note-2026-05-07.md | true | tracked | audit | v1.2.5.2 验收说明 | |
| docs/iterations/v1.2.5-attempt-01-ds-acceptance-review.md | true | tracked | audit | v1.2.5 attempt 1 DS 验收审查 | |
| docs/iterations/v1.2.5-attempt-02-ds-acceptance-review.md | true | tracked | audit | v1.2.5 attempt 2 DS 验收审查 | |
| docs/audit/workflow/workflow_governance_refactor_acceptance_package.md | true | tracked | audit | 工作流治理重构验收包 | partial_done |
| docs/_archive/history_used/2026-04-08_phase1_prompt_benchmark_handoff.md | true | tracked | historical | Phase 1 prompt benchmark 交接文档 | 唯一的独立 handoff 文件 |

### 2.12 Category 12 — Agent Instruction 文件

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| CLAUDE.md | true | tracked | agent_instruction | 根级 agent 指令 | 含 Workflow Authority Notice、实现指南、Python 环境规则、pre-flight 检查、代码验证规则 |
| .claude/SKILLS.md | true | tracked | agent_instruction | DS Team 技能注册表 | 列出 ds-pre-audit/ds-verify/ds-accept 及已退役技能 |
| docs/skills/main_agent_delivery.md | true | tracked | skill | Codex 特定 agent 指令 | Codex 角色边界、交付协议 |
| docs/skills/iteration_execution_guard.md | true | tracked | skill | Codex 执行门禁指令 | 连接 v3 工作流与 Codex global skill |

**缺失项：**

| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|
| AGENTS.md | false | — | agent_instruction | — | 不存在 |
| .codex/ | false | — | agent_instruction | — | 目录不存在 |
| CODERULES.md | false | — | agent_instruction | — | 不存在 |
| *.mdc 文件 | false | — | agent_instruction | — | 不存在 |

**说明**：Agent 指令分散在 CLAUDE.md、.claude/SKILLS.md 和 docs/skills/ 文件中。无外部 agent 指令框架（AGENTS.md、.codex/）。

### 2.13 Category 13 — 缺失引用文件

以下路径被权威文档引用，但磁盘上不存在：

| referenced_path | referenced_by | exists | notes |
|-----------------|---------------|--------|-------|
| audit/workflow/ | docs/skills/workflow_core.md §8.3 (line 317) | false | workflow_core.md 建议将非 Phase 1 审计报告存放到此路径，但目录不存在 |
| audit/general/ | docs/skills/workflow_core.md §8.3 (line 318) | false | 同上，目录不存在 |
| docs/iterations/BENCHMARK_LOG.md | docs/iterations/TASK_LOG.md (自 v1.1.13 起多处引用) | false | TASK_LOG 声明 benchmark/稳定性测试/回归测试/AQF 评分已迁移至 BENCHMARK_LOG.md，但该文件从未创建 |

**已交叉验证**：`test -f` 和 `test -d` 命令确认三者均不存在。

**workflow_core.md 中其他路径引用（已验证存在）：**
- `docs/dev_spec.md` — 存在
- `docs/iterations/TASK_LOG.md` — 存在
- `docs/iterations/CHANGELOG.md` — 存在
- `.claude/settings.json` — 存在
- `.venv/bin/python` — 存在
- `main.py` — 存在
- `config.py` — 存在

---

## 3. 缺失引用文件

| # | 引用路径 | 引用来源 | 影响 |
|---|---------|---------|------|
| 1 | audit/workflow/ | workflow_core.md §8.3 | workflow 类审计报告无建议存储路径 |
| 2 | audit/general/ | workflow_core.md §8.3 | general 类审计报告无建议存储路径 |
| 3 | docs/iterations/BENCHMARK_LOG.md | TASK_LOG.md | benchmark 指标无集中记录 |

---

## 4. 审查元数据

- **review_id**: audit-path-inventory-2026-05-18-01
- **task_id**: workflow-governance-path-inventory-r0
- **team_mode_used**: true（Reviewer A + Reviewer B + Lead Reviewer）
- **mcp_used**: true（mcp__filesystem__directory_tree、mcp__filesystem__get_file_info、mcp__filesystem__read_text_file、mcp__filesystem__search_files）
- **verdict**: PATH_INVENTORY_COMPLETE
- **report_path**: audit/hermes_tasks/workflow-governance-path-inventory-r0/ds_audit.md
- **workflow_core_path**: docs/skills/workflow_core.md（权威版本）
- **assets_found_count**: 72
- **missing_referenced_files**: 3
- **total_constitution_files**: 3（workflow_core.md 权威版 + 旧分支版 + workflow_core.md 自身含 CLAUDE.md 委托）
- **total_skill_files**: 7（6 个 docs/skills/ + audit/phase4大版本改造/SKILL.md）
- **total_hook_files**: 2（settings.json + settings.local.json）
- **total_template_files**: 3（_template.md v1/v2/v3）
- **total_protocol_files**: 17（含 product-side、receipt、relay 文件）
- **total_agent_instruction_files**: 4（CLAUDE.md、.claude/SKILLS.md、main_agent_delivery.md、iteration_execution_guard.md）
- **total_log_files**: 4（TASK_LOG.md、CHANGELOG.md、workflow_changelog.md、relay_progress.md）
- **total_historical_files**: 3（docs/workflow_core.md 旧版、docs/_archive/ 中的 handoff、docs/audit/workflow/ 文件）
- **total_unknown_files**: 1（audit/productside_review/change_point_detection.py）
- **total_audit_files**: 30
- **blockers**: 无（此为只读路径摸底，不涉及执行阻塞）
- **recommended_next_action**: "将路径清单交给 Owner-Control，用于 workflow_core.md v3.1 分节修订。"

---

## 5. 补充观察

### 5.1 关键结构性问题

1. **workflow_core.md 双副本不一致**：`docs/workflow_core.md`（根目录）为旧分支版本，使用裸 `python3` 命令，缺少 §11.1（Dirty Tree Gate Granularity）、§12（Internal Model Endpoint Preflight Rule）、§13（Project Python Interpreter Rule）三个关键章节。"权威源"声明可能导致 agent 读取错误副本。

2. **Hermes 文件全部 untracked**：audit/hermes_tasks/ 下所有 17 个文件均未纳入 git 版本控制。

3. **3 个引用路径缺失**：workflow_core.md 建议的 `audit/workflow/` 和 `audit/general/` 目录不存在；TASK_LOG.md 引用但从未创建的 `BENCHMARK_LOG.md`。

4. **无独立 Codex 执行模板**：Codex 执行/交接/回执协议全部嵌入在 `iteration_execution_guard.md` 和 `main_agent_delivery.md` 中，无独立模板。

5. **无外部 agent 指令框架**：无 AGENTS.md、.codex/、CODERULES.md 或 .mdc 文件。

### 5.2 路径分布

- docs/skills/ — 6 文件的紧凑技能集，全部 workflow 相关
- audit/phase4大版本改造/ — 21+ DS 审计报告（最密集区域）
- audit/hermes_tasks/ — 17 文件（全部 untracked），3 个子任务目录
- docs/iterations/ — 3 模板 + TASK_LOG + CHANGELOG + 多个 DS acceptance review
