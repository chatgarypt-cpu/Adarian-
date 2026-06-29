# 平行世界调度器 v0.1 — 设计文档

> **目标：** 一次跑 N 个完整的舆情模拟（Phase 1→2→3），每个世界独立进程 + 不同模型配置，支持 5 个平行世界初版。

---

## 1. 核心理念

```
Seed 文本
  │
  ├── World_1 ── qwen36-35b    ──→ outputs/runs/2026-06-07/world_1_183000/simulation_dataset.json
  ├── World_2 ── qwen3-30b-tke ──→ outputs/runs/2026-06-07/world_2_183000/simulation_dataset.json
  ├── World_3 ── minimax       ──→ outputs/runs/2026-06-07/world_3_183000/simulation_dataset.json
  ├── World_4 ── qwen3-80b     ──→ outputs/runs/2026-06-07/world_4_183000/simulation_dataset.json
  └── World_5 ── qwen35-122b   ──→ outputs/runs/2026-06-07/world_5_183000/simulation_dataset.json

      每个 = 独立子进程，跑完整 Phase 1→3
      一个 World 挂了 → 另一个模型兜底重试
      全部完成后 → 5 份 simulation_dataset.json → 对比分析
```

每个 World：
- 是**一个完整模拟**（不是 Phase 内部的一个步骤）
- 用自己独立的 **模型 + endpoint + max_tokens**
- 跑独立的 **Phase 1→2→3** 完整管线
- 写独立的 **run_dir/**（产物完全隔离）

---

## 2. 数据结构

### 2.1 WorldConfig — 一个世界的全部配置

```python
@dataclass
class WorldConfig:
    name: str                    # "world_1"
    label: str                   # "qwen36-35b" — 显示用
    model: str                   # "qwen36-35b"
    base_url: str                # "http://<llm-gateway>:port/v1"
    api_key: str                 # 该池的 key
    max_tokens: int              # 该世界的 token 预算
    fallback_model: str          # 兜底模型名
    fallback_base_url: str       # 兜底算力池
    seed_text: str               # 种子文本
    # Phase 参数
    event_scale: float           # 0.7
    event_controversy: float     # 0.8
    event_type: str              # "产品质量问题"
```

### 2.2 WorldResult — 一个世界的执行结果

```python
@dataclass
class WorldResult:
    config: WorldConfig
    status: str                  # "completed" | "failed" | "fallback_completed"
    run_dir: Path                # 产物目录
    elapsed: float               # 耗时(秒)
    fallback_used: bool          # 是否触发兜底
    error: str | None            # 失败原因
    dataset_path: Path | None    # simulation_dataset.json 路径
```

### 2.3 SchedulerConfig — 调度器本身的配置

```python
@dataclass
class SchedulerConfig:
    worlds: list[WorldConfig]    # 最多 5 个
    max_concurrent: int          # 并行数（默认 5）
    fallback_enabled: bool       # 是否启用兜底
    fallback_delay: int          # 兜底等待秒数（默认 30）
    output_root: Path            # outputs/runs/
```

---

## 3. 调度器架构

### 3.1 调度流程

```
Scheduler.run()
  │
  ├─ 1. 读取/生成 WorldConfig 列表（最多 5 个）
  │
  ├─ 2. 用 ProcessPoolExecutor 并行 spawn
  │     每个子进程 = run_world(world_config)
  │     max_workers = min(5, 可用 CPU 数)
  │
  ├─ 3. 监控所有 future
  │     ├─ completed → 收集 WorldResult
  │     ├─ failed    → 触发 fallback 重试
  │     └─ 更新状态栏（Rich Live）
  │
  ├─ 4. 所有 World 完成后汇总
  │     └─ 写入汇总对比报告
  │
  └─ 5. 输出汇总表格（每个 World 的基本指标）
```

### 3.2 Fallback 机制

```
World X 失败 → 等待 fallback_delay 秒
  → 用 WorldConfig.fallback_model + fallback_base_url 重建
  → 更新 status 为 "fallback_completed"
  → 如果 fallback 也失败 → status = "failed"
```

**兜底策略（初版）：**

| 原始模型挂了 | 用这个兜底 |
|-------------|-----------|
| qwen36-35b      | qwen3-30b-tke（同池低配） |
| qwen3-30b-tke   | qwen36-35b（同池互备） |
| minimax         | qwen36-35b（跨池） |
| qwen3-80b       | qwen35-122b（跨池高配） |
| qwen35-122b     | qwen36-35b（降级保底） |

### 3.3 子进程内部

每个 `run_world(wc: WorldConfig)` 做的事情：

```python
def run_world(wc: WorldConfig) -> WorldResult:
    t0 = time.perf_counter()
    try:
        # 设置该世界的模型上下文
        with world_context(wc):
            # 跑完整 Phase 1→2→3
            params = analyzer_set_parameters(wc.seed_text)
            entities = extract_entities_with_validation(...)
            spreaders = create_spreaders_concurrent(...)
            topology = build_topology(...)
            ticks = simulate_ticks(...)
            dataset = build_simulation_dataset(...)

        elapsed = time.perf_counter() - t0
        return WorldResult(status="completed", elapsed=elapsed, ...)
    except Exception as e:
        return WorldResult(status="failed", error=str(e), ...)
```

`world_context(wc)` 是一个上下文管理器，临时覆盖全局配置：

```python
@contextmanager
def world_context(wc: WorldConfig):
    """临时将 LLM 配置设为该世界的值"""
    old_model = config.LLM_MODEL
    old_url = config.LLM_BASE_URL
    old_key = config.LLM_API_KEY
    old_tokens = config.DEFAULT_MAX_TOKENS

    config.LLM_MODEL = wc.model
    config.LLM_BASE_URL = wc.base_url
    config.LLM_API_KEY = wc.api_key
    config.DEFAULT_MAX_TOKENS = wc.max_tokens
    try:
        yield
    finally:
        config.LLM_MODEL = old_model
        config.LLM_BASE_URL = old_url
        config.LLM_API_KEY = old_key
        config.DEFAULT_MAX_TOKENS = old_tokens
```

---

## 4. CLI 界面

### 4.1 配置入口：`worlds.yaml`

用户通过一个 YAML 文件配置 5 个世界的参数：

```yaml
# worlds.yaml
worlds:
  - name: baseline
    label: "Qwen 36B 基线"
    model: qwen36-35b
    base_url: http://127.0.0.1:8090/v1
    api_key_from_env: LLM_API_KEY     # 从环境变量读
    max_tokens: 16384
    fallback_model: qwen3-30b-tke
    fallback_base_url: http://127.0.0.1:8090/v1

  - name: fast_30b
    label: "Qwen 3 30B 快速"
    model: qwen3-30b-tke
    base_url: http://127.0.0.1:8090/v1
    api_key_from_env: LLM_API_KEY
    max_tokens: 8192
    fallback_model: qwen36-35b
    fallback_base_url: http://127.0.0.1:8090/v1

  - name: minimax
    label: "MiniMax 多视角"
    model: minimax
    base_url: http://127.0.0.1:8090/v1
    api_key_from_env: LLM_API_KEY
    max_tokens: 8192
    fallback_model: qwen36-35b
    fallback_base_url: http://127.0.0.1:8090/v1

  - name: large_80b
    label: "80B 强推理"
    model: qwen3-80b-tke
    base_url: http://127.0.0.1:8090/v1
    api_key_from_env: LLM_API_KEY
    max_tokens: 16384
    fallback_model: qwen35-122b-sg
    fallback_base_url: http://127.0.0.1:8090/v1

  - name: largest
    label: "122B 大模型"
    model: qwen35-122b-sg
    base_url: http://127.0.0.1:8090/v1
    api_key_from_env: LLM_API_KEY
    max_tokens: 32768
    fallback_model: qwen36-35b
    fallback_base_url: http://127.0.0.1:8090/v1

seed_path: seeds/test8.txt         # 所有世界共用同一份 seed
max_concurrent: 5                   # 并行数
fallback_enabled: true              # 启用兜底
fallback_delay_sec: 30              # 等 30s 再兜底
output_root: outputs/runs
```

### 4.2 CLI 命令

```bash
# 查看可用模型（从 model_router.py 读取）
python -m src.scheduler list-models

# 用默认配置跑 5 个平行世界
python -m src.scheduler run

# 指定配置文件
python -m src.scheduler run --config worlds.yaml

# 只跑其中几个
python -m src.scheduler run --worlds baseline,fast_30b,minimax

# 查看上次运行结果
python -m src.scheduler history
```

### 4.3 运行态显示

调度器运行时用 Rich Live 显示并发状态栏，符合你之前要求的"可见、可并发"风格：

```
┌─ Parallel Worlds ─────────────────────────────────────┐
│  World        Model          Status     Time   Retry   │
│  ───────────────────────────────────────────────────── │
│  ✓ baseline   qwen36-35b    Phase 3    32.1s   0      │
│  → fast_30b   qwen3-30b     Phase 2 ⏱  18.4s   0      │
│  ✓ minimax    minimax       Phase 3    45.2s   0      │
│  ⚠ large_80b  qwen3-80b     fallback⏱  12.3s   1      │
│  → largest    qwen35-122b   Phase 1 ⏱  8.7s    0      │
│  ───────────────────────────────────────────────────── │
│  5/5 running  ·  elapsed: 52.3s                        │
└───────────────────────────────────────────────────────┘
```

### 4.4 运行后汇总

跑完后输出对比表格：

```
┌─ World 对比 ──────────────────────────────────────────┐
│  World        Entities  Spreaders  Ticks  Time    Status│
│  ───────────────────────────────────────────────────── │
│  baseline     6         8          30     186.2s  ✓    │
│  fast_30b     5         7          28     142.1s  ✓    │
│  minimax      4         6          22     98.3s   ✓    │
│  large_80b    6         8          32     312.5s  ⚠ fb │
│  largest      7         9          35     425.8s  ✓    │
└───────────────────────────────────────────────────────┘
```

---

## 5. 文件结构

```text
src/
  scheduler/
    __init__.py          # 导出
    config.py            # WorldConfig, SchedulerConfig dataclass
    context.py           # world_context() 上下文管理器
    runner.py            # run_world() — 子进程入口
    scheduler.py         # Scheduler 主类 — 进程管理 + fallback + 汇总
    cli.py               # CLI 入口（argparse）
    display.py           # 并发状态栏（Rich Live）
    fallback.py          # 兜底策略表
    summary.py           # 汇总对比报告
worlds.yaml              # 默认平行世界配置
```

---

## 6. 初版范围 & 红线

**初版只做：**

| 功能 | 做不做 |
|------|--------|
| 5 个平行世界并行 | ✅ 做 |
| YAML 配置模型 | ✅ 做 |
| 子进程失败兜底 | ✅ 做 |
| CLI 启动 | ✅ 做 |
| 状态栏显示 | ✅ 做 |
| 汇总对比表 | ✅ 做 |
| Web 前端 | ❌ 初版不做 |
| 动态扩缩世界数 | ❌ 固定 5 个 |
| 跨进程通信 | ❌ 不需要，文件即总线 |
| Phase 4 自动对比分析 | ❌ 初版只汇总指标，不产报告 |

**红线：**
- 不修改 `src/phase1/` `src/phase2/` `src/phase3/` 的生产代码
- `world_context()` 是唯一与全局配置的接触点
- 子进程退出后不残留任何修改
- 兜底最多触发 1 次/世界，超过就给 failed

---

## 7. 与现有系统的关系

```
model_router.py ← 提供模型清单（CATALOG）
  │
  ▼
scheduler/cli.py ← 用户从这里启动
  │
  ├─ 读 worlds.yaml → list[WorldConfig]
  │
  ▼
scheduler/scheduler.py ← spawn 5 个进程
  │
  ├─ run_world() → world_context(wc) → 调现有的 Phase 1→3
  │                                   │
  │                                   └─ LLMClient 自动用 wc 的配置
  │
  └─ fallback → 另一模型重试
```

**对现有代码的零侵入：** Phase 1→3 不需要改一行代码。`world_context` 在进程启动时设置好全局 config，LLMClient 读的就是这个值。

---

## 8. 未定项 & 决策点

| 问题 | 选项 | 我的建议 |
|------|------|---------|
| 子进程用 `ProcessPoolExecutor` 还是 `multiprocessing.Process` 手动管理？ | Pool 或手动 | 初版用 `ProcessPoolExecutor`，足够简单 |
| 世界配置放 YAML 还是 CLI 参数？ | YAML 或 argparse | YAML，复杂配置用文件比 CLI 参数友好 |
| 兜底是自动触发还是等用户确认？ | 自动或手动 | 自动触，但打声音通知让你知道 |
| 5 个进程吃满 CPU 怎么办？ | 限流或不管 | 每个世界本身就有二分降级，够用了 |
| 不同算力池的 api_key 不同怎么办？ | 每个 WorldConfig 独立配 | YAML 里配 `api_key_from_env` 指向不同环境变量 |

---

**先确认方向对不对？** 对了我再写具体实现代码。设计文档定稿后存档到 `docs/design/` 下。
