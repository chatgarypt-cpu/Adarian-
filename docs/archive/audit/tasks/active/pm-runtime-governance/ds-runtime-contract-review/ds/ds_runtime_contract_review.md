# DS Team 审查报告：PM Runtime Communication Substrate Runtime Contract v0.1

> review_type: focused_runtime_contract_review
> task_id: ds-review-pm-runtime-communication-substrate-runtime-contract-20260522
> review_date: 2026-05-22
> reviewer: DS Team / Claude

---

## 裁决：`pass_with_known_issues`

Contract 方向正确，质量扎实，Spike 证据吸收完整。7 项 P0 全部有对应条款，无遗漏。可直接进入迭代任务书起草阶段，但需先补 YAML v0.3.3 patch。

---

## Agent Team 执行情况

- **P0-Repair-Verification Reviewer**: 7 项 P0 全体验证 — 5 项 fully_addressed, 2 项 partially_addressed（根因相同：YAML 未实际执行 patch）
- **Task-Card-Readiness Reviewer**: 评估为 needs_clarification — Contract 提供护栏但缺地图，需搭配 v0.3 Plan + YAML compact + CLAUDE.md 补充

---

## P0 修复状态

| P0 | 状态 |
|----|------|
| P0-1 YAML 目录 | partially_addressed — Contract §3.3 声明 yaml_patch_required: true，但未实际执行 patch |
| P0-2 Pre-action Gate | fully_addressed — §7 含完整 pre_action_check.yaml 格式 + hold rule |
| P0-3 Registry Status | partially_addressed — §5 双层模型正确，但 runtime_state 枚举(21)与 YAML(10)不一致（见 P0-A） |
| P0-4 Partial Output | fully_addressed — §11.2 明确 on timeout/abort 保存 *.partial.log |
| P0-5 Authority Vacuum | fully_addressed — §1 Runtime Contract 先于实现；§12.3 含 16 条 Hermes 禁止项 |
| P0-6 Anti-Tamper | fully_addressed — §10 append-only registry + hold on conflict |
| P0-7 Evidence Fidelity | fully_addressed — §15 三级 recovery + §8.2 八条规则 |

---

## 新增 P0 发现（3 项）

### P0-A：runtime_state 枚举严重不一致

Contract §5.3 定义了 21 个 runtime_state 值，YAML `runtime_state` 枚举仅 10 个值。Contract 新增了 sandbox_denied、rerun_required、partial_output、suspected_blocked 等，YAML 完全没有。需要 YAML v0.3.3 patch 对齐。

### P0-B：allowed_files / forbidden_files 为空占位符

Contract §6 task_config 中 scope.allowed_files 和 scope.forbidden_files 为 `[]`，未给出具体建议值。迭代任务书需要明确这些列表，否则 Codex 安全门无法生效。

### P0-C：YAML 目录策略未实际执行 patch

Contract §3.3 声明 yaml_patch_required: true，但 YAML 当前仍使用单级格式。需要实际 YAML patch 而非仅标记。

---

## 迭代任务书板式建议

### 结论：适合采用 Adarian 迭代任务书板式

但需满足以下条件：

### 建议字段

```yaml
task_domain: pm-runtime-infrastructure  # 明确标注：非业务源码
version: v1.2.9-communication-substrate-mvp
# 或 v0.1.0-communication-substrate-mvp

# 实施声明：本次迭代属于 PM Runtime substrate infrastructure，
# 不属于 Adarian 业务源码迭代。Codex 安全门不应按业务源码规则放行。

allowed_files:
  - pm_runtime/relay/cli.py
  - pm_runtime/relay/relay_runner.py
  - pm_runtime/relay/extractors.py
  - pm_runtime/relay/recovery.py
  - pm_runtime/templates/task_config.yaml

forbidden_files:
  - src/**                          # 业务源码，绝对禁止
  - main.py                         # 入口，禁止
  - config.py                       # 项目配置，禁止
  - tests/**                        # 业务测试，禁止
  - docs/skills/workflow_core.md    # workflow 权威，禁止
  - docs/skills/workflow_v4.0/**    # workflow 资产，禁止
  - audit/tasks/active/**           # 任务目录，禁止（除当前任务自身）

required_checks:
  - .venv/bin/python -m py_compile pm_runtime/relay/cli.py
  - .venv/bin/python -m py_compile pm_runtime/relay/relay_runner.py
  - .venv/bin/python -m py_compile pm_runtime/relay/extractors.py
  - .venv/bin/python -m py_compile pm_runtime/relay/recovery.py
  - .venv/bin/python -c "from pm_runtime.relay import cli; print('import OK')"

receipt_fields:
  - executor: codex
  - changed_files: []
  - commands_run: []
  - test_results: []
  - diff_summary
  - receipt_path
  - handoff_path
  - commit_status: no_commit | committed
  - forbidden_files_touched: []
  - known_issues: []
```

---

## 建议下一步

1. Owner 接受 Contract 方向
2. 出 YAML v0.3.3 patch（目录策略 + runtime_state 对齐）
3. Control Agent 起草迭代任务书 `v1.2.9-communication-substrate-mvp`
4. Codex 在 `pm_runtime/relay/` 下实现 Python MVP

---

## Process Issues

- **报告格式异常**：报告以纯文本 Markdown 输出在 result 字段中，而非 relay_runner 期望的嵌套 JSON。JSON 不适合 agent 间通讯——报告应该是 Markdown，结构化字段应该是 YAML frontmatter 而非 JSON 嵌套。
- Agent team 降级为单 agent 模式（team_mode_used: false），因当前环境不支持子 agent 派发。同一 agent 完成了 P0 验证 + 任务卡评估两个角色。
