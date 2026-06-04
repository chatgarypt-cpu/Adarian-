# 03-MCP 模板渲染

## 1. 设计背景

Skill 文档和 Agent 定义中经常需要引用具体的 MCP 工具名称，例如："使用 `mcp__linkly-ai__search` 检索文档"。但不同节点可能使用不同的 MCP provider（如 `linkly-ai`、`exa`、`grok-search`），每个 provider 的实际工具名也不相同（如 Exa 的搜索工具名为 `web_search_exa`，而不是 `search`）。

如果直接在 Skill 文档中硬编码工具名，会导致 Skill 无法跨 provider 复用。因此引入了**模板变量机制**：Skill 文档中使用 `{{MCP_*}}` 占位符，在 workspace 同步时根据节点的 MCP 配置将其替换为实际工具名。

## 2. 模板变量的定义

模板变量分为两组：知识库（knowledge）和网页搜索（web_search）。每组的 token 前缀分别是 `MCP_KNOWLEDGE` 和 `MCP_WEB_SEARCH`。

### 2.1 知识库模板变量 (MCP_KNOWLEDGE_*)

定义在 `common/mcp_manifest.py` 第 15-46 行的 `_DEFAULT_PROFILE_SPECS[KNOWLEDGE_PROFILE_ID]` 中：

| 模板变量 | 含义 | 示例值 |
|----------|------|--------|
| `{{MCP_KNOWLEDGE_PROVIDER}}` | 知识库 provider 名称 | `linkly-ai` |
| `{{MCP_KNOWLEDGE_TOOL_PATTERN}}` | 工具匹配模式 | `mcp__linkly-ai__*` |
| `{{MCP_KNOWLEDGE_SEARCH_TOOL}}` | 搜索工具全名 | `mcp__linkly-ai__search` |
| `{{MCP_KNOWLEDGE_OUTLINE_TOOL}}` | 大纲工具全名 | `mcp__linkly-ai__outline` |
| `{{MCP_KNOWLEDGE_GREP_TOOL}}` | 精确查找工具全名 | `mcp__linkly-ai__grep` |
| `{{MCP_KNOWLEDGE_READ_TOOL}}` | 阅读工具全名 | `mcp__linkly-ai__read` |

### 2.2 网页搜索模板变量 (MCP_WEB_SEARCH_*)

定义在 `_DEFAULT_PROFILE_SPECS[WEB_SEARCH_PROFILE_ID]` 中，与知识库变量结构完全对称：

| 模板变量 | 含义 | 示例值 |
|----------|------|--------|
| `{{MCP_WEB_SEARCH_PROVIDER}}` | 搜索 provider 名称 | `exa` |
| `{{MCP_WEB_SEARCH_TOOL_PATTERN}}` | 工具匹配模式 | `mcp__exa__*` |
| `{{MCP_WEB_SEARCH_SEARCH_TOOL}}` | 搜索工具全名 | `mcp__exa__web_search_exa` |
| `{{MCP_WEB_SEARCH_OUTLINE_TOOL}}` | 大纲/爬取结构工具全名 | `mcp__exa__crawling_exa` |
| `{{MCP_WEB_SEARCH_GREP_TOOL}}` | 精确定位工具全名 | `mcp__exa__crawling_exa` |
| `{{MCP_WEB_SEARCH_READ_TOOL}}` | 阅读工具全名 | `mcp__exa__crawling_exa` |

### 2.3 扩展模板变量

除了基础工具名外，`_render_profile_template()` 还生成以下上下文相关的模板变量（`mcp_manifest.py` 第 205-222 行）：

| 模板变量 | 内容 | 用途 |
|----------|------|------|
| `{{MCP_*_CHAIN_TEXT}}` | 工具调用链文本 | 提示 Agent 推荐的调用顺序 |
| `{{MCP_*_ANCHOR_LABEL}}` | 锚点字段名 | 提示阅读锚点（如 `doc_id` 或 URL） |
| `{{MCP_*_ANCHOR_TEXT}}` | 锚点使用说明 | 指导如何传递锚点 |
| `{{MCP_*_FOLLOWUP_TEXT}}` | 后续操作说明 | 指导获取初步结果后的下一步 |
| `{{MCP_*_SEARCH_SIGNATURE}}` | search 工具签名示例 | 供 Agent 参考的调用格式 |
| `{{MCP_*_OUTLINE_SIGNATURE}}` | outline 工具签名示例 | |
| `{{MCP_*_GREP_SIGNATURE}}` | grep 工具签名示例 | |
| `{{MCP_*_READ_SIGNATURE}}` | read 工具签名示例 | |
| `{{MCP_*_OUTLINE_EXAMPLE}}` | outline 示例调用 | |
| `{{MCP_*_GREP_EXAMPLE}}` | grep 示例调用 | |
| `{{MCP_*_READ_EXAMPLE}}` | read 示例调用 | |

## 3. render_mcp_text() 实现

`common/mcp_manifest.py` 第 729-754 行。这是模板渲染的统一入口。

### 3.1 函数签名

```python
def render_mcp_text(text: str, *, node_mcp: Mapping[str, Any] | None) -> str:
```

### 3.2 渲染流程

```
render_mcp_text(text, node_mcp)
│
├── 1. 构建渲染上下文
│   ├── knowledge_ctx = profile_prompt_context(node_mcp, profile_id="knowledge")
│   │   └── 从 node_mcp.profiles.knowledge 提取 provider 和 aliases
│   │   └── 调用 _render_spec() 生成所有模板值
│   └── web_search_ctx = profile_prompt_context(node_mcp, profile_id="web_search")
│       └── 同上，针对 web_search profile
│
├── 2. Legacy 替换（硬编码 linkly-ai 引用）
│   ├── "mcp__linkly-ai__search" → knowledge_ctx["search_tool"]
│   ├── "mcp__linkly-ai__outline" → knowledge_ctx["outline_tool"]
│   ├── "Linkly project MCP" → "{provider} project MCP"
│   └── ...
│
├── 3. MCP_KNOWLEDGE_* 模板变量替换
│   └── 遍历 _slot_replacements(knowledge_ctx, "knowledge")
│       └── {{MCP_KNOWLEDGE_SEARCH_TOOL}} → "mcp__linkly-ai__search"
│       └── {{MCP_KNOWLEDGE_PROVIDER}} → "linkly-ai"
│       └── ...
│
├── 4. MCP_WEB_SEARCH_* 模板变量替换
│   └── 遍历 _slot_replacements(web_search_ctx, "web_search")
│       └── {{MCP_WEB_SEARCH_SEARCH_TOOL}} → "mcp__exa__web_search_exa"
│       └── ...
│
└── 5. 返回渲染后的文本
```

### 3.3 Legacy 替换的重要性

Legacy 替换（第 736-747 行）处理历史遗留代码中直接引用的 `mcp__linkly-ai__*` 工具名。当知识库 provider 不是 `linkly-ai` 时，这些硬编码引用需要被替换为当前 provider 的工具名：

```python
legacy_replacements = {
    "mcp__linkly-ai__search": knowledge_ctx["search_tool"],
    "mcp__linkly-ai__outline": knowledge_ctx["outline_tool"],
    "mcp__linkly-ai__grep": knowledge_ctx["grep_tool"],
    "mcp__linkly-ai__read": knowledge_ctx["read_tool"],
    "mcp__linkly-ai__*": knowledge_ctx["tool_pattern"],
    "Linkly project MCP": f"{knowledge_ctx['provider']} project MCP",
    "Linkly MCP": f"{knowledge_ctx['provider']} MCP",
    ...
}
```

这确保了旧的 Skill 文档即使引用了 `mcp__linkly-ai__search`，在不同 provider 下也能被正确替换。

## 4. profile_prompt_context() — 渲染上下文的构建

`mcp_manifest.py` 第 581-662 行。该函数从 `node_mcp` 中提取指定 profile 的配置，生成完整的渲染上下文字典。

返回值包含以下字段：

```python
{
    "provider": "linkly-ai",                  # provider 名称
    "tool_pattern": "mcp__linkly-ai__*",      # 工具匹配模式
    "search_tool": "mcp__linkly-ai__search",  # 搜索工具全名（考虑 preferred_tool）
    "outline_tool": "mcp__linkly-ai__outline",
    "grep_tool": "mcp__linkly-ai__grep",
    "read_tool": "mcp__linkly-ai__read",
    "chain_text": "search -> outline/grep -> read",
    "anchor_label": "doc_id",
    "anchor_text": "...",
    "followup_text": "...",
    "search_signature": "...",
    ...
}
```

`search_tool` 的计算考虑了 `preferred_tool`：如果 profile 配置了 `preferred_tool`（如 `search` → `web_search_exa`），最终返回的工具名会反映出这个偏好。

### 4.1 Provider 特定的规格覆盖

`_PROFILE_PROVIDER_SPECS`（第 63-117 行）为不同 provider 提供了差异化的工具映射和描述文本。以 Exa 为例：

```python
"exa": {
    "role_tool_ids": {
        "search": "web_search_exa",     # search 工具的实际 ID 不是 "search"
        "outline": "crawling_exa",      # outline 和 grep 共享同一个工具
        "grep": "crawling_exa",
        "read": "crawling_exa",
    },
    "followup_text": "...mcp__exa__get_code_context_exa 仅在检索代码仓时使用...",
    "search_signature": "...包含 freshness, numResults 参数...",
}
```

Exa 的 `outline`、`grep`、`read` 三个语义角色都映射到 `crawling_exa` 这一个实际工具，说明 Exa 的爬虫同时承担了结构查看、精确定位和正文阅读的功能。

## 5. MCP 工具别名与 tool_alias_name()

MCP 工具的标准命名遵循 `mcp__<server>__<tool_id>` 格式。`tool_alias_name()` 函数（`mcp_manifest.py` 第 136-137 行）生成标准的别名：

```python
def tool_alias_name(server_name: str, tool_id: str) -> str:
    return f"mcp__{_clean_text(server_name)}__{_clean_text(tool_id)}"
```

例如：
- `tool_alias_name("linkly-ai", "search")` → `"mcp__linkly-ai__search"`
- `tool_alias_name("exa", "web_search_exa")` → `"mcp__exa__web_search_exa"`

`mcp_tool_id()` 函数（第 172-179 行）根据 provider 和语义角色（search/outline/grep/read）解析出实际的工具 ID：

```python
def mcp_tool_id(server_name, role, *, profile_id=None):
    # 1. 确定 profile_id
    # 2. 查 provider_spec 的 role_tool_ids
    # 3. 返回映射后的工具 ID
```

对于 Exa，`mcp_tool_id("exa", "search")` → `"web_search_exa"`（不是 `"search"`）。

## 6. _render_workspace_markdown() 的调用链

`workspace_skills.py` 第 87-93 行：

```python
def _render_workspace_markdown(root: Path, *, node_mcp: dict | None) -> None:
    for path in root.rglob("*.md"):
        raw = path.read_text(encoding="utf-8")
        rendered = render_mcp_text(raw, node_mcp=node_mcp)
        if rendered == raw:
            continue  # 无变化，跳过写入
        path.write_text(rendered, encoding="utf-8")
```

该函数在两个场景被调用：

1. **Skills 渲染**：`_copy_runtime_skill_projection()` 完成后，对 `.claude/skills/` 下所有 `.md` 文件执行渲染。
2. **Agents 渲染**：`_sync_workspace_agents()` 完成后，对 `.claude/agents/` 下所有 `.md` 文件执行渲染。

**性能策略**：如果渲染前后文本相同（即文件不包含任何 `{{MCP_*}}` 占位符且不需要 legacy 替换），则**跳过写入**，避免无意义的磁盘 I/O。

## 7. 渲染结果示例

假设 Skill 文档中有如下原始文本：

```markdown
使用 `{{MCP_KNOWLEDGE_SEARCH_TOOL}}` 检索知识库。
然后调用 `{{MCP_KNOWLEDGE_OUTLINE_TOOL}}` 查看结构，
最后用 `mcp__linkly-ai__read` 阅读正文。
```

当 node_mcp 配置的 knowledge provider 为 `linkly-ai` 时，渲染结果为：

```markdown
使用 `mcp__linkly-ai__search` 检索知识库。
然后调用 `mcp__linkly-ai__outline` 查看结构，
最后用 `mcp__linkly-ai__read` 阅读正文。
```

当 knowledge provider 切换为其他提供者（如假设有一个名为 `vector-db` 的 provider），且其 search 工具 ID 为 `vector_search` 时：

```markdown
使用 `mcp__vector-db__vector_search` 检索知识库。
然后调用 `mcp__vector-db__outline` 查看结构，
最后用 `mcp__vector-db__read` 阅读正文。
```

Legacy 替换同样生效：第 3 行的 `mcp__linkly-ai__read` 被替换为 `mcp__vector-db__read`。

## 8. MCP Manifest 的构建入口

虽然 `render_mcp_text()` 在 workspace sync 中消费 `node_mcp`，但 `node_mcp` 的构建发生在更上游的 MCP manifest 流程中。相关函数：

| 函数 | 位置 | 职责 |
|------|------|------|
| `build_mcp_manifest_from_dual_config()` | `mcp_manifest.py:432` | 从 knowledge + search 双配置构建完整 manifest |
| `resolve_node_mcp_runtime()` | `mcp_manifest.py:491` | 根据节点级开关解析运行时 MCP 配置 |
| `build_project_mcp_config()` | `mcp_registry.py` | 构建项目级 MCP 配置 payload |

这些属于第 3 层（Skill 自动绑定）和第 4 层（MCP 配置）的范畴，此处不展开。
