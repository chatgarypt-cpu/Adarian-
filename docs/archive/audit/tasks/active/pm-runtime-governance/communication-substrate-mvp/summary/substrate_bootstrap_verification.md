# Communication Substrate MVP — 实战验收结论

> 时间: 2026-05-22
> 验收方式: Hermes 实操 init → run → summary → recover 全链路
> 结论: bootstrap usable，但不可替代旧脚手架

## 通过的

| 检查项 | 结果 |
|--------|------|
| CLI 四命令可执行 | ✅ init / run / summary / recover |
| Registry 事件链完整 | ✅ created → pre_action_checked → launched → progress → summary_written → recovered |
| Registry append-only | ✅ 6 条事件未覆盖写入 |
| Artifact schema 对齐 | ✅ pre_action_check / task_state / heartbeat / progress / failure_classification / recovery |
| PM Runtime summary 17 节 | ✅ 含 no closeout 声明 |
| py_compile + import | ✅ 全部通过 |

## 不通过的

| # | 问题 | 严重度 | 说明 |
|---|------|--------|------|
| 1 | **假心跳** | P0 | `run` 时写一次 heartbeat.json 就停，无后台线程持续更新。长程任务跑 10 分钟，heartbeat 永远是启动时那一帧。 |
| 2 | **对接不了真实 executor** | P0 | local_echo 能跑，但 launch Claude Code / Codex 作为 subprocess 并捕获 stdout/stderr 的路径未走通。这是通讯层要解决的核心问题。 |
| 3 | **状态机跳步** | P1 | healthy_running → executor_completed 一步到位，缺少中间态（slow_but_progressing、waiting_input、suspected_blocked）。 |
| 4 | **task_config 路径坑** | P1 | 目录路径当文件路径导致 copyfile 崩溃。真实 dispatch 文件（ds_dispatch.md、codex_taskbook.md）名字和格式各不相同，substrate 假定一切叫 task_config.yaml。 |
| 5 | **未与 Hermes 整合** | P0 | Substrate 生成了 artifact，但 Hermes 读取汇报仍用 relay_runner 的 relay_heartbeat.txt。两套东西并行，substrate 不知道 Hermes 的存在。 |

## 结论

能跑，但还不能替代旧 relay_runner 脚手架。下一轮核心目标：

```
对接真实 executor + 真心跳 + Hermes 集成
```

不是加新功能。
