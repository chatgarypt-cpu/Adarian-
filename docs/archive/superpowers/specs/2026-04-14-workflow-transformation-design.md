# Workflow Transformation Design - 轻量状态层 A+

## 1. 设计目标

建立最小状态流闭环，使人类在 Codex / Claude / GPT 多 agent 协作中：
- 一眼看清楚当前状态
- 一键生成压缩视图
- 减少复制粘贴和上下文传递成本

**不做什么**：
- 不做自动回流
- 不做复杂任务系统
- 不做 agent 路由规则
- 不引入 handoff.py / sync_feedback.py / agent_hub / routing_rules

---

## 2. 组件规格

### 2.1 `control/state.json`

状态中枢，6个固定字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `stage` | string | 粗粒度阶段：final_profile / scheduler_v0 / iteration |
| `status` | string | 三态：in_progress / blocked / done |
| `current_focus` | string | 当前主目标，一句话，不超过50字 |
| `progress` | string | 进展描述，一句话，不超过50字 |
| `risks` | array[string] | 已知问题列表，空数组表示无风险 |
| `last_updated` | string | ISO日期：YYYY-MM-DD |

**初始空壳示例**：
```json
{
  "stage": "iteration",
  "status": "in_progress",
  "current_focus": "等待用户输入第一个状态",
  "progress": "待启动",
  "risks": [],
  "last_updated": "2026-04-14"
}
```

**更新规则**：
- 每次人工决策后手动更新
- 不做自动写入
- 人类保持控制权

---

### 2.2 `control/inbox.md`

反馈收集箱，人类或 agent 手动写入。

**格式要求**：每条记录必须包含以下三个元素，缺一不可：

```
- [YYYY-MM-DD] [来源] 一句话内容
```

**来源可选值**：Human / Codex / Claude / GPT / Minimax

**三栏结构**：

```markdown
# Inbox - 反馈入口

## 待处理
（空）

## 已采纳
（空）

## 丢弃
（空）
```

**记录示例**：

```
## 已采纳
- [2026-04-13] Human 采纳 v1.1.20 的 subprocess isolation 方案
- [2026-04-13] Codex 建议将 kill_failed_count=0 作为验收标准
```

---

### 2.3 `control/snapshot.md`

老板视图，一屏能看完。人类决策专用。

**固定格式**：

```markdown
# Snapshot - [last_updated]

## 状态总览
- **阶段**: [stage]
- **状态**: [🔴 blocked | 🟡 in_progress | 🟢 done]
- **主目标**: [current_focus]

## 进展
[progress 内容]

## 风险提示
[如果 risks 为空：✅ 无已知风险]
[如果 risks 有内容：逐条列出]

## 最新反馈
[inbox 中最后 3 条"已采纳"，按时间倒序]
[如果没有已采纳记录：暂无]
```

**生成时机**：手动运行 `scripts/generate_snapshot.py`

---

### 2.4 `scripts/generate_snapshot.py`

单向压缩脚本，无逆向操作。

**输入**：
- `control/state.json`
- `control/inbox.md`

**输出**：
- `control/snapshot.md`（覆盖写入）

**逻辑**：
```
1. 读取 control/state.json
2. 解析 inbox 中"已采纳"的所有记录
3. 取最新 3 条（按日期倒序）
4. 生成 snapshot.md 覆盖写入
```

---

## 3. 数据流

```
Human/Agent 写 inbox.md
Human/Agent 手动更新 state.json
         ↓
   python scripts/generate_snapshot.py
         ↓
   snapshot.md（人类决策视图）
```

**无自动回流**：agent 执行结果由人类手动写入 inbox.md。

---

## 4. 文件清单

```
adarian mvp/
├── control/
│   ├── state.json      # 状态中枢（6字段）
│   ├── inbox.md        # 反馈入口（三栏格式）
│   └── snapshot.md     # 脚本生成（老板视图）
└── scripts/
    └── generate_snapshot.py  # 单向压缩脚本
```

---

## 5. 验证标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | snapshot.md 在编辑器中一屏能显示完 | 目测 |
| 2 | 更新 state.json 后，重新运行脚本能反映变化 | 运行脚本后检查 snapshot |
| 3 | inbox.md 中的已采纳记录能出现在 snapshot.md | 运行脚本后检查 |
| 4 | risks 为空时显示"✅ 无已知风险" | 检查 snapshot 生成逻辑 |
| 5 | snapshot 状态指示器正确显示 🔴/🟡/🟢 | 对照 status 字段值 |

---

## 6. 使用约定

| 场景 | 操作 |
|------|------|
| 跑完一个 iteration | 手动更新 state.json + 往 inbox.md 写 feedback |
| 想看当前状态 | 直接打开 snapshot.md |
| inbox 堆积 | 定期清理，已采纳转 state.json，丢弃说明原因 |

---

## 7. 决策

本方案由用户在 2026-04-14 批准，进入实现阶段。
