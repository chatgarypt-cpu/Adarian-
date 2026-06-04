# Owner Directive — PM Runtime Task-Local Repair Boundary

> 来源：Owner Gate
> 日期：2026-05-19
> 适用：Hermes-PM 在 audit/tasks/active/<task_id>/ 下的通讯修复权限

## 允许范围（路径白名单）

- audit/tasks/active/<task_id>/scripts/
- audit/tasks/active/<task_id>/runtime/
- audit/tasks/active/<task_id>/logs/
- audit/tasks/active/<task_id>/summary/
- audit/tasks/active/<task_id>/ds/ 或 dispatch/ 下的结果回收文件

## 允许动作（仅限以下 5 类）

1. 修复 relay_runner / stdout / JSON extraction / heartbeat / progress / result 写入问题
2. 重新提取已完成 agent 输出
3. 补写 runtime_note / process_issue
4. 生成 pm_runtime_summary
5. 在不改变任务目标、不改变 prompt、不改变 verdict 选项的前提下重试通讯通道

## 禁止范围（路径黑名单）

- src/
- tests/
- main.py
- config.py
- docs/skills/workflow_core.md
- workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
- docs/iterations/
- docs/contracts/
- any prompt / schema / phase implementation files
- git commit

## 硬规则

1. Hermes 可以修通讯通道，不能修项目源码。
2. Hermes 可以修 relay，不可以修业务逻辑。
3. Hermes 可以回收报告，不可以修改报告结论。
4. Hermes 可以标记 process_issue，不可以降级 blocker。
5. Hermes 如判断必须修改禁止范围，必须立即 HOLD 回 Owner-Control。
6. 所有 task-local repair 必须在 pm_runtime_summary 中披露修改文件、修改原因、影响范围和是否改变任务语义。
