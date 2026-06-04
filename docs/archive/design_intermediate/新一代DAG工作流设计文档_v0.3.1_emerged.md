# workyb 新一代 DAG 工作流设计文档 v0.3.1（emerged）

> 版本：v0.3.1 · emerged  
> 日期：2026-05-29  
> 性质：v0.3 蓝图 + v0.2 §12 补缺 + 能力蓝图参考 + 归盘原则背书的整合设计稿  
> 来源文件：  
>   - `B_line_lightweight_production_DAG_v0.3_long_task_orchestration_blueprint.md`（流程骨架）  
>   - `B线轻量生产DAG工作流_上下文与报告_v0.2_Hermes_ClaudeCode修订版.md`（架构图 + 角色分工）  
>   - `B_line_lightweight_pipeline_capability_blueprint_v0.1.md`（能力清单 + 工具参考）  
>   - `第三次作业全流程归盘分析_Control补充版.md`（设计原则背书）  
> 审查验证方式：两份独立审查报告交叉验证（relay runner 派发 562 行 + 10 Agent 并审 230 行）  
> 设计验证实战案例：relay runner 真实派发审查任务（通过 tmux + Claude Code + MiMo/DeepSeek 双模型验证）  
> 定位：本文件即为本次设计整合的 emerged 版本产出

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
├────────────────────────────────────────────────────────┤
│                   执行层 Execution                        │
│                                                        │
│  Relay Runner + tmux + Agent CLI                       │
│  会话管理 → 心跳监控 → 弹窗处理 → 产出回收                │
│                                                        │
│  维护执行上下文（预授权路径、沙箱边界）                     │
├────────────────────────────────────────────────────────┤
│                   通讯层 Communication                   │
│                                                        │
│  CC Switch / format-fixer chain                         │
│  路由 + 鉴权 + 格式转换（按需启用，fallback 才介入）       │
│                                                        │
│  天然支持多 provider 切换、fallback 链                    │
└────────────────────────────────────────────────────────┘
```

**核心原则**：上层不知道下层的存在。编排层不知道走的什么模型，执行层不知道 API 格式怎么转换。

---

## 2. 六角色职责矩阵

| 角色 | 所属层级 | 职责 | 行使者 |
|------|----------|------|--------|
| **Owner** | 策略层 | 方向决策、Gate 裁决、终审 | 人 |
| **Control Agent** | 编排层 | 方案设计、边界定义、归盘中控 | Hermes / 架构 Agent |
| **Orchestrator** | 编排层 | 任务拆解、DAG 编排、派发调度 | Hermes / PM Runtime |
| **Executor** | 执行层 | 节点执行、代码落盘、测试运行 | Claude Code / Codex |
| **Reviewer** | 审查层 | 代码审查、设计一致性验证 | DS Team / Agent Team |
| **Infra** | 通讯层 | 会话管理、心跳监控、通讯转换、模型路由 | Relay Runner / CC Switch |

---

## 3. 核心流程

```
Owner 提出目标
  ↓
Control Agent 收集上下文 → 追问关键缺口（Context Completion）
  ↓
形成最终方案 → Owner 确认（Gate 1: Plan Gate）
  ↓
Orchestrator 拆解 DAG 节点（Gate 2: DAG Gate）
  ↓
按依赖顺序派发执行节点
  ├─ 串行节点：依赖前置完成后执行
  ├─ 并行节点：fan-out 同时派发，fan-in 聚合
  └─ Gate 节点：阻塞等待 Owner 确认
  ↓
AI 修 AI 闭环（Gate 4: AI Repair Gate）
  └─ pass / retry_once(最多2轮) / escalate_to_owner
  ↓
分阶段验收（Gate 5: Stage Gate / Gate 6: Product Gate）
  ↓
归盘复盘（Gate 7: Retrospective Gate）
  ↓
升格判断（Gate 8: Promotion Gate）→ B 线资产 or 升格 A 线
```

---

## 4. 九级 Gate 体系

| Gate | 名称 | 触发时机 | 裁决者 | 输出 |
|------|------|----------|--------|------|
| 0 | Context Gate | 上下文收集完成后 | Control Agent | 上下文完整性确认 |
| 1 | Plan Gate | 方案形成后 | Owner | 方案批准/驳回 |
| 2 | DAG Gate | DAG 拆解完成后 | Owner/Control | 节点拆解批准 |
| 3 | Node Gate | 单节点产出后 | Orchestrator | 节点通过/重跑/跳过 |
| 4 | AI Repair Gate | AI 修复后 | AI Agent | pass / retry / escalate |
| 5 | Stage Gate | 阶段间过渡 | Control Agent | 阶段产物验收 |
| 6 | Product Gate | 最终成品后 | Owner | 成品通过/驳回 |
| 7 | Retrospective Gate | 归盘完成后 | Control Agent | 归盘资产评定 |
| 8 | Promotion Gate | 升格判断 | Owner | 归档 B 线 / 升格 A 线 |

---

## 5. 目录协议（9 层标准）

```
{{task_dir}}/
├── 00_task_brief.md           # 任务书（YAML frontmatter + 目标描述）
├── 01_dag_plan/               # DAG 编排计划
│   ├── dispatch.yaml          # 整体 DAG manifest
│   └── receipts/              # 节点回执
├── 02_probe/                  # 探针阶段
├── 03_collection/             # 采集阶段
├── 04_cleaning/               # 清洗阶段
├── 05_samples/                # 样张阶段
├── 06_final_assets/           # 最终资产
├── 07_product/                # 成品整合
├── 08_retrospective/          # 归盘复盘
└── runtime/                   # 运行时（executor 自动管理）
    ├── heartbeat.json
    ├── progress.md
    ├── result.json
    └── pane_capture.log
```

每阶段目录内含：`input/`（输入契约）、`output/`（产出物）、`receipt.md`（执行回执）。

---

## 6. 通讯层：fallback-only 插件链

### 6.1 设计规则

通讯层是一个 filter chain，每个插件有状态。**插件默认不激活，仅在检测到特定错误后 fallback 时启用。**

```yaml
communication_layer:
  default_route: "cc_switch"            # 默认走 CC Switch 路由

  plugins:
    - name: thinking-fixer
      enabled: on_error                  # 仅在检测到错误时激活
      trigger_errors:
        - "content[].thinking must be passed back"
        - "unknown variant `system`"
      activation: fallback               # 触发后：启动 fixer，重试当前请求
      scope:
        providers: ["deepseek"]
        models: ["v4-pro", "v4-flash"]
```

### 6.2 正常流程 vs Fallback 流程

**正常（MiMo / 无 thinking 问题的模型）：**
```
Claude → CC Switch (15721) → MiMo API → 200 ✅
                                    ↑ fixer 不介入，零额外延迟
```

**正常（DeepSeek 首次请求无 thinking 问题）：**
```
Claude → CC Switch (15721) → DeepSeek API → 200 ✅
                                    ↑ fixer 不介入
```

**Fallback（DeepSeek 触发 thinking 400）：**
```
Claude → CC Switch → DeepSeek → 400 thinking error 🔴
                          ↓ 通讯层检测到 trigger_error
                          ↓ 自动启动 fixer
Claude → CC Switch → thinking-fixer → DeepSeek → 200 ✅
                          ↑ 缓存 + 注入 + 剥离 thinking 块
```

### 6.3 Thinking Fixer 生存周期

```
初始状态：stopped（不占端口，不占内存）
首次请求：bypass（不经过 fixer）
检测到 trigger_error → 启动 fixer（on-demand 启动）
后续请求 → 经过 fixer（缓存 + 注入 + 剥离）
同一会话连续 N 次无 error → 自动关闭 fixer
```

### 6.4 实战验证数据

| 指标 | 值 |
|------|-----|
| fixer 不介入时（MiMo） | ✅ 直通，无延迟 |
| fixer 介入后（DeepSeek） | ✅ 6 轮连续 200 |
| 缓存命中率 | ✅ 按消息索引，100% |
| 无 fixer 时效果 | ❌ DeepSeek thinking 400 |

---

## 7. 执行层：预授权执行上下文

### 7.1 启动参数

执行层启动 Claude Code 时注入预授权上下文：

```yaml
execution_context:
  task_id: "{{task_id}}"
  sandbox: "{{task_dir}}"

  permissions:
    write_paths:
      - "{{task_dir}}/outputs/*"
      - "{{task_dir}}/runtime/*"
    read_paths:
      - "{{task_dir}}/**"
      - "资产/**"
    bash_commands:
      - "ls"
      - "cat"
      - "head"
      - "tail"
      - "python3"
      - "mkdir -p"
```

实际 CLI 调用：
```bash
claude --allowedTools "Edit,Write,Bash,BashReadOnly,Read,Search" \
       --allow-dangerously-skip-permissions \
       -p "{{prompt}}"
```

### 7.2 授权 vs 安全边界

- 仅在隔离沙箱（task_dir 内）使用 `--allow-dangerously-skip-permissions`
- 写路径限定在 `outputs/` 和 `runtime/`，不开放全目录
- bash 命令白名单，禁止危险操作
- 文件读取限制在 task_dir 和明确声明的资产目录

---

## 8. DAG Manifest 定义

### 8.1 最小节点定义

```yaml
dag:
  version: "1.0"

  nodes:
    - id: "probe"
      label: "探针验证"
      depends_on: []                    # 无依赖，先执行
      executor_config:
        agent: "claude"
        prompt_file: "dispatch/probe_prompt.md"
        model_hint: "fast"              # 编排层不指定具体模型
      expected_outputs:
        - path: "{{task_dir}}/probe/report.md"
          validation: "exists"
      timeout_sec: 300

    - id: "collection"
      label: "全量采集"
      depends_on: ["probe"]             # 依赖探针完成
      executor_config:
        agent: "claude"
        prompt_file: "dispatch/collect_prompt.md"
      expected_outputs:
        - path: "{{task_dir}}/collection/data.csv"
          validation: "non_empty"
      timeout_sec: 600
      fan_out:                          # 并行化
        strategy: "split_input"
        split_on: "keywords"

    - id: "sample_gate"
      label: "样张确认门"
      depends_on: ["collection"]
      executor_config:
        agent: "hermes"
        prompt_file: "dispatch/sample_gate_prompt.md"
      gate: true                        # 阻塞后续节点直到 Owner 确认
```

### 8.2 节点状态机

```
pending → ready → dispatched → running → completed → next node
                                    → failed → retry(≤2次) → running
                                             → hold(等待 Owner)
```

### 8.3 节点回执格式

```yaml
node_id: "probe"
status: "completed"            # completed / failed / gate_blocked
executor: "claude"
started_at: "2026-05-29T15:00:00+08:00"
completed_at: "2026-05-29T15:05:00+08:00"
outputs:
  - path: "{{task_dir}}/probe/report.md"
    size_bytes: 12345
    validation: "pass"
repair_count: 0                # AI 修复轮数
verdict: "pass"                # pass / retry_once / escalate
metadata:
  total_tokens: 5000
  model: "Deepseek-v4-pro"
```

---

## 9. AI 修 AI 闭环（Repair Loop）

### 9.1 触发条件

节点产出物未通过预期校验（文件不存在、为空、格式错误等）。

### 9.2 修复流程

```
节点完成 → 校验产出 → pass → 正常进入下一节点
                     → fail → repair Agent 分析 Issue
                              → 生成 Issue Packet（含错误描述 + 期望修复方向）
                              → 原执行 Agent 重试（retry_once）
                              → 再次校验 → pass → 继续
                                          → fail → 二次重试（最多 2 轮）
                                                   → 仍 fail → escalate_to_owner
```

### 9.3 Issue Packet 格式

```yaml
issue:
  node_id: "probe"
  attempt: 2
  expected_output: "{{task_dir}}/probe/report.md"
  validation_failure: "file_exists"
  diagnosis: "Agent 未能读取到目标目录"
  repair_instruction: "请确认路径资产/ 存在后用 cat 读取"
  max_retries: 2
```

---

## 10. 设计原则（归盘验证背书）

以下 8 条原则来自第三次作业实战归盘，已在本设计中内置：

| # | 原则 | 设计中体现 |
|---|------|-----------|
| 1 | 三层委托模型：策略→方案→执行 | §2 六角色职责矩阵 |
| 2 | 一张样张原则：样张批准前不进入全量 | §4 Gate 5（Stage Gate）+ §8 fan_out |
| 3 | 30 秒判断原则：Owner 决策信息量控制 | §4 Gate 设计，每 Gate 输入标准化 |
| 4 | 进度汇报三元素：进度条+产出+决策 | §5 runtime/ 目录 + heartbeat/progress 文件 |
| 5 | 不要假定原则：配数据或样张 | AI Repair Gate 要求 Issue Packet |
| 6 | 信息层级四层设计 | 每节点输出要求结构化 |
| 7 | 拒绝的勇气制度化 | Gate 系统支持直接驳回 |
| 8 | 先整理再归盘 | Gate 7 归盘前含 workspace clean 步骤 |

---

## 11. 迭代路线

```
v0.3（已完成）→ 蓝图设计
    ↓
v0.3.1（本文件）→ 整合补缺后的设计稿（emerged）
    ↓
v0.4  模板 + 目录协议定稿
    ├─ dispatch / receipt / issue packet 模板定型
    └─ 目录协议 9 层标准定稿
    ↓
v0.5  DAG manifest 引擎
    ├─ Relay Runner 增加 DAG 解析器
    └─ 支持串行/并行节点派发
    ↓
v0.6  通讯层 fallback 链
    ├─ thinking-fixer 改为 on_error 模式
    └─ 插件注册 + 错误检测 + 重定向
    ↓
v0.7  执行层预授权
    ├─ 启动参数注入 pre-approved 权限
    └─ 弹窗自动化处理
    ↓
v0.8  Docker DAG POC
    ├─ 隔离执行舱原型
    └─ L/XL 级任务验证
    ↓
v0.9  多 Agent 协作
    ├─ fan-out/fan-in 编排协议
    └─ 节点级重试/回滚
    ↓
v1.0  正式版
    ├─ 完整 DAG 工作流系统
    └─ 支持 B 线全链路生产
```

---

## 12. 实战验证记录

本次设计文档的验证来源于 2026-05-29 的全链路实战：

| 验证项目 | 结果 |
|----------|------|
| relay runner 派发 Claude Code 任务 | ✅ tmux 模式正常启动、发 prompt、监心跳 |
| thinking-fixer 缓存 | ✅ 6 轮连续 200，按消息索引缓存 100% 命中 |
| MiMo 模型直通（无 fixer） | ✅ 跑完全程出报告，无 thinking 错误 |
| CC Switch 路由管理 | ✅ settings.json 自动接管，provider endpoint 可配置 |
| 模型切换 | ✅ DeepSeek → MiMo 零配置切换（通讯层自动适配） |
| 文件权限弹窗 | ⚠️ 需 relay runner 自动处理（v0.7 修复） |
| thinking-fixer 始终在线 | ⚠️ 应改为 on_error fallback（v0.6 修复） |

---

## 13. 文件清理建议

| 文件 | 操作 | 说明 |
|------|------|------|
| `v0.1_DAG.md` | 标记为归档 | 已被 v0.2 和 v0.3 完全覆盖 |
| `会话封存包.md` | 标记为归档 | 结论已吸收进正式文件 |
| `审查方法论卡 v0.1` | R1 完成后归档 | R0 产物 |
| `R1 审查报告（中文版）` | 以英文原版为准 | 中文版为非审查性翻译 |

---

*本设计文档由两份独立审查报告交叉验证后 emerged 产出。v0.3.1 版本号标识其为 v0.3 蓝图经补缺整合后的第一版落地设计稿。*
