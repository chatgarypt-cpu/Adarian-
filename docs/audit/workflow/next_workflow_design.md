# Next Workflow Design

## 0. Purpose

本文件不是审计报告，而是基于 `docs/workflow_audit_report.md` 的下一轮 workflow 设计建议。

目标：
- 让 workflow 可被审查
- 让 workflow 可被解释
- 让 iteration 在 git 层面可被稳定回滚

约束：
- 不先上复杂 orchestrator
- 不再引入需要人工维护的第二状态源
- 优先用最小改动获得最大治理收益

---

## 1. Design Principles

### 1.1 Auditable

每次 iteration 必须留下可重建证据：
- iteration doc
- 版本锚点
- 交付说明
- 测试结论
- 是否关闭

### 1.2 Explainable

每次结构性修改必须能回答：
- 为什么要改
- 替代方案是什么
- 为什么这次不选替代方案

### 1.3 Rollbackable

每次 iteration 结束后，必须能明确回答：
- 上一版本是谁
- 当前版本锚点是谁
- 回滚后如何验证回到了上一版本

### 1.4 Single Authority

下一轮 workflow 只能有一套规则权威源和一套运行状态权威源。

### 1.5 Read-Only Summary

任何控制台、摘要页、snapshot 都只能从权威事实自动生成，不得要求人工维护第二份状态。

---

## 2. Priority and ROI

| Rank | Item | Priority | ROI | Reason |
| --- | --- | --- | --- | --- |
| 1 | 建立 iteration 级 git freeze 规则 | P0 | Very High | 最低成本解决版本锚点与回滚不可证问题 |
| 2 | 建立 single authority model | P0 | Very High | 直接降低多源状态冲突 |
| 3 | 给 handoff 加最小事件字段 | P1 | High | 直接提升可审查、可解释能力 |
| 4 | 清退 control plane MVP | P1 | High | 立即减少额外维护链路 |
| 5 | 重建只读 summary layer | P2 | Medium-High | 在 authority 稳定后低风险恢复概览能力 |
| 6 | 评估是否需要 orchestrator | P3 | Low-Medium | 目前不是主要 ROI 点 |

---

## 3. Recommended Actions

### 3.1 P0: Iteration Freeze Contract

这是 ROI 最高的一项。

每次 iteration 关闭前必须满足：
- 工作树干净
- 有唯一 release anchor：tag 或等价命名 commit
- iteration doc 状态已关闭
- `TASK_LOG.md` 有完成记录
- 有最小验收记录

建议最小命名：
- tag: `iter-vX.Y.Z-closeout`

验收结果：
- 可以明确回答“上一版本是谁”
- 可以明确执行 `checkout <previous_tag>` 进行回退验证

### 3.2 P0: Single Authority Model

建议直接收敛为：
- 流程规则权威源：`docs/skills/workflow_core.md`
- 运行状态权威源：`docs/iterations/TASK_LOG.md` + iteration doc 状态

说明：
- 这不是最完美方案
- 但它比当前“workflow_core + state.json + snapshot + TASK_LOG 并存”更稳定

### 3.3 P1: Minimal Eventization

不做复杂事件总线，只补最小字段：
- `task_id`
- `attempt_id`
- `review_id`
- `acceptance_id`

最低落点：
- iteration doc
- `TASK_LOG.md`
- Codex 交付说明
- MiniMax 验收记录

直接收益：
- 失败项可以归属到具体 attempt
- review 意见可以区分“已消费”和“未消费”

### 3.4 P1: Retire Control Plane MVP

理由不是“它毫无价值”，而是：
- 它没有成为权威源
- 它增加维护成本
- 它与现有主流程重叠冲突

退役顺序：
1. 停止新增功能
2. 清理脚本对 `control/` 的依赖
3. 删除或归档 `control/`
4. 在主流程文档中声明退役

### 3.5 P2: Rebuild Read-Only Summary Layer

只有在 authority model 稳定后才值得做。

新 summary layer 应满足：
- 只读
- 自动生成
- 不要求人工维护第二份状态
- 可随时删除而不影响主闭环

输入建议：
- iteration doc 状态
- `TASK_LOG.md`
- 最新 release anchor

### 3.6 P3: Orchestrator Review

只有在以下条件同时成立时才值得做：
- 人工 relay 仍是主瓶颈
- minimal eventization 已稳定
- rollback 规则已落地

否则不要为了“更高级”而引入 orchestrator。

---

## 4. Minimal Target Workflow

建议的下一轮最小目标 workflow：

1. Human 创建或确认 iteration doc
2. MiniMax 初始化 `TASK_LOG`
3. Codex 输出 Pre-Implementation Review，带 `review_id`
4. Human 批准
5. Codex 实现并交付，带 `attempt_id`
6. MiniMax 测试验收，带 `acceptance_id`
7. 失败则进入下一轮 attempt
8. 通过后关闭 iteration
9. 执行 git freeze：clean tree + tag

这个版本仍然是人主导的文档工作流，但已经具备：
- 可被审查
- 可被解释
- 可被回滚

---

## 5. Do Not Do Yet

- 不要先做新的 control plane
- 不要先做复杂路由器
- 不要先做 agent chatroom
- 不要在未建立 release anchor 前承诺逐版本回滚

---

## 6. Success Criteria

下一轮 workflow 若要算成功，至少满足：
- 任一 iteration 都能定位到前一个 release anchor
- 任一失败反馈都能定位到具体 attempt
- 任一结构改动都能找到理由与替代方案说明
- summary layer 若存在，删除后不影响主闭环

---

## 7. Final Recommendation

最优路线不是“继续叠控制层”，而是：

1. 先建立 git freeze contract
2. 再收敛 authority
3. 再补最小事件字段
4. 然后退役旧 control plane
5. 最后才考虑只读 summary 或 orchestrator

这条路线的 ROI 最高，因为它优先解决的是：
- 回滚不可证
- 状态冲突
- handoff 不可审计

而不是先做新的表层工具。
