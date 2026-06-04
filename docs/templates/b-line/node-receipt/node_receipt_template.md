# DAG Node Receipt — 模板

每个 DAG 节点执行完成后生成的标准化回执。

## 格式

```yaml
node_id: <来自迭代计划>
task_id: <对应 relay task>
role: <来自迭代计划>
status: completed | failed | skipped

# 时间
started_at: <ISO 时间>
completed_at: <ISO 时间>
elapsed_minutes: <耗时>

# 执行信息
executor_type: codex | claude
execution_mode: managed_subprocess | tmux_interactive
relay_result: agent_completed | agent_failed | environment_blocked | timeout

# 产出物
outputs:
  - path: <产出物路径>
    exists: true | false
    size_bytes: <大小>
  - path: <产出物路径>
    exists: true | false

# 验证
validation:
  - check: <验证项>
    result: pass | fail | not_applicable

# 问题
issues: <执行中遇到的问题，无则不填>

# 是否就绪
ready_for_next: true | false
blocking_reason: <如果 ready_for_next=false，填原因>
```

## 实际示例（从 Registry R0 inventory 节点反推）

```yaml
node_id: node-registry-r0-inventory-01
task_id: inv-codex-self-scan-01
role: Inventory Scanner
status: completed

started_at: "2026-05-30T16:10:58+08:00"
completed_at: "2026-05-30T16:15:26+08:00"
elapsed_minutes: 4.5

executor_type: codex

outputs:
  - path: tasks/inventory/codex-self-scan/outputs/codex_capabilities.yaml
    exists: true
    size_bytes: 4210
  - path: tasks/inventory/codex-self-scan/outputs/codex_capabilities.md
    exists: true
    size_bytes: 2967

validation:
  - check: YAML 可解析
    result: pass
  - check: 未修改配置文件
    result: pass

issues:
  - WHAM sandbox 初次因代理缺失失败，设 HTTPS_PROXY 后解决

ready_for_next: true
```
