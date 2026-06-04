# Last Good Commit Search Report (2026-04-22)

## Task

定位“最后一个 `py main.py seeds/test1.txt` 能完整跑通的 commit”，作为后续恢复工作的唯一起点。

约束：

- 不修改主仓库源码
- 不在主工作区 checkout 历史版本
- 使用隔离 worktree 进行测试

## Method

本次定位分两轮：

### Round 1

直接在临时 worktree 中逐个 checkout 最近提交并运行：

```bash
py main.py seeds/test1.txt
```

该轮最初无效，因为临时 worktree 不包含 `.env`，所有提交都会因缺少 `LLM_API_KEY` 提前失败。

### Round 2

在临时 worktree 中补齐 `.env` 后，继续逐个 commit 测试。

发现新的统一外部因素：

- 历史提交广泛依赖 `qwen-turbo`
- 当前环境该模型已不可用
- 因此会在 Phase1 提前报：
  - `model not found: qwen-turbo`

### Round 3

采用“方向 B”：

- 仅在**临时 worktree**中把 `config.py` 的 `QWEN_MODEL = "qwen-turbo"` 替换为当前可用模型 `qwen35-122b-a10b`
- 不改业务逻辑
- 继续逐个 commit 运行 `test1`

该轮结果才是本报告的核心定位结果。

## Tested Commit Range

本次实际覆盖了当前仓库可见历史中与运行链相关的提交，从最新有效业务提交一直扫到最早的运行链提交：

- `cd1ef0f`
- `0a846d7`
- `461047b`
- `163367d`
- `d9d9068`
- `25a384e`
- `65f700e`
- `3c4aafd`
- `6fbc34e`
- `78a2d1e`
- `c6a3d2e`
- `cd36ce2`
- `8a994dd`
- `4c52d2a`
- `25c03b2`
- `8cfd948`
- `e204a5a`
- `bda30ef`
- `e57022d`
- `b8588f3`
- `b9af99b`
- `4e8048f`
- `a9c0a55`
- `11ea91d`
- `488e4c3`
- `938bac7`
- `8705706`
- `ebee6be`
- `e15ca48`
- `784ea0f`
- `a7433e5`
- `765fc1a`
- `9312829`
- `5661ecf`
- `61f6e51`
- `03230c8`
- `f429b83`
- `c3cdfe6`

## Result

### Final Search Result

- `last_good_commit`: **未找到**
- `first_bad_commit`: **无法定义为单一代码引入点**

更准确的说法是：

> 在当前仓库可见历史范围内，即使只在临时 worktree 中统一修正模型名，仍然没有找到一个能让 `test1` 完整 E2E 跑通的 commit。

## Failure Layers

测试过程中暴露出三层失败面，而且它们对应的是不同年代的代码形态。

### Layer A: Recent Baseline Fracture

较新的提交（例如 `cd1ef0f` 一带）主要失败于：

- `src.phase1.orchestrator` 不存在

典型报错：

```text
ModuleNotFoundError: No module named 'src.phase1'
```

说明：

- 这些提交中的 [src/phase1_entity_extraction.py](</d:/项目开发/研一/adarian/adarian mvp/src/phase1_entity_extraction.py>) 已经把入口转发到 `src.phase1.orchestrator`
- 但该模块并未实际存在于对应 commit 的提交树中
- 这属于**结构迁移未收口导致的入口断裂**

### Layer B: Older Runtime Parsing Fragility

更早的提交（例如 `e204a5a`、`f429b83`、`c3cdfe6`）不再卡在 `orchestrator`，而是卡在旧版 `LLM1/2/3` 链路的 JSON 解析：

典型位置：

- `llm1_set_parameters(seed_text)`
- 直接执行 `json.loads(result)`

典型报错：

```text
json.decoder.JSONDecodeError: Expecting value: line 3 column 1 (char 2)
```

说明：

- 旧版链路假设 LLM 返回的是严格 JSON
- 当前可用模型 `qwen35-122b-a10b` 的返回格式和当时预期不完全一致
- 因此旧链路在最早的参数抽取阶段就会失败

这类失败不是“代码一定从来跑不通”，而是：

> **旧代码对当前模型输出格式不兼容**

### Layer C: Windows Console Encoding Crash

在更早的版本中，主错误抛出后还会二次触发：

```text
UnicodeEncodeError: 'gbk' codec can't encode character ...
```

说明：

- 旧版 Rich 输出路径与 Windows `gbk` 控制台编码存在兼容问题
- 这会污染日志尾部，放大失败观感
- 但它是**次级故障**，不是主故障起点

## Why No Single First Bad Commit Was Found

这次搜索没能产出一个标准的：

- `last_good_commit = X`
- `first_bad_commit = Y`

原因不是执行不完整，而是仓库历史本身呈现出两类不同问题：

1. **新一些的版本**
   - 架构迁移到半模块化
   - 但入口引用缺失模块
   - 属于提交树自损坏

2. **更老一些的版本**
   - 主链仍然存在
   - 但对当前 LLM 输出格式过于脆弱
   - 属于环境漂移 / 协议漂移暴露旧实现弱点

因此不存在一个单一的“这里之前都好、从这里开始才坏”的边界。

更符合事实的判断是：

> 当前仓库可见历史中，没有任何一个提交在“当前运行环境 + 仅统一模型名”的条件下可以直接作为可运行恢复点。

## Practical Conclusion

本次搜索的真正结论不是“找到了 last good commit”，而是：

1. **仓库可见历史中没有现成可运行 baseline**
2. **最近版本坏在结构断裂**
3. **更老版本坏在旧 LLM 协议假设**
4. **因此恢复起点不能只靠 git 历史自动定位，必须结合文档、stash、以及当时未提交工作区痕迹来重建 baseline 认知**

## Recommendation

后续如继续恢复，应放弃“再往 git 历史里找一个现成可跑点”的假设，转为以下路线：

1. 以 `4/15` 已提交基线为结构参照
2. 结合已恢复的迭代文档链（`v1.1.12 ~ v1.1.18.2`）
3. 把“旧可运行工作区状态”视为未提交态，而不是某个现成 commit
4. 在此基础上人工重建最小可运行 baseline

## Appendix

本次定位只在临时 worktree 中进行了以下非业务性测试修正：

- 同步主仓库 `.env`
- 将历史 `qwen-turbo` 映射为当前可用 `qwen35-122b-a10b`

未对主仓库源码做任何恢复性修改。
