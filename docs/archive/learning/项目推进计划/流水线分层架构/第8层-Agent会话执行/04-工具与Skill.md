# 04 - 工具与 Skill

## 概览

Agent 容器内的工具体系由三层组成：

1. **Claude Code 原生工具**：由 `claude` CLI / SDK 内置提供，Agent 可以直接调用
2. **Runtime MCP 工具**：由 `agent/sdk_runtime_mcp.py` 注册的运行时内置工具，通过 MCP Server 暴露
3. **Skill 系统**：由 `agent/skill_bundle_loader.py` 加载的文档型 Skill，提供方法参考与检查表

---

## 4.1 Claude Code 原生工具

所有 Agent 会话都可使用以下 9 个 Claude Code 原生工具：

| 工具 | 核心参数 | 用途 |
|------|---------|------|
| `Read` | `file_path`, `offset`, `limit` | 读取文件内容（支持分页） |
| `Write` | `file_path`, `content` (字符串) | 创建或覆写文件 |
| `Edit` | `file_path`, `old_string`, `new_string` | 精确文本替换 |
| `Glob` | `pattern`, `path` | 文件名模式匹配搜索 |
| `Grep` | `pattern`, `path`, `glob` | 文件内容正则搜索 |
| `Bash` | `command` | 执行 Shell 命令 |
| `Skill` | `skill`, `args` | 调用项目 Skill |
| `Agent` | `description`, `prompt`, `subagent_type` | 委派子任务给 subagent |
| `Task` | (subagent 相关) | 后台任务执行 |

系统提示词中对这些工具有严格的参数规范约束：

```text
CRITICAL: 绝对禁止盲猜参数名。
Read 用 file_path，Write 用 file_path + 字符串 content，
Edit 用 file_path + old_string + new_string；
如使用 Agent，也必须严格按当前真实签名传参。

CRITICAL: Write.content MUST 是字符串。
写 JSON 时，先用 json.dumps(..., ensure_ascii=False, indent=2) 把完整 payload 序列化；
把 object/dict/list 直接塞进 content 会立刻触发 InputValidationError。
```

---

## 4.2 Runtime MCP 工具

`agent/sdk_runtime_mcp.py` 通过 `build_runtime_sdk_mcp_server()` (line 237) 注册一个名为 `"runtime"` 的 MCP Server，提供以下工具：

### 核心运行时工具

| 工具名 | 函数 | 用途 |
|--------|------|------|
| `get_run_context` | `_register_get_run_context` (line 278) | 返回当前 run/session 上下文和运行时约束 |
| `get_mcp_status` | `_register_get_mcp_status` (line 286) | 返回 SDK 可见的 MCP 服务器实时状态快照 |
| `reconnect_mcp_server` | `_register_reconnect_mcp_server` (line 294) | 重连指定的 MCP 服务器 |
| `toggle_mcp_server` | `_register_toggle_mcp_server` (line 305) | 启用/禁用指定的 MCP 服务器 |
| `get_runtime_flags` | `_register_get_runtime_flags` (line 317) | 返回关键运行时标志（search/enabled/thinking/effort） |
| `get_execution_contract` | `_register_get_execution_contract` (line 337) | 返回当前节点的 execution_contract、workspace_contract 与 required outputs |
| `get_mcp_runtime_manifest` | `_register_get_mcp_runtime_manifest` (line 349) | 返回当前节点可见的 MCP runtime 配置真值 |

### 产物与工作流工具

| 工具名 | 函数 | 用途 |
|--------|------|------|
| `resolve_workspace_artifact_path` | `_register_resolve_workspace_artifact_path` (line 361) | 将 artifact 相对路径解析为精确绝对路径 |
| `inspect_report_workflow_plan` | `_register_inspect_report_workflow_plan` (line 373) | 结构化检查 workflow plan 的报告节点质量 |
| `validate_artifact_index` | `_register_validate_artifact_index` (line 385) | 校验 artifact_index.json 的结构完整性 |
| `materialize_artifact_metadata` | `_register_materialize_artifact_metadata` (line 397) | 计算一组 artifact 文件的 mime_type、sha256 等元数据 |

### 共享记忆工具

| 工具名 | 函数 | 用途 |
|--------|------|------|
| `read_shared_memory` | `_register_read_shared_memory` (line 417) | 读取共享记忆（跨节点持久化的键值记忆） |
| `write_shared_memory` | `_register_write_shared_memory` (line 442) | 写入共享记忆（追加模式，不覆盖已有内容） |
| `list_shared_memories` | `_register_list_shared_memories` (line 468) | 列出所有共享记忆键名 |

共享记忆存储在 `<run_root>/.memories/<key>.md` 文件中。每个条目标注源节点 `node_id`。

### Agent Teams 协作工具（条件注入）

当 `team_enabled(workspace)` 为 true（即 `node_context.json` 中 `team` 字段存在有效的 `team_id` 和 `my_id`）时，额外注入 7 个团队协作工具：

| 工具名 | 函数 | 用途 |
|--------|------|------|
| `send_team_message` | `_register_send_team_message` (line 484) | 向共享 mailbox 写入团队消息 |
| `read_team_inbox` | `_register_read_team_inbox` (line 508) | 读取发给我的团队消息和广播 |
| `update_team_task` | `_register_update_team_task` (line 527) | 更新团队共享 task board 上的状态 |
| `claim_team_task` | `_register_claim_team_task` (line 548) | 认领 team task |
| `request_team_review` | `_register_request_team_review` (line 568) | 请求队友评审 |
| `reassign_team_task` | `_register_reassign_team_task` (line 589) | 将 task 重新分派给队友 |
| `get_team_task_board` | `_register_get_team_task_board` (line 610) | 查看共享任务看板快照 |

---

## 4.3 MCP 状态管理

### `normalize_mcp_status_payload(payload)` (line 212)

将 SDK/CLI 返回的 MCP 状态原始数据规范化为统一格式：

```python
def normalize_mcp_status_payload(payload: Any) -> list[dict[str, Any]]:
    # 从 {"mcpServers": [...]} 中提取
    # 每个 entry: {"name": "...", "status": "connected"/"failed", "error": "...", "tools": [...]}
```

### 运行时 MCP 状态缓存与监控

`election_agent.py` 中的 `_SdkRuntimeContext` 维护：
- `mcp_status_by_name: dict[str, dict]` —— 服务器名 → 状态字典
- `failed_mcp_servers: set[str]` —— 已确认失败的服务器名集合

关键监控函数：
- `_fetch_runtime_mcp_status(runtime)` (line 812)：从 SDK client 获取实时状态
- `_record_mcp_status_snapshot(runtime, ...)` (line 787)：记录状态快照到 `sdk_messages.jsonl`
- `_reconnect_runtime_mcp_server(runtime, server_name)` (line 828)：重连并记录结果
- `_toggle_runtime_mcp_server(runtime, server_name, enabled)` (line 838)：切换并记录结果
- `warn_on_unavailable_mcp_search_tools(workspace)` (session_lifecycle.py:129)：会话启动时检查 web_search 等 MCP 工具可用性，不可用时记录 warning

MCP 搜索工具不可用时的提示文本（line 731）：
```text
MCP server "{server}" 不可用。请检查管理后台中的 MCP 配置、宿主机端点连通性，
以及当前工作区 .mcp.json / .claude/settings.json 是否已正确下发。
不要继续调用 mcp__{server}__*，必须显式报告检索失败。
```

---

## 4.4 Skill 系统

### Skill bundle 加载

`agent/skill_bundle_loader.py` 提供的 `load_skill_bundle(skill_id: str) -> SkillBundle` (line 21) 负责加载 Skill 文档。

```python
@dataclass(frozen=True)
class SkillBundle:
    skill_id: str       # Skill 标识符
    doc_path: Path | None    # SKILL.md 路径
    skill_dir: Path | None   # Skill 目录
    raw_text: str       # 原始全文
    body_text: str      # 去除 frontmatter 后的正文
    frontmatter: dict   # YAML frontmatter 解析结果
```

加载流程：
1. 若 `skill_id` 是通用 Skill（`common/skills_registry.py:is_generic_skill_id()`），直接返回空 bundle
2. 否则调用 `resolve_skill_doc_path(base_dir, skill_id)` 查找 `SKILL.md`
3. 调用 `read_skill_doc(base_dir, skill_id)` 读取全文
4. 调用 `parse_frontmatter(raw_text)` 分离 frontmatter 和正文

### Skill 文档存储

Skill 源文件存放在 `claude-runtime/skills/` 目录下，由 `orchestrator/agent/workspace_skills.py:sync_workspace_skills()` 在容器启动前扁平投影到容器内的 `.claude/skills/<skill-name>/SKILL.md`。

### Skill 在系统提示词中的呈现

`build_runtime_control_system_prompt()` 将当前节点可用的 Skill 集合注入系统提示词：

```text
- 当前 primary skill 为 `xxx`；它是参考方法，不是默认身份目标。
- 当前节点可用 Skill 集合为：`skill_a`、`skill_b`、`skill_c`
- 当前 run 已挂载全部 project skills，目录为 `.claude/skills/`
```

---

## 4.5 工具调用审计与安全

### audit.jsonl 记录

`agent/event_recorder.py:append_audit_event()` 写入 `workspace/audit.jsonl`，记录每次工具调用的审计信息。`election_agent._successful_write_tracker(ws)` 从 audit.jsonl 中提取成功的 Write/Edit 操作路径，用于 short-circuit 检测——当检测到 Agent 已写入所有 required outputs 时，可提前结束会话。

### Write 操作追溯

`_tracked_write_targets()` (election_agent.py:679) 只追溯以下四种工具的写入操作：
- `Write`
- `Edit`
- `MultiEdit`
- `NotebookEdit`

若工具响应包含错误 (`_tool_response_has_error`)，则该次写入不计入成功追溯。

### 工作区安全边界

`_resolve_workspace_tool_path(ws, raw_path)` (line 655) 确保：
- 解析后的绝对路径必须在工作区 `ws` 的子树内 (`resolved.is_relative_to(ws.resolve())`)
- 拒绝 `..` 路径穿越
- 拒绝超出工作区范围的绝对路径

### Bash 违规检测

虽然 Bash 是允许的原生工具，但系统提示词中限制了其使用场景：

```text
- 目录核验优先使用 LS；不要为了确认文件是否存在而先写 Bash(ls ...)
- /public 是只读挂载文件树：不要用 Bash(head ...)、cat、find 对 /public 做批量探测
```

`BASH_VIOLATION_SEGMENT_PREVIEW_MAX_CHARS = 50`（`output_limits.py`）用于摘要提取时截断 Bash 违规片段。

---

## 4.6 Runtime Builtin Tools 实现

`agent/runtime_builtin_tools.py` 提供 Runtime MCP 工具的后端实现函数：

| 实现函数 | 代码行 | 核心逻辑 |
|----------|--------|---------|
| `execute_get_runtime_flags()` | line 31 | 从环境变量和 node_context 提取 `search_mcp_enabled`, `thinking_mode`, `effort`, `effective_context_window_tokens` 等 |
| `execute_get_execution_contract()` | line 56 | 提取 `execution_contract`, `workspace_contract`, `required_outputs` |
| `execute_get_mcp_runtime_manifest()` | line 70 | 提取 MCP runtime 配置 |
| `execute_resolve_workspace_artifact_path()` | line 76 | 路径解析 + 存在性检查 + 安全边界校验 |
| `execute_inspect_report_workflow_plan()` | line 94 | 校验 workflow plan 的 role、edge、upstream 输入 |
| `execute_validate_artifact_index()` | line 107 | 委托给 `common/artifact_index_validation.py` |
| `execute_materialize_artifact_metadata()` | line 116 | SHA256 (最大 50MB)、MIME type、schema_version |

所有实现函数都通过 `_sdk_tool_result()` 包装返回，确保输出兼容 SDK 的 tool_result 格式：

```python
def _sdk_tool_result(payload: Any) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(jsonable, ensure_ascii=False)}],
        "is_error": bool(isinstance(jsonable, dict) and jsonable.get("is_error")),
    }
```

---

## 4.7 工具调用权限模式

环境变量 `CLAUDE_PERMISSION_MODE` 控制工具调用权限（默认 `"acceptEdits"`）：

| 模式 | 行为 |
|------|------|
| `default` | 标准权限提示 |
| `acceptEdits` | 自动接受编辑操作 |
| `plan` | 仅计划模式 |
| `auto` | 自动批准所有操作 |
| `dontAsk` | 不询问 |
| `bypassPermissions` | 完全绕过权限检查 |

在 `session_lifecycle.py:prepare_sdk_runtime_context()` 中校验：不在白名单中的值一律回退到 `"acceptEdits"`。

---

## 关键文件索引

| 文件 | 职责 |
|------|------|
| `agent/sdk_runtime_mcp.py` | Runtime MCP Server 注册（14 个基础工具 + 7 个团队协作工具） |
| `agent/runtime_builtin_tools.py` | Runtime 工具的业务逻辑实现 |
| `agent/skill_bundle_loader.py` | Skill bundle 加载（SKILL.md 解析） |
| `agent/event_recorder.py` | 工具调用审计与消息压缩记录 |
| `agent/output_limits.py` | 输出截断参数常量 |
| `common/sdk_buffer_policy.py` | SDK 缓冲区策略 |
| `common/artifact_index_validation.py` | Artifact index 校验 |
| `common/report_workflow_contract.py` | 报告工作流契约校验 |
| `claude-runtime/skills/` | Skill 源文件目录 |
