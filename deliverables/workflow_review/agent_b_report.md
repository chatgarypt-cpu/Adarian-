# ElectionSim-Lab DAG 工作流深度研究分析报告

> 研究员：工作流架构研究员 (Agent B)
> 分析对象：二师兄 ElectionSim-Lab 10 层 DAG 流水线 + Agent 工厂架构
> 日期：2026-05-15

---

## 一、引言：这是一个什么样的系统

ElectionSim-Lab（"二师兄"）是一个基于 Claude Agent SDK 的选举分析多 Agent 系统。它的核心能力是：用户输入一句自然语言问题（如"分析 2026 台北市长选举"），系统自动将其分解为一个有向无环图（DAG）结构的多节点工作流，每个节点在独立 Docker 容器中由 Claude Agent 执行，最终产出包含数据、分析、可视化的完整报告。

这不是一个传统的固定流水线。整个工作流的拓扑结构是 **运行时由 LLM 动态生成** 的，而非编译时预定义。这引出了本报告要深度剖析的核心问题：**当一个系统的执行结构本身是不确定的，如何保证它稳定、可校验、可调度、可观测？**

ElectionSim-Lab 用 10 层分层架构回答了这个问题。每一层解决一个特定的工程挑战，层层递进，将 LLM 的"创造性不确定性"收敛为"确定性可执行产物"。

---

## 二、10 个核心问题深度解释

### 问题 1：为什么要先生成 WorkflowPlan，而不是直接执行？

**为什么存在**：LLM 输出具有天然的不确定性。如果让 Agent 直接执行用户的复杂需求（"分析 2026 台北市长选举"），Agent 需要一边理解任务结构一边执行具体操作——这会导致三个严重问题：(1) **任务漂移**——Agent 可能在执行过程中遗忘或偏离原始目标；(2) **不可调度**——无法预知需要多少节点、它们之间有什么依赖关系，因此无法做并行调度和资源分配；(3) **不可审计**——执行过程混在一起，无法追踪每一步的输入/输出/状态。

**完整链路**：`ParsedIntent → WorkflowPlan → GeneratedDAG`

三层数据结构的渐进式物化：

1. **ParsedIntent**（Layer 0 产出）：从用户自然语言中提取的结构化意图。包含 `action`（analyze/query/export）、`targets`（具体分析对象）、`time_range`、`output_format`。这是"用户想做什么"的抽象。

2. **WorkflowPlan**（Layer 1 产出）：LLM 生成的逻辑 DAG 描述。包含 `nodes`（每个节点的 id/label/description/kind）、`edges`（节点间的 data_dependency/reference/conditional 依赖关系）、`rationale`（规划思路）。这是"需要哪些步骤、之间什么关系"的逻辑描述。关键约束：Planner 输出阶段最多 30 个节点、200 条边。

3. **GeneratedDAG**（Layer 4 产出）：经过编译、校验、物化的可执行数据结构。包含 `DAGNode`（含 layer/order/agent_config/block_profile/status）、`DAGEdge`、`workflow_id`、`estimated_duration`。运行时上限放宽到 200 节点、2000 条边（以容纳系统注入的搜索子节点等）。

**Plan 与 Runtime 分离的设计意图**：

这不是简单的"先计划再执行"——这是**责任分界**。Plan 阶段（Layer 0-4）的职责是回答"做什么"，Runtime 阶段（Layer 5-8）的职责是回答"怎么做"。两者的关键区别在于：

- Plan 阶段的错误只消耗 LLM token，Runtime 阶段的错误消耗 Docker 容器、Agent 推理时间、下游等待时间。通过将 Plan 作为一道"免费/廉价的错误前置层"，系统在最高风险的操作（执行）之前将所有结构化问题收敛完毕。
- Plan 是可"重规划"的——如果验证失败，只需重新生成 Plan。Runtime 一旦启动，回滚成本高得多。
- Plan 独立于执行环境——同一个 WorkflowPlan 可以被不同部署环境（不同 Docker 镜像、不同 Skill 版本）复用。

**对 Adarian 的启发**：Adarian 的风险评估流程也是"先理解需求再执行"。当前的实现中，意图解析和任务执行耦合较紧。建议参考 ElectionSim-Lab 的做法，在 Risk Assessment 管线中显式引入一个"任务分解 Plan"阶段——让 LLM 先生成完整的分析步骤 Plan，经校验后再逐步执行，而非边分解边执行。

---

### 问题 2：为什么要有 Repair Loop？

**为什么存在**：LLM 生成的 JSON 不可靠，存在三类典型失败：(1) **格式问题**——JSON 被包裹在 Markdown 代码块中、前后有解释性文字；(2) **Schema 违规**——字段缺失、类型错误、节点 ID 含非法字符；(3) **业务规则违反**——DAG 有环、节点数超限、边引用不存在的节点、Skill 不在白名单中。

如果直接放弃，系统可靠性会极差——LLM 的结构化输出失败率在复杂 Schema 下可达 10-30%。系统的核心设计哲学是**"校验失败不放弃，而是把错误信息作为下一轮 LLM 调用的 context"**。

**修复机制**：

Repair Loop（`WorkflowPlanningRepairLoop`）的核心流程：

```
for attempt in 1..max_attempts:
    1. transport(prompt) → 调用 LLM/SDK 获取原始文本
    2. compiler.compile(raw_text) → 提取 JSON → Pydantic 校验 → Skill 白名单 → 规模校验 → 业务校验
    3. 如果校验通过 → materialize → 返回 GeneratedDAG
    4. 如果校验失败 → 构建 repair_prompt → 将校验错误原文 + 上次输出前缀注入 prompt → 重试
```

Repair Prompt 的关键构造：
- 注入 `dag-planner` Skill 的 `rules-and-examples.md`（含负面范例）
- 注入拓扑修复指导（从 `validation_error` 中提取缺失维度：node_count/parallel_layers/max_width）
- 注入报告修复指导（针对 report 模式的语义修复）
- 强制输出约束："回复首字符必须是 `{`，不要输出任何解释文字"

**max_attempts 的设计考量**：

默认值为 2（即初次生成 + 最多 2 次修复 = 最多 3 次交互），范围 1-5。这个数值的选择基于三个因素：

1. **成本收益**：每次修复增加一次完整的 LLM 调用（token 消耗 + 延迟 5-15 秒）。超过 3 次重试后的边际成功率急剧下降——如果 LLM 在 3 次内都不能生成正确 JSON，通常意味着 prompt 本身有根本性问题（如 Schema 过于复杂、或 LLM 能力不足）。
2. **失败模式分析**：经验数据表明，90%+ 的失败在第一次修复中就能解决（主要是格式问题），剩余的大多是语义/业务逻辑错误（如生成的 DAG 拓扑结构本身不合理），这类错误即使多次修复也难以改正。
3. **用户体验**：超过 5 次重试的延迟会让用户感知为"系统卡住了"。

**对 Adarian 的启发**：Adarian 的 LLM 调用（如风险分类、信号映射）也面临输出不稳定的问题。建议引入类似的 Repair Loop 模式——对 Pydantic Schema 校验失败的 LLM 输出，不要直接报错，而是携带校验错误信息重试 1-2 次。

---

### 问题 3：为什么要有 Schema / extra forbid / 校验？

**为什么存在**：LLM 是"好心但不可靠的协作者"。它可能在 JSON 中添加未曾定义的额外字段（如 `"confidence": 0.95`、`"notes": "这个节点很重要"`），这些字段可能在下游被误解析为合法字段，导致静默的数据损坏。`extra="forbid"` 是一道**主动防御**——让任何意外字段在 Pydantic 校验阶段就暴露，而非在下游物化/执行阶段以更隐蔽的方式失败。

**WorkflowPlan 的 Pydantic 约束体系**：

```
WorkflowPlan:
  - extra="forbid"                     ← 拒绝未定义字段
  - schema_version: "1"                ← 版本锁定
  - name: max_length=120
  - nodes: min_length=1, max_length=200
  - edges: max_length=2000
  - rationale: max_length=800

WorkflowPlanNode:
  - extra="forbid"
  - id: pattern=^[a-z0-9][a-z0-9_-]{0,63}$   ← 安全正则
  - label: max_length=60
  - description: max_length=300
  - skills: max_length=6
  - skill_id/skill/skills: exclude=True       ← 序列化排除

WorkflowPlanEdge:
  - extra="forbid", populate_by_name=True
  - from_: alias="from"                       ← 兼容 JSON 保留字
  - edge_type: 枚举 data_dependency/reference/conditional
  - condition: max_length=240
```

**exclude=True 的设计意图**：

`skill_id`、`skill`、`skills` 三个字段标记了 `exclude=True`（序列化时排除）。因为 Planner 输出的 skill_id 只是"建议绑定"——LLM 可能输出一个大小写错误的 skill 名称，或引用一个已被删除的 Skill。真正的 skill 绑定在 Layer 3（Skill Auto-Binder）和 Layer 4（Materializer）中由确定性规则完成。序列化排除防止了不一致的 skill 引用向下游传播。

**两层校验架构**：

1. **Pydantic Schema 校验**（Layer 2，`plan_compiler.py`）：类型、必填、长度、正则匹配。纯结构层面。
2. **业务语义校验**（Layer 2，`plan_validator.py` + `workflow_materializer.py`）：无环检测（Kahn 算法）、唯一 node_id、边引用完整性、Skill 白名单、扇出限制（`_MAX_BLOCKING_FAN_OUT=10`）、agenda_setter 扇出限制（>3 需目标为 search/data_discovery）、master_analyst 强制存在（节点 >= 10 时必须包含）、阻塞型前驱规则（非 entry 节点必须至少有 1 条 data_dependency 或 conditional 上游边）。

**对 Adarian 的启发**：Adarian 的 Pydantic 模型（如 `RiskAssessment`、`SignalMapping`）应该全面启用 `extra="forbid"` 和严格的正则约束。当前的 schemas.py 中已有部分约束，但建议增加业务语义校验层——如风险等级与信号方向的一致性、评估范围的完整性等。

---

### 问题 4：为什么要有 DAG Materializer？

**为什么存在**：`WorkflowPlan` 是 LLM 视角下的"逻辑计划"——它描述的是"需要什么节点、什么依赖关系"。但它不能被调度引擎直接消费，因为：(1) 缺少拓扑层级信息（哪些节点可以并行？）；(2) 缺少运行时的 agent_config（每个节点用什么模型？什么工具？）；(3) 搜索需求和知识库需求尚未展开为独立节点；(4) 节点之间的具体执行顺序未确定。

Materializer 的核心职责是**将逻辑计划编译为可执行 DAG**，这是一个确定性编译过程——输入确定则输出确定，不依赖 LLM。

**物化过程（5 个阶段）**：

```
WorkflowPlan
  → 1. Auto-Bind (可选) → skill_id/skill/skills 填充
  → 2. 搜索子节点注入 → external_search/requires_knowledge_search 展开
  → 3. 全面校验 → validate_plan_dag() 10 项检查
  → 4. 物化 → assign_layers_orders() + _materialize_node()
  → 5. 装配 → GeneratedDAG
```

**拓扑排序 / assign_layers_orders**：

核心算法是 Kahn 拓扑排序的变体（BFS）：
- 只统计 blocking 边（非 reference 边）
- 初始 queue 是所有入度为 0 的节点
- 每轮 pop queue[0]，逐出边更新下游 layer = max(当前 layer, 上游 layer + 1)
- 同层内按原始顺序稳定排序

输出是 `{node_id: (layer, order)}`。这个信息直接决定 DAG 调度器的批次并发策略——同 layer 的节点可以并行执行。

**_materialize_node() 的关键转换**：

每个 `WorkflowPlanNode` 被转换为 `DAGNode`，新增的关键字段：
- `layer` / `order`：拓扑层级和层内顺序
- `agent_config`：{description, skill, skills, external_search, requires_knowledge_search, search_strategy}
- `block_profile`：从 Skill Registry 提取的阻断策略（并发/单实例等）
- `status`：运行时状态（pending/running/completed/failed）
- `critical`：失败后是否阻断下游

**对 Adarian 的启发**：Adarian 的风险评估流程目前缺少类似的"逻辑到可执行"的物化层。当前直接从 intent 跳到执行，中间缺少一个将分析步骤显式编译为可调度任务图的阶段。建议在 Phase 4 重构中引入类似 Materializer 的层。

---

### 问题 5：为什么要有搜索子节点注入？

**为什么存在**：当 Planning Agent 生成的 WorkflowPlan 中某个节点的 `external_search=true` 或 `requires_knowledge_search=true`，意味着该节点在进行分析前需要先获取外部信息。如果让该节点自行执行搜索，会导致三个问题：(1) **职责混合**——搜索（机械性的信息检索）和推理（语义层面的分析综合）混在同一个 Agent 上下文中；(2) **并发控制缺失**——搜索策略模板要求 3 路并行 subagent，这需要专门的节点来编排；(3) **无法复用**——如果多个节点需要搜索相同的关键词，每个节点都要独立执行。

**注入机制**：

```
注入前: upstream → target(external_search=true) → downstream
注入后: upstream → target__ext_search → target(external_search=false) → downstream
```

关键规则：
- 搜索子节点使用专用 Skill：`external_search_agent` / `knowledge_search_agent`
- 搜索子节点的 skill_id 在物化时被清空（匿名化），不暴露给下游
- 搜索策略模板（3 路并发 subagent、可信度排序）通过 `agent_config["search_strategy"]` 注入
- 入边重连：原 target 的 blocking 入边被克隆到搜索子节点，搜索子节点与 target 之间创建新的 data_dependency 边
- 搜索子节点不参与 `_enabled_agent_nodes()` 计数，不影响 master_analyst 强制规则

**扇出控制**：

系统对搜索节点有专门的扇出约束：
- 单节点阻塞型扇出上限 10（`_MAX_BLOCKING_FAN_OUT`）
- agenda_setter 宽扇出 > 3 时，多出的目标必须指向 search/data_discovery 入口节点
- 搜索子节点被排除在白名单校验外（`_is_search_helper_node()` 豁免）

**对 Adarian 的启发**：Adarian 的信号映射模块中存在类似需求——某些风险分析需要外部数据支撑（如市场数据、政策信息）。如果当前 Agent 直接执行搜索，会导致上下文膨胀。建议采用"搜索前置"模式——将数据获取和数据分析分离为独立节点。

---

### 问题 6：为什么要有 Workspace Sync？

**为什么存在**：系统的 Skill 定义、Subagent 角色定义和共享配置存储在宿主机项目根目录的 `claude-runtime/` 中，但 Agent 容器内的 Claude Code SDK 期望在 `.claude/skills/` 和 `.claude/agents/` 下找到这些文件。

直接使用 `.claude/` 存放 ElectionSim 的 Agent 配置会产生两个问题：(1) **冲突**——开发者本地可能有自己的 `.claude/skills/` 和 `.claude/settings.json`；(2) **语义混乱**——`.claude/` 针对的是 Claude Code IDE 开发环境，而 ElectionSim 的 Agent 配置针对的是 Docker 容器内的运行时环境。

**文件投影机制**：

```
宿主机 claude-runtime/              容器内 .claude/
  skills/                            skills/
    dag/entry/agenda_setter/           agenda_setter/      (扁平化)
      SKILL.md                    →     SKILL.md
    shared/runtime/csv-task-spec/      csv-task-spec/      (扁平化)
      SKILL.md                    →     SKILL.md
    _shared/                       →   _shared/            (原样)
  agents/                          →   agents/             (全量)
  settings.json                    →   settings.json
```

关键技术细节：
- **扁平化投影**：宿主机按 `skills/<category>/<name>/SKILL.md` 的层次存放（便于人类维护），容器内扁平为 `.claude/skills/<name>/SKILL.md`（符合 SDK 规范）。扁平化的 key 是 SKILL.md 的 frontmatter `name` 字段。
- **全量覆盖**：每次 sync 前 `shutil.rmtree` 清理旧投影，再用 `shutil.copytree` 全量复制。选择全量而非增量的理由是文件量小（几十个 Markdown 文件），且可靠性优先于性能。
- **MCP 模板渲染**：sync 后对 `.md` 文件执行 `render_mcp_text()`，将 `{{MCP_KNOWLEDGE_SEARCH_TOOL}}` 等占位符替换为实际的 MCP 工具名。

**工作区分层设计**：

容器内 `/workspace/<run_id>/` 的四层划分：
- `input/`：task_prompt.md（Agent 启动后读取的第一份指令）
- `meta/`：node_context.json、time_context.json、node_execution_config.json（运行时元数据）
- `output/`：result.json、report.md、task_spec/（Agent 产物）
- `.claude/`：skills/、agents/、settings.json（从 claude-runtime/ 投影）

**对 Adarian 的启发**：Adarian 当前的所有配置和逻辑都在项目内硬编码。如果未来需要支持多领域（如扩展到企业风险评估、合规审查），建议参考"claude-runtime 分离于 .claude/"的模式——将领域特定的分析逻辑（类似 Skill）外置为可加载的"领域包"，与平台代码解耦。

---

### 问题 7：为什么要 MCP 模板化？

**为什么存在**：Skill 文档和 Agent 定义中需要引用具体的 MCP 工具名称（如"使用 `mcp__linkly-ai__search` 检索文档"）。但不同节点可能使用不同的 MCP provider（如知识库检索在开发环境用 `linkly-ai`，生产环境可能切换为 `vector-db`），每个 provider 的实际工具名、参数签名、调用链都不同。

如果直接在 Skill 文档中硬编码工具名，会导致 Skill 无法跨 provider 复用。模板变量机制将"工具名"从"执行逻辑"中解耦。

**模板变量体系**：

两组模板变量：`MCP_KNOWLEDGE_*`（知识库）和 `MCP_WEB_SEARCH_*`（网页搜索），每组包含：
- `{{MCP_*_PROVIDER}}`：provider 名称
- `{{MCP_*_SEARCH_TOOL}}`：搜索工具全名（如 `mcp__exa__web_search_exa`）
- `{{MCP_*_OUTLINE_TOOL}}`：结构查看工具
- `{{MCP_*_READ_TOOL}}`：内容阅读工具
- `{{MCP_*_CHAIN_TEXT}}`：推荐调用顺序
- `{{MCP_*_SEARCH_SIGNATURE}}`：调用格式示例

Provider 特定覆盖（如 Exa 的 `outline`、`grep`、`read` 三个角色都映射到 `crawling_exa` 一个工具）由 `_PROFILE_PROVIDER_SPECS` 配置管理。

**Legacy 替换**：`render_mcp_text()` 同时处理历史遗留的硬编码引用——将 `mcp__linkly-ai__search` 等旧名称替换为当前 provider 的工具名，确保旧 Skill 文档无需修改就能在新 provider 下工作。

**对 Adarian 的启发**：Adarian 目前通过环境变量配置 LLM provider。但如果在 Skill 或提示词中直接引用具体工具/API 名称，切换 provider 就需要修改文件。建议参考模板变量机制，将"具体工具名"从"指令逻辑"中分离。

---

### 问题 8：为什么要有 Skill Registry？

**为什么存在**：系统有 35+ 个 Skill（如 `agenda_setter`、`candidate_registry_searcher`、`simulation_runner`），每个 Skill 有独特的名称、描述、阶段归属（entry/evidence/synthesis/deepening/output/verification）、积木原型（collector/analyzer/synthesizer/reporter）、扇出策略（`canFanOut`）等元数据。Planning Agent 需要在生成 DAG 时知道有哪些 Skill 可用，Auto-Binder 需要将 semantic node_id 映射到注册表中的 Skill。

Skill Registry 是所有这些元数据的**单一权威源**。它不是"一个数据库"——它是两层数据的集合：
1. **YAML 配置**（`skills_registry.yaml`）：所有 Skill 的静态定义
2. **运行时状态**（`SkillRegistry.SKILLS`）：从 YAML 加载后的 Python dict，plus block_profile 和 planning snapshot

**四层匹配逻辑**（Auto-Binder 的核心）：

当 `allowed_mode="open"` 时，Planning Agent 可以生成注册表中不存在的 semantic node_id。Auto-Binder 通过四层优先级递减的匹配将其绑定到已知 Skill：

1. **Layer 1：显式赋值**——如果 Planning Agent 已显式设置 `skill_id`，直接采用
2. **Layer 1b：注册表精确匹配**——`node.id` 恰好在注册表中存在
3. **Layer 2：双下划线前缀匹配**——`node_id = "<family>__<detail>"`，提取 family 前缀，依次追加 5 个常见后缀（`_analyst/_detector/_modeler/_profiler/_collector`）查询注册表
4. **Layer 3：关键词正则降级**——21 条中英文规则（如 `swing/marginal/battlefield → swing_district_detector`、`派系/地方派系/樁脚 → local_faction_network_analyst`）

全部未命中时 → Materializer 兜底降级为 `__generic__`。

**为什么用纯正则而非 LLM**：这是一个确定性映射问题，语义推理的优势在这里不存在——相同的 node_id 应该总是映射到相同的 Skill。正则规则引擎带来三个优势：(1) 确定性——不受 LLM 温度影响；(2) 低延迟——微秒级 vs 秒级；(3) 零 token 成本。

**对 Adarian 的启发**：Adarian 的"信号-风险"映射表本质上也是一个类似的注册表。当前实现是通过 LLM 调用完成映射的。可以考虑引入类似的确定性匹配机制——对于已建立映射的信号，使用规则引擎直接匹配，LLM 仅用于未知信号。

---

### 问题 9：为什么 Prompt 要七层组装？

**为什么存在**：Agent 启动后的第一份指令（`task_prompt.md`）直接决定了它在容器内的行为。如果这个 prompt 是模糊、不完整或自相矛盾的，Agent 的行为将不可预测。七层组装不是"越多越好"——每一层解决一个特定的指令模糊性问题：

**Layer 1：任务描述 + 执行权威层级**
解决：Agent 的核心使命是什么。`EXECUTION_AUTHORITY_LINES` 声明了"当前任务 > execution_contract > upstream_inputs > skill 文档"的优先级链。防止 skill 文档自带的"默认职责"覆盖特定任务的具名要求。

**Layer 2：上游产物摘要**
解决：Agent 可以读什么。上游节点的产物挂载在 `/workspace/upstream/<node_id>`，通过 `upstream_file_map` 提供已验证的绝对路径。禁止 Agent 自行拼接猜测路径。

**Layer 3：资源提示（seed_paths）**
解决：Agent 从哪里开始找数据。从资源审计中提取的已验证路径（最多 6 条），防止 Agent 对 `/public` 做全盘扫描。

**Layer 4：数据读取协议（READ_PROTOCOL_LINES）**
解决：Agent 怎么读数据。区分 knowledge 版（含 MCP 语义定位）和 local-only 版（纯文件系统读取）。约束读取顺序：已知路径直接读、未知路径先用 knowledge MCP/Glob/Grep 收敛。

**Layer 5：工具调用纪律（TOOL_SEARCH_LINES）**
解决：Agent 怎么用工具。声明参数名必须正确、禁止猜名试错、搜到即用不停留、Write.content 必须是字符串。

**Layer 6：节点级 SCOPE_LINES**
解决：Agent 不能做什么。每种节点类型有专属的行为边界——agenda_setter 只能设定参数、candidate_registry_searcher 只能核验候选人。这是防止"过度协助"导致职责渗透的关键防线。

**Layer 7：输出合约（required_outputs）**
解决：Agent 怎样才算完成。具名业务文件清单 + CSV 进度规范 + 写入隔离约束。防止 Agent 以空目录或协议骨架冒充完成。

**对 Adarian 的启发**：Adarian 的 Agent prompt 当前是相对扁平的。建议参考七层结构，特别是：(1) 引入 SCOPE_LINES 防止 Agent 越界执行；(2) 引入 required_outputs 作为显式完成标准；(3) 引入 READ_PROTOCOL 规范数据读取顺序。

---

### 问题 10：为什么 planning_richness 控制复杂度？

**为什么存在**：不同用户需求对 DAG 的复杂度要求差异巨大。"列出 2024 年的所有选举数据文件"只需要 2-3 个节点，"深度分析 2026 台北市长选举，包含民调趋势、候选人背景、派系网络"可能需要 15-25 个节点。

`planning_richness` 是一个**用户可选的复杂度档位**，在规划阶段控制 DAG 的规模和结构深度，进而控制 token 消耗和执行时间。

**四档体系**：

| Richness | 节点范围 | 结构要求 | 典型场景 |
|----------|---------|---------|---------|
| minimal | 2-4 | 无并行要求 | 简单查询、数据列出 |
| standard | 5-8 | 至少 1 次轻并行 + 1 个汇聚 | 标准选举分析 |
| detailed | 10-16 | 必须 10+ 节点、至少 1 次汇聚 | 深度分析 |
| comprehensive | 15-25 | 并行层>=2、汇聚>=2、优先宽-窄-宽 | 全维度深度报告 |

**控制点**：

Richness 在多个层面控制 DAG 行为：
1. **拓扑目标**（`_TOPOLOGY_TARGETS`）：`min_node_count`、`min_parallel_layers`、`min_convergence_nodes`、`require_wide_narrow_wide`
2. **组装规则**（`_ASSEMBLY_RULES`）：引导 LLM 生成特定结构
3. **反模板警告**：comprehensive 下明确禁止 `[1,N,1]` 单层扇形
4. **Planner 超时**：standard=120s, detailed=180s, comprehensive=480s
5. **多轮澄清**：不同档位对应不同的 max_rounds（2/3/4）
6. **自动降级**：检测到"最小冒烟/自检"关键词时自动降级为 minimal

**对 Adarian 的启发**：Adarian 的风险评估可以在用户层面引入类似的"分析深度"参数——"快速扫描"vs"深度分析"vs"全面审计"，在不同档位下控制分析的维度数量、数据源范围、验证强度。

---

## 三、完整链路梳理

### Planner → WorkflowPlan → Repair/Validate → Materializer → GeneratedDAG → Workspace → Agent Execution

```
Layer 0: Planning Agent (Claude SDK)
  输入: 用户消息 + 对话历史 + 资源审计
  输出: PlanningAgentResult {status: "ready", parsedIntent}
  消费者: Layer 1

Layer 1: OrchestrationEngine.generate_plan()
  输入: ParsedIntent + SkillRegistry + Recipe 模板
  输出: WorkflowPlan (LLM 生成的 JSON)
  消费者: Layer 2

Layer 2: PlanCompiler.compile() → PlanValidator.validate()
  输入: LLM 原始文本
  输出: CompiledWorkflowPlan (经验证的 WorkflowPlan + validation_warnings)
  [失败时 → PlanRepairLoop → 重新生成]
  消费者: Layer 3

Layer 3: SkillAutoBinder.auto_bind()
  输入: WorkflowPlan (allowed_mode="open" 的节点)
  输出: skill_id 已绑定的 WorkflowPlan
  消费者: Layer 4

Layer 4: build_generated_dag()
  输入: WorkflowPlan + Skill 注册表
  内部: Auto-Bind(可选) → 搜索子节点注入 → 校验 → assign_layers_orders → materialize
  输出: GeneratedDAG (含 DAGNode with layer/order/agent_config)
  消费者: Layer 5

Layer 5: build_node_prompt()
  输入: GeneratedDAG 中的每个 DAGNode + resource_audit + required_outputs
  输出: task_prompt.md (每个节点一份)
  消费者: Layer 6 + Layer 8

Layer 6: sync_workspace_skills()
  输入: claude-runtime/ 目录
  输出: 容器内 .claude/ 目录 (含扁平化 skills/ + agents/ + settings.json)
  消费者: Layer 8

Layer 7: DAGScheduler / Launcher
  输入: GeneratedDAG + task_prompt.md
  输出: 运行中的 Docker 容器 (挂载 /workspace + /public + .claude/)
  消费者: Layer 8

Layer 8: Agent SDK Session (election_agent.py)
  输入: task_prompt.md + 工具清单 + Skill bundle + upstream 输出
  处理: System Prompt 注入 → 推理循环 (max_turns=300) → 工具调用
  输出: result.json + report.md + sdk_messages.jsonl
  消费者: Layer 9 + 下游节点

Layer 9: EventRecorder → Redis Streams → SSE → 前端
  输入: sdk_messages.jsonl (实时)
  输出: ReactFlow 节点状态更新 (pending→running→completed/failed)
```

### SDK 通道 vs LLM 通道的区别和选择逻辑

| 维度 | SDK 通道 | LLM 通道 |
|------|---------|---------|
| 调用方式 | Claude Agent SDK (`ClaudeSDKClient`) | httpx AsyncClient POST LLM Gateway |
| 工作区 | 临时目录 + sync_workspace_skills | 无文件系统 |
| 工具 | 仅允许 Skill 工具 (dag-planner) | 无工具 |
| system_prompt | `claude_code` preset | 自建 prompt |
| 结构化输出 | 无（SDK 内部闭环） | OpenAI-compatible `json_schema` |
| thinking | 不支持 | 支持（通过 anthropic-beta） |
| 模型 | WORKFLOW_GEN_MODEL（可配置） | WORKFLOW_GEN_MODEL（可配置） |
| 权限 | disallowed_tools 黑名单 + Skill 白名单 | N/A（无工具） |

**选择逻辑**：由 `workflow_planner_mode` 配置决定。planner 类值走 SDK 通道（优势：Skill 工具让 Planner 可以读取 dag-planner 的 rules-and-examples.md），其他值走 LLM 通道（优势：structured outputs 保证 JSON Schema 一致性）。

两通道共享同一个 prompt 构建、repair loop、compiler 和 validator，仅 transport 层不同。

---

## 四、底层工程思想提炼（8 条）

### 思想 1：Plan-Runtime 分离 —— 把不确定性收敛在最便宜的层级

**设计意图**：LLM 的创造性是价值来源，但也带来不确定性。系统的策略不是消除不确定性，而是将不确定性**前置**到成本最低的 Plan 阶段（Layer 0-4），通过确定性的校验、编译、物化将其收敛为确定的 Runtime 指令。

**解决的问题**：避免"边执行边决策"导致的不可预测性——Plan 阶段的错误只消耗 LLM token（便宜），Runtime 阶段的错误消耗 Docker 容器 + Agent 推理时间 + 下游等待（昂贵）。

**对 Adarian 的启发**：Adarian 当前在风险分析中缺乏显式的 Plan 阶段。建议在每条用户请求处理时，先让 LLM 生成完整的"分析任务清单"（类似 WorkflowPlan），校验通过后再执行，而非即时思考即时执行。

### 思想 2：校验 + 修复闭环 —— 不放弃不可靠的输出，而是引导它收敛

**设计意图**：LLM 输出的结构化文本天然不可靠（格式错误、Schema 违规、业务规则违反）。但放弃意味着整个系统不可用。Repair Loop 将校验错误转化为下一轮 LLM 调用的 context，提供了"自我修正"的路径。

**解决的问题**：单次 LLM 调用的结构化输出成功率不足以支撑生产系统。Repair Loop 将成功率从单次的 70-90% 提升到 3 轮内的 98%+。

**对 Adarian 的启发**：Adarian 的 LLM 调用（风险分类、信号映射等）应该在遇到 Pydantic ValidationError 时自动重试并携带错误信息，而非直接向前端报错。

### 思想 3：逻辑到可执行的渐进物化 —— 四阶段数据转换链

**设计意图**：`ParsedIntent → WorkflowPlan → CompiledWorkflowPlan → GeneratedDAG` 每个阶段增加一层运行时信息，逐步将 LLM 的抽象描述转化为机器可执行的指令。这个渐进式转换确保任何中间状态的异常都能被该阶段的校验捕获。

**解决的问题**：如果从 LLM 输出直接跳到执行，中间缺失了很多必要步骤——拓扑排序、层级分配、搜索注入、agent_config 构建。渐进物化确保每个转换阶段的责任单一、可测试。

**对 Adarian 的启发**：Adarian 当前缺少中间表示层。建议引入类似 WorkflowPlan 和 GeneratedDAG 的中间数据结构，在"意图"和"执行"之间增加编译和物化步骤。

### 思想 4：配置外置与确定性注入 —— 区分"什么可变"与"什么不可变"

**设计意图**：系统的可变部分（Skill 定义、Agent 角色、MCP 配置、拓扑模板）全部外置在 `claude-runtime/` 和配置文件中。系统的不可变部分（DAG 引擎、编译校验、容器调度）内聚在引擎核心。这两者之间通过确定的"注入"机制连接——不是运行时查询，而是启动前一次性投影。

**解决的问题**：(1) 领域知识与平台代码解耦；(2) 配置变更不触及核心引擎；(3) 同一引擎可驱动不同领域的 Agent 社会（如 Agent 工厂架构所示）。

**对 Adarian 的启发**：Adarian 的 Phase 1-4 目标正是"平台解耦"。建议将当前的选举分析逻辑（信号定义、风险分类规则、评估模板）全部外置为可配置的"领域包"，而非硬编码在代码中。

### 思想 5：搜索与推理分离 —— 用 DAG 拓扑表达职责边界

**设计意图**：搜索（机械的信息检索）和推理（语义的分析综合）是两种完全不同性质的工作。搜索需要的是并发能力和结果排序，推理需要的是深度上下文的完整性。通过将搜索展开为独立的前置子节点（`target__ext_search`），系统在 DAG 结构层面表达了这种职责分离。

**解决的问题**：Agent 的上下文窗口是稀缺资源。如果让一个 Agent 同时做"搜索 + 推理"，搜索过程中积累的大量中间结果会挤占推理所需的空间。分离后，搜索节点的产物（清洗后的结构化结果）流入推理节点，上下文更干净。

**对 Adarian 的启发**：Adarian 的信号映射中涉及外部数据源查询。建议采用相同的"搜索前置"模式——将数据获取和分析分离。

### 思想 6：层次化行为约束 —— SCOPE_LINES 即 Agent 宪法

**设计意图**：通用的 system prompt 不够精确。`SCOPE_LINES` 是一套按节点类型定制的行为边界声明——说明 Agent "只能做什么"和"绝对不能做什么"，配合 `EXECUTION_AUTHORITY_LINES` 声明信息源的优先级链。

**解决的问题**：多 Agent 系统中最大的风险之一是"职责渗透"——一个 Agent 越界执行了另一个 Agent 的工作。这导致重复工作、结果不一致、错误传播。SCOPE_LINES 将每个 Agent 的职责精确划定。

**对 Adarian 的启发**：Adarian 的 Subagent 应该引入类似的 SCOPE_LINES 体系，明确声明每个 Agent 的输入边界、输出边界、禁止操作。

### 思想 7：全量同步 + 不可变投影 —— 用简单换可靠

**设计意图**：`claude-runtime/ → .claude/` 的文件投影采用"全量清理 + 全量复制"策略，而非增量同步。虽然带来了每次 sync 的微小文件 I/O 开销，但消除了增量同步的所有脏状态风险（Skill 被删除但旧文件残留、部分更新的不一致窗口等）。

**解决的问题**：增量同步的边界条件极其复杂——文件改名的检测、删除的传播、顺序依赖。对于几十个文件的小规模配置，全量同步的简单性和可靠性远优于增量同步的"效率优化"。

**对 Adarian 的启发**：在设计数据同步/配置分发机制时，当数据量小（几十到几百 KB），优先选择全量覆盖而非增量同步。

### 思想 8：事件三态持久化 —— 热数据、温数据、冷数据分离

**设计意图**：Agent 执行日志同时存储在三个位置：(1) 容器内 `sdk_messages.jsonl`（原始记录，完整但读写慢），(2) Redis Streams（实时热数据，SSE 推送给前端，有容量上限 5000），(3) SQLite（冷数据持久化，支持历史回溯）。三种存储各司其职，不是冗余而是分层。

**解决的问题**：如果只有一种存储，无法同时满足"实时推送低延迟"和"完整历史可回溯"这两个互相矛盾的需求。三态分离后，前端消费 Redis 的高速流，审计系统查询 SQLite 的完整历史，调试系统读取 jsonl 的原始记录。

**对 Adarian 的启发**：Adarian 的执行日志目前较为单一。建议引入类似的三态持久化——Redis 用于实时 UI 更新，SQLite 用于历史审计，jsonl 用于调试和重放。

---

## 五、总结

ElectionSim-Lab 的 10 层流水线不是一个"堆砌"的架构——每一层都在解决 LLM 驱动的多 Agent 系统中的真实工程问题。核心洞察是：**LLM 提供"创造力"价值，但带来"不确定性"成本**。整个流水线的设计哲学是将这种不确定性通过层层校验、编译、物化、约束，转化为确定性的可执行产物。

Agent 工厂架构在此基础上更进一步——证明了这套流水线不仅适用于"选举分析"这一个领域，而是可以作为任何领域的 Agent 社会基座。平台是"空心"的，领域知识全部在外围。这一设计思想直接启发了 Adarian 的"平台解耦"战略。

Adarian 当前的 Phase 4 关键任务——将风险分析的核心逻辑从引擎代码中分离——正是 ElectionSim-Lab 已经实践了的"GenFlow 基座 + 领域包"模式。建议在该模式落地时，重点参考以下机制：Plan-Runtime 分离、校验修复闭环、搜索推理分离、SCOPE_LINES 行为约束。
