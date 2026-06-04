# PM Runtime Relay — 已知问题：临时心跳中台设计

> 记录日期：2026-05-21
> 记录方：Hermes-PM
> 位置：audit/workflow_v4.0/ds team context/

## 问题

当前 relay_runner.py 的心跳/进度/结果机制是一个**临时脚手架**，不是正式 PM Runtime 通讯层组件。

## 具体表现

1. **timeout 硬编码**：每次新任务需手动修改 timeout 值（已发生：yaml-review 任务 900s 超时，手动改为 1500s 重跑）
2. **超时后无 partial output**：subprocess.TimeoutExpired 触发后，所有已产生的 stdout 丢失，无法恢复
3. **无重试机制**：超时后只能手动清理 relay_logs 并重新启动
4. **心跳格式不统一**：heartbeat 用 txt、progress 用 md、result 用 json，无统一 schema
5. **任务内脚本**：每个任务目录复制一份 relay_runner.py 并手动修改，非全局可复用组件
6. **无集中监控**：Hermes-PM 通过 read_file 轮询各任务的心跳文件，无统一仪表盘
7. **会话绑定**：relay 是 Hermes 会话的子进程（subprocess.Popen），Hermes 会话断开后进程可能变孤儿，无人回收。重启会话后无法恢复对运行中任务的监控
8. **被动心跳**：写文件等人读，不是主动推送。Hermes 必须轮询，断线后完全失去状态感知
9. **无持久注册表**：没有 task registry 记录哪些任务在跑、PID、启动时间。会话重启后 Hermes 无法知道有哪些遗留任务需要回收

## 建议改进方向

1. relay_runner.py 抽象为全局 PM Runtime 组件（`pm_runtime/skills/` 下）
2. 通过命令行参数或 config 文件传入 task_id、timeout 等
3. heartbeat/progress/result 统一为结构化格式（JSON/YAML）
4. 超时时保留 partial stdout
5. 支持自动重试（带退避）
6. 集中状态文件 + 持久 task registry，支持会话重启后恢复监控
7. relay 进程与 Hermes 会话解耦（daemon 化或独立进程管理）
8. 主动推送通知（而非被动文件轮询）

## 当前绕过方案

- 超时后手动增加 timeout + 清理旧日志 + 重新启动
- relay_runner.py 每次从上一个任务复制并手动修改参数

---

本问题已同步记录在：
- `audit/tasks/active/control-agent-governance/pm_runtime_relay_context_packet_2026-05-21.md` §8
