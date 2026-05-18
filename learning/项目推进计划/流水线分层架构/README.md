# ElectionSim-Lab 流水线分层架构

> 从用户输入一句话到最终报告产出，完整覆盖 10 层流水线。
> 基于 2026-04-28 最新代码库状态，逐层详细拆解。

## 目录结构

```
流水线分层架构/
├── README.md                                    ← 总索引（本文件）
├── 第0层-规划代理与意图路由/                       ← Layer 0：用户输入 → Planning Agent
├── 第1层-规划器-DAG拓扑生成/                       ← Layer 1：LLM 生成 WorkflowPlan DAG
├── 第2层-计划修复与验证循环/                        ← Layer 2：Compile → Validate → Repair
├── 第3层-Skill自动绑定/                           ← Layer 3：确定性四层匹配 + 关键词降级
├── 第4层-DAG物化器/                               ← Layer 4：拓扑排序 → 搜索注入 → GeneratedDAG
├── 第5层-启动提示词组装/                            ← Layer 5：task_prompt 七层组装 + SCOPE_LINES
├── 第6层-工作区同步/                               ← Layer 6：claude-runtime/ → .claude/ 投影
├── 第7层-Docker容器启动/                           ← Layer 7：长生命周期容器 + docker exec 复用
├── 第8层-Agent会话执行/                            ← Layer 8：Agent SDK Session 节点执行
├── 第9层-事件流回传/                               ← Layer 9：sdk_messages.jsonl → Redis → SSE → 前端
└── 总结/                                         ← 谁做什么 + 端到端流程 + 设计决策
```

---

## Layer 0：规划代理与意图路由（2 文件）

| 文件 | 内容 |
|------|------|
| `01-概述.md` | 用户输入入口、规划代理在系统中的位置、三种输出状态 |
| `02-规划代理详解.md` | `planning_agent.py` + `planning_api.py` + 多轮策略 |

**核心模块**：`orchestrator/chat/planning_agent.py`（SDK 驱动的规划代理）、`orchestrator/chat/planning_api.py`（`stream_generate_workflow_response` 入口）、`orchestrator/chat/planning_round_policy.py`（多轮决策）、`orchestrator/chat/planning_intent.py`（意图提取）

**关键词**：`PlanningAgentResult`, `planning_richness`, `chat/ask/ready` 三种状态, 多轮澄清, `InformationSufficiency`, `PlanningGear`

---

## Layer 1：规划器 — DAG 拓扑生成（5 文件）

| 文件 | 内容 |
|------|------|
| `01-概述.md` | Planner 概述：双通道生成、输入输出、Recipe 模板体系 |
| `02-计划生成器.md` | `plan_generator.py` 的 SDK vs LLM 双通道、`plan_generator_support.py` |
| `03-引擎提示词.md` | `engine_prompts.py` 中 `build_workflow_plan_prompt()` 的七层组装 |
| `04-模板与策略.md` | `planning_strategies.py` + `planner_skill_assets.py`：35+ Skill 摘要表与策略模式 |
| `05-工作流计划Schema.md` | `workflow_models.py` 中 WorkflowPlan / WorkflowPlanNode / WorkflowPlanEdge 完整字段 |

**核心模块**：`orchestrator/dag/engine.py`（`OrchestrationEngine`）、`orchestrator/dag/engine_planning_mixin.py`、`orchestrator/dag/plan_generator.py`、`orchestrator/dag/engine_prompts.py`

**关键词**：`WORKFLOW_GEN_MODEL`, `generate_planner_sdk()`, `generate_llm()`, `planning_strategies`, 35 个 Skill 摘要表

---

## Layer 2：计划修复与验证循环（3 文件）

| 文件 | 内容 |
|------|------|
| `01-概述.md` | Plan → Compile → Validate → Repair 循环概述 |
| `02-计划编译器.md` | `plan_compiler.py` + `plan_validator.py`：JSON 提取、Pydantic 校验、业务校验 |
| `03-修复循环.md` | `plan_repair_loop.py` 的错误诊断、RepairPrompt、重试策略 |

**核心模块**：`orchestrator/dag/plan_compiler.py`、`orchestrator/dag/plan_validator.py`、`orchestrator/dag/plan_repair_loop.py`、`orchestrator/dag/workflow_validation.py`

**关键词**：`PlanCompiler.compile()`, `extract_json_object()`, 无环检测, 孤立节点检测, `workflow_plan_repair_attempts`

---

## Layer 3：Skill 自动绑定（4 文件）

| 文件 | 内容 |
|------|------|
| `01-概述.md` | 为什么需要 Auto-Binder、整体设计、何时触发（仅 `allowed_mode="open"`） |
| `02-四层匹配逻辑.md` | `_candidate_skill_id()` 四层匹配：显式赋值 → 注册表精确匹配 → 双下划线前缀 → 关键词降级 |
| `03-单次使用保护.md` | `single_use` / `canFanOut=false` 的保护和降级为 generic 机制 |
| `04-Skill注册表.md` | `skills_registry.yaml` → `SkillRegistry.SKILLS` 运行时状态与协作方式 |

**核心模块**：`orchestrator/dag/skill_auto_binder.py`、`orchestrator/dag/skill_binding.py`、`orchestrator/dag/types.py`（`SkillRegistry`）

**关键词**：纯正则规则引擎, 四层匹配, `_NODE_ID_SKILL_FALLBACKS` 21 条中英文关键词规则, `__` 前缀匹配, single_use 降级为 generic

---

## Layer 4：DAG 物化器（3 文件）

| 文件 | 内容 |
|------|------|
| `01-概述.md` | Materializer 在流水线中的位置和职责 |
| `02-DAG编译.md` | `build_generated_dag()`：拓扑排序、层级注入、`agent_config` 构建、`DAGNode` 物化 |
| `03-CSV扇出与搜索注入.md` | `_inject_search_sub_nodes()`：搜索子节点注入（external_search / knowledge_search）；并发搜索策略模板 |

**核心模块**：`orchestrator/dag/workflow_materializer.py`（`build_generated_dag`、`assign_layers_orders`、`_inject_search_sub_nodes`）

**关键词**：`GeneratedDAG`, `assign_layers_orders`, 搜索策略模板, 搜索子节点注入, `_SEARCH_AGENT_SKILL_IDS`

---

## Layer 5：启动提示词组装（4 文件）

| 文件 | 内容 |
|------|------|
| `01-概述.md` | 在流水线中的位置、核心职责、`build_node_prompt()` 入口、输入来源、ASCII 数据流图 |
| `02-提示词组装.md` | `build_node_prompt()` 的七层组装顺序：任务描述 → 上游产物摘要 → 资源提示 → 数据读取协议 → 工具纪律 → SCOPE_LINES → 输出合约 |
| `03-作用域约束.md` | SCOPE_LINES 体系：AGENDA_SETTER / CANDIDATE_REGISTRY / TASK / EXECUTION_AUTHORITY / PUBLIC_DATA / READ_PROTOCOL / TOOL_SEARCH 八套约束；`discovery_policy.py` 的 knowledge/search MCP 触发策略 |
| `04-输出合约.md` | `required_outputs` 生成、`task_prompt.md` 最终格式、`node_context.json.execution_contract`、CSV 进度规范、`time_context.json`、`seed_paths`/`upstream_file_map` 使用、REPORT_FINAL_NODES 约束 |

**核心模块**：`orchestrator/dag/launcher_prompt.py`、`orchestrator/dag/resource_hints.py`、`orchestrator/dag/discovery_policy.py`

**关键词**：`build_node_prompt()`, `SCOPE_LINES`, `EXECUTION_AUTHORITY_LINES`, `AGENDA_SETTER_SCOPE_LINES`, `CANDIDATE_REGISTRY_SCOPE_LINES`, `READ_PROTOCOL_LINES`, `TOOL_SEARCH_LINES`, `resource_hints.seed_paths`, `upstream_file_map`, `REPORT_FINAL_NODES`, `REPORT_CHAIN_VISUAL_NODES`

---

## Layer 6：工作区同步（4 文件）

| 文件 | 内容 |
|------|------|
| `01-概述.md` | 宿主机与容器的文件映射概述 |
| `02-同步机制.md` | `workspace_skills.py` 中 `sync_workspace_skills()` 的 `shutil.copytree` 逻辑 |
| `03-MCP模板渲染.md` | MCP 模板变量 `{{MCP_*}}` 替换机制 |
| `04-容器工作区布局.md` | 容器内 `input/` `meta/` `output/` `.claude/` 目录布局 |

**核心模块**：`orchestrator/agent/workspace_skills.py`、`common/claude_runtime_assets.py`

**关键词**：`sync_workspace_skills()`, `shutil.copytree`, MCP 模板渲染, `node_context.json`, `time_context.json`, `claude-runtime/`

---

## Layer 7：Docker 容器启动（4 文件）

| 文件 | 内容 |
|------|------|
| `01-概述.md` | 容器启动策略概述：两种执行模式（DAG 调度 / 单 Agent） |
| `02-启动器分析.md` | `execute_api.py` 中 `execute_workflow()` → `execute_with_dag_scheduler()` / `execute_single_agent()` |
| `03-容器生命周期.md` | 容器完整生命周期：启动 → 执行 → 退出 → 清理 |
| `04-卷挂载设计.md` | `/workspace`、`/workspace/upstream`、`/public` 挂载设计 |

**核心模块**：`orchestrator/chat/execute_api.py`、`orchestrator/dag/scheduler.py`（`DAGScheduler`）、`orchestrator/container_monitor.py`（`RunContainerMonitor`）

**关键词**：长生命周期容器, `docker exec` 复用, `election-network`, `agent-network`, `DAGScheduler`, `RunContainerMonitor`

---

## Layer 8：Agent 会话执行（5 文件）

| 文件 | 内容 |
|------|------|
| `01-概述.md` | Agent SDK Session 概述、容器内执行入口 |
| `02-会话生命周期.md` | `election_agent.py` 入口 → SDK client 初始化 → user message → 推理循环 → 退出 |
| `03-系统提示词.md` | `system_prompt.py` 的时间基准注入 + 运行时控制（`runtime_required_outputs`、`runtime_custom_agent_visibility`） |
| `04-工具与Skill.md` | Read/Write/Edit/Bash/Skill/Agent/MCP 完整工具清单、`skill_bundle_loader.py`、`sdk_runtime_mcp.py` |
| `05-Subagent委派.md` | Subagent 委派策略：`team_comm.py`、`runtime_builtin_tools.py`、8 个角色定义 |

**核心模块**：`agent/election_agent.py`、`agent/sdk_session.py`、`agent/system_prompt.py`、`agent/skill_bundle_loader.py`、`agent/sdk_runtime_mcp.py`、`agent/session_lifecycle.py`、`agent/native_terminal_runner.py`

**关键词**：`run_node.py`, `election_agent.py`, `system_prompt.py`, `sdk_session.py`, subagent 委派, `max_turns=300`, `session_lifecycle.py`

---

## Layer 9：事件流回传（4 文件）

| 文件 | 内容 |
|------|------|
| `01-概述.md` | 事件从 Agent Session 到前端的完整链路 |
| `02-事件管道.md` | `sdk_messages.jsonl` → Redis Streams → SSE 管道 |
| `03-Redis-SSE桥接.md` | Redis Streams 与 SSE 的桥接、消费者组、断线重连 |
| `04-前端消费.md` | `runEventStore`（Zustand）→ ReactFlow 实时更新 |

**核心模块**：`agent/event_recorder.py`、`orchestrator/routers/runs.py`（SSE 端点）、前端 `useChatStreaming.ts`、`runEventStore`

**关键词**：`event_recorder.py`, `sdk_messages.jsonl`, Redis Streams, SSE, `Last-Event-ID`, Zustand, ReactFlow

---

## 总结（3 文件）

| 文件 | 内容 |
|------|------|
| `01-谁做什么.md` | 完整"谁做什么"对照表：Layer × 执行者 × 模型 × 输入 × 输出 |
| `02-端到端流程.md` | 端到端流程：从用户输入到报告产出的完整路径 |
| `03-关键设计决策.md` | 关键设计决策汇总：Auto-Binder、容器复用、Redis Streams、多轮澄清等 |

---

## 阅读路线建议

| 目标读者 | 建议路线 |
|----------|---------|
| **新加入开发者** | 总结/02-端到端流程 → 第0层 → 第1层 → 第8层 → 第9层 |
| **想理解 DAG 生成** | 第1层 → 第2层 → 第3层 → 第4层 |
| **想理解节点执行** | 第5层 → 第6层 → 第7层 → 第8层 |
| **想理解前后端通信** | 第9层 → 总结/01-谁做什么 |
| **想理解设计哲学** | 总结/03-关键设计决策 → 第3层 → 第5层 |
