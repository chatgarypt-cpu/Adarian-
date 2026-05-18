# 03 - Redis-SSE 桥接

Redis Streams 是整个事件系统的中枢总线，SSE（Server-Sent Events）是对外暴露的实时推送协议。本章详述两者之间的桥接实现。

## Redis Streams 作为事件总线

### Stream Key 命名规范

由 `orchestrator/utils/sse.py` 中的 `run_events_stream_key()` 定义：

```python
def run_events_stream_key(run_id: str) -> str:
    return f"run:{run_id}:events"
```

每个 run 拥有独立的 Stream，天然支持按 `run_id` 的事件隔离。`dependencies.py` 中 `OrchestratorDependencies` 也定义了同名的实例方法：

```python
def run_events_stream_key(self, run_id: str) -> str:
    return f"run:{run_id}:events"
```

### Stream 容量管理：`run_event_stream_maxlen`

由环境变量 `RUN_EVENT_STREAM_MAXLEN` 配置，默认值 **5000**。定义于 `orchestrator/settings.py`：

```python
run_event_stream_maxlen = _int_env("RUN_EVENT_STREAM_MAXLEN", 5000, minimum=1)
run_event_stream_history_maxlen = _int_env("RUN_EVENT_STREAM_HISTORY_MAXLEN", run_event_stream_maxlen, minimum=1)
```

写入时通过 Redis `XADD` 的 `MAXLEN ~` 参数执行**近似裁剪**（`approximate=True`），不会严格精确到 5000 条，但在性能和内存控制之间取得平衡：

```python
def _queue_run_event_publish(self, pipe, run_id, payload, maxlen):
    pipe.xadd(
        self.run_events_stream_key(run_id),
        {"data": payload},
        maxlen=maxlen if maxlen > 0 else None,
        approximate=True,
    )
```

### Stream TTL

通过 `apply_run_ttl()` / `apply_run_ttl_async()` 对 Stream key 设置过期时间，与 run meta key 共享相同的 TTL 窗口。

## 事件发布：`publish_run_event_async()`

文件位置：`orchestrator/dependencies.py`（`OrchestratorDependencies` 类）

### 同步版本：`publish_run_event()`

用于在同步上下文中（如线程池任务）发布事件。工作流：

```
1. annotate_run_event(event, run_id)  → 添加 run_id、event_class、payload_size_bytes
2. persist_run_event_to_sqlite()      → SQLite 持久化（获得 seq）
3. computed_map = _run_event_metadata_patch(event)  → 提取需要更新到 run meta 的字段
4. Redis Pipeline:
   - XADD run:{run_id}:events MAXLEN~{maxlen}  → 写入 Stream
5. run_state_store.set_run_meta()     → 更新 run meta（status, progress 等）
6. 副作用:
   - persist_task_board_event()       → 任务看板事件持久化
   - _invalidate_run_meta_cache()     → 失效缓存
   - _sync_terminal_status_from_patch() → 同步终态到 SQLite
   - _schedule_webhooks_best_effort() → Webhook 通知
```

### 异步版本：`publish_run_event_async()`

流程与同步版相同，但使用 `redis_async_client` 和 `await` 调用。用于高频率事件（如 `llm_token_delta`）在异步上下文中的发布。

### 调度发布：`schedule_async_publish()`

```python
def schedule_async_publish(self, run_id: str, event: dict) -> None:
    loop = asyncio.get_running_loop()
    loop.create_task(self.publish_run_event_async(run_id, event))
```

允许在同步上下文中通过当前事件循环调度异步发布，避免阻塞。

## SSE 端点实现

### 路由注册

文件位置：`orchestrator/runs/event_stream.py`

两个等价的 SSE 端点：

```
GET /api/runs/{run_id}/stream          → stream_run_events()
GET /api/runs/{run_id}/events/stream   → stream_run_events_alias()（兼容别名）
```

路由注册于 `orchestrator/routers/runs.py`：

```python
from orchestrator.runs.event_stream import (
    router as event_stream_router,
    stream_run_events,
)
router.include_router(event_stream_router)
```

### 请求参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `replay` | bool | false | 是否从 Stream 头部开始重放 |
| `history` | int | 0 | 请求历史事件数量（最大不超过 `run_event_stream_history_maxlen`） |
| `view` | str | null | 视图模式，`"monitor"` 启用 Monitor 视图 |
| `after_seq` | int | 0 | 从该序列号之后开始推送（支持分页续推） |

### `Last-Event-ID` 断线重连机制

`_stream_handler()` 通过以下逻辑实现断线重连：

```python
last_event_id = _requested_last_event_id(request)  # 读取 HTTP 头 "Last-Event-ID" 或查询参数
if last_event_id:
    after_seq = max(after_seq, int(last_event_id))
```

当 `after_seq > 0` 时：
1. 优先从 SQLite 读取 `(after_seq, after_seq + history]` 范围内的历史事件
2. 以 SSE `id:` 字段标记每条事件的序列号
3. 然后接入 Redis Stream 实时流，从 `last_id` 继续

这样确保客户端断线期间的事件不丢失。前端 `EventSource` 浏览器 API 原生支持自动重连并发送 `Last-Event-ID` 请求头。

### `_event_gen()` 生成器

```python
async def _event_gen(run_id, request, deps, data, replay, history, monitor_view, after_seq):
    stream_key = run_events_stream_key(run_id)
    last_event_id = _requested_last_event_id(request)
    # 1. 解析启动状态
    last_id, recent_history = await _resolve_stream_start_state(...)
    yield ": init\n\n"                       # SSE init comment

    # 2. Monitor 快照（如需要）
    if snapshot_emitter:
        yield await snapshot_emitter.initial_chunk()

    # 3. 回放 SQLite 历史（after_seq > 0 时）
    if after_seq > 0:
        persisted_history = await _read_persisted_history_after_seq(run_id, after_seq)
        for raw in persisted_history:
            yield f"id: {sse_id}\n{sse_data(compact_sse_raw(raw))}"

    # 4. 回放 Redis 最近历史（after_seq == 0 时）
    for entry_id, raw in recent_history:
        yield f"id: {sse_id}\n{sse_data(compact_sse_raw(raw))}"

    # 5. 实时流
    async for chunk in _live_event_chunks(...):
        yield chunk
```

### 响应格式

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache, no-transform
X-Accel-Buffering: no

: init

id: 1
data: {"type":"workflow.start","run_id":"abc123","seq":1,...}

id: 2
data: {"type":"node.start","run_id":"abc123","nodeId":"node_0","seq":2,...}

...
```

## 消费者组管理：`event_stream_hub.py`

文件位置：`orchestrator/runs/event_stream_hub.py`

### `RunEventStreamHub` 类

这是一个**应用层多播**实现，解决 Redis Streams 原生消费者组在 SSE 场景中的不足。每个 Stream 对应一个 Hub 实例，Hub 内维护一个后台 `_read_loop` 任务，统一通过 `XREAD` 从 Redis 拉取事件，然后**广播**到所有订阅者。

```
                   ┌─────────────┐
                   │ Redis Stream │
                   │ XREAD        │
                   └──────┬──────┘
                          │ entries
                          ▼
              ┌───────────────────────┐
              │ RunEventStreamHub     │
              │  _read_loop()         │
              │   block=1000ms        │
              │   count=200           │
              │                      │
              │  _broadcast(entry)    │
              └──┬────────┬──────────┘
                 │        │
          ┌──────▼┐ ┌─────▼──────┐
          │client1│ │client2      │ ...  N 个 SSE 连接
          │Queue  │ │Queue        │      (最多 1000 条/队列)
          └───────┘ └────────────┘
```

### 订阅与广播

每个 SSE 客户端连接调用 `subscribe_run_events()`，该函数：
1. 查找或创建 `RunEventStreamHub`（按 `(event_loop_id, redis_client_id, stream_key)` 三元组去重）
2. 创建 `asyncio.Queue(maxsize=1000)` 作为客户端队列
3. 返回 `AsyncIterator[RunEventHubEntry | RunEventHubError]`

广播时通过 `_offer()` 尝试将事件放入每个客户端队列。如果队列满（slow consumer），触发 `RunEventHubClientDropped` 异常，该连接被断开并收到 `stream_closed` 通知（原因：`slow_consumer`）。

### 生命周期

- Hub 在第一个订阅者连接时创建
- 最后一个订阅者断开后自动销毁（`_discard_idle_hub()`）
- `_read_loop` 在无订阅者时自动取消

## 实时流事件循环：`_live_event_chunks()`

```python
async def _live_event_chunks(run_id, request, deps, stream_key, last_id,
                              monitor_view, snapshot_emitter):
    events = subscribe_run_events(...)
    next_item = asyncio.create_task(events.__anext__())
    stream_error_count = 0

    while True:
        if await request.is_disconnected():
            break
        done, _ = await asyncio.wait({next_item}, timeout=KEEPALIVE_INTERVAL_SECONDS)
        if not done:
            yield ": ping\n\n"       # 保活心跳（每 5 秒）
            continue
        item = next_item.result()
        ...
```

关键行为：
- **保活心跳**：每 `KEEPALIVE_INTERVAL_SECONDS`（5 秒）无事件时发送 `: ping\n\n`，防止代理服务器断开空闲连接
- **错误容限**：连续 Redis 错误达到 `_MAX_STREAM_ERRORS`（3 次）后，发送 `stream_closed` 事件并断开
- **慢消费者处理**：`RunEventHubClientDropped` 异常时发送 `stream_closed(reason="slow_consumer")`
- **Monitor 快照**：当事件属于 `_TASK_BOARD_SNAPSHOT_EVENT_TYPES` 集合时（如 `node.complete`、`workflow.complete`），触发任务看板快照增量更新

### XREAD 参数

```python
_XREAD_BLOCK_MS = 1000    # 阻塞等待最长时间
_XREAD_COUNT = 200        # 每次拉取最大条目数
```

## 事件过滤和路由

### 按 `run_id` 过滤

Redis Stream key 天然按 `run:{run_id}:events` 隔离，每个 run_id 的 SSE 端点仅订阅自己的 Stream，无需额外的服务端过滤逻辑。

### 事件类型路由（前端侧）

前端分为两条消费路径：

| 路径 | 入口 | 订阅端点 | 关注的事件 |
|------|------|----------|-----------|
| Chat 流 | `useChatStreaming.ts` → `subscribeGeneration()` | `/api/generations/{id}/stream` | `message.start`, `message.delta`, `message.reasoning`, `tool.start`, `tool.end`, `workflow.created`, `workflow.update`, `phase.change`, `thinking` |
| Monitor 流 | `useRunEventStream.ts` → `EventSource` | `/api/runs/{run_id}/stream?view=monitor` | `node.start`, `node.complete`, `node.error`, `workflow.start`, `workflow.complete`, `workflow.error`, `llm_token_delta`, `llm_tool_start`, `llm_tool_result`, `run_status`, `node.progress`, `snapshot` |

### SQLite 历史事件分页查询

REST API `GET /api/runs/{run_id}/events` 支持按类型过滤：

```
GET /api/runs/{run_id}/events?types=node.start,node.complete&node_id=node_0&after_seq=100&limit=200
```

实现于 `orchestrator/routers/runs.py` 的 `get_run_events()`，底层调用 `read_events_by_seq()` 查询 SQLite。

## 配置汇总

| 配置项 | 环境变量 | 默认值 | 位置 |
|--------|----------|--------|------|
| Stream 最大长度 | `RUN_EVENT_STREAM_MAXLEN` | 5000 | `orchestrator/settings.py` |
| 历史最大长度 | `RUN_EVENT_STREAM_HISTORY_MAXLEN` | 同 `MAXLEN` | `orchestrator/settings.py` |
| 每页默认数量 | `RUN_EVENT_PAGE_DEFAULT_LIMIT` | 200 | `orchestrator/settings.py` |
| 每页最大数量 | `RUN_EVENT_PAGE_MAX_LIMIT` | 2000 | `orchestrator/settings.py` |
| Hub 客户端队列 | `RUN_EVENT_HUB_CLIENT_QUEUE_SIZE` | 1000 | `event_stream_hub.py` |
| SSE 保活间隔 | `KEEPALIVE_INTERVAL_SECONDS` | 5.0 | `event_stream.py` |
| XREAD 阻塞 | `_XREAD_BLOCK_MS` | 1000 | `event_stream.py` |
| XREAD 条目数 | `_XREAD_COUNT` | 200 | `event_stream.py` |
| 最大流错误数 | `_MAX_STREAM_ERRORS` | 3 | `event_stream.py` |
