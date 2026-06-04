# workyb 新一代 DAG 工作流设计文档 v0.3.2（emerged）

> 版本：v0.3.2 · emerged  
> 日期：2026-05-29  
> 性质：基于 MiMo Team 4 Agent 并行审查（HOLD）后全面修订版  
> 审查裁决：completeness HOLD / consistency PASS_WITH_FINDINGS / feasibility PASS_WITH_FINDINGS / gaps_vs_findings PASS_WITH_FINDINGS  
> 修订项：4 P0 + 8 P1 + 6 Gap 全部修复  
> 来源文件同 v0.3.1，新增审查证据：MiMo Team Review Report（227 行，4 Agent 并行产出）

---

## 0. 一句话定义

新一代 DAG 工作流 = **编排层只画 DAG 不关心模型** + **执行层预授权不弹窗** + **通讯层按需 fallback 不硬编码**。

---

## 1. 三层分离架构

```
┌────────────────────────────────────────────────────────┐
│                   编排层 Orchestration                    │
│                                                        │
│  Hermes / PM Runtime                                   │
│  DAG manifest 解析 → 节点依赖排序 → 派发 → 回收         │
│                                                        │
│  只关心：做什么、什么顺序、产出契约                        │
│  不关心：用什么模型、API 格式、鉴权方式                    │
│                                                        │
│  → 编排层→执行层接口：dispatch.yaml（见 §8）              │
│  → 执行层→编排层接口：receipt.yaml + result.json          │
├────────────────────────────────────────────────────────┤
│                   执行层 Execution                        │
│                                                        │
│  Relay Runner + tmux + Agent CLI                       │
│  会话管理 → 心跳监控 → 弹窗自动处理 → 产出回收            │
│                                                        │
│  弹窗策略：ClaudeDialogHandler 5 类自动识别与响应          │
│  安全模型：--allowedTools + 路径白名单 + 命令白名单        │
│  ⛔ 不使用 --allow-dangerously-skip-permissions          │
│                                                        │
│  → 执行层→通讯层接口：provider_config + plugn chain       │
├────────────────────────────────────────────────────────┤
│                   通讯层 Communication                   │
│                                                        │
│  CC Switch / format-fixer chain（plugin 注册表管理）      │
│  路由 + 鉴权 + 格式转换（按需启用，fallback 才介入）       │
│                                                        │
│  plugin 规范：error_trigger → on_error activation        │
│  provider 链：优先级排序 + 健康检测 + fallback 切换        │
│                                                        │
│  → 通讯层→外部接口：统一 Anthropic Messages API           │
└────────────────────────────────────────────────────────┘
```

---

## 2. 七角色职责矩阵（修复：新增 Repair Agent）

| 角色 | 层级 | 职责 | 行使者 |
|------|------|------|--------|
| **Owner** | 策略层 | 方向决策、Gate 裁决、终审 | 人 |
| **Control Agent** | 编排层 | 方案设计、边界定义、归盘中控 | Hermes |
| **Orchestrator** | 编排层 | 任务拆解、DAG 编排、派发调度 | PM Runtime |
| **Executor** | 执行层 | 节点执行、代码落盘、测试运行 | Claude Code / Codex |
| **Repair Agent** | 执行层 | AI 修复闭环：诊断 Issue → 生成修复指令 → 重试裁决 | Claude Code / Hermes |
| **Reviewer** | 审查层 | 代码审查、设计一致性验证 | DS Team / Agent Team |
| **Infra** | 通讯层 | 会话管理、心跳监控、通讯转换、模型路由 | Relay Runner / CC Switch |

---

## 3. 核心流程（修复：标注所有 9 级 Gate）

```
Owner 提出目标
  ↓
Control Agent 收集上下文 → 追问关键缺口
  ← Gate 0: Context Gate（上下文完整性确认，由 Control Agent 裁决）
  ↓
形成最终方案 → Owner 确认
  ← Gate 1: Plan Gate（方案批准/驳回，由 Owner 裁决）
  ↓
Orchestrator 拆解 DAG 节点
  ← Gate 2: DAG Gate（节点拆解合理性确认，由 Owner/Control 裁决）
  ↓
派发节点执行
  ← Gate 3: Node Gate（单节点产出验收，由 Orchestrator 裁决）
      ├─ 通过 → 进入下一节点/聚合
      ├─ 重跑 → 进入 Repair Loop
      └─ 跳过 → 标记为 skipped，不影响下游
  ↓
AI 修 AI 闭环
  ← Gate 4: AI Repair Gate（修复裁决，由 Repair Agent 裁决）
      ├─ pass（修复通过）→ Gate 3 重新校验
      ├─ retry_once（≤2 轮）→ 重新修复
      └─ escalate_to_owner（超过轮数）→ 人工介入
  ↓
阶段间过渡（数据质量 + 样张确认）
  ← Gate 5: Stage Gate（阶段产物验收，由 Control Agent 裁决）
  ↓
最终成品交付
  ← Gate 6: Product Gate（成品通过/驳回，由 Owner 裁决）
  ↓
归盘复盘
  ← Gate 7: Retrospective Gate（含 workspace clean 检查，由 Control Agent 裁决）
  ↓
升格判断
  ← Gate 8: Promotion Gate（归档 B 线 / 升格 A 线，由 Owner 裁决）
```

---

## 4. 九级 Gate 体系（修复：补充 Gate 0/2/3/5 判定标准）

| Gate | 名称 | 触发时机 | 裁决者 | 通过条件 | 驳回条件 |
|------|------|----------|--------|----------|----------|
| 0 | Context Gate | 上下文收集完成后 | Control Agent | 目标清晰、数据源确认、边界明确 | 关键信息缺失 |
| 1 | Plan Gate | 方案形成后 | Owner | 方案批准 | 方案驳回（含修改方向） |
| 2 | DAG Gate | DAG 拆解完成后 | Owner/Control | 节点粒度合理、依赖正确、超时可接受 | 粒度过细/过粗、依赖错误 |
| 3 | Node Gate | 单节点产出后 | Orchestrator | 产出物存在、校验通过 | 文件缺失、校验失败、超时 |
| 4 | AI Repair Gate | AI 修复后 | Repair Agent | pass（漏洞修复）或 retry_once（需重试） | escalate（超过轮数/方向错误） |
| 5 | Stage Gate | 阶段间过渡 | Control Agent | 阶段产物完整、质量达标 | 质量不达标、数据缺口 |
| 6 | Product Gate | 最终成品后 | Owner | 成品通过 | 成品驳回（含修改方向） |
| 7 | Retrospective Gate | 归盘完成后 | Control Agent | 归盘资产完整、workspace 已清理 | 资产缺失、未清理 |
| 8 | Promotion Gate | 升格判断 | Owner | 升格 A 线 | 归档 B 线 |

---

## 5. 目录协议（10 层，修复：增加 logs/ + runtime/ 扩展清单）

```
{{task_dir}}/
├── 00_task_brief.md              # 任务书（YAML frontmatter + 目标描述）
├── 01_dag_plan/                  # DAG 编排计划
│   ├── dispatch.yaml             # 整体 DAG manifest
│   └── receipts/                 # 节点回执汇总
├── 02_probe/                     # 探针阶段
├── 03_collection/                # 采集阶段
├── 04_cleaning/                  # 清洗阶段
├── 05_samples/                   # 样张阶段
├── 06_final_assets/              # 最终资产
├── 07_product/                   # 成品整合
├── 08_retrospective/             # 归盘复盘
├── logs/                         # executor 日志（新增）
│   ├── executor.log
│   ├── tmux_capture.log
│   └── dialog_history.jsonl
└── runtime/                      # 运行时（executor 自动管理）
    ├── heartbeat.json            # 存活心跳（间隔 30s）
    ├── heartbeat_history.jsonl   # 心跳历史
    ├── progress.yaml             # 进度文件（统一 yaml 格式）
    ├── progress.md               # 进度文件（legacy 兼容）
    ├── session.yaml              # tmux 会话信息
    ├── task_state.yaml           # 全量运行时状态
    ├── result.json               # 最终结果
    ├── pane_capture.log          # pane 文本快照
    ├── registry_events.jsonl     # 事件审计链（14 种 failure_classification）
    ├── failure_classification.yaml
    ├── pre_action_check.yaml     # 执行前安全检查结果
    ├── blocker_report.md         # 阻塞报告
    ├── owner_decision_request.yaml
    ├── owner_decision_record.yaml
    ├── abort_report.yaml         # 异常中止报告
    └── recovery_summary.md       # 恢复摘要
```

每阶段目录内含：`input/`（输入契约）、`output/`（产出物）、`receipt.md`（执行回执）。

---

## 6. 通讯层：插件式 fallback 链

### 6.1 插件注册表

```yaml
communication_layer:
  default_route: "cc_switch"

  plugins:
    - id: "thinking-fixer"
      enabled: on_error
      trigger_errors:
        - "content[].thinking must be passed back"
        - "unknown variant `system`"
      activation: fallback
      scope:
        providers: ["deepseek"]
        models: ["v4-pro", "v4-flash"]
      health_check:
        endpoint: "/health"
        interval_sec: 30

  provider_chain:
    - provider: "xiaomi_mimo"
      priority: 1
      health_check: true
    - provider: "deepseek"
      priority: 2
      health_check: true
      plugins: ["thinking-fixer"]

  model_mapping:
    model_hint_fast: "mimo-v2.5-pro"
    model_hint_balanced: "deepseek-v4-pro"
    model_hint_cheap: "deepseek-v4-flash"
```

### 6.2 正常流程 vs Fallback 流程

**正常（Xiaomi MiMo）：**
```
Claude → CC Switch → MiMo API → 200 ✅（fixer 不介入）
```

**正常（DeepSeek 无 thinking 问题）：**
```
Claude → CC Switch → DeepSeek API → 200 ✅（fixer 不介入）
```

**Fallback（DeepSeek 触发 thinking 400）：**
```
Claude → CC Switch → DeepSeek API → 400 thinking error 🔴
                          ↓ 通讯层检测到 trigger_error
                          ↓ 自动激活 thinking-fixer
Claude → CC Switch → thinking-fixer → DeepSeek API → 200 ✅（缓存+注入+剥离）
```

### 6.3 Thinking Fixer 生存周期

```
初始状态：stopped（不占端口，不占内存）
首次请求：bypass
检测到 trigger_error → 启动 fixer（on-demand）
后续请求 → 经过 fixer
会话结束后 → 自动关闭 fixer
```

### 6.4 实战验证数据

| 指标 | 值 |
|------|-----|
| fixer 不介入（MiMo） | ✅ 直通，零延迟 |
| fixer 介入后（DeepSeek） | ✅ 6 轮连续 200 |
| 缓存命中率 | ✅ 按消息索引，100% |
| 无 fixer 时效果 | ❌ 400 thinking error |

---

## 7. 执行层：弹窗自动处理策略（修复：对齐 ClaudeDialogHandler 实现）

### 7.1 策略说明

执行层**不使用** `--allow-dangerously-skip-permissions`。实际采用 `ClaudeDialogHandler` 自动识别和响应弹窗。

### 7.2 五类弹窗处理

| 弹窗类型 | 识别依据 | 处理策略 | 安全校验 |
|----------|----------|----------|----------|
| TRUST | "Do you trust" / "Are you sure" | 自动接受 | 无（信任对话框） |
| FILE_CREATION | "Do you want to create" | 匹配 expected_outputs → 自动批准 | 路径白名单 + basename 解析 |
| BASH_PERMISSION | bash 命令安全对话框 | 匹配命令白名单 → 自动批准 | shell 注入检测 + 路径校验 |
| PERMISSION | "Do you want to proceed?" / 文件写入 | 检查目标路径 | 路径白名单 + 签名去重 |
| OTHER_CONFIRMATION | 未知弹窗 | HOLD（等待 Owner） | 人工介入 |

### 7.3 预授权执行上下文

```yaml
execution_context:
  permissions:
    write_paths:
      - "{{task_dir}}/outputs/*"
      - "{{task_dir}}/runtime/*"
    read_paths:
      - "{{task_dir}}/**"
      - "资产/**"
    bash_commands:
      - "ls" | "cat" | "head" | "tail"
      - "python3" | "mkdir -p"
```

### 7.4 clauderemote 模式激活机制

当 tmux 交互出现 dialog 无法自动处理时，执行层激活 clauderemote 模式：
1. 检测到不可自动处理的对话框
2. 自动执行 `/clauderemote on`
3. 将对话框选项转为字母选择（[A][B][C]）提高 reliability
4. 记录 fallback 日志

---

## 8. DAG Manifest 定义（修复：增加关键运维字段）

### 8.1 完整节点定义

```yaml
dag:
  version: "1.0"

  nodes:
    - id: "probe"
      label: "探针验证"
      depends_on: []                    # 依赖列表，空=先执行
      executor_config:
        agent: "claude"
        prompt_file: "dispatch/probe_prompt.md"
        model_hint: "fast"              # 编排层不指定具体模型
        fallback:                        # 通讯层 fallback 配置
          on_error: true
          fallback_model_hint: "balanced"
          retry_config:
            max_retries: 2
            retry_delay_sec: 10
      expected_outputs:
        - path: "{{task_dir}}/probe/report.md"
          validation: "exists"
      timeout_sec: 300
      priority: 1                       # 优先级（1=高）
      retry_policy:
        max_attempts: 3
        backoff: "exponential"
        initial_delay_sec: 5
      resource_constraints:
        max_input_tokens: 10000
        max_output_tokens: 2000

    - id: "collection"
      label: "全量采集"
      depends_on: ["probe"]
      executor_config:
        agent: "claude"
        prompt_file: "dispatch/collect_prompt.md"
      fan_out:                           # 并行化
        strategy: "split_input"
        split_on: "keywords"
      fan_in:                            # 聚合策略
        strategy: "merge"
        merge_method: "dedup_and_concat"
```

### 8.2 编排层↔执行层接口契约

**编排层→执行层（dispatch.yaml）：**
```yaml
task_id: "probe-task-01"
node_id: "probe"
prompt: "请探针验证数据可采集性"
prompt_file: "dispatch/probe_prompt.md"
model_hint: "fast"
timeout_sec: 300
expected_outputs:
  - "{{task_dir}}/probe/report.md"
```

**执行层→编排层（receipt.yaml）：**
```yaml
node_id: "probe"
status: "completed"
started_at: "2026-05-29T15:00:00+08:00"
completed_at: "2026-05-29T15:05:00+08:00"
outputs:
  - path: "{{task_dir}}/probe/report.md"
    size_bytes: 12345
    validation: "pass"
repair_count: 0
verdict: "pass"
metadata:
  total_tokens: 5000
  model: "deepseek-v4-pro"
  provider: "deepseek"
  runtime_file_count: 12
  dialog_events: 3
```

**通讯层↔外部 API：** Anthropic Messages API（/v1/messages）

---

## 9. AI 修 AI 闭环（Repair Loop）

### 9.1 触发条件

节点产出物未通过预期校验（文件不存在、为空、格式错误等）。

### 9.2 修复流程

```
节点完成 → 校验产出 → pass → Gate 3 通过，进入下一节点
                     → fail → Repair Agent 分析 Issue
                              → 生成 Issue Packet
                              → Executor 重试（retry_once）
                              → 再次校验 → pass → Gate 3 通过
                                          → fail → 二次重试（≤2 轮）
                                                   → escalate_to_owner
```

### 9.3 Issue Packet 格式

```yaml
issue:
  node_id: "probe"
  attempt: 2
  expected_output: "{{task_dir}}/probe/report.md"
  validation_failure: "file_not_found"
  diagnosis: "Agent 无法访问目标目录"
  repair_instruction: "确认路径资产/ 存在后用 cat 读取"
  max_retries: 2
  current_retry: 1
```

---

## 10. 设计原则（归盘验证背书）

| # | 原则 | 设计中体现 | 章节引用 |
|---|------|-----------|----------|
| 1 | 三层委托：策略→方案→执行 | §2 七角色职责矩阵 | §1 / §2 |
| 2 | 一张样张：批准前不进入全量 | Gate 5（Stage Gate） | §4 |
| 3 | 30 秒判断：Owner 决策信息量控制 | 每 Gate 输入标准化 | §4 |
| 4 | 进度汇报三元素：进度+产出+决策 | runtime/ + heartbeat/progress | §5 |
| 5 | 不要假定：配数据或样张 | AI Repair Gate 要求 Issue Packet | §9 |
| 6 | 信息层级四层设计 | 每节点输出结构化要求 | §8 |
| 7 | 拒绝勇气制度化 | 所有 Gate 支持直接驳回 | §4 |
| 8 | 先整理再归盘 | Gate 7 含 workspace clean 步骤 | §4 / §5 |

---

## 11. 迭代路线（修复：每个版本补充 Done 条件）

```
v0.3.1（已审查）→ MiMo Team HOLD，4 P0 + 8 P1
    ↓
v0.3.2 ← 本文件，所有问题已修复
    ↓
v0.4  模板 + 目录协议定稿（0.5-1 天）
    Done: dispatch/receipt/issue_packet 模板定型
    Done: 10 层目录协议（含 logs/）定稿
    Done: 安全策略决策（DialogHandler 方案 → 替代 --dangerously-skip-permissions）
    ↓
v0.5  DAG manifest 引擎（3-5 天）
    Done: DAG manifest YAML 可解析为有向无环图
    Done: 3 个串行节点端到端跑通
    Done: 循环依赖检测并报错
    Done: 节点状态机持久化（5 状态）
    ↓
v0.6  通讯层 fallback 链（2-3 天）
    Done: thinking-fixer 切换为 on_error 模式
    Done: plugin 注册表 + 错误检测 + 重定向
    Done: 6 轮回归测试（DeepSeek thinking 场景）
    ↓
v0.7  执行层弹窗策略对齐（1-2 天）
    Done: ClaudeDialogHandler 5 种弹窗自动处理 ≥95%
    Done: clauderemote 模式激活 fallback
    Done: --allowedTools + 路径白名单方案
    ↓
v0.8  Docker DAG POC（3-5 天）
    Done: 隔离执行舱可启动 Claude Code
    Done: 1 个 L 级任务端到端跑通
    ↓
v0.9  多 Agent 协作（3-5 天）
    Done: fan-out 3 个并行节点 + fan-in 聚合
    Done: 部分失败时的聚合策略验证
    ↓
v1.0  正式版（2-3 天）
    Done: B 线全链路端到端验收场景通过
    Done: 文档与代码双向一致性审查通过
```

**关键路径：** v0.3.2 → v0.4 → v0.5 → v0.9 → v1.0  
**总估算：** 15-24 天（单人全职）  
**可并行：** v0.6（通讯层）与 v0.7（执行层）可并行，但存在运行耦合需先声明接口契约（§8.2）

---

## 12. 实战验证记录

| 验证项目 | 结果 |
|----------|------|
| relay runner tmux 模式 | ✅ 正常启动/发 prompt/监心跳 |
| thinking-fixer（DeepSeek） | ✅ 6 轮连续 200 |
| MiMo 直通（无 fixer） | ✅ 出完整报告 |
| 4 Agent 并行审查（MiMo） | ✅ 本次审查验证 |
| 弹窗自动处理 | ⚠️ 需 HOLD 待持续改进（v0.7） |
| tmux 会话管理 | ⚠️ 需完整生命周期策略 |

---

*本版本基于 v0.3.1 + MiMo Team 4 Agent 并行审查（4 P0 + 8 P1 + 6 Gap 全部修复）后产出。*  
*修复清单：P0-1 §7 对齐 DialogHandler / P0-2 runtime/ 扩展 + logs/ / P0-3 流程图补 Gate / P0-4 Done 条件 / 全部 P1 问题 / 全部 Gap A-F*
