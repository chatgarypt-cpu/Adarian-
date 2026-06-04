@skill code-reality-review

## 审查目标

对 Adarian MVP 源码做全面 Code Reality Mapping Review，提取真实代码结构、职责边界、运行时流程。

### 范围

1. **Adarian 源码**：项目根下全部 Python 代码
   - `src/` — 模拟引擎核心（phase0-phase4、social_network、event 等）
   - `main.py` — 入口与 CLI
   - `config.py` — 配置系统
   - `tests/` — 测试覆盖
   - `profiling/` — 性能分析
2. **报告语言**：中文

### 审查深度

标准 + 红队双重深度。不仅要看代码结构，还要找：
- 代码粘稠度和过度设计
- 模棱两可的职责边界
- 可维护性隐患
- 实际运行时流程 vs 预期设计

### 关键原则

- 从真实代码出发，先描述再评价
- 必须画 Mermaid 图（模块关系、运行时流程）
- 必须给出 PASS / PASS_WITH_FINDINGS / REPAIRABLE_HOLD 裁决

---

@agent registry-file-mapper
@agent capability-authenticity
@agent yaml-schema-consistency
@agent boundary-risk
@agent review-synthesis
