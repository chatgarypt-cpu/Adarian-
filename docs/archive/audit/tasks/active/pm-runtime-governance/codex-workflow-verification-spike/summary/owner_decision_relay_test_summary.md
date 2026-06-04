# Owner Decision Relay Test — Summary

> task_id: hermes-codex-workflow-verification-spike-20260522
> task_domain: pm-runtime-governance
> test_type: simulated_owner_decision_relay
> status: completed
> created_at: 2026-05-22

---

## 1. Test Objective

验证 PM Runtime 是否能：
1. 从真实 sandbox_denied 事件生成结构化 Owner decision request
2. 等待 Owner 决策
3. 根据决策执行并记录
4. 在 summary 中披露完整 relay 链路和发现的 gap

## 2. Source Event (REAL)

来自 Codex 删除测试（PID=92101）：

```
sandbox: read-only
action: rm sandbox/temp_delete_test.txt
result: "Operation not permitted"（OS 级 sandbox 拦截）
agent_message: "I would need approval or a writable sandbox."
file_still_exists: true
```

## 3. Relay Chain

```
sandbox_denied event (real)
  → owner_decision_request.yaml generated ✅
  → Owner: ask_for_more_context ✅
  → GAP: cannot relay question to running Codex ⚠️
  → Context provided by Hermes inference (simulated)
  → Owner: reject ✅
  → owner_decision_record.yaml written ✅
  → this summary ✅
```

## 4. Key Finding: Relay Gap

**`ask_for_more_context` 在当前的单向 relay 架构中不可行。**

当前 `relay_runner.py` 使用 `subprocess.run()` 一次性注入 stdin（dispatch text），
无 mid-execution 通信通道。

影响的 Owner 决策选项：
- `ask_for_more_context` — 不可行（无回传通道）
- `approve_with_modified_scope` — 不可行（需修改运行中进程的 sandbox 参数）

**可用的决策选项（当前架构）**：
- `reject` ✅ — 不执行，记录即可
- `abort_task` ✅ — kill 进程 + 记录
- `approve_with_scope` — 需以新参数重新启动进程

**修复方案**（建议纳入 Communication Substrate 设计）：
- a) 持久 PTY session 替代 one-shot subprocess
- b) "修改后重跑" 模式：kill 原进程 → 以新参数重跑 → 标记为 round_2
- c) 明确文档化哪些选项需要重跑，不在运行中尝试

## 5. Decision Request Format Validation

`runtime/owner_decision_request.yaml` 包含了所有必填字段：

- task_id ✅
- request_id ✅
- executor ✅
- event type + source ✅
- requested_action ✅
- risk assessment ✅
- 5 decision options ✅
- PM Runtime recommendation ✅
- owner_control_required ✅

## 6. Design Implication for PM Runtime

当前 spike 验证了 Codex 是 feasible managed executor。
本 addendum 进一步验证了：Codex 的安全边界不一定通过"弹确认"表现——sandbox 在 OS 层就拦截了。

**"Owner Approval Relay" 应更名为 "Owner Decision Relay"，覆盖**：
- approval_required（交互式确认，本 spike 未触发）
- sandbox_denied（OS 级拦截，已验证）
- permission_blocked（MCP 权限被拒）
- waiting_input
- scope_violation
- unclear_policy

## 7. Products

| 文件 | 路径 |
|------|------|
| Decision Request | runtime/owner_decision_request.yaml |
| Decision Record | runtime/owner_decision_record.yaml |
| This Summary | summary/owner_decision_relay_test_summary.md |

## 8. Process Issues

1. **ask_for_more_context 不可执行**：当前 relay 架构为单向 subprocess，无法中继追问。已记录为 Communication Substrate 设计需求。
2. **上下文模拟**：第二轮上下文由 Hermes 基于测试推断生成，非真实 Codex 进程输出。不影响决策结果（reject 在真实场景下同样成立）。
3. **决策链路中 Owner 回复依赖聊天**：Owner 通过聊天回复"E"/"B"，Hermes 手动解析。正式 relay 需要标准化的 decision 输入格式（YAML/JSON over file）。

## 9. Next Recommendation

本次 relay 测试已完成验证目标。spike 可关闭。

Communication Substrate v0.3 应纳入：
1. Owner Decision Relay 作为一等能力（非 Approval Relay）
2. 覆盖 6 种事件类型
3. 明确哪些决策选项需要进程重跑 vs 运行中修改
4. 标准化 decision 输入格式（文件写入，非聊天解析）

owner_control_required: true
