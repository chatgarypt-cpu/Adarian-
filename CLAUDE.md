# Adarian MVP 开发规范

## Implementation Guidelines（实施准则）

**实施前必须确认方法**：
在写任何代码之前，先向用户确认实现方案。用以下格式：
> "我的计划是：A 这么做原因X，B 那么做原因Y。你选哪个？"

如果不确定正确方向，提出 2-3 个选项让用户选择。**不要**在未获确认前直接执行代码。

**Why：** wrong_approach 是最高频摩擦来源（12次），避免在架构决策上返工。

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
- LLM 调用流程变化（如新增 Validator 校验）
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

---

### 常用命令（可用 Skill 封装）

针对重复性高的命令，可以创建 Skill 简化操作：

| Skill 名称 | 命令 | 用途 |
|-----------|------|------|
| `/test1` | 运行 `python main.py seeds/test1.txt` | 运行 test1 模拟 |
| `/verify` | 运行模拟并验证输出质量 | 验证修改是否正确 |

---

### 代码验证规范

每次代码修改后，必须运行验证：

1. **Python 文件修改** → 运行 `python -c "import xxx"` 验证导入
2. **配置修改** → 运行模拟验证配置生效
3. **修复 bug** → 运行模拟验证问题已解决

避免出现：
- 语法错误
- 缺失导入
- 运行失败

**修复 bug 后主动扫描**：
修复用户报告的 bug 后，用 Grep 搜索相关代码中是否有类似问题。例如：
- 修复已故实体发言 bug → 检查其他实体状态处理逻辑
- 修复距离检查 bug → 检查其他 proximity 检查是否有同类问题
- 修复参数校验 bug → 检查其他参数校验是否遗漏同类边界条件

---

### 文件确认规范

当用户提及特定文件时：
1. 先用 Glob 搜索确认文件存在
2. 如不存在，询问用户确认
3. 不要假设文件位置

---

### 自动同步规范

每次运行模拟或代码修改后，**必须自动同步**以下内容到云端：

1. **outputs 文件夹** → 同步到 `BaiduSyncdisk/文件快传/outputs(cloud)/`
   - `entities_and_relations.json`
   - `social_graph.json`
   - `final_report.md`
   - `agents_profile.json`
   - `tick_logs/`（整个文件夹）

2. **CHANGELOG.md** → 同步到 `BaiduSyncdisk/文件快传/docx(cloud)/iterations/CHANGELOG.md`

**触发时机**：
- 运行 `py main.py seeds/*.txt` 后
- 修改 CHANGELOG 后
- 任何产生新输出文件的操作后

**同步命令**：
```bash
# 同步 outputs
cp outputs/entities_and_relations.json BaiduSyncdisk/文件快传/outputs(cloud)/
cp outputs/social_graph.json BaiduSyncdisk/文件快传/outputs(cloud)/
cp outputs/final_report.md BaiduSyncdisk/文件快传/outputs(cloud)/
cp outputs/agents_profile.json BaiduSyncdisk/文件快传/outputs(cloud)/
cp -r outputs/tick_logs/* BaiduSyncdisk/文件快传/outputs(cloud)/tick_logs/

# 同步 CHANGELOG
cp docs/iterations/CHANGELOG.md BaiduSyncdisk/文件快传/docx(cloud)/iterations/
```
