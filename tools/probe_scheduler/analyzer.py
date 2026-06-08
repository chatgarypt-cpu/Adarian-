"""analyzer.py — 探针分析：延迟矩阵 + 池拓扑推断。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple


def analyze(batch_dir: str | Path) -> str:
    """
    读取一次探针运行的全部 latency_per_call.json，
    输出分析报告文本。

    算法：
    1. 收集每个 world 的每次 LLM 调用延迟
    2. 按时间窗口对齐（同一秒内的调用视为并发冲突）
    3. 对每对 world，计算"并发时延迟是否明显高于单跑"
       → 是 → 可能同池
    4. 输出拓扑猜想
    """
    batch_dir = Path(batch_dir)
    # 收集所有 world 的延迟数据
    worlds_data: dict[str, list[dict]] = {}
    for child in sorted(batch_dir.iterdir()):
        if not child.is_dir():
            continue
        latency_file = child / "whitebox" / "latency_per_call.json"
        if not latency_file.exists():
            continue
        data = json.loads(latency_file.read_text(encoding="utf-8"))
        if data:
            worlds_data[child.name] = data

    if len(worlds_data) < 2:
        return "需要至少 2 个成功 world 才能分析。"

    # 统计每个 world
    stats: dict[str, dict] = {}
    for name, calls in worlds_data.items():
        elapsed_list = [c["elapsed"] for c in calls]
        stats[name] = {
            "n_calls": len(calls),
            "min_elapsed": min(elapsed_list),
            "max_elapsed": max(elapsed_list),
            "mean_elapsed": sum(elapsed_list) / len(elapsed_list) if elapsed_list else 0,
            "total_elapsed": sum(elapsed_list),
        }

    # 时间窗口对齐检测干扰
    pairs = _detect_interference(worlds_data)

    # 生成报告
    lines = [
        "=" * 60,
        f"探针延迟分析报告",
        f"批次: {batch_dir.name}",
        f"成功 worlds: {len(worlds_data)}",
        "=" * 60,
        "",
        "── 各 World 延迟统计 ──",
        f"{'World':30s} {'Calls':>6s} {'Mean':>8s} {'Min':>8s} {'Max':>8s} {'Total':>8s}",
        f"{'─'*30} {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*8}",
    ]
    for name in sorted(stats):
        s = stats[name]
        lines.append(
            f"{name:30s} {s['n_calls']:6d} {s['mean_elapsed']:7.1f}s "
            f"{s['min_elapsed']:7.1f}s {s['max_elapsed']:7.1f}s {s['total_elapsed']:7.1f}s"
        )

    lines.extend([
        "",
        "── 并发干扰对（可能同算力池） ──",
    ])

    if pairs:
        for p in pairs:
            lines.append(
                f"  ⚡ {p['a']:30s} ↔ {p['b']:30s}  "
                f"冲突窗口: {p['conflicts']}  "
                f"延迟升高: {p.get('a_slowdown','?')} / {p.get('b_slowdown','?')}"
            )
    else:
        lines.append("  未检测到显著并发干扰。")

    lines.extend([
        "",
        "── 拓扑猜想 ──",
    ])

    # 分组：干扰对 → 同池
    pool_map = _infer_pools(pairs, list(worlds_data.keys()))
    seen_worlds = set()
    for pool_id, members in enumerate(pool_map):
        for m in members:
            seen_worlds.add(m)
        name_str = ", ".join(members)
        lines.append(f"  池 #{pool_id + 1}: {name_str}")
    standalone = [w for w in worlds_data if w not in seen_worlds]
    if standalone:
        lines.append(f"  独立（可能独占池）: {', '.join(standalone)}")

    lines.append("")
    report = "\n".join(lines)
    return report


def _detect_interference(
    worlds_data: dict[str, list[dict]],
) -> list[dict]:
    """
    检测并发干扰对。

    对每对 world，看它们的请求时间窗口是否存在重叠，
    以及重叠时的延迟是否比非重叠时高。
    简化版：只看请求数量（同时跑说明是并发→可能同池争抢）。
    """
    # 计算每个 world 的请求时间范围
    ranges: dict[str, Tuple[float, float]] = {}
    for name, calls in worlds_data.items():
        if not calls:
            continue
        timestamps = [
            _parse_ts(c.get("timestamp", "")) for c in calls
        ]
        timestamps = [t for t in timestamps if t is not None]
        if timestamps:
            ranges[name] = (min(timestamps), max(timestamps))

    # 对每对 world，计算范围重叠程度
    pairs = []
    names = sorted(ranges.keys())
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            a_start, a_end = ranges[a]
            b_start, b_end = ranges[b]
            overlap_start = max(a_start, b_start)
            overlap_end = min(a_end, b_end)
            overlap = max(0, overlap_end - overlap_start)
            if overlap > 0:
                pairs.append({
                    "a": a,
                    "b": b,
                    "conflicts": f"{overlap:.0f}s",
                    "a_slowdown": "?",
                    "b_slowdown": "?",
                })
    return pairs


def _parse_ts(ts: str) -> float | None:
    """解析 ISO 时间戳为 Unix 时间戳。"""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(ts)
        return dt.timestamp()
    except (ValueError, AttributeError):
        return None


def _infer_pools(
    pairs: list[dict], all_worlds: list[str],
) -> list[list[str]]:
    """
    用简单的分组算法：干扰对视为同池。
    把有交叠干扰的 world 归为一组。
    """
    # 建图
    graph: dict[str, set] = {w: set() for w in all_worlds}
    for p in pairs:
        graph[p["a"]].add(p["b"])
        graph[p["b"]].add(p["a"])

    # BFS 找连通分量
    visited = set()
    pools = []
    for w in all_worlds:
        if w in visited:
            continue
        pool = []
        stack = [w]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            pool.append(node)
            stack.extend(graph[node] - visited)
        if len(pool) > 1 or (len(pool) == 1 and graph[pool[0]]):
            pools.append(pool)
        elif len(pool) == 1:
            pools.append(pool)

    return pools
