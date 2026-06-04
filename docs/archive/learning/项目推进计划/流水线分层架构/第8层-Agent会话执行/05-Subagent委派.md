# 05 - Subagent 委派

## 概览

Subagent 委派是 Agent 容器内实现任务分解与并行执行的核心机制。主线程（主 Agent）负责规划、汇总与写回；搜索、查找、读取大文件和多源合并则必须委托给专门的 subagent。本章描述 subagent 的定义、委派策略、上下文隔离及团队通信机制。

---

## 5.1 Subagent 定义与加载

### 定义文件

Subagent 定义存储在 `claude-runtime/agents/` 目录下的 `.md` 文件中，通过 Orchestrator 的 `sync_workspace_skills()` 在容器启动前投影到容器内的 `.claude/agents/`。

每个 subagent 定义文件包含 YAML frontmatter 和 Markdown prompt body：

```markdown
---
name: knowledge-researcher
description: 搜索内部知识库，输出完整 evidence pack
model: sonnet
permissionMode: acceptEdits
tools:
  - Read
  - Grep
  - Glob
skills:
  - data-discovery
mcpServers:
  - knowledge
background: true
maxTurns: 50
---
你是一个内部知识库研究员...
```

### 加载逻辑

`agent/custom_agents.py` 提供加载函数：

- **`load_workspace_agents(workspace, AgentDefinition)`**：扫描 `.claude/agents/*.md`，将每个文件解析为 `AgentDefinition` 实例
- **`workspace_agent_names(workspace)`**：返回已同步的 subagent 名称列表（用于系统提示词中渲染可用 subagent 清单）
- **`validate_workspace_agents(workspace)`**：启动前校验（使用 `_WorkspaceAgentValidationDefinition` 作为假 `AgentDefinition` 类型）

加载优先查找 `workspace/claude-runtime/agents/`（源目录），若不存在则查找 `workspace/.claude/agents/`（生成目录）。

### AgentDefinition 的 legal 字段

```python
# 字符串字段
_STRING_FRONTMATTER_KEYS = {"name", "description", "model", "permissionMode",
                             "effort", "initialPrompt", "isolation", "color"}

# 列表字段
_LIST_FRONTMATTER_KEYS = {"tools", "disallowedTools", "skills", "mcpServers"}

# 布尔字段
_BOOL_FRONTMATTER_KEYS = {"background"}

# 整数字段
_INT_FRONTMATTER_KEYS = {"maxTurns"}
```

Model 合法值限于 `{"sonnet", "opus", "haiku", "inherit"}`。

---

## 5.2 8 个 Subagent 角色

系统提示词中 `_runtime_subagent_strategy_lines()` 只列出工作区实际同步的 subagent，以下是本项目中定义的 6 个核心 subagent（`quality-checker` 已废弃，`data-discovery` 不作为 Agent 而是作为 Skill 使用）：

| Subagent 名称 | 职责 | 产出路径模板 |
|--------------|------|-------------|
| `knowledge-researcher` | 搜索内部知识库，输出完整 evidence pack 到文件 | `output/subagents/knowledge-researcher/<task_id>/evidence_pack.md` |
| `web-searcher` | 外部搜索 MCP 获取最新网络信息，标注与内部基线差异 | `output/subagents/web-searcher/<task_id>/evidence_pack.md` |
| `data-explorer` | 发现工作区或 `/public` 中的数据文件并快速理解 schema | `output/subagents/data-explorer/<task_id>/data_inventory.md` |
| `upstream-reader` | 读取 1-N 个上游节点 output，提取当前任务需要的事实 | `output/subagents/upstream-reader/<task_id>/upstream_facts.md` |
| `evidence-aggregator` | 在 2+ 个上游之间做交叉校验、冲突检测和统一证据合并 | （按需） |
| `quality-checker` | **已废弃**；收尾结构核验改用 `Skill(skill="node-output-quality-check")` | N/A |

### 系统提示词中的角色提示

```text
Subagent 委派（强制搜索策略）：当前 run 提供了以下可委派 subagent：
  `knowledge-researcher`、`web-searcher`、`data-explorer`、`upstream-reader`、`evidence-aggregator`。
  主线程负责拆解、收敛、决策与最终写回；搜索、查找、检索、读取大文件和多源合并必须交给对应 subagent/Skill 先并发完成。

  各 agent 职责：
  - `data-explorer`：发现工作区或 /public/ 中的数据文件并快速理解 schema——进入分析前先调用
  - `upstream-reader`：读取 1~N 个上游节点 output，提取当前任务需要的事实——避免把上游正文灌进主上下文
  - `evidence-aggregator`：在 2+ 个上游之间做交叉校验、冲突检测和统一证据合并
  - `knowledge-researcher`：搜索内部知识库，输出完整 evidence pack 到文件 —— 本地资料优先调用
  - `web-searcher`：外部搜索 MCP 获取最新网络信息，标注与内部基线差异后写入文件 —— 本地不够时调用
  - `quality-checker`：已废弃；收尾结构核验请改用 Skill(skill="node-output-quality-check")
```

---

## 5.3 Subagent 委派策略

### 初始化委派清单（CRITICAL）

系统提示词强制要求：在收到任务后的第一条回复中，主 Agent 必须先列出委派计划表格：

```text
## 委派计划
| 子任务 | 委派给 | 输入关键词 | 预期产出路径 |
|--------|--------|-----------|-------------|
| 内部知识检索 | knowledge-researcher | <query> | output/subagents/.../evidence_pack.md |
| 外部最新信息 | web-searcher | <query> | output/subagents/.../evidence_pack.md |
| 数据文件定位 | data-explorer | <scope> | output/subagents/.../data_map.md |
| ... | ... | ... | ... |
```

### 并发委派纪律

```text
1. 确认清单覆盖所有信息需求后，在同一条回复中一次性发出所有对应的 Agent/Skill 调用。
2. 禁止先发 1 个 Agent/Skill，等结果回来再发第 2 个——除非第 2 个的输入完全依赖第 1 个的输出。
3. 清单中没有的子任务，不允许主线程自己执行 Bash/Glob/Grep/WebSearch/WebFetch。
4. 如果执行过程中发现清单遗漏的信息需求，补充到清单并立即委派——不能"顺手自己查一下"。
```

### 推荐并发模式

| 模式 | 组合 | 场景 |
|------|------|------|
| 内部 + 外部搜索 | `knowledge-researcher` + `web-searcher` 并发 | 需要同时查内部知识库和外部最新信息 |
| 数据 + 上游采集 | `data-explorer` + `upstream-reader` + `Skill(skill="data-discovery")` | 需要理解数据结构并读取上游产出 |
| 多源冲突处理 | `knowledge-researcher` + `web-searcher` + `evidence-aggregator` | 需要多源交叉校验 |
| 收尾校验 | `Skill(skill="node-output-quality-check")` | 复杂任务完成后的结构核验 |

### 强制委派规则

某些类型的工作被强制要求委派给 subagent，主线程禁止直接执行：

| 工作类型 | 必须委派给 | 禁止主线程执行 |
|----------|-----------|---------------|
| 内部数据搜索 | `data-explorer` + `knowledge-researcher` | `Bash`, `Glob`, `Grep` |
| 外部信息搜索 | `web-searcher` | `WebSearch`, `WebFetch` |
| CSV/表格分析 | `data-explorer` (定位) + `Skill(skill="data-discovery")` (探查) | `Read` 大表格、shell 解析 |
| 上游产物读取 | `upstream-reader` | `Read` 上游大文件 |
| 多源合并 | `evidence-aggregator` | 主线程手动合并 2+ 来源 |

---

## 5.4 Subagent 上下文隔离与结果合并

### 上下文隔离

每个 subagent 在独立的上下文中执行：
- Subagent 不继承主线程的消息历史
- Subagent 的 prompt 由主 Agent 在调用时传入（通过 `Agent` 工具的 `prompt` 参数）
- Subagent 的 tool_use / tool_result 消息流独立记录

### 文件产出型 Subagent 纪律

```text
- knowledge-researcher、web-searcher、data-explorer、upstream-reader、evidence-aggregator
  的详细结果必须写文件，summary 仅含状态、关键摘要和 output_path。
- 调用时 prompt 必须包含 task_id、query/scope 或 input_paths、task_output_dir、
  required_output_path、expected_sections。
- task_output_dir 须在当前节点业务输出目录下，推荐 output/subagents/<subagent_type>/<task_id>/。
- 主线程收到 summary 后，必须用 Read 读取 output_path/required_output_path 获取完整结果，
  再合并进业务输出；不要只依赖 subagent 的简短 summary。
```

### 标准调用示例

```text
# 示例：内部基线 + 外部最新信息，在同一条回复中并发执行
Agent(description="内部知识库检索",
      prompt="task_id=kaohsiung_polling_20260427;
              query=高雄市长民调趋势; scope=2024-2026 ...;
              task_output_dir=output/subagents/knowledge-researcher/.../;
              required_output_path=.../evidence_pack.md;
              expected_sections=Timeline, Key Polls, Source Anchors",
      subagent_type="knowledge-researcher")
Agent(description="外部网络检索",
      prompt="task_id=kaohsiung_polling_20260427;
              query=高雄市长最新民调; ...;
              task_output_dir=output/subagents/web-searcher/.../;
              required_output_path=.../evidence_pack.md;
              expected_sections=Latest Polls, News Timeline, ...",
      subagent_type="web-searcher")

# 主线程等待 summary 后：
# Read(output/subagents/knowledge-researcher/.../evidence_pack.md)
# Read(output/subagents/web-searcher/.../evidence_pack.md)
# 再继续综合。
```

---

## 5.5 Subagent 事件记录

`election_agent._subagent_event_payload()` (line 858) 为每个 subagent 调用生成事件记录：

```python
def _subagent_event_payload(*, kind, input_data, session_phase, session_id):
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": _execution_run_id(),
        "kind": kind,                              # "subagent_start" | "subagent_stop"
        "event_group": "subagent",
        "agent_id": input_data.get("agent_id"),
        "agent_type": input_data.get("agent_type"),
        "session_phase": session_phase,
        "session_id": session_id,
        "transcript_path": input_data.get("agent_transcript_path"),
        "stop_hook_active": input_data.get("stop_hook_active"),
    }
```

这些事件通过 `append_sdk_message()` 写入 `sdk_messages.jsonl`，供前端监控面板展示 subagent 的执行状态。

### Subagent 的事件组分类

`common/sdk_events.py` 中 `sdk_event_group()` 将 `kind` 以 `"subagent_"` 开头的消息归类为 `EventGroup.SUBAGENT`。

---

## 5.6 Agent Teams 通信 (`team_comm.py`)

`agent/team_comm.py` 实现了 Agent Teams（多 Agent 协作）模式下的通信机制。这与 subagent 委派是不同的概念——subagent 是主线程单向委派，Agent Teams 是对等协作。

### 上下文摘要

`team_context_summary(workspace)` (line 51) 从 `node_context.json` 的 `team` 字段提取团队上下文：

```python
return {
    "mode": "agent_teams",
    "team_id": "...",
    "team_name": "...",
    "my_id": "...",
    "member_ids": [...],
    "member_count": N,
}
```

此摘要同时注入到 `_SdkRuntimeContext` 的 `runtime_context_payload()` 和 `get_runtime_flags` 返回中。

### 通信协议

消息通过共享 mailbox（JSONL 文件）传递。核心操作：

| 操作 | 函数 | 描述 |
|------|------|------|
| 发送消息 | `send_team_message(ws, to, event, payload)` | 向 mailbox 追加消息；`to="*"` 则广播；消息去重（相同 message_id 不重复写入） |
| 读取收件箱 | `read_team_inbox(ws, limit, after_ts)` | 读取发给我的消息和广播消息，排除自己发送的 |
| 状态更新 | `update_team_task(ws, status, note, subject, task_id)` | 更新 task board 上的任务状态 |
| 认领任务 | `claim_team_task(ws, task_id, note, subject)` | 认领 task（不能抢占队友持有的） |
| 请求评审 | `request_team_review(ws, task_id, to, note, subject)` | 请求特定队友评审，同步写 task board + 发 mailbox 消息 |
| 重新分派 | `reassign_team_task(ws, task_id, to, note, subject)` | 改派 task 给另一个队友（受 revision 上限约束） |
| 查看看板 | `get_team_task_board(ws)` | 返回 team 共享 task board 的最新快照 |

### 消息校验

- **payload 大小限制**：`MAX_TEAM_MESSAGE_PAYLOAD_CHARS = 500` 字符（JSON 序列化后）
- **event 白名单**：`TEAM_MESSAGE_EVENTS`（10 个合法事件名）
- **任务状态白名单**：`TEAM_TASK_STATUSES` = `{"pending", "in_progress", "completed", "blocked", "error"}`
- **绝对路径校验**：`evidence_ready`, `handoff_ready`, `task_completed` 等事件中的 `path`/`paths`/`output_path` 等字段必须是绝对路径
- **task_started 限制**：禁止携带 `expected_output`/`output_path`/`brief_path` 等未来文件路径（只能用 `planned_output` 做文件名提示）
- **消息 TTL**：`TEAM_MESSAGE_TTL_SECONDS = 3600`（1 小时），超时消息在 `_cleanup_mailbox()` 时自动清除
- **Revision 上限**：默认 `DEFAULT_TEAM_MAX_REVISIONS = 3`，超过后禁止重新分派

### message_id 生成

```python
def _message_id(*, event_name, payload):
    explicit = payload.get("msg_id") or payload.get("message_id")
    if explicit:
        return explicit
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha1(serialized.encode("utf-8")).hexdigest()[:16]
    return f"{event_name}:{digest}"
```

### Task Board 快照合并

`_task_snapshots(team)` 从 task board JSONL 逐行读取，按 `task_id` 分组，使用 `_merge_task_snapshot()` 合并多次更新为最新状态。最终快照包含 `task_id`, `subject`, `owner`, `status`, `note`, `coordination`, `reviewer`, `revision`。

### 工具结果重建

`rebuild_team_tool_result(workspace, tool_name, tool_input)` (line 244) 用于 CLI 路径下重建被 compact 掉的团队工具结果——从 mailbox/task board JSONL 文件中回溯匹配最近的消息或任务状态。

---

## 5.7 Subagent 权限与安全边界

### Custom agent 名称限制

`system_prompt.py` 中 `CUSTOM_AGENT_NAMES_LIMIT = 8`：最多向系统提示词暴露 8 个 subagent 名称。`runtime_custom_agent_names()` 在返回前执行 `[:CUSTOM_AGENT_NAMES_LIMIT]` 截断。

### Subagent 的 Tool 访问控制

每个 subagent 的 `tools` / `disallowedTools` frontmatter 字段定义了其能使用的工具集。`AgentDefinition` 接收这些约束并在 subagent 上下文初始化时强制执行。

### Subagent hooks

在 `session_lifecycle.py:build_sdk_client_options()` 中注册：
- `subagent_start_hook`：subagent 启动时的审计钩子
- `subagent_stop_hook`：subagent 停止时的审计钩子

这两个 hooks 由 `election_agent.build_subagent_hooks(audit_deps)` 构建，记录 subagent 的起止事件和 transcript 路径。

---

## 关键函数索引

| 函数 | 文件 | 职责 |
|------|------|------|
| `load_workspace_agents()` | `agent/custom_agents.py:40` | 加载工作区 subagent 定义 |
| `workspace_agent_names()` | `agent/custom_agents.py:48` | 获取已同步 subagent 名称 |
| `_subagent_event_payload()` | `agent/election_agent.py:858` | 生成 subagent 事件记录 |
| `_runtime_subagent_strategy_lines()` | `agent/system_prompt.py:245` | 组装 subagent 委派策略系统提示词 |
| `team_enabled()` | `agent/team_comm.py:47` | 检查 Agent Teams 是否启用 |
| `team_context_summary()` | `agent/team_comm.py:51` | 提取团队上下文摘要 |
| `send_team_message()` | `agent/team_comm.py:89` | 发送团队消息 |
| `read_team_inbox()` | `agent/team_comm.py:113` | 读取团队收件箱 |
| `update_team_task()` | `agent/team_comm.py:135` | 更新团队任务状态 |
| `get_team_task_board()` | `agent/team_comm.py:237` | 获取团队任务看板 |
| `rebuild_team_tool_result()` | `agent/team_comm.py:244` | CLI 路径下重建团队工具结果 |
