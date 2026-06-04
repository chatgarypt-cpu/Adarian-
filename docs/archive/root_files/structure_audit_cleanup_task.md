# Structure Cleanup Task

基于 Structure Audit Report v1（2026-04-14）

---

## 背景

审计发现项目存在结构性混乱，但**禁止修改任何代码**。本任务只做**文件层操作**（移动/删除/重命名）。

**重要澄清（来自用户）：**
- `outputs/` 是项目运行产生的**有效产物**，不是临时文件
- `outputs/benchmark/` 和 `outputs/normal/` 是正常运行的产物，应**保留**
- 历史 run 可按时间归档，不应删除整个目录
- `profiling/output/runs/` 是 profiling pipeline 的运行产物，应**保留**

---

## 必须遵守的约束

1. **不修改任何 .py 文件**（代码逻辑、prompt、schema）
2. **不修改任何 .yaml/.json 配置文件**
3. **不修改 docs/ 下的迭代文档**（CHANGELOG.md, TASK_LOG.md, v1.1.*.md）
4. **outputs/ 目录整体保留**，只归档历史子目录
5. 所有操作必须是**原子性的**（移动/删除，不改变文件内容）

---

## 任务清单

### Task 1: 隔离实验探针脚本

**现状：**
```
scripts/
├── generate_snapshot.py    # 控制层脚本，应保留
├── p1a_prompt_probe.py    # 实验探针，应移动
├── p1g_prompt_probe.py    # 实验探针，应移动
└── reduced_schema_chain_probe.py  # 实验探针，应移动
```

**操作：**
1. 创建 `scripts/probes/` 目录
2. 移动 `p1a_prompt_probe.py` → `scripts/probes/`
3. 移动 `p1g_prompt_probe.py` → `scripts/probes/`
4. 移动 `reduced_schema_chain_probe.py` → `scripts/probes/`
5. 确认 `scripts/generate_snapshot.py` 仍在原位

**验证：**
- `scripts/generate_snapshot.py` 存在
- `scripts/probes/` 包含 3 个 probe 文件

---

### Task 2: 归档 profiling/output/runs/ 历史产物

**现状：**
```
profiling/output/runs/
├── run_20260413_173917_*     # 旧的，应归档
├── run_20260413_174044_*     # 旧的，应归档
├── run_20260413_174758_*     # 旧的，应归档
├── run_20260413_175147_*     # 旧的，应归档
├── run_20260413_175148_*     # 旧的，应归档
├── run_20260414_112916_p1a_prompt_probe  # probe产物，可选归档
├── run_20260414_120429_p1g_prompt_probe  # probe产物，可选归档
├── run_20260414_120615_p1g_prompt_probe  # probe产物，可选归档
└── run_20260414_120802_p1g_prompt_probe  # probe产物，可选归档
```

**操作：**
1. 创建 `profiling/output/runs_archive/` 目录
2. 移动所有 `run_20260413_*` 文件夹 → `profiling/output/runs_archive/`
3. 移动所有 `run_*_p1*_prompt_probe` 文件夹 → `profiling/output/runs_archive/`
4. 保留 `profiling/output/runs/` 目录（可为空或留一个占位文件）

**验证：**
- `profiling/output/runs/` 为空或只有占位文件
- `profiling/output/runs_archive/` 包含所有历史 run

---

### Task 3: 标记 Legacy 文件

**现状：**
`src/phase1_entity_extraction.py` 包含 legacy 的 P1-A/P1-G/P1-V prompt，但主流程已迁移到 `src/phase1/` 子模块。

**操作：**
在 `src/phase1_entity_extraction.py` 文件头部（docstring 之后）添加：

```python
# ⚠️ LEGACY FILE — v1.1.14+ 已迁移到 src/phase1/
# 本文件保留用于兼容，新代码请使用 src/phase1/ 模块
```

**注意：** 只添加注释，不修改任何代码逻辑。

**验证：**
- 文件头部有 `⚠️ LEGACY` 标记

---

### Task 4: 归档 docs/ 非项目文档

**现状：**
```
docs/
├── obsidian/           # 个人笔记，应移出
├── debug/              # 调试文档，应移出
├── history used/       # 历史文档，应移出
├── 4月第一周工作汇报.md  # 个人汇报，应移出
├── 9_4.md             # 历史文档，应移出
└── 9_5.md             # 历史文档，应移出
```

**操作：**
1. 创建 `docs/_archive/` 目录
2. 移动 `docs/obsidian/` → `docs/_archive/obsidian/`
3. 移动 `docs/debug/` → `docs/_archive/debug/`
4. 移动 `docs/history used/` → `docs/_archive/history_used/`
5. 移动 `docs/4月第一周工作汇报.md` → `docs/_archive/`
6. 移动 `docs/9_4.md` → `docs/_archive/`
7. 移动 `docs/9_5.md` → `docs/_archive/`

**保留不动：**
- `docs/iterations/`（包含 CHANGELOG, TASK_LOG, v1.1.*）
- `docs/dev_spec.md`
- `docs/CLAUDE.md`
- `docs/skills/`
- `docs/prompt_inventory.md`
- `docs/prompt_risk_report.md`
- `docs/profiling_prep_report.md`
- `docs/structure_audit_report.md`
- `docs/structure_audit_cleanup_task.md`（即本文档）

**验证：**
- `docs/_archive/` 包含 6 个被归档的目录/文件
- 上述保留的文档仍在原位

---

### Task 5: 暂存 profiling/ 临时备份文件（不删除）

**原则：** 所有要"删除"的文件先移动到暂存区，确认无误后再删除。

**暂存区：** `profiling/output/_to_be_deleted/`

**现状：**
```
profiling/output/
├── *.backup.txt       # modelslist 备份
├── *backup*.json       # manifest 备份
└── run_manifest.*snapshot*.json  # 中间 snapshot
```

**操作：**
1. 创建 `profiling/output/_to_be_deleted/` 目录
2. 移动 `profiling/output/modelslist.pre4run.backup.txt` → `profiling/output/_to_be_deleted/`
3. 移动 `profiling/output/modelslist.pre8run.backup.txt` → `profiling/output/_to_be_deleted/`
4. 移动 `profiling/output/run_manifest.pre4run.backup.json` → `profiling/output/_to_be_deleted/`
5. 移动 `profiling/output/run_manifest.pre8run.backup.json` → `profiling/output/_to_be_deleted/`
6. 移动 `profiling/output/run_manifest.snapshot.json` → `profiling/output/_to_be_deleted/`

**保留：**
- `profiling/output/run_manifest.json`（主 manifest）
- `profiling/output/model_profiles.json`
- `profiling/output/profile_summary.md`

**验证：**
- `profiling/output/_to_be_deleted/` 包含 6 个被暂存文件
- `profiling/output/` 中不存在 `.backup.` 或 `.snapshot.` 文件

**后续（用户确认后）：** 可安全删除 `profiling/output/_to_be_deleted/`

---

## 执行顺序

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5
```

每个 Task 完成后验证，再执行下一个。

**安全原则：** 所有"删除"操作改为移动到 `xxx_to_be_deleted/` 暂存区，用户确认后可安全删除。

---

## 变更汇总（操作前）

| 操作类型 | 文件/目录 | 目标位置 |
|---------|----------|---------|
| 移动 | scripts/p1a_prompt_probe.py | scripts/probes/ |
| 移动 | scripts/p1g_prompt_probe.py | scripts/probes/ |
| 移动 | scripts/reduced_schema_chain_probe.py | scripts/probes/ |
| 移动 | profiling/output/runs/run_* | profiling/output/runs_archive/ |
| 编辑 | src/phase1_entity_extraction.py | （加注释） |
| 移动 | docs/obsidian/ | docs/_archive/ |
| 移动 | docs/debug/ | docs/_archive/ |
| 移动 | docs/history used/ | docs/_archive/history_used/ |
| 移动 | docs/4月第一周工作汇报.md | docs/_archive/ |
| 移动 | docs/9_4.md | docs/_archive/ |
| 移动 | docs/9_5.md | docs/_archive/ |
| 移动 | profiling/output/*.backup* | profiling/output/_to_be_deleted/ |
| 移动 | profiling/output/*snapshot*.json | profiling/output/_to_be_deleted/ |

---

## 验收标准

- [ ] scripts/ 只有 generate_snapshot.py + probes/ 子目录
- [ ] profiling/output/runs/ 为空或只有占位
- [ ] profiling/output/runs_archive/ 包含所有历史 run
- [ ] src/phase1_entity_extraction.py 头部有 ⚠️ LEGACY 标记
- [ ] docs/_archive/ 包含 6 个被归档的目录/文件
- [ ] docs/ 根目录不包含 obsidian/debug/history used/ 个人文档
- [ ] profiling/output/_to_be_deleted/ 包含 6 个被暂存文件
- [ ] profiling/output/ 根目录不包含 .backup. 或 .snapshot. 文件
- [ ] 无 .py 文件被修改（除加注释外）
- [ ] 无 .yaml/.json 配置文件被修改
- [ ] outputs/ 目录完全未动

---

## 禁止事项

- ❌ 不修改 src/ 下任何 .py 的代码逻辑（只加注释）
- ❌ 不修改 profiling/ 下任何 .yaml/.json 配置
- ❌ 不修改 outputs/ 任何文件
- ❌ 不删除 docs/iterations/ 下任何文档
- ❌ 不修改 CHANGELOG.md 或 TASK_LOG.md
- ❌ 不直接删除任何文件，统一先移动到 `_to_be_deleted/` 暂存区
