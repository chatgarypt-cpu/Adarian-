# Git Freeze Checklist

## 0. Purpose

本文件定义每次 iteration closeout 前必须执行的 git freeze 检查。

目标：
- 让每次 iteration 成为可审查的版本单元
- 让每次 iteration 之后都存在明确 rollback target
- 让“回到上一版本”成为可执行动作，而不是口头承诺

---

## 1. When to Use

在以下场景必须执行本检查：
- iteration 准备关闭
- 准备创建版本 tag
- 准备宣布“该版本已完成”
- 准备把当前版本作为下一轮的 baseline

---

## 2. Freeze Rules

### Rule-01: Clean Working Tree

必须满足：
- 无未提交的已跟踪改动
- 无意外未跟踪文件

推荐命令：

```powershell
git status --porcelain=v1
```

通过标准：
- 输出为空

### Rule-02: Iteration Status Closed

必须满足：
- iteration doc 已明确关闭
- `TASK_LOG.md` 已有完成记录

### Rule-03: Acceptance Recorded

必须满足：
- 至少有最小验收记录
- 若有失败项，必须已声明是否留待后续版本

### Rule-04: Version Anchor Created

必须满足：
- 当前 iteration 有明确 tag 或等价 release commit

推荐 tag 规则：

```text
iter-vX.Y.Z-closeout
```

### Rule-05: Previous Version Identified

必须满足：
- 能明确说出上一版本 tag 是什么

如果回答不了“上一版本是谁”，则不允许宣布当前版本可回滚。

---

## 3. Pre-Tag Checklist

在打 tag 之前逐项确认：

- [ ] iteration doc 状态为完成
- [ ] `TASK_LOG.md` 已记录完成
- [ ] `CHANGELOG.md` 已更新
- [ ] 必要的 workflow/doc 变更已落盘
- [ ] 工作树干净
- [ ] 当前版本与上一版本边界清晰

---

## 4. Tagging Checklist

- [ ] 创建当前 iteration 的 closeout tag
- [ ] 记录该 tag 名称
- [ ] 记录上一版本 tag 名称
- [ ] 在需要的文档中写入当前版本锚点

推荐命令：

```powershell
git tag iter-vX.Y.Z-closeout
git tag --sort=-creatordate
```

---

## 5. Rollback Verification

每次 freeze 后，至少要能回答以下问题：

- 当前版本 tag 是什么
- 上一版本 tag 是什么
- 若回滚，回滚目标是谁
- 回滚后如何做最小验证

最低验证建议：

```powershell
git describe --tags --abbrev=0
git rev-list --count <previous_tag>..HEAD
```

如果要做实际回滚演练，至少应在隔离环境验证：
- 能 checkout 到上一版本
- 能运行最小 smoke test
- 能确认关键文档与代码边界一致

---

## 6. Failure Conditions

出现以下任一情况，不允许 freeze：

- `git status --porcelain=v1` 非空
- iteration 仍为进行中
- 没有验收记录
- 没有版本锚点
- 无法明确上一版本是谁

---

## 7. Minimal Closeout Record

每次 freeze 后至少记录以下信息：

- iteration id
- current tag
- previous tag
- acceptance result
- known carry-over items

建议格式：

```text
iteration: vX.Y.Z
current_tag: iter-vX.Y.Z-closeout
previous_tag: iter-vX.Y.(Z-1)-closeout
acceptance: pass / pass_with_known_issues / fail
carry_over:
- item 1
- item 2
```

---

## 8. Decision Standard

只有当以下命题同时成立时，才可以说“本 iteration 可回滚”：

- 有明确的上一版本锚点
- 当前版本锚点已创建
- 工作树干净
- 验收记录存在
- 回滚后最小验证路径明确

否则，只能说：
- git 上存在历史提交

不能说：
- 当前 workflow 具备稳定的 iteration rollback capability
