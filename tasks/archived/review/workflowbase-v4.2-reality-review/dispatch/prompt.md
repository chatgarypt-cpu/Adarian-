@skill workflow-reality-review

## 审查目标

对 Adarian MVP A 线 WorkflowBase 三层结构做全面 Reality Review（第二版），验证 v4.2 架构调整后的现状。

### 范围

1. **WorkflowBase 三层**：`WorkflowBase/` 下 registry/ / runner/ / governance/ / self-maint/ / infra/ 全部文件
2. **G1-G6 实现验证**：对照 `tasks/archived/review/workflowbase-v4-reality-review/supplements/reality_review_g1g6_update_2026-06-04.md` 确认各项缺口状态
3. **四层工作流模型**：Owner Brief → Iteration Contract → Runtime Dispatch → Evidence/Closeout 的落地情况
4. **报告语言**：中文

### 审查深度

标准 + 红队双重深度。不仅要找面上的问题，还要找隐藏的矛盾和路线差异。

### 特殊要求

1. **结构完整性**：所有文件齐全、目录完整、注册表声明与文件系统一致
2. **能力真实性**：每个 YAML 声明的 module_path / command / call_pattern 真实可解析
3. **一致性**：跨文件引用（depends_on）、枚举合法性、命名规则一致
4. **边界与风险**：permission_level / risk_level / allowed_paths 合理性
5. **G1-G6 状态核查**：G5（expected_outputs validator）和 G2/G4（log callback）是否已在 relay_runner.py 中实现且语法通过；G6（--generate-map）是否已在 drift_check.py 中实现
6. **新模板质量**：docs/iterations/templates/ 下的 v4.2 模板结构是否合理

### 关键原则

- 从真实文件出发，不依赖设计文档做"缺失"判断
- 路线差异 ≠ 未实现
- 必须给出 PASS / PASS_WITH_FINDINGS / REPAIRABLE_HOLD / BLOCKING_HOLD / FAIL 裁决
- 报告必须包含 Mermaid 图

---

@agent registry-file-mapper
@agent capability-authenticity
@agent yaml-schema-consistency
@agent boundary-risk
@agent review-synthesis
