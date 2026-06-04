@skill workflow-reality-review

## 审查目标

对 Adarian MVP A 线工作环境做全面 Reality Review，验证 WorkflowBase v4.0 收口就绪度。

### 范围

1. **WorkflowBase 三层**：`WorkflowBase/` 下 registry/ / runner/ / governance/ / self-maint/ / infra/ 全部文件
2. **Adarian 源码**：项目根下 src/ / main.py / tests/ / config.py / docs/iterations/ / docs/design/ 
3. **设计文档比对**：
   - 设计蓝图：`docs/design/workflow_core/workflow_core_v4.0_r2.md`（6973 行，A 线 v4.0 真实设计）
   - 实施对比报告：`docs/design/_design_vs_implementation_report_2026-06-03.md`（Hermes 写的 design vs implementation 结论）
4. **报告语言**：中文

### 审查深度

标准 + 红队双重深度。不仅要找面上的问题，还要找隐藏的矛盾和路线差异。

### 特殊要求

1. **结构完整性**：所有文件齐全、目录完整、注册表声明与文件系统一致
2. **能力真实性**：每个 YAML 声明的 module_path / command / call_pattern 真实可解析
3. **一致性**：跨文件引用（depends_on）、枚举合法性、命名规则一致
4. **边界与风险**：permission_level / risk_level / allowed_paths 合理性
5. **设计对比**：对比实际 WorkflowBase 结构 vs workflow_core_v4.0_r2.md 的设计章节
6. **结论验证**：对比 Hermes 之前写的 `_design_vs_implementation_report.md` 结论——它的"路线差异"定性是否准确？它的"未实现"断言是否合理？还是说实际是通过不同路线实现的？

### 关键原则

- 从真实文件出发，不依赖设计文档做"缺失"判断
- 路线差异 ≠ 未实现。如果设计要 A 路线但实际走了 B 路线但效果等效，标记为"路线差异"
- 必须给出 PASS / PASS_WITH_FINDINGS / REPAIRABLE_HOLD / BLOCKING_HOLD / FAIL 裁决
- 报告必须包含 Mermaid 图

---

@agent capability-authenticity
@agent boundary-risk
@agent yaml-schema-consistency
@agent registry-file-mapper
@agent structure-comparison
@agent review-synthesis
