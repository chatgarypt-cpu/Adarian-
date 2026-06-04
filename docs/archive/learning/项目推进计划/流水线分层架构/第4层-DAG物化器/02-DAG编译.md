# 第4层 DAG 物化器 -- DAG 编译

## 1. 编译概览

`build_generated_dag()` 将 `WorkflowPlan` 编译为 `GeneratedDAG` 的核心过程包含三个关键步骤：**校验 (validation)**、**拓扑排序 (topological sort)**、**节点物化 (materialization)**。本章逐一展开。

## 2. validate_plan_dag() 完整校验流程

入口函数 `validate_plan_dag()`（`workflow_materializer.py:51-82`）串联 10 项校验，任何一项失败即抛 `ValueError`。

### 2.1 唯一 node_id

```python
_ensure_unique_node_ids(node_ids)  # 第62行
```

收集 `plan.nodes` 的所有 `id`，如果 `len(node_ids) != len(set(node_ids))` 则报 "duplicate node ids"。

### 2.2 节点语义校验

```python
_validate_node_semantics(plan=prepared_plan)  # 第64行
```

规则：`WorkflowNodeKind.INTERNAL` 类型的节点**必须** `enabled=false`。INTERNAL 节点是 Planner 的中间占位，不应作为可执行 Agent 节点参与调度。

### 2.3 节点白名单校验

```python
_validate_node_allowlist(...)  # 第65-71行
```

`_is_allowed_node_id()` 判定逻辑（`workflow_materializer.py:180-191`）：

| allowed_mode | 规则 |
|-------------|------|
| `"open"` | 任意 node_id 均合法 |
| `"skills"` | node_id 必须在 `skill_entries` 中存在 |
| `"skills_plus_custom"` | node_id 必须在 skill_entries 中 **或** 以 `custom_prefix` 开头 |

此外还会校验每个 enabled AGENT 节点是否绑定了已知 skill 或提供了非空 `description`（用于 generic execution fallback），且至少存在一个可执行节点。

### 2.4 Skill 扇出校验

```python
_validate_skill_fan_out(prepared_plan, skill_entries=entries)  # 第72行
```

对于 `blockProfile.canFanOut` 明确设为 `False` 的 skill，不允许出现在多个 enabled AGENT 节点中。换句话说，单实例 skill 只能在 DAG 中出现一次。

### 2.5 节点 Skill 集合大小校验

```python
_validate_node_skill_set_size(prepared_plan, skill_entries=entries)  # 第73行
```

每个节点的 skill 集合大小不得超过 `WORKFLOW_NODE_MAX_SKILLS = 6`。

### 2.6 边校验

```python
_validate_edges(plan=prepared_plan, node_set=node_set)  # 第74行
```

四条规则（`workflow_materializer.py:214-227`）：
1. `edge.from_` 必须存在于 node_set
2. `edge.to` 必须存在于 node_set
3. `self-loop` 不允许（`from_ == to`）
4. `edge_type` 必须是 `WORKFLOW_EDGE_TYPES` 之一：`data_dependency`、`reference`、`conditional`
5. `conditional` 类型的边必须提供 `condition` 字段

### 2.7 最大扇出限制

```python
_validate_max_blocking_fan_out(prepared_plan)  # 第75行
```

单节点的 blocking 扇出（仅统计 `edge_type != "reference"` 的出边）不得超过 `_MAX_BLOCKING_FAN_OUT = 10`。

### 2.8 Agenda Setter 宽扇出限制

```python
_validate_agenda_setter_wide_fan_out(prepared_plan, skill_entries=entries)  # 第76行
```

当包含 `agenda_setter` skill 的节点扇出超过 `_AGENDA_SETTER_WIDE_FAN_OUT_LIMIT = 3` 时，多的目标必须是 search 或 `data_discovery` 入口节点（即 `_AGENDA_DIRECT_ENTRY_SKILL_IDS` 内的 skill）。这是为了约束 agenda_setter 不直接扇出到大量分析节点。

### 2.9 Master Analyst 强制存在

```python
_validate_master_analyst_presence(prepared_plan, skill_entries=entries)  # 第77行
```

当 enabled AGENT 节点数量 >= `_MASTER_ANALYST_REQUIRED_NODE_COUNT = 10` 时，DAG 中**必须**包含 `master_analyst` 节点。这是防止大型 DAG 缺少综合汇聚节点的硬约束。

### 2.10 无环检测（拓扑排序 BFS）

```python
_ensure_acyclic(node_set=node_set, edges=[...])  # 第79-82行
```

仅统计 blocking 边（`_edge_blocks_execution()` 为 `True`，即 `edge_type != "reference"`）。使用标准 Kahn 算法 BFS：构建入度表，从入度为 0 的节点开始 queue，逐层消去。处理节点数 != 总节点数则存在环。

## 3. assign_layers_orders() 拓扑排序与层级分配

`workflow_materializer.py:400-418`

```python
def assign_layers_orders(plan: WorkflowPlan) -> dict[str, tuple[int, int]]:
```

返回字典 `{node_id: (layer, order)}`，其中：
- **layer** = BFS 层级（入度为 0 的根节点 layer=0，依赖越深 layer 越大）
- **order** = 层内顺序（按原始 `plan.nodes` 中的出现顺序稳定排序）

算法细节：
1. 只统计 blocking 边（`_edge_blocks_execution()` 过滤 reference）
2. 初始 queue 是所有入度为 0 的节点，按 `preferred_order` 排序
3. 每轮 pop queue[0]（FIFO），逐出边更新下游 layer = max(当前 layer, 上游 layer + 1)
4. 新入度为 0 的节点入队后**重新排序** queue，保证同层内按原始顺序

最终通过 `_layout_by_layer()` 将 layer→order 扁平化为 `(layer, order)` 二元组。

## 4. _build_runtime_nodes() 与 _materialize_node()

`workflow_materializer.py:798-817`

```python
def _build_runtime_nodes(...) -> list[DAGNode]:
    layout = assign_layers_orders(plan)
    nodes = [_materialize_node(node=node, layer_order=layout.get(node.id, (0, 0)), ...) for node in plan.nodes]
    nodes.sort(key=lambda item: (int(item.layer), int(item.order), str(item.id)))
    return nodes
```

每个 `WorkflowPlanNode` 通过 `_materialize_node()` 转换为 `DAGNode`（`workflow_materializer.py:824-873`）。

物化分两类：

**visual-only 节点**（满足 `_is_visual_only_node()` 条件 -- INTERNAL 类型 / enabled=false / 开放模式下的自定义前缀节点）：
- 仅产出基本字段: id, label, kind, enabled, critical, layer, order
- `agent_config` 只含 `description`（若有）
- 不参与实际调度

**可执行 AGENT 节点**：
- `kind` 强制为 `"agent"`, `enabled` 强制为 `True`
- `agent_config` 通过 `_agent_config()` 构建
- `block_profile` 从 skill registry 提取

## 5. _agent_config() 构建

`workflow_materializer.py:876-900`

agent_config 是一个 dict，包含以下字段（所有字段仅在存在/非空时写入）：

| 字段 | 来源 | 说明 |
|------|------|------|
| `description` | node.description 或 skill.description | agent 任务描述 |
| `skill` | 解析后的 skill_id 或 `GENERIC_AGENT_SKILL_ID` | 主 skill ID |
| `skills` | `resolve_node_skill_ids()` 去重结果 | 完整 skill 列表 (去除 generic) |
| `external_search` | node.external_search | 是否需要外部搜索 |
| `requires_knowledge_search` | node.requires_knowledge_search | 是否需要知识库搜索 |
| `search_strategy` | `_search_strategy_for_skill()` | 搜索策略模板（仅搜索子节点） |

注意：`_runtime_agent_skill_id()` 会将搜索 agent skill（`external_search_agent` / `knowledge_search_agent`）的 skill_id 置为空字符串，因为它们是运行时内部 skill，不应作为 agent 的主 skill 传递。

## 6. GeneratedDAG 最终结构

`workflow_models.py:86-113`

```python
@dataclass
class GeneratedDAG:
    workflow_id: str                    # new_workflow_id() 生成
    name: str                           # plan.name 或 name_fallback 或时间戳
    nodes: list[DAGNode]                # 已排序的物化节点列表
    edges: list[DAGEdge]                # from_node/to_node/edge_type/condition
    estimated_duration: int             # 预估执行时长(秒)
    created_at: str                     # UTC ISO 时间戳
    generation_source: str              # "planning" / "manual" 等
    generation_details: dict[str, Any]  # 扩展信息 (planner 元数据等)
    thinking: str                       # LLM 思考过程原文
    thinking_duration_ms: int           # LLM thinking 耗时(ms)
```

名称解析优先级（`_resolve_plan_name()`）：`plan.name` > `name_fallback` > `f"workflow_{timestamp}"`。
