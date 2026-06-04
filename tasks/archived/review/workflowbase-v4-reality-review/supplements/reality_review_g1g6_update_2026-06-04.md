# WorkflowBase v4.0 Reality Review — G1-G6 缺口重新评估（2026-06-04）

> **用途：** 给 Control Agent 的上下文。整合 Reality Review 报告 + Go1 预检结果 + 今日已修复项。
> 原始报告：`tasks/archived/review/workflowbase-v4-reality-review/outputs/reality_review.md`
> 行业基准：`docs/design/patches/v4.0_patch_001_industry_benchmark.md`

---

## Part 1：Reality Review 过时项修正

今天的 drift_check 修复后，以下 Reality Review 发现项已不再是问题：

| 原报告 # | 原发现 | 今日修复 | 新状态 |
|---------|--------|---------|-------|
| F1 | README 过时（4 MCP, 2 hooks, 4 executors） | README 更新为 7 MCP / 13 hooks / 7 executors | ✅ 已修复 |
| F5 | plugin 混入 executor_registry.yaml | schema 扩展，允许 resolver/plugin 共存 | ✅ Schema 已更新 |
| F7 | skill-sound-utils depends_on 引用错误 | `tools/tools_config.yaml` 移除 | ✅ 已修复 |
| F8 | compact.yaml 消费未实现 | G6 重新定义（见 Part 2） | ✅ 需重审 |
| — | skill-cc-dogfood depends_on 指向 `hook-task-status-writer`（不存在） | 改为 `script-task-status-writer` | ✅ 已修复 |
| — | skill-pre-execution-plan-review depends_on 指向 `skill-karpathy-coding`（不存在） | 改为 `skill-cc-karpathy-coding` | ✅ 已修复 |
| — | 8 个 cc_switch skill 缺 `owner_approval_required` | 全部补齐 | ✅ 已修复 |
| — | `skill_type: hermes_builtin` 非法枚举 | 改为 `hermes` | ✅ 已修复 |
| — | `execution_model: sqlite` 非法枚举 | 改为 `http_proxy` | ✅ 已修复 |
| — | drift_check 不读 config.yaml MCP env 块 | 全部修复，env 检查现在可以跨 config.yaml 查 | ✅ 已修复 |

---

## Part 2：G1-G6 重新评估

### G1 — 任务等级 S/M/L/Patch

**报告原始描述：** 设计 §8 的四级任务体系有 `task_level` 透传字段，但无不同级别的 gate/执行路径。closeout-gate 的 3 级 profile（smoke/standard/full_dag）未与 S/M/L 映射。

**现状：** 
- `relay_runner.py:340` 已从 task_config 读 `task_level` 字段，但 **不据此改变行为**，只是透传
- `pre-execution-plan-review` skill 已创建（填补了"方案审查"缺口），但 task_level 本身无执行路径分流
- closeout-gate 有 3 档 profile 但无 S/M/L 映射

**Pending 判断：** 需要 Owner 决定"不同等级要不要走不同执行路径"。如果走敏捷（不区分等级），则 G1 不存在。如果走等级化，则 relay_runner + closeout-gate 两处需要对应修改。

---

### G2 — Codex 写 TASK_LOG/CHANGELOG

**报告原始描述：** 设计 §10.1(7) 规定 Codex 必须按授权写入 TASK_LOG/CHANGELOG。

**现状：** Codex executor 没有任何写入逻辑。

**重新评估：** 
- 日志写入不应绑在 Codex 上，应升级为 **relay runner 后处理回调**（不限 executor）
- TASK_LOG 格式：`## 日期: version 标题` + task_id + 实际变更文件列表
- CHANGELOG 格式：版本号 + 主题 + 新增/修改/修复分类
- 代价预估：~50 行代码，加在 relay_runner 的 result 回收阶段

---

### G3 — Change Advisory

**报告原始描述：** Owner 想调整方案时无辅助判断机制。

**重新评估：** 
- `dispatch-approval-gate` 已拦截 dispatch 意图，让你确认"要改什么"
- 正式 Change Advisory Board（变更委员会）跟你的快速决策风格冲突
- **建议跳过，现有 gate 已覆盖核心需求**

---

### G4 — TASK_LOG/CHANGELOG 强制维护

**报告原始描述：** 无强制机制要求新版迭代更新台账。

**现状：** closeout-gate §2 Full DAG profile 有 `TASK_LOG_CHANGELOG_updated` 条目，但标注了"当前不强制检查此项"。

**重新评估：**
- 如果 G2 做了自动写入，G4 就是"确认自动写入成功"——成本≈0
- **建议并入 G2 一起做**

---

### G5 — 产物完整性 Validator

**报告原始描述：** 无代码级的 artifact completeness validator。

**现状：** relay_runner 有 `artifact_target_paths` 追踪，但跑完后不校验文件是否存在。

**重新评估：**
- 低成本高收益：relay_runner 收尾时 check `expected_outputs` 存在且非空
- 与 G2/G4 无关，可独立做
- 代价预估：~30 行代码

---

### G6 — Compact YAML 消费（重新定义）

**报告原始描述：** 设计 §15 定义 `workflow_compact.yaml` 为机器可读全局索引，无解析器。

**Gary 重新定义（2026-06-04）：** 
不是解析旧的 v0.3.3 YAML。而是创建一个 **由机器维护的工作地图 YAML**：简化、agent 导航用的索引文件。Agent 加载后能知道"顺着这张地图我应该去看哪些文件"。关键是 **机器维护**，不是人写。

**现状：** 零代码，需要先定性：YAML 格式？粒度？更新时机？

---

## Part 3：汇总

| 缺口 | 结论 | 建议动作 | 代价 |
|------|------|---------|------|
| **G1** | ⚠️ 待Owner确认 | 决定 S/M/L 是否需要分流 | 待定 |
| **G2** | ✅ 做，扩大范围 | relay runner 后处理加日志回调 | 低（~50行） |
| **G3** | ❌ 跳过 | 现有 gate 已覆盖 | 0 |
| **G4** | ✅ 并入 G2 | 确认自动日志写入成功 | ~0 |
| **G5** | ✅ 独立做 | relay runner 收尾校验 expected_outputs | 低（~30行） |
| **G6** | ⚠️ 需设计 | 先定格式/粒度/更新时机 | 待定 |

---

*本文件由 Hermes 根据 Reality Review 原始报告 + 2026-06-04 Go1 预检生成。Control Agent 复核后可做 final gate 决策。*
