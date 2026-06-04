# v0.1.2 Task Package Self-Containment Patch

## 问题

v0.1.1 DS real relay 测试暴露：executor（Claude Code）的 sandbox 限制了文件访问范围，外部 dispatch 文件 `communication-substrate-mvp/dispatch/ds_relay_verify_dispatch_v0_1_1.md` 无法被 executor 读取。

sandbox 没有失效——它正确地拦截了外部访问。问题是任务物料不在 task 包内。

## 目标

每个 task_dir 自包含——executor 只读 `<task_dir>/**`，不依赖 sandbox 外部路径。

## 修法

在 `init` 阶段 materialize 任务物料：

```
init 执行后，task_dir 结构：
sandbox/<task_name>/
├── dispatch/
│   ├── task_config.yaml      ← 已存在（init 写入）
│   ├── dispatch.md            ← [新增] 从外部 dispatch_path 复制
│   └── system_prompt.md       ← [新增] 从外部 system_prompt_path 复制（如果配置了）
├── runtime/
├── logs/
└── summary/
```

executor 只需读 `<task_dir>/dispatch/dispatch.md` 获取任务说明。

## 改动范围

- `tools/pm_runtime/relay/cli.py` — init 命令增加 materialize 步骤
- `tools/pm_runtime/relay/relay_runner.py` — 执行时 dispatch 路径指向 task_dir 内副本

## 不改

- sandbox 边界不变
- task_config.yaml 格式不变
- Hermes compat 逻辑不变
- 不让 executor 读外部目录
