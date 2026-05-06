# /ds-pre-audit — DS 前置结构审查

## 定位

对即将进入执行的版本做**只读**结构审查，输出带 `audit_id` 的 Pre-Audit Report。

**不负责**：不重新设计版本范围、不扩大架构、不把建议项自动升级为 blocker、不替 Control Agent 做最终 Gate。

---

## 触发时机

Control Agent 完成初版迭代文档且 Gate 为 `GO` 或 `CONDITIONAL_GO`，且本版本涉及以下任一事项：

1. 源码结构调整
2. schema / contract 调整
3. main.py 主链路调整
4. phase package / import 路径调整
5. whitebox / runtime artifact contract 调整
6. R1 / R2 / R3 前置设计
7. 任何可能影响下游 Phase 的变更

---

## 输入

1. 当前迭代文档 draft / under_review
2. 当前源码树
3. 当前 dev_spec.md
4. 当前 TASK_LOG.md / CHANGELOG.md
5. 相关上一版本验收记录

---

## 执行步骤

1. 读取迭代文档，提取目标结构、允许/禁止修改列表
2. 扫描 `src/` 下所有 `.py` 文件，建立文件清单
3. 追踪 `main.py` 的 import 链路，区分主链 / legacy / 独立工具
4. 搜索 whitebox 相关关键词，定位分散的观测逻辑
5. 检查 forbid 声明的文件是否确实存在且不应触碰
6. 评估循环 import 风险、shim 策略可行性
7. 输出结构化 DS Pre-Audit Report

---

## 输出

必须包含：

```text
audit_id
verdict: GO / CONDITIONAL_GO / HOLD / FAIL
source tree facts
main chain dependency facts
allowed files check
forbidden files check
risk list
blockers
recommended execution scope
DS must not do
```

### 报告存放路径

```text
audit/phase1大版本审计/vX.Y.Z-{topic}-{YYYY-MM-DD}.md
```

如非 Phase 1 大版本审计：

```text
audit/workflow/vX.Y.Z-{topic}-{YYYY-MM-DD}.md
audit/general/vX.Y.Z-{topic}-{YYYY-MM-DD}.md
```

---

## 格式要求

```text
audit_id: audit-vX.Y.Z-01
```

---

## 边界

DS Pre-Audit 不得：

1. 重新设计版本范围
2. 扩大架构
3. 把建议项自动升级为 blocker
4. 替 Control Agent 做最终 Gate
5. 要求进入下一版本
