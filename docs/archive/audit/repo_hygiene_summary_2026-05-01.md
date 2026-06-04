# Repo Hygiene 任务汇总 - 2026-05-01

## 1. 任务背景

本轮任务发生在 Phase 1 工程改造之前。

在审计 `audit/phase1工程改造.md` 时，发现当前仓库曾处于 dirty working tree 状态：大量源码、文档、运行产物、profiling 产物、seed 文件和 audit 文件同时存在未收口变更。由于 Phase 1 Output Contract Freeze 属于输出契约治理任务，如果直接在混乱工作树上继续推进，会带来以下风险：

- 无法清楚判断新改动与历史改动的边界。
- 无法可靠回滚。
- 运行产物 `outputs/` 和 `profiling/output/` 会持续污染 Git diff。
- 大量输出文件会淹没真正的源码和文档变更。
- 后续 Phase 1 R0 / R1 的审计结论可能建立在不稳定基线上。

因此决定先做 repo hygiene，再继续 Phase 1 R0。

## 2. 任务规划

本轮 hygiene 的目标不是修改业务逻辑，而是建立一个可审计、可回滚、可继续迭代的仓库状态。

规划原则：

- 先建立 checkpoint，再做清理。
- 不删除本地运行产物。
- 只让生成产物退出 Git 跟踪。
- 把少量关键证据转移为轻量 audit evidence。
- 不做 Phase 1 / Phase 2 / Phase 3 / Phase 4 业务代码修改。
- 不做 Parser / Compiler / Validator / Repair Loop 实现。
- EOL 归一化只先建立策略，不在本轮做大规模 renormalize。

计划备份文件：

- `audit/repo_hygiene_plan_2026-05-01.md`

关键计划：

1. 建立 pre-hygiene checkpoint。
2. 更新 `.gitignore`，阻止未来运行产物进入 Git。
3. 新增 `.gitattributes`，固定文本换行策略。
4. 在 `audit/evidence/` 下保存轻量运行证据。
5. 使用 `git rm --cached -r outputs profiling/output` 让生成产物退出 Git 跟踪。
6. 验证工作树、退踪数量、whitespace 状态。
7. 单独提交 hygiene commit。

## 3. 执行过程

### 3.1 建立 checkpoint

用户先在本地完成 checkpoint commit：

```text
f9fae60 checkpoint: pre hygiene dirty tree before phase1 r0
```

该提交用于保存 Mac 迁移后的完整现场，作为后续 repo hygiene 的回滚锚点。

### 3.2 运行产物盘点

只读盘点结果：

- `outputs/` 和 `profiling/output/` 下原本有 `166` 个 tracked 文件。
- 本地物理文件约 `168` 个，多出的主要是 `.DS_Store`。
- 分类如下：
  - `113` 个 tracked 文件位于 `outputs/`
  - `53` 个 tracked 文件位于 `profiling/output/`
- 这些文件主要是：
  - timestamped run artifacts
  - legacy output snapshots
  - profiling archived runs
  - `_to_be_deleted` 下的 profiling backup/snapshot

判断：这些目录属于生成产物，不应继续作为普通源码版本管理对象。

### 3.3 更新 Git 忽略策略

修改 `.gitignore`：

- 忽略 `outputs/`
- 忽略 `profiling/output/`
- 保留 `audit/evidence/` 作为可提交的轻量证据目录

目的：

- 后续运行 `main.py` 或 profiling 工具时，不再让生成产物进入 Git diff。
- 避免运行产物污染源码变更。

### 3.4 新增文本规范策略

新增 `.gitattributes`：

- 设置常见文本文件为 LF。
- 包括 `.py`、`.md`、`.txt`、`.json`、`.jsonl`、`.yaml`、`.yml` 等。
- 标记常见图片、PDF、zip 为 binary。

注意：

- 本轮只建立策略。
- 没有执行 `git add --renormalize .`。
- 大规模 EOL 归一化留到未来独立提交，避免产生难读的大 diff。

### 3.5 建立 audit evidence

新增轻量证据目录：

- `audit/evidence/README.md`

新增两份 evidence：

- `audit/evidence/run_test5_20260429_022613.md`
- `audit/evidence/run_test7_20260427_174326.md`

其中 `test5_20260429_022613` 是主 evidence：

- 运行路径为当前 Mac 路径。
- 状态为 `success`。
- 包含完整 run artifacts。
- 模型：`qwen35-122b-a10b`
- provider：`qwen`
- elapsed seconds：`198.57`
- risk level：`low`
- final polarization index：`0.26`

`test7_20260427_174326` 作为历史对照 evidence：

- 运行成功。
- 但 metadata 中仍包含旧 Windows 路径。
- 因此只作为对照，不作为当前主 evidence。

### 3.6 生成产物退踪

执行命令：

```bash
git rm --cached -r outputs profiling/output
```

说明：

- 该命令只移除 Git 跟踪。
- 不删除本地文件。
- 本地 `outputs/runs/test5_20260429_022613/run_meta.json` 已验证仍然存在。

退踪后验证：

```text
git ls-files outputs profiling/output | wc -l
=> 0
```

### 3.7 提交 hygiene commit

用户在本地完成提交：

```text
b13dd57 chore: isolate generated runtime artifacts
```

当前提交链：

```text
b13dd57 chore: isolate generated runtime artifacts
f9fae60 checkpoint: pre hygiene dirty tree before phase1 r0
3c418aa 1.2.1.2
```

## 4. 最终效果

当前验证结果：

```text
git status --short -b
=> ## master

git ls-files outputs profiling/output | wc -l
=> 0

git diff --check HEAD
=> 无报错
```

最终效果：

- 当前工作树干净。
- `outputs/` 和 `profiling/output/` 已退出 Git 跟踪。
- 本地运行产物仍保留在磁盘上。
- 关键运行证据已转为轻量 audit evidence。
- `.gitignore` 已防止未来生成产物再次污染 Git。
- `.gitattributes` 已建立文本换行策略。
- Phase 1 R0 之前已有明确回滚锚点。

已新增或修改的治理文件：

- `.gitignore`
- `.gitattributes`
- `audit/repo_hygiene_plan_2026-05-01.md`
- `audit/repo_hygiene_closeout_2026-05-01.md`
- `audit/evidence/README.md`
- `audit/evidence/run_test5_20260429_022613.md`
- `audit/evidence/run_test7_20260427_174326.md`

## 5. 是否收口

本轮 repo hygiene 第一阶段已收口。

收口判断：

- 有 checkpoint：是，`f9fae60`
- 有 hygiene commit：是，`b13dd57`
- 工作树干净：是
- 运行产物退出 Git 跟踪：是
- 本地运行产物未删除：是
- evidence 已留痕：是
- 未触碰 Phase 1 业务逻辑：是

剩余未做事项：

- 未做大规模 EOL renormalization。
- 未清理 Git 历史中的旧运行产物。
- 未执行 Phase 1 Output Contract Freeze。
- 未实现 Parser / Compiler / Validator。

这些事项不阻塞 Phase 1 R0。

## 6. 下一个任务安排

建议下一步进入：

```text
R0：Phase 1 Output Contract Freeze
```

原因：

- 当前 Git 状态已经干净。
- 运行产物不再污染 diff。
- 已有 checkpoint 和 hygiene commit 作为回滚锚点。
- 可以安全新增正式 R0 文档。

建议下一个任务的产物：

- `docs/iterations/phase1-output-contract-freeze.md`

R0 任务应完成：

- 审计 Phase 1 当前输出结构。
- 审计 Phase 2 / Phase 3 / Phase 4 / main.py 对 Phase 1 字段的真实依赖。
- 标记 required / optional / legacy / candidate_intermediate / forbidden 字段。
- 明确 R1 Parser-Compiler-Validator 的准入条件。
- 不改业务代码。

暂缓任务：

- EOL renormalization：建议未来单独提交。
- Git 历史瘦身：除非仓库体积成为问题，否则暂不做。
- CLI / CSV / profiling 深层治理：不纳入 Phase 1 R0。

