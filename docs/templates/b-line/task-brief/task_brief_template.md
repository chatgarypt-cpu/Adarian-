# DAG Node Task Brief — 模板

从迭代计划的 DAG 节点生成 relay task 时使用。
每个 DAG 节点对应一个 task 目录，通过 `iteration_plan_path` + `node_id` 关联回计划。

## task_config 模版

```yaml
task_id: <domain>-<node_name>-<seq>
task_domain: <domain>
short_task: <short-name-no-dots>
task_level: S | M | L

executor_type: codex | claude
execution_mode: managed_subprocess | tmux_interactive

# ── 关联迭代计划 ──
iteration_plan_path: 资产/iteration-plans/<plan-name>/<plan-file>.md
node_id: <plan node_id>
node_goal: <plan node goal>
node_dependency: [<dependent node_ids>]

workdir: /Users/gary/项目开发/workyb

paths:
  task_dir: tasks/<domain>/<short-task>
  dispatch_path: tasks/<domain>/<short-task>/dispatch/task_config.yaml
  runtime_dir: tasks/<domain>/<short-task>/runtime
  logs_dir: tasks/<domain>/<short-task>/logs
  summary_path: tasks/<domain>/<short-task>/summary/pm_runtime_summary.md

executor_options:
  prompt_file: dispatch/prompt.md
  expected_outputs:
    - outputs/<artifact1>
    - outputs/<artifact2>
  codex_bypass_approvals: true
  no_output_timeout_sec: 180
  enable_sound_notification: true

runtime_control:
  mode: health_based
  heartbeat_interval_sec: 10
  progress_check_interval_sec: 30
  emergency_max_wall_time_sec: 600
  abort_requires_owner: true
  preserve_partial_output_on_abort: true
```

## 使用流程

1. 从迭代计划复制一个 node 定义
2. 填写 task_id / short_task（无点号）
3. 填写 `iteration_plan_path` + `node_id` + `node_goal`
4. 填写 `expected_outputs`（对应迭代计划 node 的 output）
5. `relay init --config dispatch/task_config.yaml`
6. `relay run --task-dir <dir>`
7. 回收 result.json

## 进度查看

执行后查看以下文件判断当前 DAG 节点状态：

| 文件 | 看什么 |
|------|--------|
| `runtime/result.json` | classification = agent_completed / agent_failed |
| `runtime/task_state.yaml` | runtime_state + task_status |
| `outputs/` | 预期产出物是否存在 |

整体 DAG 进度看迭代计划目录下的 promotion_gate 文件。
