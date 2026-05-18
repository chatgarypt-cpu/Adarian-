# Mock Relay Test Result

**test_id**: mock-relay-claude-piped-2026-05-18
**parent_task**: hermes-agent-call-capability-check-r0
**date**: 2026-05-18

---

## 1. Test Summary

| 项目 | 值 |
|------|-----|
| 调用方式 | `ls docs/skills/ \| claude -p '...'` (管道数据进 Claude) |
| 权限标志 | 无（不使用 `--allowedTools`） |
| max_turns | 3 |
| 输出格式 | JSON (`--output-format json`) |
| 结果 | ✅ **PASS** |

## 2. Claude Code 回执摘要

| 字段 | 值 |
|------|-----|
| subtype | `success` |
| is_error | `false` |
| stop_reason | `end_turn` (正常完成) |
| num_turns | 2 |
| session_id | `7ddaa35f-0205-4cb0-be6e-040555c9908b` |
| total_cost_usd | $0.185 |
| duration_ms | 10075 |
| terminal_reason | `completed` |

## 3. 业务结果

```json
{
  "total_files": 6,
  "file_list": [
    "ds_accept.md",
    "ds_pre_audit.md",
    "ds_verify.md",
    "iteration_execution_guard.md",
    "main_agent_delivery.md",
    "workflow_core.md"
  ],
  "status": "completed"
}
```

**验证**：文件列表与 `ls docs/skills/` 输出一致。✅

## 4. Hermes Intake 验证

| 步骤 | 结果 |
|------|------|
| write_file 输出 mock_receipt.json | ✅ 落盘 |
| read_file 读取 mock_receipt.json | ✅ 成功读取 |
| JSON 结构完整 | ✅ subtype, session_id, result, cost 齐全 |
| 业务结果可解析 | ✅ 6 个文件，列表正确 |

## 5. 观察到的边界行为

| 行为 | 说明 |
|------|------|
| MCP tools 权限拒绝 | Claude 尝试调用 `mcp__filesystem__list_directory` 被拒绝（permission_denials）。但不影响任务：Claude 通过管道数据完成了统计。 |
| 双模型调用 | Claude Code 内部使用了 Deepseek-v4-flash（小模型做快速判断）+ Deepseek-v4-pro（主模型做回答），自动分层。 |
| 缓存命中 | `cache_read_input_tokens: 30720` — 第二次调用命中了第一次的上下文缓存。 |

## 6. 能力等级更新

| 等级 | 之前 | 之后 |
|------|------|------|
| A (只能生成 prompt) | ✅ | ✅ |
| B (terminal 启动 agent) | ⚠️ 部分 | ✅ **已证明** |
| C (piped-data 任务 + 读 receipt) | ❌ | ✅ **已证明** |
| C (Read tools 任务 + 读 receipt) | ❌ | ❓ 未测试 — 仍可能被权限对话框阻塞 |

## 7. 已验证的完整 Relay 链路

```
Hermes terminal
  → claude -p (管道输入, 无 --allowedTools)
  → Claude Code 处理
  → stdout JSON (subtype=success)
  → tee → 落盘文件
  → Hermes read_file
  → JSON 解析
  → 字段验证
  ✅ 全链路通过
```

## 8. 仍未验证的

| 项目 | 状态 |
|------|------|
| `--allowedTools 'Read'` 的 Claude Code dispatch | ❓ 之前 4 次全失败 |
| `--permission-mode auto` 是否可行 | ❓ 未测试 |
| Codex CLI 调用 | ❓ 未测试 |
| `--append-system-prompt-file` 是否影响权限对话框 | ❓ 未测试（mock 中未使用） |

## 9. 建议的下一步升级测试

### 升级 Mock 1：加 `--allowedTools 'Read'`

```bash
cd "..." && claude -p "读取 docs/skills/workflow_core.md 第一行" \
  --allowedTools 'Read' --max-turns 3 --output-format json
```

**风险**：可能再次触发权限对话框，被 Hermes terminal 拦截。

### 升级 Mock 2：加 `--allowedTools 'Read' --permission-mode auto`

同上，加 `--permission-mode auto` 尝试自动批准权限。

**风险**：`--permission-mode` 标志可能被 Hermes terminal 拦截。

## 10. 结论

**基础 relay 通道已验证可用。** Hermes 可以通过 terminal 启动 Claude Code、获取结构化回执、落盘文件并回收验证。阻塞点在 `--allowedTools` 触发的权限对话框，而非 Claude Code 本身。

```
CURRENT_STATUS: HOLD_WAITING_OWNER_REVIEW
```
