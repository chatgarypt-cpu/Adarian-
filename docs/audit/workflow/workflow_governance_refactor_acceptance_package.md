# Workflow Governance Refactor Acceptance Package

## 1. Final Summary

- overall_status: `partial_done`
- confidence: `medium`

判定原因：

- authority consolidation 已落地
- control plane 退役与 probe 去耦已落地
- minimal eventization 已落到 workflow artifacts
- freeze governance 已落到规则与 closeout 模板
- 但当前 iteration 未 closeout，且仓库存在大量既有脏变更，因此不能宣称 freeze execution 完成

---

## 2. What Changed

- 将 `docs/skills/workflow_core.md` 重构为唯一流程规则权威源
- 明确运行状态权威源为 iteration 文档状态 + `docs/iterations/TASK_LOG.md`
- 将 `CLAUDE.md` 与 `docs/skills/main_agent_delivery.md` 降级为从属规范
- 为 iteration 模板、当前 iteration、`TASK_LOG.md` 引入 `task_id / review_id / attempt_id / acceptance_id`
- 移除 `scripts/probes/*` 对 `control/` 的运行时读写
- 将 `control/` 与 `scripts/generate_snapshot.py` 归档到 `docs/_archive/control_plane/`
- 归一化 `third_round_audit_checklist.md` 到 `docs/audit/workflow/`
- 更新 `control_plane_retirement.md` 为已执行状态

---

## 3. Evidence by Objective

### 3.1 Authority consolidation

files changed:

- `docs/skills/workflow_core.md`
- `docs/skills/main_agent_delivery.md`
- `CLAUDE.md`

what was changed:

- `workflow_core.md` 新增 authority model、closure rules、freeze gate、minimal eventization 要求
- `workflow_core.md` 明确声明：
  - rule authority = `workflow_core.md`
  - runtime authority = iteration 状态 + `TASK_LOG.md`
  - control plane = retired historical artifact
- `main_agent_delivery.md` 增加“若冲突以 workflow_core 为准”
- `CLAUDE.md` 增加 `Workflow Authority Notice`

why it satisfies the target:

- 现行规则 authority 已被单点声明
- 其他 active docs 不再与其并列定义主流程
- “当前状态以什么为准”已有明确答案，不再依赖 control plane

### 3.2 Control plane retirement

files changed:

- `scripts/probes/reduced_schema_chain_probe.py`
- `scripts/probes/p1a_prompt_probe.py`
- `scripts/probes/p1g_prompt_probe.py`
- `docs/audit/workflow/control_plane_retirement.md`
- `docs/_archive/control_plane/README.md`
- `docs/_archive/control_plane/control/*`
- `docs/_archive/control_plane/generate_snapshot.py`

what was changed:

- `reduced_schema_chain_probe.py` 删除 `control/state.json` / `control/inbox.md` 读写，只保留 probe-local outputs
- `p1a_prompt_probe.py` 删除 `control/inbox.md` 回写
- `p1g_prompt_probe.py` 删除 `control/inbox.md` 回写
- 原 `control/` 目录与 `scripts/generate_snapshot.py` 已归档到 `docs/_archive/control_plane/`
- 退役文档增加已执行状态与归档位置

why it satisfies the target:

- active probe/runtime 路径已不再依赖 `control/`
- control plane 保留了审计证据，但退出了现行 workflow
- retirement 顺序遵守了“先去耦，再归档”

grep evidence:

```text
rg -n "control/|state.json|inbox.md|snapshot.md|generate_snapshot" scripts/probes docs/skills docs/iterations CLAUDE.md

only matches:
- docs/skills/workflow_core.md (retired-component declaration)
```

### 3.3 Minimal eventization

files changed:

- `docs/skills/workflow_core.md`
- `docs/skills/main_agent_delivery.md`
- `docs/iterations/_template_v2.md`
- `docs/iterations/v1.1.21.md`
- `docs/iterations/TASK_LOG.md`

what was changed:

- 在 `workflow_core.md` 增加 event IDs 规范
- 在 `main_agent_delivery.md` 增加 `review_id` / `attempt_id` 交付要求
- 在 `_template_v2.md` 增加 `task_id`、event IDs、closeout record 模板
- 在 `v1.1.21.md` 增加 `task_id` 和当前 event IDs
- 在 `TASK_LOG.md` 增加 acceptance record contract

why it satisfies the target:

- workflow artifacts 已有最小事件字段落点
- 失败反馈和验收记录开始具备 attempt-level traceability
- 未引入新的 runtime state file

search evidence:

```text
`task_id` / `review_id` / `attempt_id` / `acceptance_id`
present in:
- docs/skills/workflow_core.md
- docs/skills/main_agent_delivery.md
- docs/iterations/_template_v2.md
- docs/iterations/v1.1.21.md
- docs/iterations/TASK_LOG.md
```

### 3.4 Freeze governance

files changed:

- `docs/skills/workflow_core.md`
- `docs/iterations/_template_v2.md`
- `docs/iterations/v1.1.21.md`
- `docs/audit/workflow/third_round_audit_checklist.md`

what was changed:

- `workflow_core.md` 增加 freeze gate、rollback restrictions、minimal closeout record
- `_template_v2.md` 与 `v1.1.21.md` 增加 closeout record section
- 规范化 `third_round_audit_checklist.md` 到审计目录

why it satisfies the target:

- freeze contract 已从审计建议进入 workflow rule 与 artifact 模板
- rollback anchors 已有明确字段
- 但 freeze execution 仍受当前 repo 状态阻塞

freeze evidence:

```text
git tag --sort=-creatordate
v1.1.19-profiling-closeout
```

```text
git status --porcelain=v1
non-empty; repository still contains extensive pre-existing tracked and untracked changes
```

current blocker:

- `docs/iterations/v1.1.21.md` 仍为 `🚧 进行中`
- 当前 tag 仍只有 `v1.1.19-profiling-closeout`
- 工作树远非 clean

---

## 4. Acceptance Package for MiniMax

### Mapping Against `git_freeze_checklist.md`

- Rule-01 Clean Working Tree: `blocked`
- Rule-02 Iteration Status Closed: `blocked`
- Rule-03 Acceptance Recorded: `blocked`
- Rule-04 Version Anchor Created: `blocked`
- Rule-05 Previous Version Identified: `satisfied`
- Minimal Closeout Record Template Exists: `satisfied`

### Mapping Against `control_plane_retirement.md`

- Phase 1 Freeze: `satisfied`
- Phase 2 Remove Runtime Dependencies: `satisfied`
- Phase 3 Archive Or Remove Control Files: `satisfied` via archive
- Phase 4 Update Workflow Docs: `satisfied`
- No Silent Breakage: `satisfied` by dependency removal before archive

### Mapping Against `third_round_audit_checklist.md`

- Freeze execution: `blocked`
- Probe dependencies removed: `satisfied`
- Runtime no longer depends on control: `satisfied`
- Retirement state declared: `satisfied`
- Rule authority declared: `satisfied`
- Runtime authority declared: `satisfied`
- No authority vacuum: `satisfied`
- Review / Attempt / Acceptance / Task IDs landed: `partially satisfied`

`partially satisfied` reason:

- IDs 已进入文档与模板
- 但尚未形成一轮真实完成的 acceptance record 实例

---

## 5. Remaining Gaps

- `v1.1.21` 尚未 closeout
- `TASK_LOG.md` 尚无本轮真实 `acceptance_id` 完成记录
- `CHANGELOG.md` 未写入本轮 closeout
- 当前仓库工作树极脏，freeze proof 无法成立
- 当前版本尚未创建新的 iteration closeout tag

known carry-over items:

- 需要由后续 closeout 执行者补写 `v1.1.21` 的真实 acceptance record
- 需要在 clean-tree 条件下补做 tag 与 rollback proof

risks:

- 若现在直接宣布 workflow fully done，会把“规则落地”误报为“版本已可回滚”
- 若后续又在 active 脚本中重新引入 `control/` 依赖，会破坏退役结论

---

## 6. Human Escalations

- 是否要在当前大量既有脏变更环境下继续推进 `v1.1.21` closeout，还是先单独整理版本边界
- 是否要为本轮 workflow governance refactor 单独建立一次受控 closeout iteration
