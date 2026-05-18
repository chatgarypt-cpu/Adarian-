# 第4层 DAG 物化器 -- 搜索子节点注入与扇出控制

## 1. 设计动机

当一个 `WorkflowPlanNode` 标记 `external_search=true` 或 `requires_knowledge_search=true` 时，物化器不会让该节点自行执行搜索，而是**自动创建专用搜索子节点**，将其注入到 DAG 中。这样做的理由：

1. **职责分离**: 搜索节点专注于并发多路搜索，分析节点专注于推理与综合
2. **并发控制**: 搜索策略模板明确要求 3 路并发 subagent，由专用节点统一编排
3. **依赖清晰**: 搜索作为显式前置节点，数据流可审计

## 2. _inject_search_sub_nodes() 注入机制

`workflow_materializer.py:522-558`

入口逻辑（在 `build_generated_dag()` 中 auto_bind 之后、validate 之前调用）：

```python
prepared_plan = _inject_search_sub_nodes(prepared_plan, skill_entries=entries)
```

### 2.1 触发条件

对 `plan.nodes` 中的每个节点：

| 条件 | 注入节点 ID | 使用的 skill |
|------|-----------|-------------|
| `node.external_search == True` | `{node.id}__ext_search` | `external_search_agent` |
| `node.requires_knowledge_search == True` | `{node.id}__kb_search` | `knowledge_search_agent` |

节点 ID 通过 `_search_sub_node_id()` 生成，总长度限制 `_SEARCH_NODE_ID_MAX_LENGTH = 64`。超长时从原始 node_id 右侧截断。

### 2.2 注入过程

对每个匹配节点，执行以下步骤：

1. **跳过 search agent 自身** -- `_resolve_or_preserve_node_skill_id()` 识别出节点本身是 `external_search_agent` 或 `knowledge_search_agent`，不再为其注入搜索子节点，避免无限递归。

2. **创建搜索子节点** -- 调用 `_build_search_plan_node()`，为每种搜索类型创建一个独立的 `WorkflowPlanNode`：
   - `kind=AGENT`, `enabled=True`, `critical=True`
   - `skill_id` 为相应的搜索 agent ID
   - `label` 格式: `"搜索(外部): {原标题[:20]}"` 或 `"搜索(知识库): {原标题[:20]}"`
   - `description` 控制在 300 字符内（中文主题摘要）

3. **更新原节点** -- 通过 `model_copy` 将原节点的 `external_search` / `requires_knowledge_search` 置为 `False`，因为搜索职责已委托给前置搜索子节点。

4. **边重连** -- 这是注入的核心逻辑（`_search_sub_node_edges()`）：

```
注入前:
    upstream_nodes --> target_node --> downstream_nodes

注入后:
    upstream_nodes --> __ext_search --> target_node --> downstream_nodes
                    \-> __kb_search ->/
```

重连规则：
- 收集 `target_node` 的所有入边（blocking 边）
- 将入边**克隆**到每个搜索子节点（`_clone_blocking_incoming_edges()`）
- 在搜索子节点与 target_node 之间创建新的 `data_dependency` 边
- 删除 target_node 原有的 blocking 入边（非 blocking 的 reference 边保留）

5. **重组 Plan** -- 通过 `plan.model_copy(update={"nodes": next_nodes, "edges": next_edges})` 返回新 Plan，保持 immutability。

## 3. 搜索策略模板

搜索结果的质量取决于注入到 `agent_config["search_strategy"]` 的搜索策略模板。有两套模板：

### 3.1 外部搜索策略 (`_EXT_SEARCH_STRATEGY`)

`workflow_materializer.py:596-611`

要求搜索协调者在一个 turn 中同时生成 3 个 subagent，并行搜索：

| Subagent | 职责 |
|----------|------|
| Core topic search | 精准关键词深度搜索 |
| News/timeline search | 最新动态和时间线 |
| Alternative/English search | 英文关键词或同义词补充 |

执行规则：所有 subagent 一次性并行 spawn；每个 subagent 执行 2-3 次 MCP 搜索调用。合成结果按可信度排序：官方源 > 权威媒体 > 一般媒体 > 社交媒体。

### 3.2 知识库搜索策略 (`_KB_SEARCH_STRATEGY`)

`workflow_materializer.py:613-626`

同样要求并行 subagent，但面向内部知识库：

| Subagent | 职责 |
|----------|------|
| Topic search | 主题关键词检索文档和数据 |
| Historical data search | 历史记录、趋势、时间序列 |

执行规则：先用 knowledge 工具做主题定位，再用精确路径读取关键文件。输出需列出每个发现文件的路径、核心内容和相关度。交叉引用多份资料以识别一致性与差异。

### 3.3 策略匹配

`_search_strategy_for_skill()` 根据 skill_id 返回对应策略：
- `"external_search_agent"` -> `_EXT_SEARCH_STRATEGY`
- `"knowledge_search_agent"` -> `_KB_SEARCH_STRATEGY`
- 其他 -> `None`

## 4. 搜索子节点在物化阶段的处理

`_materialize_node()` 对搜索子节点的特殊处理（`workflow_materializer.py:854,873`）：

1. **search_strategy 注入**: 来自 `_search_strategy_for_skill(skill_id)` 的并发搜索模板被写入 `agent_config["search_strategy"]`
2. **skill_id 清空**: `_runtime_agent_skill_id()` 将搜索 agent skill ID 映射为空字符串，表示这些是"匿名"搜索节点，不暴露给下游使用者
3. **search_strategy 字段**: `external_search` / `requires_knowledge_search` 在 `_agent_config()` 中重新设置为注入节点的对应布尔值

## 5. CSV (Concurrent Search Vector) 扇出约束

搜索子节点注入与 DAG 校验层紧密配合。以下约束确保搜索不会破坏 DAG 的结构完整性：

### 5.1 搜索子节点不被白名单拦截

`_is_search_helper_node()` 识别搜索子节点（后缀 `__ext_search` / `__kb_search` 或 skill_id 在 `_PRESERVED_UNREGISTERED_SKILL_IDS` 中），将其从白名单校验中豁免（`workflow_materializer.py:104-113`）。

### 5.2 搜索子节点不参与节点计数

`_enabled_agent_nodes()` 统计 executable agent 节点时显式过滤掉搜索子节点（`workflow_materializer.py:299-305`），因此搜索子节点的存在不影响 `master_analyst` 强制规则的触发阈值。

### 5.3 Agenda Setter 扇出豁免

`_AGENDA_DIRECT_ENTRY_SKILL_IDS` 包含 `data_discovery`、`external_search_agent`、`knowledge_search_agent`。当 agenda setter 扇出超过 3 个时，多出的目标如果指向这些 ID，则被视为合法（`_is_agenda_direct_entry_target()` -- `workflow_materializer.py:272-283`）。

### 5.4 搜索策略独立于 description 长度限制

`WorkflowPlanNode.description` 有 300 字符限制。搜索策略模板（`_EXT_SEARCH_STRATEGY` 约 1000 字符 / `_KB_SEARCH_STRATEGY` 约 700 字符）不走 description 通道，而是通过 `agent_config["search_strategy"]` 注入，避免被截断。

## 6. estimated_duration 计算

`workflow_materializer.py:982-983`

```python
_SECONDS_PER_AGENT_STEP = 60

def _estimated_duration(nodes: list[DAGNode]) -> int:
    return sum(1 for node in nodes if node.kind == "agent" and node.enabled) * 60
```

每个 enabled agent 节点按 60 秒估算。包含搜索子节点（它们也是 kind=agent, enabled=True）。因此注入搜索子节点后 `estimated_duration` 会自动增加：每个 `__ext_search` 和 `__kb_search` 各加 60 秒。例如一个 5 节点 DAG 中有一个节点同时需要外部搜索和知识库搜索，注入后变为 7 节点，预估时长从 300s 变为 420s。

## 7. 完整示例

假设 Planner 生成如下 DAG：

```
entry --> data_discovery --> swing_analyst{external_search=true} --> report
```

物化后的 DAG（简化表示）：

```
entry --> data_discovery --> swing_analyst__ext_search --> swing_analyst --> report
```

其中：
- `swing_analyst__ext_search` 的 `agent_config` 包含 `EXT_SEARCH_STRATEGY` 模板
- `swing_analyst__ext_search` 的 `skill` 字段为空（搜索节点匿名化）
- `swing_analyst` 的 `external_search=false`（职责已委托）
- `estimated_duration` = 4 节点 x 60s = 240s (vs 注入前 3 节点 = 180s)
