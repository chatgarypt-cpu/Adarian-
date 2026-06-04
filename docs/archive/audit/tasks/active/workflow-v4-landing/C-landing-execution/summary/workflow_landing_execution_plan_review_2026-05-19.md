# Workflow Core v4.0 Landing Execution Plan Review

> 审查日期：2026-05-19  
> 审查人：Landing Execution Reviewer  
> 任务ID：v4.0-workflow-landing-execution-review-01  
> 审查对象：workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md  
> 目标落盘路径：docs/skills/workflow_core.md  

---

## 1. Executive Verdict

**Verdict: LANDING_PLAN_READY_WITH_CONDITIONS**

R2 文档结构完整（§0–§16），一致性修复已完成，具备进入 Codex 第一批落盘的基础条件。第一批落盘边界清晰：仅覆盖 `docs/skills/workflow_core.md`，不触碰任何其他文件。

但以下条件必须满足：

1. **A线（R2 Structural Review）必须 PASS** — 本审查假设 A线通过，但这是前置条件
2. **Owner 必须明确批准** — 这是 L-Level 任务，不得自动批准
3. **Codex 必须完成全部静态检查** — 见 §6
4. **Codex 不得自行 commit** — 采用 C0 模式
5. **落盘后 DS Team 必须执行 post-landing path/reference review**

---

## 2. First Landing Batch Boundary

```yaml
first_landing_batch:
  executor: Codex
  purpose: "将已通过 R2 结构审查的 workflow_core v4.0 全文落盘到 docs/skills/workflow_core.md，替换当前 v3.0 版本"
  task_level: L-Level
  allowed_files:
    - docs/skills/workflow_core.md
  forbidden_files:
    - docs/skills/workflow_core_compact.md
    - docs/skills/workflow_core_compact.yaml
    - docs/skills/ds_pre_audit.md
    - docs/skills/ds_verify.md
    - docs/skills/ds_accept.md
    - docs/skills/iteration_execution_guard.md
    - docs/skills/main_agent_delivery.md
    - docs/iterations/TASK_LOG.md
    - docs/iterations/CHANGELOG.md
    - docs/iterations/*.md（全部迭代文档）
    - docs/dev_spec.md
    - src/**/*.py（全部源码）
    - main.py
    - config.py
    - tests/**/*.py
    - audit/**/*.*（全部审计文件）
    - .claude/**/*.*
    - CLAUDE.md
    - README.md
    - .codex/**/*.*（Codex 全局配置）
    - profiling/**/*.*
    - scripts/**/*.*
    - seeds/**/*.*
    - outputs/**/*.*
  required_commands: []
  required_static_checks:
    - "§0–§16 每节恰好出现一次（检查 # §0 到 # §16 标题）"
    - "Markdown 代码围栏平衡（``` 开头和结尾数量一致）"
    - "无空代码围栏（``` 后紧跟 ``` 无内容）"
    - "无 audit/hermes_tasks 作为 canonical path（仅作为 legacy/transitional）"
    - "无 owner_approval.md 作为默认批准文件"
    - "无 DS Verify / DS Accept 作为独立流程节点"
    - "docs/skills/workflow_core.md 自述为唯一权威源"
    - "文件第一行标题为 # Adarian MVP 核心开发工作流 v4.0"
    - "文件末尾无截断（最后一行是完整内容）"
  required_receipts:
    - codex_receipt.yaml
    - codex_handoff.md
  post_landing_review:
    - DS Team readonly post-landing path/reference review
  commit_mode: no_commit_until_owner_confirmed
  stop_conditions:
    - "R2 源文件无法读取"
    - "Codex 本地安全门未通过"
    - "任一静态检查失败"
    - "需要修改 forbidden files"
    - "git status 显示 docs/skills/workflow_core.md 之外的文件被修改"
    - "Owner 未确认"
```

---

## 3. Allowed Files

### 3.1 唯一允许修改的文件

```text
docs/skills/workflow_core.md
```

**操作**：用 R2 全文（`audit/workflow_v4.0/workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md`）替换当前 v3.0 内容。

### 3.2 允许读取的文件

```text
1. workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md（源）
2. docs/skills/workflow_core.md（当前 v3.0，用于对比）
3. docs/iterations/TASK_LOG.md（用于了解当前版本状态）
4. docs/iterations/CHANGELOG.md（用于了解当前版本状态）
5. git status / git log（用于 git safety gate）
```

### 3.3 允许新增的文件

```text
audit/tasks/active/workflow-v4-landing/C-landing-execution/codex/codex_receipt.yaml
audit/tasks/active/workflow-v4-landing/C-landing-execution/codex/codex_handoff.md
```

仅限在已存在的任务目录中写入 Codex 回执和交接文件。

---

## 4. Forbidden Files

### 4.1 绝对禁止修改

| 类别 | 文件 | 原因 |
|------|------|------|
| Compact 衍生品 | `docs/skills/workflow_core_compact.md` | 不存在，不应在此批创建 |
| Compact 衍生品 | `docs/skills/workflow_core_compact.yaml` | 不存在，不应在此批创建 |
| DS 旧指令 | `docs/skills/ds_pre_audit.md` | v3.0 产物，需在后续批次更新 |
| DS 旧指令 | `docs/skills/ds_verify.md` | v3.0 产物，v4.0 已合并为 Post-Execution Review |
| DS 旧指令 | `docs/skills/ds_accept.md` | v3.0 产物，v4.0 已合并为 Post-Execution Review |
| 执行 guard | `docs/skills/iteration_execution_guard.md` | 需在后续批次更新 |
| 交付规范 | `docs/skills/main_agent_delivery.md` | 需在后续批次更新 |
| 迭代台账 | `docs/iterations/TASK_LOG.md` | 不在第一批修改范围 |
| 变更日志 | `docs/iterations/CHANGELOG.md` | 不在第一批修改范围 |
| 全部迭代文档 | `docs/iterations/*.md` | 不在第一批修改范围 |
| 技术规格 | `docs/dev_spec.md` | 不在第一批修改范围 |
| 项目规范 | `CLAUDE.md` | 不在第一批修改范围 |
| 全部源码 | `src/**/*.py`, `main.py`, `config.py` | 绝对不碰 |
| 全部测试 | `tests/**/*.py` | 绝对不碰 |
| 全部审计 | `audit/**/*.*` | 绝对不碰（任务产出文件除外） |
| Claude 配置 | `.claude/**/*.*` | 绝对不碰 |
| Codex 全局配置 | `.codex/**/*.*` | 绝对不碰 |
| Profiling | `profiling/**/*.*` | 绝对不碰 |
| 脚本 | `scripts/**/*.*` | 绝对不碰 |
| 种子文件 | `seeds/**/*.*` | 绝对不碰 |
| 运行产物 | `outputs/**/*.*` | 绝对不碰 |

### 4.2 已知的过渡期不一致

以下文件在 v4.0 落盘后会与 `workflow_core.md` 产生语义不一致，但**明确禁止在第一批修复**：

```text
1. docs/skills/ds_verify.md — 仍描述 v3.0 的独立 DS Verify 阶段
2. docs/skills/ds_accept.md — 仍描述 v3.0 的独立 DS Accept 阶段
3. docs/skills/ds_pre_audit.md — 仍使用 v3.0 术语
4. docs/skills/main_agent_delivery.md — 引用 v3.0 的事件 ID 格式
5. docs/skills/iteration_execution_guard.md — 引用 v3.0 的 dirty tree gate
6. CLAUDE.md — 引用 docs/skills/workflow_core.md 为权威源（不变），但其他描述可能过时
```

这些不一致应在后续批次（第 6-8 批）中逐步修复，不得在第一批中顺手处理。

---

## 5. Execution Order

### 5.1 前置条件（本批次之前）

```text
Step 0: R2 文档冻结（已完成）
Step 1: A线 DS R2 Structural Review 通过（PASS_TO_CODEX_LANDING 或 PASS_WITH_MINOR_NOTES）
Step 2: B线 Rollout Readiness Review 通过（READY_FOR_STAGED_ROLLOUT 或 READY_AFTER_CONTROL_AGENT_PATCH）
Step 3: C线（本审查）Landing Execution Plan Review 通过
Step 4: Control Agent 汇总 A/B/C 三线报告
Step 5: Owner 明确批准进入 Codex first landing
```

### 5.2 第一批 Codex 执行顺序

```text
Step 6: PM Runtime 创建 Codex dispatch
Step 7: Owner 批准 dispatch（A0 单次人工批准）
Step 8: Codex 本地安全门（adarian-iteration-safety-gate）
        → 检查 dirty tree、forbidden files、version isolation
        → 如果输出 NEEDS_CLARIFICATION / NEEDS_VERSION_ISOLATION / NO_GO，立即 HOLD
Step 9: Git safety gate
        → 检查当前 branch（work/v1.2.8）
        → 检查 git status（当前有 dirty files，见下方风险提示）
        → 确认 docs/skills/workflow_core.md 是可写的唯一文件
Step 10: Codex 读取 R2 源文件
Step 11: Codex 执行静态检查（§6）
Step 12: Codex 写入 docs/skills/workflow_core.md
Step 13: Codex 再次执行静态检查（验证写入后文件完整性）
Step 14: Codex 生成 codex_receipt.yaml + codex_handoff.md
Step 15: Codex 向 Owner 汇报（不改动 commit）
Step 16: Owner 确认文件内容
Step 17: DS Team 执行 post-landing path/reference review
Step 18: Owner-Control 判断是否 git commit
```

### 5.3 明确不在此批执行的操作

```text
- 不修改 Control Agent 指令文件
- 不修改 DS Team 指令文件
- 不修改 Codex 指令文件
- 不修改 Hermes/PM Runtime 模板
- 不生成 compact.md
- 不生成 compact.yaml
- 不更新 TASK_LOG（除非极简记录本次 landing）
- 不更新 CHANGELOG（除非极简记录本次 landing）
- 不修改 CLAUDE.md
- 不运行 smoke test
- 不 git commit（除非 Owner 显式确认）
```

---

## 6. Required Checks

### 6.1 静态检查清单

Codex 必须在写入前后各执行一次以下检查：

| # | 检查项 | 方法 | 通过标准 |
|---|--------|------|---------|
| 1 | §0–§16 每节恰好一次 | `grep -c '^# §' workflow_core.md` | 17 行（§0 到 §16） |
| 2 | Markdown 代码围栏平衡 | 统计 ``` 出现次数 | 偶数次 |
| 3 | 无空代码围栏 | 检查 ```\n``` 模式 | 不存在 |
| 4 | audit/hermes_tasks 不作为 canonical path | grep 'canonical' 上下文 | 仅出现于 legacy/transitional 声明中 |
| 5 | owner_approval.md 不作为默认文件 | grep 'owner_approval.md' | 仅出现于否定声明中 |
| 6 | DS Verify/DS Accept 不作为独立节点 | grep 'DS Verify' 和 'DS Accept' | 仅出现于“不再作为”解释中 |
| 7 | 唯一权威源自述正确 | grep 'docs/skills/workflow_core.md' | 确认为唯一权威路径 |
| 8 | 开头标题正确 | head -1 | `# Adarian MVP 核心开发工作流 v4.0（Workflow Core）草案` |
| 9 | 文件末尾无截断 | tail -5 | 最后一行是完整内容，不是半截句子 |
| 10 | 无重复顶级章节 | 检查 §0-§16 标题无重复 | 每个编号只出现一次 |
| 11 | 无遗留 v3.0 旧流程描述 | grep 'DS Verify → DS Accept' 或类似 | 不在正文中作为正向流程出现 |
| 12 | task/approval.yaml 是默认批准记录 | grep 'task/approval.yaml' | 确认为默认 |

### 6.2 不需要的检查

以下检查明确不要求在第一批执行：

```text
1. py_compile — 不涉及 Python 源码
2. import check — 不涉及 Python 源码
3. pytest — 不涉及 Python 源码
4. smoke test — 不涉及主链、schema、prompt、report generation
5. performance test — 不涉及运行产物
6. full DS Post-Execution Review — 文档落盘，轻量路径审查即可
```

---

## 7. Required Evidence

### 7.1 Codex 必须回传的证据

**codex_receipt.yaml**：

```yaml
task_id: v4.0-workflow-landing-execution-review-01
executor: Codex
baseline_commit: <当前 HEAD commit>

actual_modified_files:
  - docs/skills/workflow_core.md

actual_added_files: []
actual_deleted_files: []

commands_run: []

static_checks:
  - check: "§0–§16 section count"
    result: pass/fail
  - check: "Markdown fence balance"
    result: pass/fail
  - check: "No empty code fences"
    result: pass/fail
  - check: "No audit/hermes_tasks as canonical path"
    result: pass/fail
  - check: "No owner_approval.md as default"
    result: pass/fail
  - check: "No DS Verify/DS Accept as separate nodes"
    result: pass/fail
  - check: "docs/skills/workflow_core.md sole authority"
    result: pass/fail
  - check: "File header title correct"
    result: pass/fail
  - check: "File not truncated"
    result: pass/fail

git_status:
  branch: <当前分支>
  dirty_files: <dirty files 列表>
  workflow_core_changed_only: true/false

diff_summary: "Replaced docs/skills/workflow_core.md v3.0 with v4.0 R2 reviewed draft"
known_issues: []
blockers: []
recommended_commit_message: "feat: land workflow_core v4.0 full authority document"
commit_performed: false
```

**codex_handoff.md** 至少包含：

```markdown
# Codex Handoff — workflow_core v4.0 First Landing

## What was done
- 将 R2 审查通过的 workflow_core v4.0 草案写入 docs/skills/workflow_core.md
- 替换了原有 v3.0 版本

## Static check results
- [列出所有检查及结果]

## Git status
- [当前 git status]

## Notes for DS Team post-landing review
- 检查新 workflow_core.md 中所有路径引用是否真实存在
- 检查 docs/skills/ 下其他文件与 v4.0 的已知不一致
- 检查 CLAUDE.md 是否需要更新 workflow_core 版本引用

## Notes for next batch (Control Agent patch)
- Control Agent 需按 v4.0 口径调整迭代文档模板
- task_id 格式从 task-vX.Y.Z-xxx 改为 vX.Y.Z-xxx-01
- DS Verify/DS Accept 不再作为独立阶段

## What NOT to do next
- 不要一次性修改 docs/skills/ 下所有文件
- 不要在此批生成 compact.md/compact.yaml
- 不要在此批修改 TASK_LOG/CHANGELOG
```

### 7.2 PM Runtime 应回收的证据

```text
1. codex_receipt.yaml
2. codex_handoff.md
3. git diff（确认仅 docs/skills/workflow_core.md 被修改）
4. git status（确认无其他文件被修改）
```

---

## 8. Commit Policy

### 8.1 采用 C0：默认人工确认提交

```yaml
commit_mode: no_commit_until_owner_confirmed
```

**原因**：

1. 这是 L-Level 任务（workflow authority document 变更）
2. 当前 work/v1.2.8 分支有 dirty files（见 git status）
3. workflow_core.md 是项目最核心的流程规则文件
4. 落盘后需要 DS post-landing review 确认路径引用正确

### 8.2 Codex 必须准备但不得执行

Codex 必须准备以下材料并呈现给 Owner：

```yaml
git_status:
  branch: work/v1.2.8
  changed_files:
    - docs/skills/workflow_core.md
  dirty_files_present: <列出所有非本任务的 dirty files>
diff_summary: "Replaced v3.0 with v4.0 R2 reviewed draft"
test_results: "N/A — documentation-only change"
ds_acceptance_verdict: <待 DS post-landing review>
smoke_result: "N/A — no source code changes"
performance_summary: "N/A"
recommended_commit_message: "feat: land workflow_core v4.0 full authority document"
```

### 8.3 禁止的提交行为

```text
1. Codex 在 Owner 未确认时 git commit
2. PM Runtime git commit
3. DS Team git commit
4. 将 dirty files 一并提交
5. 使用 --no-verify 跳过 hooks
6. 使用 --amend 修改历史 commit
```

---

## 9. Post-Landing Review

### 9.1 执行方

```text
DS Team（只读，不同于 A线 R2 review 的 reviewer）
```

### 9.2 审查内容

```text
1. 确认 docs/skills/workflow_core.md 内容与 R2 源文件一致
2. 检查 §0-§16 完整性
3. 检查所有路径引用是否真实存在：
   - docs/skills/workflow_core.md（自身）✓
   - docs/skills/workflow_core_compact.md（尚未存在）
   - audit/tasks/active/<task_id>/（存在）
   - audit/tasks/closed/<task_id>/（存在）
   - audit/tasks/archive/<milestone_id>/<task_id>/（存在）
   - docs/iterations/（存在）
   - outputs/runs/<run_id>/（存在）
   - ~/.codex/skills/adarian-iteration-safety-gate/SKILL.md（检查是否存在）
4. 标记 docs/skills/ 下其他文件与 v4.0 的已知不一致
5. 确认 TASK_LOG / CHANGELOG 未被非授权修改
6. 确认没有 forbidden files 被触碰
```

### 9.3 输出

```text
audit/tasks/active/workflow-v4-landing/C-landing-execution/ds/ds_post_landing_review.md
audit/tasks/active/workflow-v4-landing/C-landing-execution/ds/ds_receipt.yaml
```

### 9.4 不做的事

```text
1. 不修改任何文件
2. 不重新设计工作流
3. 不要求重写 R2
4. 不自动 closeout
5. 不 git commit
```

---

## 10. Stop Conditions

以下任一情况发生时，Codex 必须立即停止并回到 Owner-Control：

### 10.1 前置条件失败

```text
1. R2 源文件无法读取
2. MCP / file read 不可用
3. docs/skills/workflow_core.md 当前文件无法读取
```

### 10.2 安全门失败

```text
4. Codex 本地安全门输出 NEEDS_CLARIFICATION
5. Codex 本地安全门输出 NEEDS_VERSION_ISOLATION
6. Codex 本地安全门输出 NO_GO
7. Git safety gate 发现 docs/skills/workflow_core.md 之外的 dirty files 且未解释
```

### 10.3 执行中发现问题

```text
8. 任一静态检查失败（写入前或写入后）
9. 需要修改 forbidden files
10. 需要扩大 scope
11. 发现 R2 源文件存在结构性缺陷
12. 写入后 workflow_core.md 文件损坏或不完整
```

### 10.4 流程违规

```text
13. Owner 未确认批准
14. 试图绕过 Owner-Control 直接 commit
15. 试图在第一批中修改 forbidden files
```

### 10.5 HOLD 后的动作

```text
1. Codex 保留当前 diff
2. Codex 生成 codex_receipt.yaml（标记为 hold）
3. Codex 生成 codex_handoff.md（说明阻塞原因）
4. PM Runtime 向 Owner 打印阻塞摘要
5. 等待 Owner-Control 判断
```

---

## 11. Risks

### 11.1 已识别风险

| # | 风险 | 严重度 | 缓解措施 |
|---|------|--------|---------|
| 1 | **当前 work/v1.2.8 分支有 dirty files**：git status 显示 `.claude/worktrees/` 下有多个 agent worktree 的未提交变更，以及 `docs/workflow_core.md` 已删除。这些 dirty files 与 workflow landing 无关，但可能在 git safety gate 触发阻塞 | MEDIUM | 在 Codex dispatch 中明确排除这些 dirty files；如阻塞，先由 Owner 处理 dirty tree |
| 2 | **docs/skills/ 下 v3.0 旧文件与新 workflow_core.md v4.0 不一致**：`ds_verify.md`、`ds_accept.md` 等仍描述 v3.0 独立阶段，v4.0 已合并为 Post-Execution Review | MEDIUM | 在 handoff 中明确标注这些不一致；在后续批次（6-7 批）中修复；不在第一批处理 |
| 3 | **Control Agent 仍按 v3.0 口径运行**：如果 Control Agent 在 workflow_core.md 落盘后仍使用 v3.0 术语（DS Verify/DS Accept/task-vX.Y.Z-xxx ID 格式），会产生新旧口径混用 | HIGH | 第二批优先处理 Control Agent v4.0 instruction patch；在 handoff 中明确提醒 |
| 4 | **R2 文档过长（6974 行）**：可能在 Claude Code 上下文中被截断，导致 Codex 无法完整读取 | LOW | Codex 使用 Read 工具分段读取；静态检查确保文件完整 |
| 5 | **PM Runtime / Hermes 仍按旧模板派发任务**：如果 PM Runtime 在 workflow_core.md 落盘后仍使用旧 dispatch 模板，会产生旧格式任务书 | MEDIUM | 第五批更新 Hermes dispatch template；期间人工审核任务书 |
| 6 | **TASK_LOG/CHANGELOG 使用旧 event ID 格式**：当前 TASK_LOG 使用 `task-vX.Y.Z-xxx` 格式，v4.0 改用 `vX.Y.Z-xxx-01` 格式 | LOW | 格式迁移是渐进过程；不要求历史记录重新编号 |

### 11.2 风险缓解总体策略

```text
1. 小步落盘：第一批只改一个文件
2. 不自动 commit：所有 git 操作必须 Owner 显式确认
3. 过渡期容忍不一致：明确标注已知不一致，不在一批中修复
4. 每批后 review：DS post-landing review 确认每批质量
5. Owner 最终收口：所有 closeout 判断回到 Owner-Control
```

---

## 12. Control Agent / Hermes PM 传达职责（Owner Directive 补充）

v4.0 的落地不仅是文件替换，更是协作模式升级。Control Agent 和 Hermes PM 的核心能力不只是「执行任务」，而是准确传达、明确告知、稳定编排。

### 12.1 Control Agent 传达要求

**Control Agent 必须明确告知 Owner**：
- 当前状态是什么
- 当前阶段是什么
- 当前 blocker 是什么
- 当前唯一下一步动作是什么
- 下一步由谁执行：Owner / Control Agent / Hermes / DS Team / Codex
- 是否需要 Owner 批准

**进入执行期后，Control Agent 不应只给抽象建议，而应给出可执行文本**：
- 如果下一步需要 Hermes 派发任务 → 给完整 Hermes dispatch prompt
- 如果下一步需要 DS Team 审查 → 给完整 DS Team prompt
- 如果下一步需要 Codex 落盘 → 给完整 Codex execution prompt
- 如果需要 Owner 转发给其他 agent → 在 Owner 确认后直接给出可复制 prompt

**不应让 Owner 自己拼提示词、补上下文或猜执行顺序**。
Owner 的角色是方向判断、批准和最终 gate，不是人肉邮差或流程调度器。

**Control Agent 每次进入执行期或 landing gate 时，固定输出**：

```
当前状态：
当前阶段：
当前 blocker：
唯一下一步：
执行方：
是否需要 Owner 批准：
如需转交其他 agent，完整 prompt 如下：
```

### 12.2 Hermes PM 汇报要求

**Hermes PM 每次汇报时，固定说明**：
- 当前运行状态
- 已完成任务
- 阻塞任务
- 产物路径
- 是否需要 Owner 决策
- 推荐的唯一下一步

### 12.3 Closeout 不等于完成

- Hermes completed ≠ closeout
- DS pass ≠ closeout
- Codex delivered ≠ closeout
- 所有执行结果必须由 Control Agent 转译为 Owner 可判断的下一步

---

## 13. Final Recommendation

### 12.1 推荐推进路径

```text
当前状态：C线审查完成，verdict = LANDING_PLAN_READY_WITH_CONDITIONS

下一步：
  1. Control Agent 汇总 A/B/C 三线报告
  2. 如 A线 PASS + B线 PASS/READY + C线 LANDING_PLAN_READY_WITH_CONDITIONS
     → Owner 批准 Codex first landing
  3. PM Runtime 创建 Codex dispatch（仅 docs/skills/workflow_core.md）
  4. Codex 执行（含安全门、静态检查、写入、回执）
  5. DS Team post-landing path/reference review
  6. Owner 确认 → git commit
  7. 进入第二批（Control Agent v4.0 instruction patch）
```

### 12.2 回答 15 个关键问题

| # | 问题 | 答案 |
|---|------|------|
| 1 | 第一批是否只修改 docs/skills/workflow_core.md？ | **是**。仅此一个文件。 |
| 2 | Control Agent v4.0 instruction patch 是否必须在第一批之前？ | **否**。Control Agent 对齐是第二批，不是第一批前置条件。但 Control Agent 应在第一批落盘后尽快对齐。 |
| 3 | compact.md 是在第一批还是之后生成？ | **之后**。建议第三批。compact.md 是衍生品，不影响 workflow_core.md 的权威性。 |
| 4 | compact.yaml 是手动生成还是机器生成？ | **机器生成**。必须在 compact.md 稳定后，由机器/脚本从 compact.md 提取生成。建议第四批。 |
| 5 | Hermes dispatch template 在 workflow_core.md 落盘前还是后更新？ | **之后**。建议第五批。落盘前更新会导致模板引用尚未生效的规则。 |
| 6 | DS/Codex agent-specific instructions 在 workflow_core.md 落盘前还是后更新？ | **之后**。建议第六-七批。这些是从属文件，应以 workflow_core.md 为权威源。 |
| 7 | TASK_LOG/CHANGELOG 是否在第一批修改？ | **否**。除非仅添加一行极简记录标记本次 landing。 |
| 8 | 是否需要 smoke test？ | **否**。这是纯文档变更，不涉及任何源码、schema、prompt 或主链。 |
| 9 | 需要哪些静态检查？ | **12 项**：§0-§16 计数、围栏平衡、空围栏、canonical path、owner_approval.md、DS Verify/Accept、权威源自述、标题、截断、重复章节、旧流程残留、approval.yaml 默认。详见 §6。 |
| 10 | Codex 是否应自动 commit？ | **否**。采用 C0 模式，Owner 显式确认后才 commit。 |
| 11 | 允许修改的文件？ | **仅 docs/skills/workflow_core.md**。 |
| 12 | 禁止修改的文件？ | **所有其他文件**。包括 compact 衍生品、DS 旧指令、迭代文档、源码、测试、审计、配置等。详见 §4。 |
| 13 | 停止条件？ | **15 项**。包括前置条件失败、安全门失败、静态检查失败、forbidden files 触碰、scope 扩大、Owner 未确认等。详见 §10。 |
| 14 | Codex 应回传什么证据？ | **codex_receipt.yaml + codex_handoff.md**。包含静态检查结果、git status、diff summary。详见 §7。 |
| 15 | 谁执行 post-landing review？ | **DS Team**（只读，不同于 A线 reviewer）。执行 path/reference 一致性审查。 |

### 12.3 最终判断

```text
第一批落盘边界清晰、风险可控。

前提条件：
  - A线 R2 Structural Review 必须 PASS
  - Owner 必须明确批准

执行原则：
  - 只改一个文件
  - 不 commit 直到 Owner 确认
  - 不顺手修任何其他文件
  - 过渡期容忍已知不一致

建议：
  LANDING_PLAN_READY_WITH_CONDITIONS
  → 等待 A线/B线完成后，Owner 批准进入第一批
```
