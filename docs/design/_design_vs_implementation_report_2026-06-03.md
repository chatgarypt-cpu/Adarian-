# WorkflowBase v4.0 — Design vs Implementation 对比

> 基于两份设计文档 + WorkflowBase 实际代码：
> 1. **A 线真实蓝图**：`docs/design/workflow_core/workflow_core_v4.0_r2.md`（197KB，6973 行，v4.0 §0–§16 完整草案）
> 2. **B 线快速迭代设计**（已确认部分实现合并到 A 线）：`docs/design/新一代DAG工作流设计文档_v0.4_emerged.md`（53KB）
> 3. **PM Runtime 岗位说明书**：`docs/design/pm_runtime/pm_runtime_instruction_v0.1.3.md`
> 日期：2026-06-03

---

## 一、角色与流程（A 线 workflow_core v4.0 §3–§4）

### 1.1 角色分工（§3）

| 角色 | 设计定义 | WorkflowBase 覆盖 |
|------|---------|------------------|
| PM Runtime | 生成任务书草案、启动任务、维护状态、回收收据 | ✅ relay_runner.py + path_resolver.py + skill 注册表 |
| DS Team | 前置审查、后置验证、验收判定 | ✅ registry-reality-review / code-reality-review skill（agent-team） |
| Codex | 按迭代文档执行、自检、回传 diff/status | ✅ codex/tmux_executor.py + codex/executor.py |
| Owner/Control | 方向判断、Gate、closeout | ✅ closeout-gate + dispatch-approval-gate |

### 1.2 标准流程（§4）

| 流程步骤 | 设计描述 | 实现 |
|---------|---------|------|
| Control Agent 定边界写任务卡 | §4.1 | ✅ dispatch-prompt-authoring skill |
| DS Pre-Audit | §4.1 | ✅ reality-review hook + agent-team |
| Owner 批准推进 | §4.1 | ✅ dispatch-approval-gate |
| PM Runtime 启动任务 | §4.2 | ✅ relay runner dispatch |
| Codex 安全门 → 修改 → 自检 | §4.3 | ✅ executor_registry + safety_context |
| DS Post-Execution Review | §4.1 | ✅ Team Review / agent-team 验收 |
| PM Runtime 汇总报告 | §4.2 | ✅ receipt 回收 + summary 生成 |
| Owner-Control Closeout | §4.6 | ✅ closeout-gate（commit-gate + task_status 写入） |

### 1.3 任务目录（§5）

| 设计项 | 实现 |
|------|---------|
| task_id 命名规则（§5.1） | ⏳ task-directory-canonical skill 有命名规范但无强制校验 |
| 任务书 dispatch（§5.2） | ✅ dispatch/task_config.yaml + dispatch/prompt.md |
| 任务回执 receipt（§5.3） | ✅ dispatch-receipt-summary skill + .receipt.yaml |
| 任务目录结构（§5.4） | ✅ task-directory-canonical skill 定义完整 |

### 1.4 PM Runtime 执行边界（§6）

| 设计职责 | 实现 |
|---------|------|
| 生成任务书草案 | ✅ dispatch-prompt-authoring skill + relay_runner |
| 启动已批准任务 | ✅ relay runner dispatch → tmux |
| 维护任务状态 | ✅ heartbeat_monitor.py + progress.yaml + result.json |
| 回收 receipt/report/summary | ✅ receipt 回收 + summary 生成 |
| 检查任务产物齐全 | ⏳ artifact completeness 检查通过 skill 约定而非代码强制 |
| 把执行事实交回 Owner-Control | ✅ execution_report.md + summary/summary.md |

### 1.5 长程任务 Relay 与失败 HOLD（§7）

| 设计 | 实现 |
|------|------|
| relay 执行模式（dispatch → executor → report → recovery → review） | ✅ 完整 relay runner 链路 |
| 长程任务持久化状态 | ✅ progress.yaml + result.json + runtime/registry_events.jsonl |
| 失败默认 HOLD | ✅ executor_completed 以外的 runtime_state 触发 HOLD |
| Dialog 弹窗处理 | ✅ dialog_watcher primary + pm-relay-dialog skill + DialogHandler fallback |

### 1.6 Closeout 与版本收口（§11）

| 设计 | 实现 |
|------|------|
| Attempt / Patch Loop / Patch Lane | ✅ closeout-gate skill 定义完整 |
| Commit Gate（C0/C1） | ✅ commit-gate.py + git safety checks |
| Closeout checklist | ✅ 3 级 profile（smoke/standard/full_dag） |
| Closeout → Milestone | ✅ compress_handoffs.py 已有完整链路（扫 handoffs → 提 task_id → 查 closeout → 生成 milestone） |

---

## 二、PM Runtime 设计（v0.1.3）

### 2.1 核心能力

| 设计职责 | 实现状态 |
|---------|---------|
| 接任务、建目录、dispatch | ✅ relay_runner.py + path_resolver.py |
| 等待批准 | ⏳ dispatch-approval-gate 已存在但 A 线尚未配置为默认 gate |
| 启动 approved task | ✅ relay runner dispatch 至 tmux（Claude/Codex 双 executor） |
| 维护 heartbeat / progress / result | ✅ heartbeat_monitor.py + progress.yaml + result.json |
| 回收 report / receipt / summary | ✅ receipt 回收（.receipt.yaml）+ summary 生成 |
| 整理执行事实 → 回传 Owner | ✅ execution_report.md + summary/summary.md |

### 2.2 工具地图与使用边界（§16）

| 注册表 | 条目数 | 实现 |
|--------|-------|------|
| executor_registry.yaml | 6 | ✅ Claude/Codex tmux + fallback 等 |
| skill_registry.yaml | 41 | ✅ 12 个 PM Runtime skill + 其他 Hermes skill |
| hook_registry.yaml | 12 | ✅ iteration-gate、handoff-loader、dispatch-approval-gate 等 |
| mcp_registry.yaml | 4 | ✅ Brave、Zhipu、Fetch、Arxiv |
| 自持维护 | drift_check/scan_proposal/proposal_apply | ✅ 三件套 |

### 2.3 真正的缺口

| 设计 | 状态 | 说明 |
|------|------|------|
| Workflow compact YAML 消费 | ❌ 未实现 | §15 设计的 `workflow_compact.yaml` 机器可读索引，无解析器消费 |

---

## 三、总结

### ✅ 已实现的核心底座
- relay runner 调度（dispatch → tmux → monitor → collect）
- path_resolver 路径解析
- safety_context 安全白名单
- 注册表体系（skill/executor/hook/mcp 四件套）
- 自持维护（drift_check/scan_proposal/proposal_apply）
- 治理基础（audit/compress/handoff 三脚本 + 协议配置）
- 声音通知（sound_utils）
- dialog_watcher + heartbeat_monitor 双 companion
- closeout-gate、dispatch-approval-gate 等 gate/hook

### ❌ 设计有但底座未覆盖项
- **Workflow compact YAML 消费** — 无 compact.yaml 解析器（pm-runtime skill 只是口头引用）

### ✅ 设计写了但不需要
- **Repair Agent** — Claude Code 自带 retry/fix loop
- **Context Recovery 5 步协议** — handoff-loader 的轻量注入已覆盖需求
- **Fan-in Python 聚合引擎** — agent-team 合著合成替代了代码聚合

### ⚠️ 路线差异（设计 vs 实现走了不同路）
- **Fan-in 聚合**：设计要 Python 引擎 → 实际走 agent-team 合著合成
- **模板 schema 校验**：设计要 YAML schema → 实际走 5-agent 审查（含 yaml-schema-consistency agent）
- **安全弹窗处理**：设计要 5 类 Handler → 实际走 dialog_watcher + pm-relay-dialog skill + relay runner dialog handling + DialogHandler fallback
- **clauderemote 模式**：设计要 `/clauderemote on` 命令 → 实际走 dialog 分类 + auto-mode routing（executor_registry 有 clauderemote/dialog_handling 标记，pm-relay-dialog skill 定义完整协议）
- **安全边界正式检查**：设计要 ArtifactDetector/BashPermissionValidator → 实际 safety_context.py 有 validate_write_path/validate_read_path/validate_bash_command 三个方法
- **Handoff Writer 9 补丁**：设计文档列了 9 项 → 实际 handoff-writer.py 全部 9 项已实现（我漏看了）
- **Milestone/History Stewardship**：设计要 closeout 联动 → 实际 compress_handoffs.py 已有完整流程（扫 handoffs → 提 task_id → 查 closeout → 生成 milestone_snapshot.md + task_index.yaml），脚本头写着"由 closeout-gate 触发"，只是尚未自动挂钩
