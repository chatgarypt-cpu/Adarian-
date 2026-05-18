# Upgrade Mock Relay Test Result

**test_id**: mock-upgrade-claude-read-tools-2026-05-18
**parent_task**: hermes-agent-call-capability-check-r0
**fix_applied**: `.claude/settings.local.json` — added `"Read"` to `permissions.allow`

---

## 修复

| 文件 | 修改 | 原因 |
|------|------|------|
| `.claude/settings.local.json` | `permissions.allow` 新增 `"Read"` | Claude Code 从 settings 读权限白名单，`"Read"` 加入后自动批准，不弹对话框 |

修改内容：只在 `"allow"` 数组第一行加了 `"Read"`，其余不变。

## 测试结果：✅ PASS

| 字段 | 值 |
|------|-----|
| subtype | `success` |
| is_error | `false` |
| stop_reason | `end_turn` |
| num_turns | 3 |
| session_id | `09596bf1-1226-4880-b646-f5695dc18e2b` |
| total_cost_usd | $0.208 |
| duration_ms | 15869 |
| **permission_denials** | **`[]` — 空！** |

## 业务结果验证

| 预期 | 实际 | 结果 |
|------|------|------|
| workflow_core.md 第一行 | `# Adarian MVP 核心开发工作流 v3（Workflow Core）` | ✅ |
| 总行数 | `1209` | ✅ |
| read_success | `true` | ✅ |

## 对比：修复前 vs 修复后

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| `--allowedTools 'Read'` | ❌ BLOCKED: User denied | ✅ PASS |
| permission_denials | N/A（未执行） | `[]` 空数组 |
| Claude Code 读取文件 | 不可能 | ✅ 正常读取 |
| Hermes terminal 拦截 | 拦截权限对话框 | 不拦截（无对话框） |

## Relay 通道完整状态

| 层级 | 状态 |
|------|------|
| A (生成 prompt) | ✅ |
| B (terminal 启动 Claude Code) | ✅ |
| C (piped-data 任务) | ✅ |
| **C (Read tools 任务)** | ✅ **已打通** |
| C (multi-file audit + receipt) | ❓ 下一步验证 |

## 修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `.claude/settings.local.json` | 加 1 行 `"Read"` | 唯一修改 |
| workflow_core.md | 未修改 | ✅ |
| 业务源码 | 未修改 | ✅ |
| docs/、audit/ 正文 | 未修改 | ✅ |

---

```
CURRENT_STATUS: HOLD_WAITING_OWNER_REVIEW
```
