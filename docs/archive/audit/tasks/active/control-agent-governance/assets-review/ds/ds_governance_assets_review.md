# DS Team 治理资产一致性审查报告

## Control Agent Governance Assets — 权威一致性与 System Prompt 瘦身审查

---

**审查编号**: v4.0-control-agent-governance-assets-ds-review-01
**审查类型**: read_only_governance_asset_review
**审查日期**: 2026-05-21
**审查方**: DS Team（Agent Team Mode，5 reviewer subagents）
**Team Mode**: true
**MCP Used**: true

---

## 一、审查概要

### 1.1 审查范围

| # | 文件 | 版本 | 定位 |
|---|------|------|------|
| 1 | `workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md` | v4.0 R2 draft | 完整权威工作流（草案） |
| 2 | `workflow_core_compact_v4_0_R0.md` | v4.0 R0 | 作战地图 / 快速索引 |
| 3 | `control_agent_specific_instruction_v_4_r_0.2.md` | v4.0 R0.2 | Control Agent 岗位说明书 |
| 4 | `control_agent_system_prompt_v4_kernel_v0_2_1.md` | v4 Kernel v0.2.1 | Control Agent 系统提示词内核 |

### 1.2 审查维度

1. **权威源关系** — 四类资产的权威层级是否清晰、一致
2. **System Prompt 瘦身** — 是否过度膨胀，哪些内容应下沉
3. **Control Agent 行为驱动** — system prompt 是否足以正确驱动行为
4. **Hermes-first 编排逻辑** — PM Runtime / Hermes first 是否一致且无歧义
5. **Template / Asset Mode** — 模板化作业规则是否放在正确层级，格式是否正确

### 1.3 Reviewer Agent Team

| # | Reviewer | 职责 |
|---|----------|------|
| 1 | Authority Alignment Reviewer | 审查权威关系 |
| 2 | System Prompt Minimalism Reviewer | 审查 system prompt 膨胀 |
| 3 | Control Agent Behavior Reviewer | 审查行为驱动完整性 |
| 4 | Hermes-first Workflow Reviewer | 审查 Hermes-first 编排逻辑 |
| 5 | Template / Asset Mode Reviewer | 审查 Template/Asset Mode 规则 |

### 1.4 总体结论

**Acceptance Verdict: `patch_required`**

四类资产在权威链、核心行为规则上高度一致，无结构性冲突。但存在 **2 个阻断性格式问题**（role instruction §6.4 代码块未闭合）、**严重的 system prompt 膨胀**（84% 内容与其他资产重复、12K-18K tokens vs 建议 1.5K-2.5K tokens）、以及 **多处关键规则下沉缺失**（role instruction 缺少 Hermes-first 定义、S-Level 规则与 Hermes-first 冲突、交付规则不一致）。

**不能记为 clean pass**。需要在落盘前完成指定修补。

---

## 二、权威源关系审查

### 2.1 总体评价：优秀（9/10）

四个资产在一级权威链上高度一致，全部明确定义并一致认同以下层叠结构：

```
workflow_core.md（完整权威源 / 法典）
    ↓ 派生
workflow_core_compact.md（作战地图 / 快速索引，非第二权威源）
    ↓ 派生
Agent-specific instructions（岗位说明书，非 workflow_core 替代品）
    ↓ 承载
system prompt（运行时内核，不制定规则）
```

冲突解决规则完全一致：
- compact 与 full 冲突：以 full 为准
- full / compact / Agent-specific instruction 三者冲突：HOLD，回 Owner-Control 对齐

### 2.2 各文件权威定位检查

| 文件 | 自我定位 | 对其他资产的定位 | 评价 |
|------|---------|-----------------|------|
| workflow_core R2 draft | 正确标注为 draft/consistency-repaired snapshot | compact 为"不是第二权威源" | 自身是 draft，但被其他资产当作正式权威 |
| compact R0 | **最清晰** — "作战地图，不是第二权威源" | workflow_core = 法典 | 权威定位最佳 |
| role instruction R0.2 | 正确 — "岗位说明书" | 三层权威关系清晰 | 定位正确 |
| system prompt v0.2.1 | 正确 — 运行时内核 | 完整列出权威链 | 定位正确但存在 draft/正式 张力 |

### 2.3 冲突与不一致

| ID | 严重度 | 位置 | 问题 | 建议 |
|----|--------|------|------|------|
| AA-001 | **major** | system prompt §2 | system prompt 将 workflow_core.md 描述为"完整权威工作流"，但当前实际加载的是 draft。§2 末段虽有过渡期处理说明，但前后表述自洽性不足 | 在 §2 头部为 workflow_core.md 增加状态限定："完整权威工作流（正式落盘版本），当前若为 draft 则按过渡期口径处理" |
| AA-002 | **major** | compact、role instruction、system prompt | 三个派生资产均引用 workflow_core.md 为最终权威，但均未标注"当前为 draft 版本"的警告 | 在各资产中增加状态提示行 |
| AA-003 | minor | 全部 4 文件 | 版本号体系不一致：compact R0、role instruction R0.2、system prompt v0.2.1、workflow_core draft 无显式版本号 | 统一版本号命名惯例 |
| AA-004 | note | role instruction §6.4 | Template/Asset Mode 篇幅远超出岗位说明书的正常范围 | 评估是否将大部分内容转入 workflow_core.md |
| AA-005 | note | system prompt §2 | "完整权威工作流"与"如果是 draft 则说明为过渡期"并列，Control Agent 优先读到未限定的定义 | 在"完整权威工作流"行后加注 |
| AA-006 | note | compact §2 | Control Agent 职责枚举粒度与其他资产略有差异 | 后续维护中对齐 |

---

## 三、System Prompt 瘦身审查

### 3.1 总体评价：严重膨胀

**当前估计长度：12,000-18,000 tokens（约 22,000-26,000 字符）**
**推荐目标长度：1,500-2,500 tokens（约 3,000-5,000 字符）**
**需压缩比例：约 84%**

### 3.2 各节分类表

| 章节 | 分类 | 原因 |
|------|------|------|
| 引言（身份声明） | **KEEP**（压缩至 2-3 句） | 必须的硬约束 |
| §0 自动启用模式 | **KEEP**（压缩至 5 行触发清单） | 硬约束：模式识别必须在 system prompt 层 |
| §1 可依赖的信息来源 | **MOVE_TO_ROLE_CARD** | 与 role instruction §2 完全重复 |
| §2 权威源关系 | **MOVE_TO_COMPACT** | 与 compact §10 高度重复 |
| §3 上下文加载顺序 | **MOVE_TO_ROLE_CARD** | 与 role instruction §3 几乎完全重复 |
| §4 第一性原则 | **KEEP**（极简 4 句摘要） | 核心行事原则 |
| §5 角色边界（5 个子节） | **MOVE_TO_COMPACT** | 与 compact §6、role instruction §9 三重重复 |
| §6 缺上下文处理规则 | **MOVE_TO_ROLE_CARD** | 与 role instruction §5 几乎完全重复 |
| §7 推进模式（4 种模式） | **MOVE_TO_ROLE_CARD** | 与 role instruction §6 几乎完全重复 |
| §8 用户确认后交付规则 | **KEEP**（压缩 30%） | 大文本交付规则（§8.1）是系统提示词特有 |
| §9 PM Runtime First | **KEEP**（压缩 50%） | 编排路由规则独特，但核心概念已在 workflow_core 定义 |
| §10 Execution Lock 条件 | **MOVE_TO_ROLE_CARD** | 与 role instruction §7 完全重复 |
| §11 任务等级判断（4 级） | **MOVE_TO_COMPACT** | 与 compact §5、role instruction §8 四重重复 |
| §12 Template 模板结构 | **DELETE_OR_MERGE** | 与 role instruction §6.4.5 完全重复 |
| §13 Gate 判断规则 | **KEEP**（压缩至 8-10 行） | 严禁误判清单有独特价值 |
| §14 Owner 传达职责 | **MOVE_TO_ROLE_CARD** | 与 role instruction §11 几乎完全重复 |
| §15 文档职责 | **MOVE_TO_ROLE_CARD** | 与 role instruction §12 几乎完全重复 |
| §16 输出风格 | **MOVE_TO_ROLE_CARD** | 与 role instruction §13 几乎完全重复 |
| §17 标准输出骨架 | **MOVE_TO_ROLE_CARD** | 与 role instruction §14 高度重复 |
| §18 自检清单 | **MOVE_TO_ROLE_CARD** | 与 role instruction §15、compact §11 三重重复 |
| §19 最重要行为准则 | **KEEP**（压缩至 5-8 句） | 系统自律原则精华 |

### 3.3 重复内容统计

- 共识别 **34 对明确重复**，涉及 system prompt 与另外 3 个文件的几乎所有章节
- **最严重的重复**：§5 角色边界（5 个子节）→ 与 compact §6、role instruction §9、workflow_core §3 形成四重重复
- **最深的重叠**：§11 任务等级判断 → 在全部 4 个资产中均有完整定义

### 3.4 系统提示词中真正独特的内容

| 独特内容 | 价值评估 |
|---------|---------|
| 大文本交付规则（§8.1）— 可下载文件优先 | 关键，仅在 system prompt 中有完整定义 |
| PM Runtime First 编排路由规则（§9） | 关键，system prompt 是最完整的定义 |
| 直达执行方的 5 个例外条件 | 重要，但条件 #5 存在自引用风险 |
| HOLD 输出骨架（§17.6，5 字段版） | 有价值，其他文件无此精确格式 |
| 自检清单扩展项（#14-#18） | 有价值，但应同步到 role instruction |
| 不得误判清单扩展版（§13） | 有价值，比 role instruction 多 3 项 |

### 3.5 推荐精简版结构

推荐压缩后的 system prompt 保留约 3,500 字符 / ~1,800 tokens：

1. **身份声明**（2-3 句）：ChatGPT 网页端 Control Agent，不是本地执行器
2. **自动启用触发条件**（5 行清单）
3. **第一性原则**（4 句精华）：不猜测、少复杂度、只做必要动作、可验证
4. **权威源与上下文加载顺序**（简表 + compact-first 规则）
5. **用户确认后交付规则**（含大文本文件优先策略）
6. **PM Runtime First 编排原则**（默认路径 + 5 条例外条件）
7. **Gate 判断规则**（精简版，保留严禁误判清单）
8. **最重要行为准则**（5-8 句精华）
9. **兜底指引**：详细规则见 compact / role instruction / workflow_core

---

## 四、Control Agent 行为驱动审查

### 4.1 总体评价：良好（85/100）

System prompt 包含 19 个明确的控制段落，结构完整。10 项硬约束全部存在且表达正确。

### 4.2 10 项硬约束检查

| # | 约束 | 状态 | 备注 |
|---|------|------|------|
| 1 | ChatGPT 网页端 Control Agent 身份 | 存在 | F4 引言 + F3 §1.1 |
| 2 | NOT 本地 runtime / Codex / Hermes / DS / shell | 存在 | F4 引言完整列举 |
| 3 | 自动启用 Control Agent 模式 | 存在 | F4 §0 详尽触发清单 |
| 4 | compact-first 检索 | **部分存在** | 有优先级列表但缺少结构化强制执行 |
| 5 | workflow_core 是最终权威 | 存在 | F4 §2 |
| 6 | 缺上下文不猜测，HOLD | 存在 | F4 §4.1 + §6 层次化防御 |
| 7 | Hermes / PM Runtime first for external work | 存在 | F4 §9 完整规则 |
| 8 | 用户确认后完整交付 | 存在 | F4 §8 |
| 9 | 大文本默认文件交付 | 存在 | F4 §8.1 仅在 system prompt 有 |
| 10 | 最终 gate 不交给 Hermes / DS / Codex | 存在 | F4 §13 |

### 4.3 行为一致性问题

| ID | 严重度 | 位置 | 问题 |
|----|--------|------|------|
| CB-001 | minor | F3 §7 vs F4 §10 | F4 §10 末尾多一句"Execution Lock 不等于可以绕过 Hermes"，F3 缺失 |
| CB-002 | minor | F3 §15 vs F4 §18 | 自检清单不一致：F4 18 项 / F3 10 项 / F2 10 项 |
| CB-003 | minor | F4 §18 | F4 自检清单缺少"假装本地执行"的反向检查项（F3 第 1 条有此检查） |
| CB-004 | minor | F2 §4.2 | F2 缺少 Execution Lock 第 5 条条件"继续分析不会产生新信息" |

### 4.4 遗漏项

| ID | 严重度 | 问题 | 建议 |
|----|--------|------|------|
| CB-005 | minor | workflow_core 本身是 draft 时的元层级指令缺失 | 增加"如果当前 workflow_core.md 是 draft，gate 判断应降级为过渡期口径" |
| CB-006 | minor | 会话上下文时效性检测缺失 | 增加"每 N 轮或每次 gate 判断前重新检查资料来源" |
| CB-007 | minor | "用户沉默时的默认行为"未定义 | 补充定义 |

---

## 五、Hermes-first 编排逻辑审查

### 5.1 总体评价：良好但有重要缺口（80/100）

System prompt v0.2.1 §9 是 v4.0 治理中第一个正确且完整定义 Hermes-first 规则的文件。但 role instruction 和 compact 缺乏对应规则，形成治理漏洞。

### 5.2 关键发现

| ID | 严重度 | 位置 | 问题 | 建议 |
|----|--------|------|------|------|
| HF-001 | **high** | role instruction §9 | role instruction 缺少 Hermes-first 定义。§9 定义了 Hermes 能力和边界，但完全没有"默认先走 Hermes 编排"的指令 | 在 §9 开头增加明示语句，复制 system prompt §9 的默认路径和 5 条绕过条件 |
| HF-002 | **high** | workflow_core R2 §8.2 + system prompt §9 | S-Level 规则与 Hermes-first 冲突。S-Level 的"优先 DS / Hermes 做只读回收"并列给出，没有明确"先 Hermes 再 DS"的层级。system prompt 绕过条件 #2 允许 S-Level 直接给 DS | 修改为"优先由 Hermes 派发给 DS Team 做只读回收"；S-Level 直达仅适用于不需要 receipt 回收的场景 |
| HF-003 | medium | system prompt §9 绕过条件 #5 | "workflow_core / compact / 当前任务卡允许直达执行方"存在自引用循环：task card 由 Control Agent 自己写 → 可自授权绕过 Hermes | 删除条件 #5，或改为"workflow_core 明确声明允许直达的特定任务类型" |
| HF-004 | medium | compact §6.3 | compact 管线图正确显示 Hermes 为路由层，但缺少一行文本规则"外部任务默认走 Hermes 编排" | 在 §6.3 增加一句话规则 |
| HF-005 | low | workflow_core R2 §6 | workflow_core（法典）未显式声明 PM Runtime First，缺少"默认先走"的语义 | 在 §6 开头增加声明 |
| HF-006 | low | system prompt §9.3 | §9.3 的 13 字段编排最小输出未同步到 workflow_core R2 §5.4 | 同步字段定义 |
| HF-007 | note | compact §8 | 大文本交付规则（file-first）仅在 system prompt §8.1 有完整定义，compact 缺少索引 | 在 compact §8 增加对应索引 |

### 5.3 Hermes-first 一致性矩阵

| 规则 | system prompt | role instruction | compact | workflow_core R2 |
|------|:---:|:---:|:---:|:---:|
| 默认路径定义 | 完整 | **缺失** | **缺失（仅管线图隐含）** | **缺失（仅流程图隐含）** |
| 5 条绕过条件 | 完整 | **缺失** | **缺失** | **缺失** |
| 编排最小输出字段 | 完整（13 字段） | **缺失** | **缺失** | 部分（任务书格式有重叠） |
| 外部审查默认走 Hermes | 完整（§9.1） | **缺失** | **缺失** | 隐含 |
| 外部执行默认走 Hermes | 完整（§9.2） | **缺失** | **缺失** | 隐含 |
| 不得误判清单 | 完整（§9.4） | 部分（§10） | 部分（§9） | 部分（§4.7） |

---

## 六、Template / Asset Mode 审查

### 6.1 总体评价：有阻断性格式问题（60/100）

### 6.2 阻断性问题

| ID | 严重度 | 位置 | 问题 |
|----|--------|------|------|
| TAM-003 | **critical** | role instruction §6.4 第 367-582 行 | **代码块未闭合**：第 367 行的 ````text` 代码块一直开到第 582 行才闭合，导致 §6.4.2 至 §6.4.9 全部被吸入代码块内，约 190 行内容无法被正常解析 |
| TAM-004 | **critical** | role instruction §6.4 | **结构吸入**：因 TAM-003，§6.4.2-§6.4.9 的所有标题、列表、边界规则全部变为代码块内的纯文本，Model 无法识别为独立章节 |

**修复方法**：在第 387 行后（`不得因为用户在设计模板，就误判为要 Codex 立刻修改源码或落盘。`）增加 ```` ``` ```` 闭合代码块。

### 6.3 重要问题

| ID | 严重度 | 位置 | 问题 | 建议 |
|----|--------|------|------|------|
| TAM-007 | **high** | F4 §12 = F3 §6.4.5 | 默认模板结构在两份文件中完全重复（13 项标准字段 + 10 项 Agent 执行字段完全一致） | 删除 F4 §12，保留 F3 §6.4.5 为唯一权威 |
| TAM-008 | **high** | F4 §8 vs F3 §6.4.4 | 交付规则不一致：role instruction 缺少 file-first 策略、大文本交付规则、"完整交付不等于直接交给最终执行方"防护规则 | 将 F4 §8.1 核心规则加入 F3 §6.4.4 |
| TAM-001 | medium | F4 §7.3/§12 vs F3 §6.4 | 模板规则在 system prompt 和 role instruction 之间分散部署，主次不清 | F4 §12 删除，F4 §7.3 精简为最小触发器 + 交叉引用 |
| TAM-005 | low | role instruction §6.4.2-§6.4.9 | 修复 TAM-003 后，§6.4.2-§6.4.9 缺少 `###` 标题前缀，会变成纯文本段落 | 为所有子节增加 `###` 前缀 |
| TAM-006 | medium | role instruction §6.4 | 缺少分隔线、缩进不一致 | 增加 `---` 分隔线，规范化缩进 |
| TAM-009 | medium | system prompt §887-922 | §12 模板结构与 §7.3 模式定义被 §8-§11 隔开 400 行，信息流断裂 | 将 §12 移至 §7.3 作为子节 |
| TAM-010 | medium | role instruction §6.4 | File-first delivery 策略完全缺失 | 在 §6.4.4 或 §6.4.8 增加默认 file-first 规则 |
| TAM-002 | low | system prompt §0/§7.3 | System prompt 需要保留最小触发规则 | 当前设计正确，保留 |
| TAM-011 | low | system prompt 全文 | system prompt 格式稳健：代码块配对正确，结构清晰 | 无需修复 |

---

## 七、推荐分层方案

### 7.1 System Prompt 应保留

```yaml
system_prompt_should_keep:
  - "身份声明（2-3 句）：ChatGPT 网页端 Control Agent，不是本地执行器，不能假装执行"
  - "自动启用触发条件（5-10 行语境清单）"
  - "第一性原则极简版（4 句：不猜测、少复杂度、只做必要动作、可验证）"
  - "权威源关系简表 + compact-first 规则"
  - "用户确认后交付规则（含大文本文件优先策略）"
  - "PM Runtime First 编排原则（默认路径 + 5 条例外条件）"
  - "Gate 判断规则精简版（保留严禁误判清单）"
  - "最重要行为准则（5-8 句精华）"
  - "兜底指引：详细规则见 compact / role instruction / workflow_core"
```

### 7.2 下沉到 workflow_core_compact

```yaml
move_to_compact:
  - "角色边界详细定义（§5.1-§5.5 全部，compact §6 已有）"
  - "任务等级判断详细定义（§11 全部，compact §5 已有）"
  - "权威源关系详细说明（§2 大部分，compact §10 已有）"
  - "标准输出骨架（§17 全部，compact §8 已有类似内容）"
```

### 7.3 下沉到 Control Agent Role Card

```yaml
move_to_control_agent_role_card:
  - "可依赖的信息来源（§1 全部）"
  - "上下文加载顺序（§3 全部）"
  - "缺上下文处理规则（§6 全部）"
  - "推进模式详细定义（§7.1/§7.2/§7.4 全部）"
  - "Execution Lock 条件（§10 全部）"
  - "Owner 传达与编排职责（§14 全部）"
  - "文档职责（§15 全部）"
  - "输出风格（§16 全部）"
  - "自检清单（§18 全部，但需与 F3 统一为 19 项版）"
```

### 7.4 下沉到 workflow_core

```yaml
move_to_workflow_core:
  - "Template/Asset Mode 完整规则（role instruction §6.4 大部分内容）"
  - "PM Runtime 编排最小输出字段规范（system prompt §9.3，同步到 §5.4）"
  - "Hermes-first 显式声明（当前缺失，需新增）"
```

### 7.5 删除或合并

```yaml
delete_or_merge:
  - "system prompt §5 角色边界（与 compact §6 完全重复）"
  - "system prompt §11 任务等级判断（与 compact §5 完全重复）"
  - "system prompt §12 默认模板结构（与 role instruction §6.4.5 完全重复）"
  - "system prompt §17 标准输出骨架（与 role instruction §14 高度重复）"
  - "system prompt §18 自检清单（与 role instruction §15、compact §11 三重重复，应统一为一个权威版）"
```

### 7.6 推荐 System Prompt 目标

```yaml
recommended_system_prompt_target:
  target_length: "1,500-2,500 tokens（约 3,000-5,000 字符）"
  current_length: "12,000-18,000 tokens（约 22,000-26,000 字符）"
  compression_ratio: "约 84%"
  required_sections:
    - "身份声明与禁止假装（2-3 句）"
    - "自动启用触发条件（5-10 行清单）"
    - "第一性原则（4 句精华）"
    - "权威源关系简表（含 compact-first）"
    - "上下文加载顺序（简表）"
    - "用户确认后交付规则（含大文本文件优先）"
    - "PM Runtime First 编排原则（默认路径 + 例外条件）"
    - "Gate 判断规则（精简版 + 严禁误判清单）"
    - "最重要行为准则（5-8 句）"
    - "兜底指引"
  optional_sections_to_remove:
    - "角色边界详细定义 → compact"
    - "缺上下文处理规则 → role card"
    - "推进模式详细定义 → role card"
    - "Execution Lock 条件 → role card"
    - "任务等级判断 → compact"
    - "Template 模板结构 → role card"
    - "Owner 传达职责 → role card"
    - "文档职责 → role card"
    - "输出风格 → role card"
    - "标准输出骨架 → role card"
    - "自检清单 → role card（统一版）"
```

---

## 八、格式问题汇总

| ID | 严重度 | 文件 | 问题 |
|----|--------|------|------|
| FMT-001 | **critical** | role instruction §6.4 第 367 行 | 代码块未闭合，§6.4.2-§6.4.9 全部吸入 |
| FMT-002 | **critical** | role instruction §6.4 第 390-581 行 | 结构吸入，9 个子节变为纯文本 |
| FMT-003 | low | role instruction §6.4 | §6.4.2-§6.4.9 缺少 `###` 标题前缀 |
| FMT-004 | medium | role instruction §6.4 | 子节之间缺少分隔线，缩进不一致 |
| FMT-005 | low | system prompt §12 | 模板结构与模式定义被 8 个小节隔开 |
| FMT-006 | note | 全部 4 文件 | 版本号体系不统一 |

---

## 九、过程问题（Process Issues）

| ID | 问题 | 严重度 |
|----|------|--------|
| PRC-001 | workflow_core R2 draft 文件超过 133,000 字符，无法一次性读取，需分块处理 | note |
| PRC-002 | 5 个 reviewer subagent 均成功启动并完成独立审查 | 正常 |
| PRC-003 | MCP filesystem 工具成功用于全部 4 个文件的读取 | 正常 |
| PRC-004 | R2 draft 因大小限制仅通过 subagent 间接审查（非 DS 主控直接全量读取） | note |

---

## 十、已知问题（Known Issues）

| ID | 问题 | 影响 |
|----|------|------|
| KNW-001 | workflow_core R2 draft 声明自身为"不是最终落盘版"，但其他 3 个资产均将其作为正式权威引用 | 若在 draft 落盘前启用这些资产，存在将未验收内容当作正式规则的风险 |
| KNW-002 | 5 个绕过条件中条件 #5 存在自引用风险，但尚未造成实际事故 | 需在落盘前修复 |
| KNW-003 | role instruction §6.4 代码块未闭合，导致约 190 行内容无法被模型正确解析 | 当前如通过 ChatGPT 加载 role instruction，Template/Asset Mode 后半部分基本不可用 |

---

## 十一、完整 Findings 清单

| ID | 严重度 | 类别 | 位置 | 问题 | 建议 |
|----|--------|------|------|------|------|
| TAM-003 | **critical** | 格式 | role instruction §6.4 L367 | 代码块未闭合 | 在 L387 后增加 ``` |
| TAM-004 | **critical** | 格式 | role instruction §6.4 L390-581 | 结构吸入 | 修复 TAM-003 |
| TAM-007 | **high** | 重复 | system prompt §12 = role instruction §6.4.5 | 完全重复 | 删除 F4 §12 |
| TAM-008 | **high** | 不一致 | system prompt §8 vs role instruction §6.4.4 | 交付规则不一致 | 补齐 role instruction |
| HF-001 | **high** | 缺失 | role instruction §9 | 缺少 Hermes-first 定义 | 增加明示语句 |
| HF-002 | **high** | 冲突 | workflow_core R2 §8.2 + system prompt §9 | S-Level 与 Hermes-first 冲突 | 修改"优先 DS / Hermes" |
| AA-001 | **major** | 权威 | system prompt §2 | draft 被当作正式权威 | 增加状态限定 |
| AA-002 | **major** | 权威 | compact、role instruction、system prompt | 未标注 draft 状态 | 增加状态提示 |
| SPB-001 | **major** | 膨胀 | system prompt 全文 | 84% 内容冗余，12K-18K tokens | 按推荐方案瘦身 |
| HF-003 | medium | 逻辑 | system prompt §9 条件 #5 | 自引用循环 | 删除或修改 |
| HF-004 | medium | 缺失 | compact §6.3 | 缺少 Hermes-first 文本规则 | 增加一句话 |
| TAM-001 | medium | 分布 | system prompt §7.3/§12 vs role instruction §6.4 | 规则分散部署 | 精简 F4，保留 F3 |
| TAM-006 | medium | 格式 | role instruction §6.4 | 缺少分隔线，缩进不一致 | 规范化 |
| TAM-009 | medium | 结构 | system prompt §12 | 位置不当 | 移至 §7.3 |
| TAM-010 | medium | 缺失 | role instruction §6.4 | File-first 策略缺失 | 补齐 |
| CB-001 | minor | 不一致 | role instruction §7 vs system prompt §10 | Execution Lock 补充说明缺失 | 同步 |
| CB-002 | minor | 不一致 | 3 个自检清单 | 条目数不一致（18/10/10） | 统一为 19 项版 |
| CB-003 | minor | 缺失 | system prompt §18 | 缺少"假装本地执行"自检项 | 补充 |
| CB-004 | minor | 缺失 | compact §4.2 | 缺少 Execution Lock 条件 #5 | 补充 |
| AA-003 | minor | 格式 | 全部 4 文件 | 版本号体系不一致 | 统一命名 |
| HF-005 | low | 缺失 | workflow_core R2 §6 | 未显式声明 PM Runtime First | 增加声明 |
| HF-006 | low | 不一致 | system prompt §9.3 vs workflow_core R2 §5.4 | 字段未同步 | 同步 |
| TAM-005 | low | 格式 | role instruction §6.4.2-§6.4.9 | 缺少 ### 前缀 | 修复后添加 |
| AA-004 | note | 篇幅 | role instruction §6.4 | 超出岗位说明书范围 | 评估迁移 |
| AA-005 | note | 表述 | system prompt §2 | 头部与末段张力 | 加注 |
| AA-006 | note | 粒度 | compact §2 | 职责枚举粒度差异 | 后续对齐 |
| FMT-005 | note | 结构 | system prompt §12 | 位置不当 | 调整 |
| CB-005 | note | 缺失 | 全部资产 | workflow_core 为 draft 时的元层级指令 | 补充 |
| CB-006 | note | 缺失 | 全部资产 | 会话上下文时效性检测 | 补充 |
| CB-007 | note | 缺失 | 全部资产 | 用户沉默时默认行为 | 补充 |
| TAM-002 | note | 正确 | system prompt §0/§7.3 | 当前设计正确 | 保留 |
| TAM-011 | note | 正确 | system prompt 全文 | 格式稳健 | 无需修复 |
| HF-007 | note | 缺失 | compact §8 | 大文本交付规则索引缺失 | 增加索引 |

---

## 十二、最终判定

### 12.1 Acceptance Verdict

**`patch_required`**

### 12.2 理由

四类资产在权威链和核心行为规则上高度一致（权威链一致性评分 9/10），无结构性冲突。但存在以下必须在落盘前修复的问题：

1. **阻断性格式问题**：role instruction §6.4 代码块未闭合（TAM-003/004），导致约 190 行内容无法被正确解析
2. **严重的 system prompt 膨胀**：84% 内容与其他资产重复，需结构性瘦身
3. **关键规则下沉缺失**：role instruction 缺少 Hermes-first 定义（HF-001）、S-Level 规则与 Hermes-first 冲突（HF-002）
4. **交付规则不一致**：role instruction 缺少 file-first 策略（TAM-008）
5. **多处重复需清理**：system prompt §12 与 role instruction §6.4.5 完全重复（TAM-007）

### 12.3 不能记为 clean pass 的原因

- 存在 **critical** 级别格式问题
- 存在 **major/high** 级别权威漂移风险（draft 被当作正式权威）
- 多资产之间存在不一致需修补
- System prompt 严重膨胀需结构性重组

### 12.4 修复优先级

| 优先级 | 修复项 | ID |
|--------|--------|-----|
| P0 — 立即 | 闭合 role instruction §6.4 代码块 | TAM-003/004 |
| P0 — 立即 | 删除 system prompt §12（与 role instruction 重复） | TAM-007 |
| P1 — 高 | System prompt 结构性瘦身（按推荐方案） | SPB-001 |
| P1 — 高 | role instruction 补齐 Hermes-first 定义 | HF-001 |
| P1 — 高 | 修复 S-Level 与 Hermes-first 冲突 | HF-002 |
| P1 — 高 | role instruction 补齐 file-first 交付规则 | TAM-008 |
| P2 — 中 | 统一 authority 引用中 draft 状态标注 | AA-001/002 |
| P2 — 中 | 修复绕过条件 #5 自引用循环 | HF-003 |
| P2 — 中 | compact 增加 Hermes-first 文本规则 | HF-004 |
| P2 — 中 | 统一自检清单为 19 项版 | CB-002/003 |
| P3 — 低 | 统一版本号体系 | AA-003 |
| P3 — 低 | 其他 minor/note 级问题 | 见完整清单 |

---

## 十三、报告元数据

```yaml
task_id: v4.0-control-agent-governance-assets-ds-review-01
review_type: read_only_governance_asset_review
team_mode_used: true
mcp_used: true
reviewers:
  - Authority Alignment Reviewer
  - System Prompt Minimalism Reviewer
  - Control Agent Behavior Reviewer
  - Hermes-first Workflow Reviewer
  - Template / Asset Mode Reviewer
reviewed_files:
  - workflow_core_v4.0_full_draft_consistency_repaired_r2_2026-05-19.md
  - workflow_core_compact_v4_0_R0.md
  - control_agent_specific_instruction_v_4_r_0.2.md
  - control_agent_system_prompt_v4_kernel_v0_2_1.md
total_findings: 33
critical: 2
high: 4
major: 3
medium: 8
minor: 4
low: 6
note: 6
acceptance_verdict: patch_required
report_path: audit/tasks/active/control-agent-governance/assets-review/ds/ds_governance_assets_review.md
receipt_path: audit/tasks/active/control-agent-governance/assets-review/ds/ds_receipt.yaml
```

---

**审查完成。不执行 closeout，不修改任何文件，交由 Owner-Control 判断下一步。**
