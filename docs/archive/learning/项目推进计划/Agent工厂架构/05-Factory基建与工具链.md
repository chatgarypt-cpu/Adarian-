# 05 — Factory 基建与工具链

---

## 核心命题

> 主模型要入驻 GenFlow，需要一套基础设施——不是让主模型直接调 API，而是通过一套工程化流水线来触达 GenFlow 的每个可编程表面。

---

## 基建总览

```
┌─────────────────────────────────────────────────────────────────┐
│                       Factory 基础架构                            │
│                                                                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐      │
│  │ 契约冻结器 │   │ Subagent │   │ 确定性    │   │ 结构化    │      │
│  │           │   │ 编排器    │   │ 质量门    │   │ 记忆系统   │      │
│  │ 主模型   │   │          │   │          │   │           │      │
│  │ 产出蓝图   │   │ 管理并行  │   │ 7层校验   │   │ JSONL日志  │      │
│  │ → YAML    │   │ Subagent │   │ 不用LLM   │   │ 可重放     │      │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    代码生成安全层                           │    │
│  │  · Python 沙箱（AST扫描，禁止 os.system/subprocess/eval）   │    │
│  │  · 文件写保护（Subagent 只能写分配给它的文件）              │    │
│  │  · import 白名单（生成的 code 只能 import 预批准的库）      │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    版本与回滚                               │    │
│  │  · 每次 Factory run 有唯一 run_id                          │    │
│  │  · 每个领域包的每个版本有 git 历史                          │    │
│  │  · 支持回滚到任何历史版本                                   │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. 契约冻结器（Contract Freezer）

### 做什么

主模型产出的是**自然语言蓝图**。契约冻结器把它转成**机器可读的 YAML 合同**。

### 流程

```
主模型产出:
  "金融分析领域需要 13 个 Skill，分 5 个阶段。
   风险评估 Skill 依赖上游 3 个数据采集 Skill，
   产出一个包含置信区间的风险评估报告。"

        ↓ 契约冻结器解析

输出: blueprint.yaml
  domain: finance
  skills:
    - id: risk_assessor
      stage: synthesis
      depends_on: [stock_price_collector, sec_filing_analyzer, macro_indicator_collector]
      output: risk_assessment_report
      output_schema: {confidence_interval: float, risk_level: enum, factors: list}
      forbidden_overlap: ["Do not perform data cleaning", "Do not generate trading signals"]
      domain_terms: [volatility, correlation, drawdown, VaR, beta, sharpe_ratio, ...]

    - id: stock_price_collector
      stage: evidence
      ...
```

### 为什么需要

自然语言蓝图是模糊的——"风险评估"在不同语境下可能指完全不同的事。冻结成 YAML 合同后：
- Subagent 拿到精确的输入/输出/禁止项
- 质量门有明确的校验目标
- 后续轮迭代有 diff 基础

---

## 2. Subagent 编排器

### 做什么

管理主模型派发的 Subagent 池。确保并行执行时不冲突、不重复、不遗漏。

### 任务分配策略

```
按 Skill 簇分配（不是按 Skill 数量平均分）:

Entry 簇（2个Skill）         → Subagent A
Evidence 簇（4个Skill）      → Subagent B
Synthesis 簇（3个Skill）     → Subagent C
Output + Review 簇（4个Skill）→ Subagent D
Planner + Models            → Subagent E
Tests + Fixtures            → Subagent F

6 个 Subagent 并行。每人只写自己簇内的文件。
```

### 冲突预防

```
每个 Subagent 在启动时拿到:
  ✓ owned_paths: ["skills/risk_assessor/SKILL.md", "skills/portfolio_analyzer/SKILL.md"]
  ✗ forbidden_paths: ["planner/", "models/", "skills.yaml", "skills/stock_price_collector/"]
  ✓ canonical_ids: [risk_assessor, portfolio_analyzer, valuation_modeler]
  ✓ contracts: 每个 Skill 的 frozen contract
  ✓ reference: 已有成功领域包中最相似的 1-2 个 SKILL.md 摘要
```

### 模型分配策略

| Subagent 类型 | 推荐模型 | 原因 |
|---|---|---|
| Skill 编写组 | Sonnet | 结构化写作，模板驱动 |
| Planner 编写组 | Sonnet/Opus | DAG 逻辑和接口耦合度高 |
| Model 编写组 | Sonnet | Pydantic 代码模式固定 |
| Test/Fixture 编写组 | Haiku | 低风险，可由 pytest 验证 |

---

## 3. 确定性质量门（7 层）

### 设计原则

> 所有裁判逻辑是确定性代码。不用 LLM 评价 LLM 的产出。

### 第 1 层：文件完整性

```
检查项:
  ✓ package.yaml 存在且 YAML 可解析
  ✓ skills.yaml 存在且 YAML 可解析
  ✓ skills.yaml 中声明的每个 skill_id 都有对应的 skills/<skill_id>/SKILL.md
  ✓ planner/*.py 可 import
  ✓ models/*.py 可 import
  ✓ 没有未声明的文件
  ✓ 没有 TODO/TBD/placeholder 占位符
```

### 第 2 层：Frontmatter Schema

```
检查项:
  ✓ name: 必填，kebab-case，与 skills.yaml 中的 skill_id 一致
  ✓ description: 必填，80-240 字符
  ✓ version: semver 格式
  ✓ domain: 必填
  ✓ inputs: 非空列表
  ✓ outputs: 非空列表
  ✓ depends_on: 引用的 skill_id 全部存在
  ✓ 无重复 key
  ✓ 无循环依赖
```

### 第 3 层：Markdown 结构

```
SKILL.md 必须包含以下章节（标题检测）：
  ✓ # Purpose
  ✓ # When to use
  ✓ # When not to use
  ✓ # Inputs
  ✓ # Outputs
  ✓ # Procedure
  ✓ # Quality checks
  ✓ # Examples
  ✓ # Failure modes

检查项:
  ✓ Procedure 至少 3 个步骤
  ✓ 每个步骤以动作动词开头（从白名单中检测）
  ✓ Inputs 中的每个字段在 Procedure 或 Examples 中出现
  ✓ Outputs 中的每个字段在 Quality checks 中出现
  ✓ Examples 至少 2 个，其中至少 1 个负例
  ✓ Failure modes 至少 3 个
```

### 第 4 层：领域锚点检测

```
从 blueprint.yaml 中提取领域词表:
  finance_terms: [volatility, correlation, drawdown, VaR, beta,
                  sharpe_ratio, alpha, P/E, EBITDA, DCF, ...]

检查项:
  ✓ 每个 SKILL.md 命中 ≥ 8 个领域锚点
  ✓ 至少 2 个 model 字段引用
  ✓ 至少 1 个 evidence/provenance 术语

泛化废话黑名单（命中 ≥ 1 → 阻断）:
  "do your best"
  "as appropriate"
  "handle all cases"
  "ensure quality"
  "根据情况处理"
  "进行分析"
  "输出结果"
  ... （随迭代扩展）
```

### 第 5 层：跨文件一致性

```
检查项:
  ✓ Planner 引用的每个 skill_id 在 skills.yaml 中存在
  ✓ Planner 的 node input/output type 与 Model schema 兼容
  ✓ 不同 SKILL.md 之间的相似度 < 0.85（防止模板化复制粘贴）
  ✓ 所有 depends_on 引用可解析
  ✓ artifact key 无冲突
```

### 第 6 层：Python 静态校验

```
对 planner/*.py 和 models/*.py:

  ✓ AST parse 成功（语法正确）
  ✓ 所有 export 的 class/function 可 import
  ✓ Pydantic/dataclass schema 可生成 JSON Schema
  ✓ fixtures 可反序列化
  ✓ JSON round-trip 不丢字段

安全扫描:
  ✗ 禁止 os.system
  ✗ 禁止 subprocess
  ✗ 禁止 eval/exec
  ✗ 禁止 requests/urllib（网络访问）
  ✗ 禁止 import socket
  ✗ 禁止文件系统写入（os.remove, shutil.rmtree, open(path, 'w')）
```

### 第 7 层：空跑 DAG

```
不启动 Docker，不调用 LLM。纯拓扑验证：

  1. 加载 domain package
  2. import models, import planner
  3. 读取 tests/fixtures/tasks/*.json
  4. planner.generate(task, dry_run=True)
  5. 得到 DAG spec
  6. 验证:
     ✓ node_id 唯一
     ✓ 无环（topological sort 成功）
     ✓ 所有 depends_on 存在
     ✓ 每个 node 的 skill_id 存在
     ✓ input/output schema 兼容
     ✓ 入口节点和终止节点存在
     ✓ retry_policy/timeout 合法

推荐命令:
  genflow-factory validate ./packages/finance --strict
  genflow-factory dry-run ./packages/finance --fixtures ./packages/finance/tests/fixtures
```

---

## 4. 结构化记忆系统

### 为什么不是 RAG/向量库

Factory 不是开放问答系统，是编译/构建系统。它需要的是**可重放的因果链**，不是语义相似度。

```
RAG 的问题:
  ✗ 检索结果不稳定
  ✗ "相似" ≠ "相关"（一个领域的失败记录可能和另一个领域完全无关）
  ✗ 无法追踪 diff

JSONL 的优势:
  ✓ 每行是一个事件，可 grep
  ✓ 可重放（按 run_id 重放整个构建过程）
  ✓ 可 diff（两轮之间的 artifact sha256 变化）
  ✓ 可统计（失败模式频率、修复成功率）
  ✓ 可审计（谁改了哪个文件、因为什么规则失败）
```

### 数据结构

```
factory_run.jsonl 中的事件类型:

1. Run 开始
   {"type":"run_start","run_id":"factory-20260429-001","domain":"finance"}

2. 蓝图冻结
   {"type":"blueprint","skills":[...],"model_exports":[...],"planner_entrypoints":[...]}

3. 任务分配
   {"type":"task_assignment","agent_id":"skill-A","owned_paths":[...],"round":1}

4. 产物登记
   {"type":"artifact","path":"skills/risk_assessor/SKILL.md","sha256":"abc123","round":1}

5. 校验事件
   {"type":"validation","severity":"error","rule_id":"planner.skill_ref.exists",
    "path":"planner/default_planner.py","line":87,
    "expected":"risk_assessor","actual":"risk_assessment_analyzer"}

6. 修复补丁
   {"type":"repair","round":2,"agent_id":"planner-subagent",
    "fixes":["planner.skill_ref.exists"],"paths_changed":["planner/default_planner.py"]}

7. Run 结束
   {"type":"run_end","run_id":"factory-20260429-001","status":"passed","rounds":2}
```

### 失败模式库

从 JSONL 中自动提取高频失败模式：

```yaml
failure_patterns:
  - signature: "unknown_skill_id"
    detector: "planner.skill_ref.exists"
    cause: "Planner Subagent 发明了本地别名而非使用 canonical ID"
    prevention: "向 Planner Subagent 注入 canonical skill ID enum"
    repair_template: "将所有非标准 skill_id 替换为蓝图中的 canonical ID"
    occurrence_count: 7
    domains: [domain-a, domain-b, domain-c]
```

---

## 5. 代码生成安全层

### 问题

主模型或 Subagent 可能生成有害代码。生成的代码在执行时运行在 Agent 容器中，具有该容器的完整权限。

### 防线

```
第一道防线 — 静态 AST 扫描（阻断级）:
  在写入文件前扫描 Python AST:
    ✗ os.system, os.popen, os.exec*
    ✗ subprocess.run, subprocess.Popen, subprocess.call
    ✗ eval, exec, compile, __import__
    ✗ requests.get, urllib.request, socket.connect
    ✗ shutil.rmtree, os.remove, os.unlink (销毁性写入)
    ✗ import ctypes, import sys (通常不需要)

第二道防线 — import 白名单（阻断级）:
  models/*.py 只能 import:
    pydantic, dataclasses, typing, datetime, enum, decimal, math, statistics
  planner/*.py 只能 import:
    以上 + genflow_core.dag.types, genflow_common.skills_registry

第三道防线 — 文件写保护（阻断级）:
  Subagent 的文件操作工具被限制:
    只能写 owned_paths 中声明的文件
    不能改 skills.yaml（只能由专门的 Subagent 写）
    不能改其他 Subagent 的文件
    不能写 genflow-core/ 的任何文件

第四道防线 — 运行时隔离（如果前三层被绕过）:
  Agent 容器运行在 uid 1000
  /workspace 是独立 volume
  genflow-core/ 是只读挂载
  packages/ 是只读挂载（Agent 不能改写领域包）
```

---

## 6. 版本与回滚

```
每个领域包是独立 git 仓库（或 monorepo 中的独立目录）:

packages/finance/
  .git/
  factory_history/
    2026-04-29-001/         ← run_id
      blueprint.yaml          ← 本轮冻结的蓝图
      factory_run.jsonl       ← 本轮完整日志
      validation_report.json  ← 质量门结果
      diff_from_prev.patch    ← 与上一版本的差异

回滚命令:
  genflow-factory rollback finance --to 2026-04-28-003
  genflow-factory diff finance 2026-04-28-003 2026-04-29-001
```

---

## MVP 范围

如果只做 6 件事来验证可行性：

```
1. blueprint.yaml schema + 冻结器
2. skill_contracts/*.yaml schema
3. SKILL.md linter（第 1-4 层质量门）
4. package manifest validator（第 5 层交叉校验）
5. planner dry-run DAG validator（第 7 层空跑）
6. factory_run.jsonl 结构化日志
```

不需要一开始就做完整的安全沙箱、版本回滚、Subagent 编排器。这些可以在验证了核心流程后再加。

---

*返回 [README](./README.md)*
