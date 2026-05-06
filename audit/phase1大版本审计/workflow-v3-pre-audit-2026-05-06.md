# DS Workflow v3 Pre-Audit Report

**audit_id**: `audit-workflow-v3-01`
**审计对象**: `docs/skills/workflow_core.md` v3 修订版（Control Agent 提供）
**日期**: 2026-05-06
**审计团队**: DS Agent Team

---

## 1. Verdict

**GO**

Control Agent 的 v3 修订版角色边界清晰、Pipeline 完整、防漂移机制到位，可以直接落盘。

---

## 2. Summary

1. **角色模型正确**: 四角色（User / Control Agent / DS Team / Codex）的职责边界和对"不负责"的声明都足够精确，没有模糊地带。
2. **DS 三条 Skill 的边界严格**: `/ds-pre-audit` 不能扩大范围、`/ds-verify` 覆盖了五阶段检查、`/ds-accept` 明确不能越权 closeout。
3. **Attempt 串行默认 + 并行条件严格**: 五个并行条件缺一不可，且明确两个 attempt 不能同时改 main.py，符合 v1.2.5 的实际需求。
4. **防漂移规则是亮点**: §16 列出了 10 种具体 drift 类型，比 DS 提案中的模糊表述强得多，可以直接作为 Codex 执行前的检查清单。
5. **Hook 定位正确**: "只作为低成本预警，不作为验收权威"——这句话解决了 Hook 替代 DS Verify 的风险。

---

## 3. Hard Blockers

None.

---

## 4. Required Fixes Before Landing

None.

Control Agent 版本已经可以直接落盘。以下 §5 的建议均为 soft，不影响 GO 判定。

---

## 5. Soft Recommendations

| # | 位置 | 问题 | 建议 |
|---|------|------|------|
| 1 | §8.3 DS Pre-Audit 输出 | 列举了 report 必须包含的字段，但没有给出 report 文件名约定 | 建议补充：报告存放路径 `audit/phase1大版本审计/vX.Y.Z-{topic}-{date}.md`，让 DS 团队有明确的落盘位置 |
| 2 | §9.4 Phase 2 Forbidden Files | `git diff --name-only <base_commit_or_HEAD>` 在 HEAD 是 merge commit 或多 commit 时可能不准确 | 建议明确：若 Codex 产生了多个 commit，DS Verify 应要求 Codex 提供本轮 iteration 开始前的 `base_commit`，而不是用 `HEAD~1` 猜测 |
| 3 | §11 Codex 执行规则 | "执行声明的测试命令" 与 DS Verify 的测试职责有轻微重叠 | 建议明确：Codex 执行的是"自检级"测试（确保不崩），DS Verify 执行的是"验收级"测试（对照 Hard target）。两者不冲突但应注明层级差异 |
| 4 | §17 Hook | `compileall -q src` 的 `-q` 参数在部分 Python 版本中行为不一致 | 建议改为 `python3 -m compileall src`（去掉 `-q`），或显式指定 `-q` 仅在 Python 3.9+ 生效。不影响功能，仅影响 hook 输出的可读性 |
| 5 | §18 当前项目阶段规则 | 记录了 v1.2.3 → v1.2.5 和 R1 的路线，但没有标注本文件自身的版本 | 建议在 §0 或末尾加一行：`workflow_core.md version: v3.0, ratified: 2026-05-06` |

---

## 6. Boundary Risk Assessment

### Control Agent boundary: **SAFE**

- §6 明确 Control Agent 负责版本治理、Gate、迭代文档、closeout
- §6 同时列出 5 条"不得"，包括"不得把最终 Gate 交给 DS"、"不得把迭代文档写作交给 Codex"
- Control Agent 的权力和限制对称，没有权力真空

### DS Team boundary: **SAFE**

- §8.4 / §9.5 / §10.5 三次强调 DS 不能扩大范围、不能替代 Gate
- `/ds-accept` 输出 `acceptance_result` 和 `closeout_recommendation`，但明确"最终 closeout 由 Control Agent / User 确认"
- DS 的三条 skill 形成闭环但不越权

### Codex boundary: **SAFE**

- §11 严格限制 Codex 只按迭代文档执行
- 交付说明的字段要求完整（attempt_id + 文件清单 + 测试结果 + run_dir）
- "不得自行修改 TASK_LOG / CHANGELOG" 直接切断了 Codex 越权路径

### User / Owner boundary: **SAFE**

- §1 和 §15 明确 User 保留最终方向判断和 closeout 审批权
- Pipeline 图中 User 出现在起点和终点，位置正确

---

## 7. Runtime Authority Assessment

| 权威源 | 处理是否正确 | 说明 |
|--------|------------|------|
| iteration doc | 正确 | §5.1 第一条 |
| TASK_LOG | 正确 | §5.1 第二条 + §14 详细规则 |
| CHANGELOG | 正确 | §14.2 明确记录内容 |
| run_dir | 正确 | §5.2 列为运行事实权威源，列出 9 个证据文件 |
| DS reports | 正确 | §5.3 列为审计事实权威源 |
| legacy control files | 正确 | §5.4 明确排除 `control/state.json`、`inbox`、`snapshot`、历史 probe |

特别肯定：§5.4 把"未被 DS / Control Agent 接受的建议项"也列为非权威源，这个细节防止了聊天记录里的随口建议污染 workflow。

---

## 8. Hook Assessment

**适合当前阶段。**

理由：
1. `${CLAUDE_PROJECT_DIR}` 变量解决了路径跨平台问题，不再硬编码 Windows 路径
2. `python3 -m compileall src` 比原来的 `py -m py_compile src/*.py` 更规范（compileall 递归处理子目录）
3. Forbidden files hook 只是 echo 提醒，不做硬阻断——符合"Hook 不替代 DS Verify"的规则
4. Hook 数量少（仅 2 个），不造成提交噪音

---

## 9. Final Recommendation

**建议将该 `workflow_core.md` v3 修订版直接落盘。**

不需要 Control Agent 再修订一轮。5 条 soft recommendation 可以在落盘后作为 patch 补充，也可以在下一轮 workflow 维护中处理。

Control Agent 的 v3 版本在 DS 提案的基础上做了关键升级：
- 防漂移规则从概念升级为具体清单（§16）
- Attempt 并行条件从 3 条收紧到 5 条
- 明确了 closeout_recommendation 与最终 Gate 的边界
- 补充了当前项目阶段规则（§18）

这些升级使 DS 提案中的风险全部被覆盖。**允许 Codex 执行落盘。**

---

**DS Verdict: GO**
**落盘就绪: 是**
**建议接收方: Control Agent → Codex**
