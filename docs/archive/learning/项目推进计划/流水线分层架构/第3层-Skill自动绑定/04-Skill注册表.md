# 04 - Skill 注册表

## 概述

Skill 注册表是 Auto-Binder 的**唯一数据源**。它定义了所有可用的 Agent Skill（约 60+ 个），包括 skill 的元数据、计划触发条件、运行时配置、block 结构 profile 等。注册表以 YAML 文件形式持久化，在运行时被解析为 Python 字典并通过 `SkillRegistry` 类暴露。

## 数据源结构

注册表由两个 YAML 文件组成，均位于 `common/` 目录：

| 文件 | 内容 |
|------|------|
| `common/skills_registry.yaml` | 主注册表：`defaults`（全局默认约束）、`planning_blocks`（DAG 结构块定义）、`quality_defaults`（报告质量标准）、`categories`（skill 分类元数据）、`skills`（所有 skill 条目） |
| `common/skills_assets.yaml` | 扩展资产：`assets`（用于 skill 间的共享文本片段或模板） |

**代码路径**：`common/skills_registry.py`

- `load_skills_registry()`（第 52-56 行）负责读取并合并两个 YAML 文件
- 注册表加载使用 `@lru_cache(maxsize=1)` 缓存，避免重复 I/O
- `_ensure_registry_cache_current()`（第 42-48 行）通过对比文件的 `(st_mtime_ns, st_size)` 元组检测源文件是否变化，变化时自动刷新缓存

## `SkillRegistry` 类

**代码位置**：`orchestrator/dag/types.py` 第 50-90 行

```python
class SkillRegistry:
    """Agent Skills 注册表。"""

    SKILLS = skill_registry_entries()

    @classmethod
    def get_skill(cls, skill_id: str) -> Optional[dict]:
        ensure_skills_runtime_state_current()
        return cls.SKILLS.get(skill_id)

    @classmethod
    def list_skills(cls) -> list[dict]:
        ensure_skills_runtime_state_current()
        return list(cls.SKILLS.values())

    @classmethod
    def planning_snapshot(cls) -> list[dict[str, Any]]:
        ...
```

**核心属性**：

- **`SKILLS`**：类变量，类型为 `dict[str, dict]` ——以 `skill_id` 为 key，规范化后的 skill 条目 dict 为 value。由 `skill_registry_entries()` 初始化。
- **`get_skill(skill_id)`**：按 id 查找单个 skill（返回 `Optional[dict]`）
- **`list_skills()`**：返回所有 skill 条目的 list
- **`planning_snapshot()`**：返回 Planning Agent 可用的 skill 快照（只包含 id、label、description、layer、category、blockProfile、planning trigger 等必要字段，用于组装 system prompt）
- **`planning_block_catalog()`**：返回 `planning_blocks`（archetypes + recipes）的快照

## 运行时刷新机制

**代码位置**：`orchestrator/dag/types.py` 第 33-48 行

```python
def refresh_skills_runtime_state(*, force: bool = False) -> str:
    global _SKILLS_RUNTIME_SOURCE_REVISION
    revision = _skills_runtime_source_revision()
    if not force and revision == _SKILLS_RUNTIME_SOURCE_REVISION:
        return revision
    skills_registry_module.load_skills_registry.cache_clear()
    refresh_skill_doc_runtime_state()
    _planning_skill_metadata.cache_clear()
    SkillRegistry.SKILLS = skill_registry_entries()
    _SKILLS_RUNTIME_SOURCE_REVISION = revision
    return revision

def ensure_skills_runtime_state_current() -> str:
    return refresh_skills_runtime_state(force=False)
```

**刷新触发条件**：

1. `_skills_runtime_source_revision()`（第 28-30 行）计算两个维度的 SHA1 hash：
   - `skills_registry_source_state()` —— `skills_registry.yaml` 和 `skills_assets.yaml` 的 `(mtime_ns, size)` 元组
   - `_skills_doc_source_state()` —— 所有 `*/SKILL.md` 文件的 `(路径, mtime_ns, size)` 元组列表
2. 当 hash 变化时（或 `force=True`），执行完整的刷新：
   - 清除 `load_skills_registry` 的 lru_cache
   - 调用 `refresh_skill_doc_runtime_state()` 刷新 skill 文档的运行时状态
   - 清除 `_planning_skill_metadata` 的 lru_cache
   - 重新通过 `skill_registry_entries()` 装配 `SkillRegistry.SKILLS`

**Auto-Binder 调用链中的 refresh**：
- `_runtime_skills()`（`skill_auto_binder.py` 第 81-84 行）内部调用 `ensure_skills_runtime_state_current()`
- 如果调用方通过 `skills=` 参数注入了外部 skill 字典，则跳过 refresh（测试优化路径）

## Skill 条目结构

每个 skill 在 YAML 中的原始字段经 `_normalized_skill_entry()`（`common/skills_registry.py` 第 136-165 行）规范化后，形成标准化的 dict 结构：

### 基础字段

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `id` | `str` | YAML key | skill 唯一标识符，如 `"district_race_analyst"` |
| `label` | `str` | `label` | 中文显示名，如 `"选区分析"` |
| `description` | `str` | `description` | 功能描述，用于 Planning Agent 的 skill selection |
| `layer` | `int` | `layer` | 规划层级（0-4）：0=澄清入口，1=数据采集，2=分析，3=综合输出，4=审校 |
| `category` | `str` | `category` | 分类标签：`analysis`、`collection`、`synthesis`、`report_output` 等 |

### `blockProfile`

规范化自 YAML 中的 `block_profile`（snake_case → camelCase），由 `_normalized_block_profile()` 处理（`common/skills_registry.py` 第 226-247 行）：

```yaml
# YAML 原始格式
block_profile:
  stage: evidence
  archetype: evidence_collector
  can_fan_out: false
  can_converge: false
  preferred_predecessors:
    - entry
    - synthesis
  preferred_successors:
    - synthesis
    - deepening
  preferred_recipes:
    - layered_diamond
    - split_merge_report
```

归一化后：

```python
{
  "stage": "evidence",
  "archetype": "evidence_collector",
  "canFanOut": False,
  "canConverge": False,
  "preferredPredecessors": ["entry", "synthesis"],
  "preferredSuccessors": ["synthesis", "deepening"],
  "preferredRecipes": ["layered_diamond", "split_merge_report"],
}
```

### `planning`

规范化自 YAML 中的 `planning`，由 `_normalized_skill_planning()` 处理（`common/skills_registry.py` 第 168-187 行）：

| 规范化字段 | YAML 源字段 | 说明 |
|-----------|-----------|------|
| `triggerWhen` | `trigger_when` | 自然语言触发条件描述（供 Planning Agent 阅读） |
| `triggerKeywords` | `trigger_keywords` | 关键词列表（供 Planning Agent 的 system prompt 匹配） |
| `preferredPredecessors` | `preferred_predecessors` | 偏好的上游 stage |
| `preferredSuccessors` | `preferred_successors` | 偏好的下游 stage |
| `canFanOut` | `can_fan_out` | 同 blockProfile |
| `canConverge` | `can_converge` | 同 blockProfile |

### `runtime`

规范化自 YAML 中的 `runtime`，由 `_normalized_skill_runtime()` 处理（`common/skills_registry.py` 第 190-210 行）：

| 规范化字段 | 说明 |
|-----------|------|
| `docPath` | SKILL.md 的相对路径 |
| `conflictPolicy` | 输出冲突处理策略 |
| `requiredOutputs` | 必须产出的文件列表（如 `["output/polls_summary.md"]`） |
| `allowedCapabilities` | 允许的工具能力列表 |
| `timeoutSeconds` | 超时秒数 |
| `maxParallelInstances` | 最大并行实例数 |

### `collaboration` / `evaluation`

由 `_normalized_skill_mapping()` 直接透传 YAML 中的 dict 值，无额外结构转换。这两个字段为可扩展的协作和评估配置预留入口。

## 示例：`district_race_analyst` 的完整条目

```yaml
district_race_analyst:
  label: 选区分析
  description: 分析单一选区的选情结构、历史走势、候选人优劣势与关键变量...
  category: analysis
  layer: 2
  planning:
    trigger_when: "需要分析单一选区的选情结构、历史走势、候选人优劣势..."
    trigger_keywords:
      - "选区分析"
      - "选区竞争"
      - "单一选区"
      - "地方选情"
  required_outputs:
    - output/district_analysis.md
  block_profile:
    stage: deepening
    archetype: thematic_deepener
    can_fan_out: true       # 允许多个选区并行分析
    can_converge: true      # 可以接收多个上游输入
    preferred_predecessors:
      - evidence
      - synthesis
    preferred_successors:
      - synthesis
      - output
```

## 注册表与 Auto-Binder 的协作方式

注册表在 Auto-Binder 中扮演两个角色：

### 1. 技能存在性验证

所有 Layer 1b、Layer 2、Layer 3 的候选 skill_id 在返回前必须通过 `_has_skill()` 验证。`_has_skill()`（`skill_auto_binder.py` 第 92-93 行）直接查询 `skills` 字典：

```python
def _has_skill(*, skills: dict[str, dict], skill_id: str) -> bool:
    return _skill_entry(skills=skills, skill_id=skill_id) is not None
```

### 2. `blockProfile` 的 `canFanOut` 读取

`_is_single_use_skill()` 从注册表的 `blockProfile.canFanOut` 字段判断 skill 是否为单次使用（详见文档 03）。

## 辅助工具函数

`orchestrator/dag/skill_binding.py` 提供两个与注册表联动的工具函数：

### `resolve_node_skill_id()`

```python
def resolve_node_skill_id(node, *, skills=None) -> str:
```

**逻辑**（`skill_binding.py` 第 62-67 行）：

1. 从 node 提取显式 skill binding（`node.skill_id` / `node.skill` / `node.agent_config.skill`）
2. 规范化后检查是否在注册表中存在
3. 若不存在，尝试用 `node.id` 作为 skill_id 查询注册表
4. 都未命中时返回 `""`

**用途**：Plan Compiler 在 canonicalize 阶段使用此函数为每个 node 预解析 skill binding（`plan_validator.py` 第 248 行）。

### `resolve_node_skill_ids()`

```python
def resolve_node_skill_ids(node, *, skills=None) -> list[str]:
```

**逻辑**（`skill_binding.py` 第 70-80 行）：

1. 提取 node 的所有显式 skill binding（`node.skill_id` + `node.skills` list + `node.agent_config`）
2. 逐个规范化并验证注册表存在性
3. 追加 node.id 作为候选（若注册表命中则插入列表头部）
4. 去重后返回

**用途**：生成 node 的 `skills` 字段（多 skill 能力集），在 `_canonical_skills()` 中使用（`plan_validator.py` 第 299-304 行）。

## `GENERIC_AGENT_SKILL_ID`

**定义**：`common/skills_registry.py` 第 9 行

```python
GENERIC_AGENT_SKILL_ID = "__generic__"
```

常量 `"__generic__"` 在注册表中不作为普通 skill 条目存在（`skills` 字典中没有 key 为 `"__generic__"` 的条目），但它是一个**语义保留 ID**，在整个流水线中表示"无特定 skill 绑定的通用 agent"：

- Auto-Binder Layer 1：若 node 显式设置为 `"__generic__"` → 返回 `""`（不参与后续自动匹配）
- Materializer：未绑定 node 被赋予 `"__generic__"` 作为 agent_config.skill
- 容器启动：`__generic__` skill 可能对应 `claude-runtime/skills/__generic__/SKILL.md`（如果项目定义了通用 agent 的默认行为），或直接使用 Claude Code 原生默认行为

## 关键代码路径汇总

| 功能 | 文件 | 函数/类 |
|------|------|---------|
| 注册表加载 | `common/skills_registry.py` | `load_skills_registry()`、`skill_registry_entries()` |
| 条目规范化 | `common/skills_registry.py` | `_normalized_skill_entry()`、`_normalized_block_profile()` |
| 注册表缓存 | `common/skills_registry.py` | `_ensure_registry_cache_current()` |
| SkillRegistry 类 | `orchestrator/dag/types.py` | `SkillRegistry`、`refresh_skills_runtime_state()` |
| 运行时状态刷新 | `orchestrator/dag/types.py` | `ensure_skills_runtime_state_current()`、`_skills_runtime_source_revision()` |
| auto_bind 获取 skills | `skill_auto_binder.py` | `_runtime_skills()`（第 81-84 行） |
| 技能存在性查询 | `skill_auto_binder.py` | `_has_skill()`、`_skill_entry()` |
| 技能绑定解析 | `skill_binding.py` | `resolve_node_skill_id()`、`resolve_node_skill_ids()`、`canonical_skill_id()` |
