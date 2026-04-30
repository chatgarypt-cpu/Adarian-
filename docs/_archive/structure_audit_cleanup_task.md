# Structure Cleanup Task

基于 Structure Audit Report v1（2026-04-14）
更新：2026-04-14（执行边界修正版）

---

## 背景

审计发现项目存在结构性混乱，但**禁止修改任何代码**。本任务只做**文件层操作**（移动/重命名）。

---

## 明确允许的 .py 文件变更

**唯一允许变更：** `src/phase1_entity_extraction.py`

**变更内容：** 仅在文件头部 docstring 之后添加 LEGACY 注释，不改任何代码逻辑。

**禁止：** 任何其他 .py 文件不允许任何变更。

---

## 必须遵守的约束

1. **不修改任何 .py 文件**（仅允许 `src/phase1_entity_extraction.py` 加 LEGACY 注释）
2. **不修改任何 .yaml/.json 配置文件**
3. **不修改 docs/ 下的迭代文档**（CHANGELOG.md, TASK_LOG.md, v1.1.*.md）
4. **outputs/ 目录整体保留**，只归档历史子目录
5. 所有操作必须是**原子性的**（移动/重命名，不改变文件内容）
6. **outputs/ 是有效产物，不是临时文件**，不可删除或移动

---

## 任务清单

### Task 1: 隔离实验探针脚本

**当前路径：**
```
scripts/
├── generate_snapshot.py
├── p1a_prompt_probe.py
├── p1g_prompt_probe.py
└── reduced_schema_chain_probe.py
```

**操作：**
```bash
mkdir -p scripts/probes/
mv scripts/p1a_prompt_probe.py scripts/probes/
mv scripts/p1g_prompt_probe.py scripts/probes/
mv scripts/reduced_schema_chain_probe.py scripts/probes/
```

**验证：**
- `scripts/generate_snapshot.py` 存在
- `scripts/probes/` 包含 3 个 probe 文件

---

### Task 2: 归档 profiling/output/runs/ 历史产物

**前置条件（必须全部满足）：**
1. run 目录已结束（不是当前正在运行的）
2. 最近 10 分钟内无文件写入
3. 不移动当前可能仍被读取/写入的目录

**检查方法：**
```bash
# 检查最近修改时间（应 < 当前时间 -10 分钟）
ls -ltr profiling/output/runs/
find profiling/output/runs/* -type d -mmin +10
```

**操作：**
```bash
mkdir -p profiling/output/runs_archive/

# 移动已结束的旧 run（按实际情况选择）
# 模式：run_20260413_* 和 run_*_prompt_probe
mv profiling/output/runs/run_20260413_* profiling/output/runs_archive/
mv profiling/output/runs/run_*_prompt_probe profiling/output/runs_archive/
```

**验证：**
- `profiling/output/runs/` 为空或只有当前运行的 run
- `profiling/output/runs_archive/` 包含所有归档的 run

**注意：** 如果有 run 在最近 10 分钟内有写入，跳过该目录。

---

### Task 3: 标记 Legacy 文件

**唯一允许变更的文件：** `src/phase1_entity_extraction.py`

**操作：**
在文件头部 docstring 之后（第 19 行之后）添加：
```python
# ⚠️ LEGACY FILE — v1.1.14+ 已迁移到 src/phase1/
# 本文件保留用于兼容，新代码请使用 src/phase1/ 模块
```

**验证：**
- 文件头部有 `⚠️ LEGACY` 标记
- 无任何代码逻辑变更

---

### Task 4: 归档 docs/ 非项目文档

**确认：CLAUDE.md 实际路径是 `adarian mvp/CLAUDE.md`（项目根目录），不在 `docs/` 下。**

**当前需要归档的（docs/ 下）：**
```
docs/
├── obsidian/           # 个人笔记
├── debug/              # 调试文档
├── history used/       # 历史文档
├── 4月第一周工作汇报.md  # 个人汇报
├── 9_4.md             # 历史文档
└── 9_5.md             # 历史文档
```

**操作：**
```bash
mkdir -p docs/_archive/
mv docs/obsidian/ docs/_archive/obsidian/
mv docs/debug/ docs/_archive/debug/
mv docs/"history used"/ docs/_archive/history_used/
mv docs/4月第一周工作汇报.md docs/_archive/
mv docs/9_4.md docs/_archive/
mv docs/9_5.md docs/_archive/
```

**保留不动（不在 docs/ 归档范围）：**
- `docs/iterations/`（包含 CHANGELOG, TASK_LOG, v1.1.*）
- `docs/dev_spec.md`
- `docs/skills/`
- `docs/prompt_inventory.md`
- `docs/prompt_risk_report.md`
- `docs/profiling_prep_report.md`
- `docs/structure_audit_report.md`
- `docs/structure_audit_cleanup_task.md`

**验证：**
- `docs/_archive/` 包含 6 个被归档的目录/文件
- `docs/` 根目录不包含 obsidian/debug/history used/ 个人文档

---

### Task 5: 暂存 profiling/ 临时备份文件

**模式匹配优先（先匹配模式，再补查显式文件名）：**

**Step 1: 模式匹配**
```bash
# 匹配 *.backup.* 文件
find profiling/output/ -maxdepth 1 -name "*.backup.*" -type f

# 匹配 *snapshot*.json 文件
find profiling/output/ -maxdepth 1 -name "*snapshot*.json" -type f
```

**Step 2: 确认显式文件名**
```bash
# 检查是否存在这些文件
ls profiling/output/modelslist.pre4run.backup.txt 2>/dev/null
ls profiling/output/modelslist.pre8run.backup.txt 2>/dev/null
ls profiling/output/run_manifest.pre4run.backup.json 2>/dev/null
ls profiling/output/run_manifest.pre8run.backup.json 2>/dev/null
ls profiling/output/run_manifest.snapshot.json 2>/dev/null
```

**Step 3: 移动到暂存区**
```bash
mkdir -p profiling/output/_to_be_deleted/

# 移动匹配到的文件
mv profiling/output/*.backup.* profiling/output/_to_be_deleted/ 2>/dev/null
mv profiling/output/*snapshot*.json profiling/output/_to_be_deleted/ 2>/dev/null
```

**保留（不移动）：**
- `profiling/output/run_manifest.json`
- `profiling/output/model_profiles.json`
- `profiling/output/profile_summary.md`

**验证：**
- `profiling/output/_to_be_deleted/` 包含所有被暂存文件
- `profiling/output/` 根目录不存在 `.backup.` 或 `.snapshot.` 文件

---

## 执行顺序

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5
```

每个 Task 完成后验证，再执行下一个。

---

## 安全原则

1. **先移动，后确认，最后删除** — 所有"删除"操作改为移动到 `_to_be_deleted/` 暂存区
2. **Task 2 要检查活跃 run** — 跳过最近 10 分钟有写入的目录
3. **Task 5 模式匹配优先** — 先 glob，后显式文件名

---

## 禁止事项

- ❌ 不修改任何 .py 的代码逻辑（仅允许 `src/phase1_entity_extraction.py` 加注释）
- ❌ 不修改任何 .yaml/.json 配置文件
- ❌ 不修改 outputs/ 任何文件
- ❌ 不删除 docs/iterations/ 下任何文档
- ❌ 不修改 CHANGELOG.md 或 TASK_LOG.md
- ❌ 不直接删除任何文件，统一先移动到 `_to_be_deleted/` 暂存区
- ❌ 不移动最近 10 分钟内有写入的 run 目录
