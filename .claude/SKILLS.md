# Adarian DS Team Skills

DS Team 三条审计/验收 skill，按 Pipeline 阶段依次触发。

---

## /ds-pre-audit — DS 前置结构审查

**触发时机**：Control Agent 完成初版迭代文档，Gate = GO / CONDITIONAL_GO，且涉及结构/contract/main链路/whitebox 变更时。

**输入**：迭代文档、源码树、dev_spec.md、TASK_LOG、CHANGELOG、上版本验收记录。

**输出**：`audit/phase1大版本审计/vX.Y.Z-{topic}-{date}.md`，含 audit_id、verdict、source tree facts、risk list、blockers。

**不负责**：不重新设计版本范围、不扩大架构、不替 Control Agent 做 Gate。

详见：`docs/skills/ds_pre_audit.md`

---

## /ds-verify — DS 后置验证

**触发时机**：Codex 完成 attempt 交付后。

**五阶段验证**：
1. 静态检查（py_compile + compileall + declared tests）
2. Forbidden Files 检查（git diff 对照 iteration doc §6.3）
3. Import 完整性检查
4. Smoke Test（test1，可选 test7 若声明为 hard gate）
5. Artifact Contract 检查（run_dir 产物完整性）

**输出**：overall_verify_result: all_pass / partial_fail / hard_fail。

**不负责**：不修改代码、不更新 TASK_LOG/CHANGELOG。

详见：`docs/skills/ds_verify.md`

---

## /ds-accept — DS 验收判定

**触发时机**：`/ds-verify` 完成后。

**验收逻辑**：
- 任一 Hard Target 不满足 → fail / hold
- Hard 全满足 + 部分 Soft 不满足 → pass_with_known_issues
- 全部满足 → pass

**可更新**：TASK_LOG.md、CHANGELOG.md、迭代文档 acceptance section。

**不负责**：不直接 closeout、不替 Control Agent 做最终 Gate。

详见：`docs/skills/ds_accept.md`

---

## 退役 Skill

以下旧 skill 已被 DS Team skill 吸收，不再使用：

- `/test1` → 被 `/ds-verify` Phase 4 Smoke Test 吸收
- `/verify` → 被 `/ds-verify` + `/ds-accept` 吸收
