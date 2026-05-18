# 05 - 工作流计划 Schema

## 概述

`orchestrator/dag/workflow_models.py` 定义了 Planner 产出的完整数据结构体系。该文件包含三层模型：Planner 输出模型（`WorkflowPlan`/`WorkflowPlanNode`/`WorkflowPlanEdge`）、DAG 运行时模型（`DAGNode`/`DAGEdge`/`GeneratedDAG`）以及 Planner 草稿模型（`WorkflowDraftPlan`/`WorkflowDraftNode`/`WorkflowDraftEdge`）。

本文聚焦于 Planner 层直接产出的 `WorkflowPlan` 及运行时约束。

## 常量定义

```python
# 节点 ID 安全正则：小写字母或数字开头，后续可含小写字母/数字/下划线/短横线，最长 64 字符
SAFE_NODE_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"

# 默认非关键节点（不阻塞工作流的节点）
NON_CRITICAL_DEFAULT_NODE_IDS = frozenset({"realtime_status_researcher"})

# 边类型常量
EDGE_TYPE_DATA_DEPENDENCY = "data_dependency"    # 数据依赖（阻塞型）
EDGE_TYPE_REFERENCE = "reference"                 # 引用（非阻塞型）
EDGE_TYPE_CONDITIONAL = "conditional"             # 条件依赖（带 condition 字段时阻塞）

WORKFLOW_EDGE_TYPES = frozenset({data_dependency, reference, conditional})

# 节点/边约束
PLANNER_WORKFLOW_MAX_NODES = 30                   # Planner 输出阶段的最大节点数
PLANNER_WORKFLOW_MAX_EDGES = 200                  # Planner 输出阶段的最大边数
RUNTIME_WORKFLOW_MAX_NODES = 200                  # 运行时物化后的最大节点数
RUNTIME_WORKFLOW_MAX_EDGES = 2000                 # 运行时物化后的最大边数
WORKFLOW_NODE_MAX_SKILLS = 6                      # 单节点的最大 skill 绑定数
```

**注意 Plannner 与 Runtime 约束的差异**：Planner 输出的 JSON 受 `PLANNER_WORKFLOW_MAX_NODES=30` 限制，但系统后续注入的运行时系统节点（如 session setup、cleanup）可超出此限制，只要总节点数不超过 `RUNTIME_WORKFLOW_MAX_NODES=200`。

## WorkflowPlan -- 顶层计划模型

```python
class WorkflowPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")       # 禁止额外字段

    schema_version: str = Field("1", max_length=20) # 固定 "1"
    name: str = Field("", max_length=120)           # 工作流名称
    nodes: list[WorkflowPlanNode] = Field(
        ...,                                        # 必填
        min_length=1,                               # 最少 1 个节点
        max_length=RUNTIME_WORKFLOW_MAX_NODES       # 最多 200 个节点
    )
    edges: list[WorkflowPlanEdge] = Field(
        default_factory=list,                       # 默认为空
        max_length=RUNTIME_WORKFLOW_MAX_EDGES       # 最多 2000 条边
    )
    rationale: str | None = Field(None, max_length=800)  # 可选，规划思路说明
```

`extra="forbid"` 确保 LLM 不会输出任何未定义的字段，这是一道重要的 schema 防线。

## WorkflowPlanNode -- 节点模型

```python
class WorkflowPlanNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=SAFE_NODE_ID_PATTERN)
    label: str = Field("", max_length=60)
    description: str | None = Field(None, max_length=300)
    kind: WorkflowNodeKind = Field(default=WorkflowNodeKind.AGENT)
    enabled: bool = Field(default=True)
    critical: bool | None = Field(default=None)
    skill: str | None = Field(None, exclude=True)
    skill_id: str | None = Field(None, exclude=True)
    skills: list[str] = Field(default_factory=list, max_length=WORKFLOW_NODE_MAX_SKILLS, exclude=True)
    external_search: bool | None = Field(default=None)
    requires_knowledge_search: bool | None = Field(default=None)
```

### 字段详解

| 字段 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| `id` | `str` | 是 | `pattern=SAFE_NODE_ID_PATTERN`（小写字母/数字/下划线/短横线，最长 64 字符） | 节点唯一标识。在 skills_only 模式下必须来自 Skill 目录的 id；在 open 模式下建议格式为 `skill_id__职责短名` 或 `custom_prefix__职责短名` |
| `label` | `str` | 否 | `max_length=60` | 中文短语标签，建议以动词开头，如"议题设定"、"数据采集"、"交叉验证" |
| `description` | `str\|None` | 否 | `max_length=300` | 节点职责与输出说明。执行 Agent 节点必须提供非空 description，否则校验失败 |
| `kind` | `WorkflowNodeKind` | 否 | 枚举：`AGENT`/`INTERNAL` | `AGENT` 表示由 Agent 沙箱执行；`INTERNAL` 表示系统内部占位节点（通常 `enabled=false`） |
| `enabled` | `bool` | 否 | 默认 `True` | 是否参与执行。`INTERNAL` 占位节点通常设为 `false` |
| `critical` | `bool\|None` | 否 | -- | 是否为关键节点。关键节点失败会中断整个工作流。`None` 时由 `default_node_critical()` 根据 id 判断。`realtime_status_researcher` 默认为非关键 |
| `skill_id` | `str\|None` | 否 | `exclude=True`（序列化时排除） | 主 Skill 标识。在 skills_only 模式下若 node.id 即 skill_id，可省略此字段。Planner 级别的软引用，最终绑定在第 3 层完成 |
| `skills` | `list[str]` | 否 | 最多 6 个，`exclude=True` | 备选/补充 Skill 列表。Planner 级别的软引用 |
| `external_search` | `bool\|None` | 否 | -- | 是否允许运行时外部搜索 |
| `requires_knowledge_search` | `bool\|None` | 否 | -- | 是否需要进行知识库搜索 |

### skill_id / skill / skills 的 exclude=True 设计

这三个字段标记了 `exclude=True`，意味着在 `model_dump()` 和 JSON 序列化时会被排除。这是因为 Planner 输出的 `skill_id` 只是"建议绑定"，真正的 skill 绑定在第 3 层"Skill 自动绑定"和第 4 层"DAG 物化器"中由系统完成（通过 `orchestrator/dag/skill_binding.py` 的 `canonical_skill_id()` 和 `workflow_materializer.py` 的 `build_generated_dag()`）。序列化时排除可防止不一致的 skill 引用向下游传播。

### default_node_critical()

```python
def default_node_critical(node_id: object) -> bool:
    return str(node_id or "").strip() not in NON_CRITICAL_DEFAULT_NODE_IDS
```

除 `realtime_status_researcher` 外，所有节点默认为关键节点。

## WorkflowPlanEdge -- 边模型

```python
class WorkflowPlanEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: str = Field(..., alias="from", pattern=SAFE_NODE_ID_PATTERN)
    to: str = Field(..., pattern=SAFE_NODE_ID_PATTERN)
    edge_type: str = Field(default=EDGE_TYPE_DATA_DEPENDENCY, alias="type")
    condition: str | None = Field(default=None, max_length=240)
```

### 字段详解

| 字段 | JSON 键 | 类型 | 约束 | 说明 |
|------|---------|------|------|------|
| `from_` | `"from"` | `str` | `pattern=SAFE_NODE_ID_PATTERN` | 边的起点节点 ID。必须引用 nodes 中已存在的 node.id |
| `to` | `"to"` | `str` | `pattern=SAFE_NODE_ID_PATTERN` | 边的终点节点 ID。必须引用 nodes 中已存在的 node.id |
| `edge_type` | `"type"` | `str` | 枚举：`data_dependency`/`reference`/`conditional`，默认 `data_dependency` | 边的语义类型 |
| `condition` | `"condition"` | `str\|None` | `max_length=240` | 条件表达式，仅当 `edge_type=conditional` 时有意义 |

`populate_by_name=True` 允许通过 Python 属性名（`from_`）和 JSON 键名（`"from"`）双向访问。

### 三种边类型

#### 1. data_dependency（数据依赖 -- 阻塞型）

```json
{"from": "agenda_setter", "to": "evidence_collector", "type": "data_dependency"}
```

表示 `to` 节点的执行**必须等待** `from` 节点完成并产出数据。这是最常见的边类型，也是默认值。满足"阻塞型上游边"要求时必须使用此类型或 `conditional`。

#### 2. reference（引用 -- 非阻塞型）

```json
{"from": "data_discovery", "to": "evidence_collector", "type": "reference"}
```

表示 `to` 节点**可以参考** `from` 节点的输出，但不强制等待。`reference` 边**不算**阻塞型上游边，不能用来满足前驱约束。

#### 3. conditional（条件依赖）

```json
{"from": "evidence_collector", "to": "deepening_analysis", "type": "conditional", "condition": "data_gap_detected"}
```

表示当 `condition` 满足时，`to` 节点**必须等待** `from` 节点完成。带 `condition` 的 `conditional` 边算阻塞型上游边，可以满足前驱约束。

### 阻塞型前驱规则

来自 `engine_prompts.py` 的 `blocking_predecessor_prompt_lines()`：

- entry 节点**可以**作为根节点（无上游边）
- 除 entry 外，其他所有可执行节点**必须**至少有 1 条 `data_dependency` 或带 `condition` 的 `conditional` 上游边
- `reference` 不算阻塞型上游
- 阶段间依赖：evidence 节点从 entry/synthesis 连入；synthesis 节点从 evidence/deepening 连入；deepening 节点从 synthesis 连入；verification 节点从 evidence/synthesis/deepening 连入；review 节点从 output 连入

## WorkflowNodeKind 枚举

```python
class WorkflowNodeKind(str, Enum):
    AGENT = "agent"        # Agent 沙箱执行节点
    INTERNAL = "internal"  # 系统内部节点
```

- `AGENT`：标准执行节点，由 Agent 沙箱（Docker 容器中的 Claude Agent SDK）执行。绑定 skill 或通过通用 Agent prompt 执行
- `INTERNAL`：系统占位/标记节点。通常 `enabled=false`，不参与实际执行。在 skills_plus_custom 模式下用于添加非执行标记节点

## 运行时约束总结

| 约束常量 | 值 | 适用阶段 | 说明 |
|---------|---|---------|------|
| `SAFE_NODE_ID_PATTERN` | `^[a-z0-9][a-z0-9_-]\{0,63\}$` | 全阶段 | 节点 ID 命名规范 |
| `PLANNER_WORKFLOW_MAX_NODES` | 30 | Planner 输出 | LLM/SDK 产出 JSON 的节点上限 |
| `PLANNER_WORKFLOW_MAX_EDGES` | 200 | Planner 输出 | LLM/SDK 产出 JSON 的边上限 |
| `RUNTIME_WORKFLOW_MAX_NODES` | 200 | 运行时 | 含系统注入节点的总上限 |
| `RUNTIME_WORKFLOW_MAX_EDGES` | 2000 | 运行时 | 含系统注入边的总上限 |
| `WORKFLOW_NODE_MAX_SKILLS` | 6 | 全阶段 | 单节点的最大 skill 绑定数 |

## Planner 草稿模型（WorkflowDraftPlan）

除 `WorkflowPlan`（用于 LLM structured output + 运行时的 canonical model）外，`workflow_models.py` 还定义了 `WorkflowDraftPlan`/`WorkflowDraftNode`/`WorkflowDraftEdge` 三件套。它们使用 `ConfigDict(extra="forbid")` 但 `id` 字段不强制 `pattern=SAFE_NODE_ID_PATTERN`（`WorkflowDraftNode.id` 仅限制 `max_length=120`），允许 Planner 输出不规范 ID，由后续 `WorkflowPlanCompiler` 的 `compile()` pass 进行正规化。这在某些 Planner 策略（如需要通过编译器动态改写 node id）的场景下提供灵活性。

## DAG 运行时模型（GeneratedDAG / DAGNode / DAGEdge）

当 `WorkflowPlan` 经过正规化和验证后，由 `WorkflowPlanCompiler.materialize()`（调用 `workflow_materializer.py` 的 `build_generated_dag()`）转换为运行时模型：

```python
@dataclass
class GeneratedDAG:
    workflow_id: str                 # 系统生成的唯一 ID
    name: str                        # 来自 WorkflowPlan.name
    nodes: list[DAGNode]             # 物化后的 DAGNode 列表
    edges: list[DAGEdge]             # 物化后的 DAGEdge 列表
    estimated_duration: int = 300    # 预估耗时（秒）
    created_at: str                  # ISO 时间戳
    generation_source: str           # "planner_sdk" / "llm"
    generation_details: dict         # 生成元数据（model, attempts, thinking, warnings...）
    thinking: str                    # LLM 思考内容（SDK 通道为空）
    thinking_duration_ms: int        # 思考耗时（毫秒）
```

与 `WorkflowPlanNode` 的差异：`DAGNode` 增加了 `layer`、`order`（拓扑排序后的层级和顺序）、`agent_config`（注入的 Agent 配置）、`status`（运行时状态：pending/running/done/failed）和 `block_profile`（绑定的积木原型）等运行时字段。

## 数据结构流转全图

```
LLM/SDK 输出 JSON
    |
    v
extract_json_object()           # plan_generator_support.py
    |
    v
json.loads() -> dict            # plan_compiler.py
    |
    v
WorkflowPlan.model_validate()   # Pydantic 校验（id pattern / max_length / extra="forbid"）
    |
    v
_validate_explicit_skill_whitelist()   # plan_compiler.py
_validate_planner_size()               # plan_compiler.py (≤30 nodes / ≤200 edges)
    |
    v
canonicalize_workflow_plan()    # plan_validator.py（normalize node id / bind default critical...）
    |
    v
validate_generated_plan()       # plan_validator.py（拓扑校验 / 阻塞前驱校验 / richness 达标校验...）
    |
    v
build_generated_dag()           # workflow_materializer.py（WorkflowPlan -> GeneratedDAG）
    |
    v
assign_layers_orders()          # workflow_materializer.py（拓扑排序，赋予 layer/order）
    |
    v
GeneratedDAG                    # 最终物化产物，传递给调度层
```
