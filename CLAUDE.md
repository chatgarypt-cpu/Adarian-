# Adarian MVP 开发规范

## 工作流程

当用户给予关于 adarian mvp 的迭代任务时：

1. **读取迭代文档**：`docs/iterations/vX.Y.Z_xxx.md`
2. **理解修复目标**：明确本次要解决什么问题
3. **识别文件变更范围**：哪些文件需要新增、修改、保持不变

### 执行步骤

1. 在 `docs/iterations/TASK_LOG.md` 中记录任务开始
2. 按照迭代文档的"详细修改指令"执行代码修改
3. 在 `docs/iterations/TASK_LOG.md` 中记录任务完成
4. 在 `docs/iterations/CHANGELOG.md` 中追加记录
5. 更新迭代文档状态为"✅ 已完成"

### 自迭代机制（每次迭代后执行）

在任务完成后，我需要主动反思并提出工作流改进建议：

1. **回顾本次执行**：检查是否有遵循工作流规范
2. **识别痛点**：思考本次遇到的阻塞点、沟通成本、不清晰之处
3. **提出建议**：用 AskUserQuestion 向用户展示改进方案选项
4. **用户决策**：由用户选择是否采纳
5. **更新规范**：如果用户采纳，更新 CLAUDE.md

**自迭代触发时机**：
- 每次版本迭代完成后（vX.Y.Z 任务标记为"已完成"时）
- 用户主动要求时

### 核心原则

- 文档驱动开发：所有修改必须基于迭代文档
- 最小化修改：只改必须改的，不做"顺手优化"
- 向后兼容：除非明确标注 Breaking Change
- 透明化记录：所有操作必须在任务日志中留痕
- 遇到不清晰处立即停止并向用户提问
- 命名规范：文件/变量命名遵循 snake_case，类名遵循 PascalCase

### 架构变更记录（每次迭代后执行）

在任务完成后，检查本次是否有架构层面的变化，同步到对应文档：

1. **代码架构变化**（如 Phase 模块、数据结构、拓扑规则）→ 追加到 `docs/dev_spec.md`
2. **工作流变化**（如自迭代机制、命名提醒）→ 追加到 `docs/workflow_changelog.md`

**代码架构变化判断标准**：
- 新增/删除模块（Phase X）
- 数据结构变化（schemas.py 中的模型变更）
- LLM 调用流程变化（如新增 LLM3 校验）
- 社交网络拓扑规则变化
- 核心算法逻辑变化

**工作流变化判断标准**：
- 开发流程调整
- 文档规范变化
- Claude Code 操作方式变化

### 命名规范提醒

当用户提及的命名不符合规范时，需要提醒并建议：

| 规范类型 | 正确示例 | 错误示例 |
|---------|---------|---------|
| 文件/变量 | `entity_extraction.py`, `event_temperature` | `EntityExtraction.py`, `eventTemp` |
| 类名 | `class EntityExtractor` | `class entity_extractor` |
| 常量 | `MAX_AGENT_COUNT = 15` | `maxAgentCount = 15` |
| 函数 | `def extract_entities()` | `def ExtractEntities()` |

**提醒场景**：
- 用户说"那个 EntityExtraction 文件" → 提示：建议使用 snake_case，即 `entity_extraction`
- 用户说"那个 phase0" → 提示：建议使用全小写 `phase0` 或带下划线的描述
