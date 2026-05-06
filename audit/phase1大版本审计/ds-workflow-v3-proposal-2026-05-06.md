# DS Workflow v3 Proposal: Role Model & Skill & Hook Redesign

**日期**: 2026-05-06
**作者**: DS Agent Team
**目的**: 将 Adarian MVP 工作流从 User/Codex/MiniMax 三角色模型升级为 User/Control Agent/Codex/DS Team 四角色 pipeline，对齐 v3 迭代模板

---

## 1. 角色模型变更

### 旧（v1.x）

```
User → Codex（实现）→ MiniMax（测试验收）
```

### 新（v3）

```
User/Owner → Control Agent → DS Pre-Audit → Codex → DS Verify → DS Accept → Closeout
```

### 角色定义

| 角色 | 职责 | 不负责 |
|------|------|--------|
| **User / Owner** | 提出版本需求、审核方案、最终 Gate 决策 | 不实现、不测试 |
| **Control Agent** | 版本定位、Gate 判断、采纳/不采纳 DS 建议、收口范围、编写迭代文档 | 不落盘代码、不执行测试 |
| **DS Team** | 前置审查（源码事实/风险/边界）、后置验证（py_compile/import/forbidden/smoke/artifact）、验收判定（Hard/Soft target） | 不重新设计版本范围、不扩大架构、不替 Control Agent 做 Gate |
| **Codex (Main Agent)** | 按迭代文档执行代码落盘、输出 attempt 交付说明 | 不测试、不更新 TASK_LOG/CHANGELOG、不自行决定范围 |

---

## 2. Pipeline 流程

```mermaid
A["User / Owner<br/>提出版本需求"] --> B["Control Agent<br/>版本定位与 Gate"]
    
B --> C{"是否需要 DS 前置审查？"}
    
C -->|需要| D["DS Pre-Audit<br/>源码事实 / 风险 / 边界"]
C -->|不需要| E["Scope Freeze<br/>范围冻结"]
    
D --> F["Control Agent<br/>采纳 / 不采纳 / 二次收口"]
F --> E
    
E --> G["Iteration Plan<br/>目标 / 允许 / 禁止 / 延后"]
    
G --> H{"是否需要分 attempt？"}
    
H -->|单阶段| I["Codex Attempt 01<br/>执行落盘"]
H -->|多阶段| J["Codex Attempt 01<br/>子任务 A"]
J --> K["Codex Attempt 02<br/>子任务 B"]
    
I --> L["DS Verify<br/>测试 / 产物 / 范围检查"]
K --> L
    
L --> M{"DS Accept"}
    
M -->|pass| N["Closeout<br/>允许进入下一版本"]
M -->|pass_with_known_issues| O["Closeout + Carry-over<br/>允许但带债务"]
M -->|fail / hold| P["Stop<br/>不得进入下一版本"]
```

### 各阶段产物

| 阶段 | 角色 | 输入 | 输出 |
|------|------|------|------|
| B | Control Agent | 用户需求 | Gate 判断 + 初版迭代文档 |
| D | DS Team | 初版迭代文档 + 当前源码 | DS Pre-Audit Report (`audit_id`) |
| F | Control Agent | DS Pre-Audit Report | 采纳/不采纳决策 + 范围收口 |
| G | Control Agent | 收口后的范围 | 正式 Iteration Plan（v3 模板） |
| I/J/K | Codex | Iteration Plan | 代码变更 + 交付说明 (`attempt_id`) |
| L | DS Team | Codex 交付 + Iteration Plan | DS Verify Report |
| M | DS Team | DS Verify Report | Acceptance Result (`acceptance_id`) |
| N/O/P | User/Control Agent | Acceptance Result | Closeout 决策 |

---

## 3. Eventization 字段升级

### 旧字段（v2）

```
task_id / review_id / attempt_id / acceptance_id
```

### 新字段（v3）

| 字段 | 生产者 | 含义 | 出现位置 |
|------|--------|------|---------|
| `task_id` | Control Agent | 迭代级唯一任务标识 | 迭代文档、TASK_LOG |
| `audit_id` | DS Team | 一次 DS 前置审查标识 | DS Pre-Audit Report、迭代文档 §4 |
| `attempt_id` | Codex | 一次代码交付标识 | Codex 交付说明、TASK_LOG |
| `acceptance_id` | DS Team | 一次验收结论标识 | DS Accept Report、TASK_LOG |

### 最小要求

- 迭代文档必须声明 `task_id`
- DS Pre-Audit 必须声明 `audit_id`
- 每次 Codex 交付必须声明 `attempt_id`
- DS Accept 必须声明 `acceptance_id`，且引用对应的 `attempt_id` 和 `audit_id`

---

## 4. DS Skill 设计

### 4.1 `/ds-pre-audit` — DS 前置结构审查

**触发时机**: Control Agent 完成初版迭代文档后，Gate = CONDITIONAL_GO 或 GO 时

**输入**:
- 当前迭代文档（draft 或 under_review）
- 当前源码树（`src/`、`main.py`、`config.py`）
- v1.2.5 前置审查报告（作为参考模板）

**执行步骤**:
1. 读取迭代文档，提取目标结构、允许/禁止修改列表
2. 扫描 `src/` 下所有 `.py` 文件，建立文件清单
3. 追踪 `main.py` 的 import 链路，区分主链/legacy/独立工具
4. 搜索 whitebox 相关关键词，定位分散的观测逻辑
5. 检查 forbid 声明的文件是否确实存在且不应触碰
6. 评估循环 import 风险、shim 策略可行性
7. 输出结构化 DS Pre-Audit Report

**输出**:
- `audit_id`（格式：`audit-vX.Y.Z-{序号}`，如 `audit-v1.2.5-01`）
- Verdict：GO / CONDITIONAL_GO / HOLD / FAIL
- Source Tree Facts 表格
- Phase Package Migration Assessment
- Whitebox Logic Inventory
- Whitebox Boundary Judgment
- Blockers / Risk List / Carry-over 建议
- Recommended Execution Scope for Codex

**输出位置**: `audit/phase1大版本审计/vX.Y.Z-{topic}-{date}.md`

**不负责**:
- 不重新设计版本范围
- 不扩大架构
- 不把建议项自动升级为 blocker
- 不替 Control Agent 做最终 Gate 判断

---

### 4.2 `/ds-verify` — DS 后置验证

**触发时机**: Codex 完成一轮 attempt 交付后

**输入**:
- Codex 交付说明（含 `attempt_id`、修改文件列表）
- 当前迭代文档（含验收命令、Hard/Soft acceptance target）
- 当前 git 状态

**执行步骤**:

**Phase 1 — 静态检查**:
1. 对 Codex 修改的每个 `.py` 文件执行 `python -m py_compile`
2. 对迭代文档声明的所有新增文件执行 `python -m py_compile`

**Phase 2 — Forbidden Files 检查**:
3. `git diff --name-only HEAD` 对照迭代文档 §6.3 禁止修改列表
4. 如发现禁止文件被修改 → 立即报 FAIL，不继续后续步骤

**Phase 3 — Import 完整性检查**:
5. 新 package import 测试（如 `python -c "from src.phase1 import ..."`）
6. Legacy shim import 测试（如 `python -c "from src.phase1_entity_extraction import ..."`）
7. Whitebox import 测试

**Phase 4 — Smoke Test**:
8. `python main.py seeds/test1.txt`
9. 检查进程退出码 = 0
10. 检查控制台无 traceback

**Phase 5 — Artifact Contract 检查**:
11. 确认 `outputs/runs/<latest_run_id>/` 存在
12. 逐项检查迭代文档 §8.5 声明的所有产物是否存在
13. 对 whitebox 产物做结构校验

**输出**:
- 每个 Phase 的通过/失败状态
- Forbidden files 检查结果
- 产物清单检查结果
- 总体判定：all_pass / partial_fail / hard_fail

**不负责**:
- 不修改代码
- 不运行 test7（除非迭代文档声明为硬门槛）
- 不更新 TASK_LOG/CHANGELOG（那是 accept 阶段的事）

---

### 4.3 `/ds-accept` — DS 验收判定

**触发时机**: `/ds-verify` 完成后

**输入**:
- `/ds-verify` 的输出
- 当前迭代文档的 Hard/Soft Acceptance Target（§9）

**执行步骤**:
1. 逐项对照 Hard Acceptance Target
2. 任一 Hard target 不满足 → `fail`
3. 所有 Hard target 满足，但存在 Soft target 不满足 → `pass_with_known_issues`
4. 全部满足 → `pass`
5. 输出 Acceptance Report
6. 将结果写入 `TASK_LOG.md`（含 `acceptance_id`）
7. 更新 `CHANGELOG.md`
8. 更新迭代文档状态

**输出**:
- `acceptance_id`（格式：`accept-vX.Y.Z-{序号}`）
- `acceptance_result`：pass / pass_with_known_issues / fail / hold
- `carry_over`：软目标未满足项
- 是否允许进入下一版本

**Acceptance Report 最小字段**:
```text
task_id: task-vX.Y.Z-xxx
audit_id: audit-vX.Y.Z-01
attempt_id: attempt-vX.Y.Z-01
acceptance_id: accept-vX.Y.Z-01
acceptance_result: pass / pass_with_known_issues / fail
hard_targets: 16/16
soft_targets: 5/7
carry_over:
  - item 1
  - item 2
```

---

## 5. Hook 设计

### 5.1 PreCommit Hook 更新

**当前问题**:
1. Windows 路径 `D:/项目开发/研一/adarian/adarian mvp` 在 macOS 上无效
2. 只做 py_compile，不做 forbidden files 检查
3. 无 DS 相关检查

**更新后**:

```json
{
  "hooks": {
    "PreCommit": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"${CLAUDE_PROJECT_DIR}\" && python3 -m py_compile main.py 2>&1 && python3 -m py_compile src/*.py 2>&1 || echo \"[DS] 语法检查失败\"",
            "timeout": 30,
            "statusMessage": "[DS] py_compile 语法检查..."
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"${CLAUDE_PROJECT_DIR}\" && echo \"[DS] forbidden files check: manual gate required for schemas.py config.py llm_client.py runtime_logger.py speaker_selector.py\"",
            "timeout": 5,
            "statusMessage": "[DS] forbidden files 提醒..."
          }
        ]
      }
    ]
  }
}
```

**说明**: 第二个 hook 只是提醒，不做硬阻断。真正的 forbidden files 检查在 `/ds-verify` 中通过 `git diff` 强制执行。

### 5.2 未来可选的 PostToolUse Hook

当 `python main.py seeds/*.txt` 执行完成后，自动触发 artifact check。但当前阶段不建议自动触发（可能造成噪音），保留为 `/ds-verify` 的手动步骤。

---

## 6. `workflow_core.md` 重写草案

以下是 `docs/skills/workflow_core.md` 的重写草案，替换当前 v2 版本。

---

```markdown
# Adarian MVP 核心开发工作流 v3（Workflow Core）

## 定位

本文件是 Adarian 项目的唯一流程规则权威源。

如与其他 workflow 文档冲突，以本文件为准。

---

## 角色分工

| 角色 | 职责 | 不负责 |
|------|------|--------|
| **User / Owner** | 提出版本需求、审核方案、最终 Gate 决策 | 不实现、不测试 |
| **Control Agent** | 版本定位、Gate 判断、采纳/不采纳 DS 建议、收口范围、编写迭代文档 | 不落盘代码、不执行测试 |
| **DS Team** | 前置审查（源码事实/风险/边界）、后置验证（py_compile/import/forbidden/smoke/artifact）、验收判定（Hard/Soft target）、更新 TASK_LOG/CHANGELOG | 不重新设计版本范围、不扩大架构、不替 Control Agent 做 Gate |
| **Codex (Main Agent)** | 按迭代文档执行代码落盘、输出 attempt 交付说明 | 不测试、不更新 TASK_LOG/CHANGELOG、不自行决定范围 |

---

## Pipeline

```
User → Control Agent → [DS Pre-Audit] → Control Agent 收口 →
  Iteration Plan → Codex Attempt(s) → DS Verify → DS Accept → Closeout
```

DS Pre-Audit 是否需要由 Control Agent 在 Gate 阶段决定。

---

## Authority Model

### Rule Authority

本文件定义所有流程规则、gate、closeout 条件。

### Runtime Authority

当前运行状态只看三类事实：

- 当前 iteration 文档中的状态字段
- `docs/iterations/TASK_LOG.md` 中最新的验收记录
- `audit/phase1大版本审计/` 中最新的 DS Pre-Audit Report

以下内容不是现行状态源：

- `control/state.json`
- `control/inbox.md`
- `control/snapshot.md`
- 任何 probe 运行摘要

---

## Eventization

| 字段 | 生产者 | 含义 |
|------|--------|------|
| `task_id` | Control Agent | 迭代级唯一任务标识 |
| `audit_id` | DS Team | 一次 DS 前置审查标识 |
| `attempt_id` | Codex | 一次代码交付标识 |
| `acceptance_id` | DS Team | 一次验收结论标识 |

最小要求：

- 迭代文档必须声明 `task_id`
- DS Pre-Audit 必须声明 `audit_id`
- 每次 Codex 交付必须声明 `attempt_id`
- DS Accept 必须声明 `acceptance_id`，且引用对应的 `attempt_id`

---

## 核心流程

### Phase A: 规划

1. User 提出版本需求
2. Control Agent 做版本定位，输出初版迭代文档（含 Gate 判断）
3. Control Agent 判断是否需要 DS 前置审查
4. 若需要：DS Team 执行 `/ds-pre-audit`，输出带 `audit_id` 的 Pre-Audit Report
5. Control Agent 审阅 Pre-Audit Report，采纳/不采纳/二次收口
6. Control Agent 输出正式 Iteration Plan（v3 模板，含 Execution Attempts）

### Phase B: 执行

7. Codex 读取 Iteration Plan、workflow_core.md、相关源码
8. Codex 执行一轮代码修改，输出带 `attempt_id` 的交付说明
9. 若多 attempt：attempt-02 必须等 attempt-01 通过后才能开始

### Phase C: 验证

10. DS Team 执行 `/ds-verify`
11. DS Team 执行 `/ds-accept`，输出带 `acceptance_id` 的验收结论
12. 若 fail：用户转发失败信息给 Codex，进入下一轮 attempt
13. 若 pass / pass_with_known_issues：DS Team 更新 TASK_LOG、CHANGELOG、迭代文档状态

### Phase D: 收口

14. User/Control Agent 做 Closeout 决策
15. 允许进入下一版本 / 需要补充修复

---

## Attempt 依赖规则

当 Iteration Plan 声明多 attempt 时：

- attempt-02 必须依赖 attempt-01 通过（DS Accept 判定为 pass）
- 两个 attempt 不得并行执行
- 若两个 attempt 都需修改同一文件，必须在 Iteration Plan 中明确声明
- 若 attempt-01 fail，attempt-02 不得开始

---

## 验收分级

### Hard Acceptance Target

不满足任一项即 fail / hold。定义在迭代文档 §9.1。

### Soft Acceptance Target

不满足可记录为 pass_with_known_issues。定义在迭代文档 §9.2。

### 验收结果

| 结果 | 含义 | 是否可进入下一版本 |
|------|------|-----------------|
| `pass` | 全部 Hard + Soft 通过 | 是 |
| `pass_with_known_issues` | Hard 全部通过，部分 Soft 未满足 | 是（带 carry-over） |
| `fail` | 至少一项 Hard 未通过 | 否 |
| `hold` | 发现阻塞性问题，需 Control Agent 重新决策 | 否 |

---

## 禁止变化守则

每轮执行必须遵守迭代文档 §3.4 和 §6.3 声明的禁止变化。

DS Team 在 `/ds-verify` 中通过 `git diff` 强制执行 forbidden files 检查。
DS Team 在 `/ds-accept` 中逐项对照 Hard target 中的禁止变化项。

---

## DS Skill 清单

| Skill | 用途 | 阶段 |
|-------|------|------|
| `/ds-pre-audit` | 前置结构审查 | Phase A |
| `/ds-verify` | 后置验证（py_compile + forbidden + import + smoke + artifact） | Phase C |
| `/ds-accept` | 验收判定 + 更新 TASK_LOG/CHANGELOG/迭代文档 | Phase C |

---

## 文档更新规则

| 文档 | 更新触发 | 责任 |
|------|--------|------|
| `TASK_LOG.md` | DS Accept 完成后 | DS Team |
| `CHANGELOG.md` | DS Accept 通过后 | DS Team |
| 迭代文档 | 状态变化 / closeout | DS Team（验收后）/ Control Agent（规划阶段） |
| `dev_spec.md` | 架构变化 | DS Team |

---

## 异常处理

### 迭代文档不清晰
- DS Team 在 Pre-Audit 阶段标记
- Control Agent 澄清后继续

### 测试失败
- DS Verify 输出具体失败项
- 附带 `attempt_id`
- 用户转发 Codex

### 文档与代码结构冲突
- DS Team 在 Pre-Audit 阶段指出
- 不允许 Codex 直接按文档强行实现
- 必须等待 Control Agent 确认

### 发现越界修改
- DS Verify 的 forbidden files 检查捕获
- 立即报 FAIL
- Codex 必须回退越界修改

---

## 关联文档

| 文档 | 作用 |
|------|------|
| `iteration_execution_guard.md` | Codex 实现前架构核对 |
| `main_agent_delivery.md` | Codex 行为规范 |
| `audit/phase1大版本审计/` | DS Pre-Audit Report 存档 |

---

## 一句话总结

> Control Agent 定范围，DS Team 审边界验产物，Codex 落盘不改范围，User 做最终 Gate。
```

---

## 7. .claude/settings.json 更新

```json
{
  "hooks": {
    "PreCommit": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -m py_compile main.py 2>&1 && python3 -m py_compile src/*.py 2>&1 || echo \"[DS] py_compile 语法检查失败\"",
            "timeout": 30,
            "statusMessage": "[DS] py_compile 语法检查..."
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"[DS] forbidden files 提醒: schemas.py config.py llm_client.py runtime_logger.py speaker_selector.py 不得修改\"",
            "timeout": 5,
            "statusMessage": "[DS] forbidden files 提醒..."
          }
        ]
      }
    ]
  }
}
```

**变动**:
1. 移除硬编码 Windows 路径 `D:/项目开发/研一/adarian/adarian mvp`，改用 `python3` 直接从 CWD 执行
2. `py` → `python3`（macOS 兼容）
3. 新增第二个 hook：forbidden files 提醒（不硬阻断，仅提示）

---

## 8. CLAUDE.md 需同步的变更

当前 CLAUDE.md 中：

```
`docs/skills/workflow_core.md` 是当前唯一流程规则权威源。
```

保持不变。但角色描述部分从 "MiniMax Claude Code（Sub Agent）负责测试与验收" 需更新为 "DS Team 负责前置审查、测试验收与文档同步"。

---

## 9. 待决策事项

| # | 问题 | 建议 |
|---|------|------|
| 1 | `iteration_execution_guard.md` 是否保留？ | 保留但简化，去掉 MiniMax 引用，DS Team 不再需要这份 gate（那是 Codex 的） |
| 2 | `main_agent_delivery.md` 是否保留？ | 保留，Codex 行为规范仍有效 |
| 3 | 旧的 `SKILLS.md` 是否更新？ | 替换为新的 DS Skill 清单 |
| 4 | `/test1`、`/verify` 旧 skill 是否退役？ | 退役，功能被 `/ds-verify` 吸收 |
```

---

## 10. 实施步骤（待你审批后）

1. 将 §6 的 `workflow_core.md` 草案落盘到 `docs/skills/workflow_core.md`
2. 更新 `.claude/settings.json`
3. 更新 `.claude/SKILLS.md`
4. 更新 `CLAUDE.md` 中角色描述
5. 简化 `iteration_execution_guard.md`（去 MiniMax 引用）
6. 三个 DS Skill 在后续实际使用时通过 `/skill` 创建
