# Session Report: 并发调度 + 确定性校验 + 实时状态面板

**日期**: 2026-06-07  
**分支**: `work/v1.2.8`  
**种子**: `test8.txt`（OPPO 母亲节营销争议）  
**模型**: qwen36-35b（内网 Qwen 集群）

---

## 一、本次做了什么

### 1. Phase 3 Tick 并发（已落地）

将 `run_tick` 中选中 agent 的 LLM 发言调用从串行改为 `ThreadPoolExecutor` 并行，每 tick 选中 5-6 个 agent 同时调 LLM。

**串行**: `Agent A 10s → Agent B 12s → Agent C 8s → ... = 48s/tick`  
**并发**: `max(A 10s, B 12s, C 8s, ...) = 12s/tick`（由最慢决定）

**提交**: `9c342df`

### 2. Phase 1 传播者并发生成（已落地）

将 Generator 拆分为两层：

- **Entity Generator**（1 次 LLM）：提取事件实体 + 规划传播者框架（数量和分布）
- **Concurrent Spreader Generator**（N 次 LLM 并行）：每个传播者独立生成完整人设

并发写死了 Generator prompt 中的 7 个传播者 11 字段人设，改为每个 agent 只生成自己的 8 个描述字段。

**提交**: `5edb40d`

### 3. 二分并发降级（已落地）

Phase 1 和 Phase 3 都实现相同的降级策略：

```
全量 N 并发 → 批量失败 → N/2 重试 → N/4 → ... → 单线程 → fallback
```

由 `config.py` 中的 `PHASE1_MAX_CONCURRENT_SPREADERS` 和 `PHASE3_TICK_MAX_CONCURRENT_WORKERS` 控制上限（`0` = 无上限，由二分法自动决定）。

**提交**: `5edb40d`, `e9656cc`

### 4. Pydantic 确定性校验（已落地）

删除了 `validator_check_format`（LLM 调用），替换为 `EntityExtractionOutput(**merged)` 的 Pydantic 校验：

- 校验速度快 1000x+（毫秒 vs 秒级 LLM）
- 错误信息精准（具体到字段名 + 原因）
- 消除"LLM 审 LLM"的模糊性
- 在 `EntityExtractionOutput` 中新增 `estimated_percentage` 之和 = 100 校验

**涉及的 Prompts 死代码删除**：`VALIDATOR_SYSTEM_PROMPT`（~50 行）、`VALIDATOR_USER_PROMPT`（~10 行）

**提交**: `544025c`

### 5. 实时状态面板（已落地）

新建 `src/display/` 包，4 个文件：

| 文件 | 职责 |
|---|---|
| `concurrency_tracker.py` | 线程安全的并发池跟踪（add/done/summary） |
| `phase_tracker.py` | 阶段名 + 计时 |
| `status_bar.py` | Rich Live 底部面板，Spinner 动画 + 并发状态 |
| `__init__.py` | 导出 + `get_bar()` 全局访问 |

**运行效果**（终端底部实时显示）：

```
┌──────────────────────────────────────────────────────────┐
│ ⠋ Phase 1 实体提取  ⏱ 02:17  ┃ 并发 7  ✓6  ⏳1  最慢 34.9s
│   传统伦理坚守者 ✓ 17.2s  营销行业从业者 ✓ 33.9s  ...
└──────────────────────────────────────────────────────────┘
```

- Spinner 循环转动 → 工程师一眼可知进程未挂
- 并发数实时更新 → 每完成一个 worker 立即刷新
- 最慢耗时 → 可知当前批次的瓶颈

**集成方式**：`get_bar()` 全局可访问，不从调用链层层传递。

**提交**: `912b309`

### 6. midPhaseTest.py 自动化（已落地）

- 增加 `_ensure_visible_window()`：检测到 stdout 非 TTY（Hermes 后台）时，自动通过 `osascript` 开可见 Terminal 窗口
- 路径空格用 `shlex.quote` 安全处理
- 包裹 `StatusBar` 上下文管理器，三阶段 `set_phase()`

**以后从 Hermes 跑测试**: `.venv/bin/python tests/midPhaseTest.py seeds/test8.txt` → 自动弹窗口，不阻塞 Hermes。

**提交**: `112748e`, `3c3c353`, `98f34d3`

### 7. CLI 并发标记（已落地）

追加 `→ 并 N` / `← 并` 首尾标记 + 每个并发单元完成行的耗时 `[Xs]`：

```
→ 并 7 7 个传播者人设并发生成...
  Spreader 1/7: 传统伦理坚守者...
  ✓ 老张 (退休教师) [17.2s]
  ✓ 小李 (广告策划) [33.9s]    ← 散布不同耗时
  ...
← 并 7/7 全部返回
```

**提交**: `86216aa`, `336e9cd`

---

## 二、性能对比

### 总体

```
                   老（6月6日 串行）     新（今天 并发）      加速
────────────────────────────────────────────────────────────
Phase 1             203.96s               143.48s           1.4x
Phase 3 (tick)      382.20s               155.67s           2.5x
────────────────────────────────────────────────────────────
总计（不含Phase4）    ~586s                 299s             2.0x
```

### Phase 1 详细拆解

**老版（LLM Validator 地狱）**:

| 步骤 | 耗时 | 说明 |
|---|---|---|
| Analyzer | 17.74s | 1 次 LLM |
| Generator | 47.86s + 36.61s + 45.70s | 重试 3 次 |
| LLM Validator | 32.58s + 23.40s | 2 次 LLM |
| 有效产出 | ~42s | 仅最后一次通过 |
| **总耗时** | **203.96s** | 有效产出比 ~20% |

**新版（Pydantic + 并发）**:

| 步骤 | 耗时 | 说明 |
|---|---|---|
| Analyzer | 14.44s | 1 次 LLM |
| Entity Gen | 47.60s + 43.69s | 重试 1 次（Pydantic 捕获） |
| Concurrent Pool | 37.64s | **7 个同时启动** |
| LLM Validator | 0s | 已删除 |
| **总耗时** | **143.48s** | 有效产出比 ~100% |

### Phase 3 Tick 详细拆解

| Tick | 老版串行 | 新版并发 | 加速 |
|---|---|---|---|
| Tick 1 | ~72s (6 agents) | 25.64s (6 agents) | 2.8x |
| Tick 2 | ~87s (6 agents) | 35.30s (6 agents) | 2.5x |
| Tick 3 | ~69s (5 agents) | 33.73s (5 agents) | 2.0x |
| Tick 4 | ~75s (5 agents) | 28.42s (5 agents) | 2.6x |
| Tick 5 | ~79s (5 agents) | 32.56s (5 agents) | 2.4x |
| **总计** | **382s** | **155.67s** | **2.5x** |

### 并发稳定性

- **Qwen 集群**：7 路并发零异常、零限流、零超时、零 fallback
- **二分降级**：从未触发——Qwen 扛得住全量并发
- **Pydantic 校验**：Entity Generator 重试 1 次（`estimated_percentage` 和不等于 100），捕获精准

---

## 三、架构变更

### 并发调度通用模式

```
全量 N 并发 ──成功──→ 完成
    │
    失败（批量）
    │
    N/2 并发 ──成功──→ 完成
    │
    失败
    │
    N/4 ... → 1 → fallback
```

Phase 1 和 Phase 3 共享同一模式，未来 Phase 2 / Parser 如有并发需求可直接复用。

### 确定性校验链路

```
LLM raw output
  ↓
Parser（_parse_llm_json_payload，已有）
  ↓
Compiler（_post_process_entities，已有）
  ↓
Validator（Pydantic model_validate，替代 LLM）
  ↓
通过 → EntityExtractionOutput → 下游
```

### 全局状态面板架构

```
midPhaseTest.py
  │  with StatusBar() as bar:
  │    bar.set_phase("Phase 1")
  │    bar.set_concurrency()  → ConcurrencyTracker
  │
  ├── extraction.py
  │     get_bar().concurrency.done(name, elapsed)
  │                              ↓
  │                     ConcurrencyTracker(done)
  │                              ↓ on_change callback
  │                     StatusBar.refresh()
  │                              ↓
  │                     Rich Live.update(panel)
  │
  └── tick_simulation.py
        get_bar().concurrency.done(name, elapsed)
```

### 配置项新增（`config.py`）

| 配置 | 默认值 | 说明 |
|---|---|---|
| `PHASE1_MAX_CONCURRENT_SPREADERS` | 0 | Phase 1 传播者并发上限（0=无上限） |
| `PHASE3_TICK_MAX_CONCURRENT_WORKERS` | 0 | Phase 3 tick 并发上限（0=无上限） |

---

## 四、Commit 历史

```
3c3c353  midPhaseTest: 路径空格用 shlex.quote 修
98f34d3  midPhaseTest: 移除无用 os import
112748e  midPhaseTest: 自动开可见 Terminal 窗口 (isatty 检测)
912b309  display: StatusBar + ConcurrencyTracker 实时状态面板
336e9cd  cli: 并发单元完成行加耗时 [Xs]
86216aa  cli: 并发生成加 → 并 N / ← 并 标记
544025c  phase1: 删除 LLM Validator，改用确定性 Pydantic 校验
c688a8a  config: PHASE1_MAX_CONCURRENT_SPREADERS = 0
5edb40d  phase1 concurrent: 传播者并发生成 + 二分降级
e9656cc  phase3 tick: 并发调度加二分降级
9c342df  parallel: concurrent LLM calls per tick + tick_entries in dataset
```

---

## 五、下一步建议

1. **Repair Loop**（治理文档 v1.2.7）：Pydantic 校验失败后，不重做全部 Generator，只定向修复出错的字段
2. **ConcurrencyTracker 持久化**：将每次并发的耗时散布写入 timing_summary.json，方便长期 profiling
3. **Phase 1 Generator prompt 缩减**：Entity Generator prompt 目前仍请求完整 11 字段人设，可精简为只请求框架字段以节省 token
4. **Phase 3 tick 收敛检测**：恢复被注释掉的收敛检测逻辑（目前跑满 10 tick，可提前停止）
