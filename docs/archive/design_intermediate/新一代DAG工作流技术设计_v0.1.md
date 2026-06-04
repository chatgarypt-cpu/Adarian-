# workyb 新一代 DAG 工作流技术设计 v0.1

> 基于 2026-05-29 全链路实战验证总结  
> 包含：三层分离架构、通讯层 fallback 机制、执行层预授权、落地路径  
> 实战案例：relay runner 派发 + DeepSeek thinking-fixer + MiMo 模型切换

---

## 一、三层分离架构

```
┌────────────────────────────────────────────────────────┐
│                   编排层 Orchestration                    │
│                                                        │
│  Hermes / PM Runtime                                   │
│  DAG manifest 解析 → 节点依赖排序 → 派发 → 回收         │
│  只关心：做什么、什么顺序、产出契约                        │
│  不关心：用什么模型、API 格式、鉴权方式                    │
├────────────────────────────────────────────────────────┤
│                   执行层 Execution                        │
│                                                        │
│  Relay Runner + tmux + Agent CLI                       │
│  会话管理 → 心跳监控 → 弹窗处理 → 产出回收                │
│  维护执行上下文（预授权路径、沙箱边界）                     │
├────────────────────────────────────────────────────────┤
│                   通讯层 Communication                   │
│                                                        │
│  CC Switch / format-fixer chain                         │
│  路由 + 鉴权 + 格式转换（按需启用）                       │
│  天然支持多 provider 切换、fallback 链                    │
└────────────────────────────────────────────────────────┘
```

**核心原则：上层不知道下层的存在。编排层不知道走的什么模型，执行层不知道 API 格式怎么转换。**

---

## 二、通讯层：插件式 fallback 链

### 2.1 设计规则

通讯层是一个 filter chain，每个插件有状态：

```yaml
communication_layer:
  default_route: "cc_switch"            # 默认走 CC Switch 路由
  
  plugins:
    - name: thinking-fixer
      enabled: on_error                  # 仅在检测到 specific error 时激活
      trigger_errors:
        - "content[].thinking must be passed back"
        - "unknown variant `system`"
      activation: fallback               # 触发后：重试一次带 fixer 的请求
      upstream: "{{default_route}}"      # 错误发生后，重定向到 fixer
      scope:                             # 只对指定 provider/model 生效
        providers: ["deepseek"]
        models: ["v4-pro", "v4-flash"]
```

### 2.2 正常流程 vs Fallback 流程

**正常（MiMo）**：
```
Claude → CC Switch (15721) → MiMo API → 正常返回 ✅
```

**正常（DeepSeek 无 thinking 问题）**：
```
Claude → CC Switch (15721) → DeepSeek API → 正常返回 ✅
```

**Fallback（DeepSeek 触发 thinking 400）**：
```
Claude → CC Switch (15721) → DeepSeek API → 400 thinking error 🔴
                                    ↓ detect error
                                    ↓ activate thinking-fixer
Claude → CC Switch (15721) → thinking-fixer (4569) → DeepSeek API → 200 ✅
                                    ↑ 缓存 + 注入 + 剥离 thinking 块
```

**效果**：无 thinking 问题的模型全程无感，触发错误的模型自动 fallback。

### 2.3 Thinking Fixer 的生存周期

```
初始状态：stopped
首次请求：bypass（不经过 fixer）
检测到 trigger_error → 启动 fixer（延迟 0 启动，节省资源）
后续同一会话所有请求 → 经过 fixer
会话结束、或连续 N 次无 error → 自动关闭 fixer
```

---

## 三、执行层：预授权执行上下文

### 3.1 当前痛点

今天 relay runner 两次卡在确认弹窗：
1. `Do you want to create workflow_authority_review_zh.md?`
2. `Do you want to proceed? [file write permission]`

每次都要手动 `tmux send-keys` 或 `tmux attach` 去确认。

### 3.2 解决方案

在启动 Claude Code 时通过 `--allowedTools` 和 `--allow-dangerously-skip-permissions` 预授权：

```yaml
execution_context:
  task_id: "agent-orchestration-demo-01"
  sandbox: "{{task_dir}}"
  
  permissions:
    write_paths:
      - "{{task_dir}}/outputs/*"         # 写入产出
      - "{{task_dir}}/runtime/*"         # 运行时文件
    read_paths:
      - "{{task_dir}}/**"                # 读任务目录
      - "资产/**"                        # 读资产目录
    bash_commands:
      - "ls"
      - "cat"
      - "head"
      - "tail"
      - "python3"
      - "mkdir -p"
```

执行层在启动 claude 时注入：
```bash
claude --allowedTools "Edit,Write,Bash,BashReadOnly,Read,Search" \
       --allow-dangerously-skip-permissions \
       -p "{{prompt}}"
```

---

## 四、编排层：DAG Manifest 定义

### 4.1 最小 DAG 节点定义

```yaml
dag:
  version: "1.0"
  
  nodes:
    - id: "probe"
      label: "探针验证"
      depends_on: []                              # 无依赖，先执行
      executor_config:
        agent: "claude"
        prompt_file: "dispatch/probe_prompt.md"    # prompt 模板
        model_hint: "fast"                         # 编排层不指定具体模型
      expected_outputs:
        - path: "{{task_dir}}/probe/report.md"
          validation: "exists"
      timeout_sec: 300

    - id: "collection"
      label: "全量采集"
      depends_on: ["probe"]                        # 依赖探针完成
      executor_config:
        agent: "claude"
        prompt_file: "dispatch/collect_prompt.md"
      expected_outputs:
        - path: "{{task_dir}}/collection/data.csv"
          validation: "non_empty"
        - path: "{{task_dir}}/collection/log.md"
          validation: "exists"
      timeout_sec: 600
      fan_out:                                     # 并行化
        strategy: "split_input"
        split_on: "keywords"

    - id: "sample_gate"
      label: "样张 Owner 确认门"
      depends_on: ["collection"]
      executor_config:
        agent: "hermes"                            # 样张门走 Hermes（交互式确认）
        prompt_file: "dispatch/sample_gate_prompt.md"
      gate: true                                   # 阻塞后续节点直到 Owner 确认
```

### 4.2 节点状态机

```
pending → ready → dispatched → running → completed → gate(可选) → next
                              → failed   → retry(可选) → running
                                         → hold(等待 Owner)
```

---

## 五、落地路径

### Phase 1（今天就能做）

| # | 事项 | 说明 |
|---|------|------|
| 1 | DAG manifest 格式定稿 | YAML schema + 节点定义 + 依赖声明 |
| 2 | 执行层预授权 | relay runner 启动 claude 时注入 `--allowedTools` |
| 3 | 通讯层 fallback 机制设计 | 插件注册 + 错误检测 + 重定向 |

### Phase 2（本周）

| # | 事项 | 说明 |
|---|------|------|
| 4 | thinking-fixer 改为 fallback-only | 从"始终在线"改为"检测到 error 后激活" |
| 5 | Relay Runner 增加 DAG 解析器 | 读 manifest → 按依赖排序派发 |
| 6 | 节点回收 + 产出契约校验 | 检查 expected_outputs 是否存在 |

### Phase 3（下周）

| # | 事项 | 说明 |
|---|------|------|
| 7 | 并行 fan-out/fan-in 实现 | 多个独立节点同时派发 |
| 8 | Gate 节点（Owner 确认门） | 阻塞等待 Owner 确认 |
| 9 | 节点重试 + 失败隔离 | 单节点失败不阻塞无关节点 |

### Phase 4（两周后）

| # | 事项 | 说明 |
|---|------|------|
| 10 | Docker DAG Agent Team POC | 隔离执行舱 |
| 11 | 通讯层插件市场 | 社区贡献的 format-fixer |
| 12 | 跨会话 DAG 恢复 | tmux session attach/detach 管理 |

---

## 六、今天实战验证的关键数据

| 指标 | 值 |
|------|-----|
| relay runner 派发成功率 | ✅ tmux 模式可正常启动、发 prompt、收心跳 |
| thinking-fixer 缓存正确率 | ✅ 6 轮连续 200（13:05:38-13:06:11） |
| MiMo 直通成功率 | ✅ 无 thinking 错误，跑完全程出报告 |
| CC Switch 路由管理 | ✅ settings.json 自动接管，provider endpoint 可配置 |
| 阻塞点 | ❌ 权限弹窗需手动确认（Phase 1 修复） |
| 阻塞点 | ❌ thinking-fixer 当前始终在线（Phase 2 改为 fallback-only） |

---

## 七、一句话总结

新一代 DAG 工作流 = **编排层只画 DAG 不关心模型** + **执行层预授权不弹窗** + **通讯层按需 fallback 不硬编码**。thinking-fixer 只在检测到 DeepSeek 的 thinking 400 错误时才激活，其余模型全程无感。
