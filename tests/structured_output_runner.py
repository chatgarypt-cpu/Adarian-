#!/usr/bin/env python3
"""
结构化输出路径实验 — 直接复制 Generator 原函数，只换 LLM 调用。

每个方案：copy generator_create_event_entities()，只替换 llm.generate() → 直调 API + 额外参数。
10 次 × 3 重试（同 orchestrator），记录单次成功率 vs 重试后成功率。
"""

import json
import os
import re
import shlex
import subprocess
import sys
import time
import requests
from typing import Any, Dict, List, Optional
from pathlib import Path

# ── 非 TTY → 开 Terminal 窗口 ──
if not sys.stdout.isatty():
    _sp = Path(__file__).resolve()
    _wd = _sp.parent.parent
    _py = _wd / ".venv" / "bin" / "python"
    subprocess.run([
        "osascript", "-e", 'tell application "Terminal" to activate',
        "-e", f'tell application "Terminal" to do script "cd {shlex.quote(str(_wd))} && {shlex.quote(str(_py))} {shlex.quote(str(_sp))}"',
    ])
    sys.exit(0)

# ── TTY ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["NO_PROXY"] = "localhost"
os.environ["no_proxy"] = "localhost"

from adarian.config import LLM_API_KEY, LLM_BASE_URL
from adarian.phase1.prompts import GENERATOR_SYSTEM_PROMPT, GENERATOR_USER_PROMPT
from adarian.phase1.utils import _parse_llm_json_payload, _coerce_top_level_object, console
from adarian.phase1.compiler import _post_process_entities

HEADERS = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
NO_PROXY = {"http": None, "https": None}
MAX_RETRIES = 3

SEED_PATH = PROJECT_ROOT / "seeds" / "test8.txt"
SEED_TEXT = SEED_PATH.read_text(encoding="utf-8").strip()
EVENT_SCALE = 0.7
EVENT_CONTROVERSY = 0.8
EVENT_TYPE = "产品质量问题"
EVENT_SUMMARY = "OPPO母亲节广告文案被指低俗营销，引发品牌公关危机"


# ── 思维链清洗（同 LLMClient._strip_think_block）──
def _strip_think_block(content: str) -> str:
    if not content:
        return ""
    if content.startswith(":react") or content.startswith(":React"):
        lines = content.split("\n", 2)
        if len(lines) >= 3:
            content = lines[2]
    content = re.sub(r'<think>[\s\S]*?</think>', '', content)
    content = re.sub(r'<!--[\s\S]*?-->', '', content)
    return content.strip()


# ── Generator 原函数，只换 llm.generate() → 直调 API ──
def _call_llm(system: str, user: str, extra_params: Optional[Dict] = None) -> str:
    """替换 llm.generate()：直调 API + 思维链清洗"""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    payload = {
        "model": "qwen36-35b",
        "messages": messages,
        "max_tokens": 8192,
        "temperature": 0.7,
    }
    if extra_params:
        payload.update(extra_params)

    resp = requests.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers=HEADERS, json=payload, timeout=120, proxies=NO_PROXY,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"API error {resp.status_code}: {resp.text[:200]}")

    rd = resp.json()
    msg = rd["choices"][0].get("message", {})
    content = msg.get("content") or msg.get("reasoning_content") or ""
    return _strip_think_block(content)


# ── 复制 generator_create_event_entities，只换 LLM 调用 ──
def _raw_generator(seed_text, event_scale, event_controversy, event_type,
                   event_summary, error_feedback="", extra_params=None) -> Dict[str, Any]:
    """完全复刻 Generator，替换 llm.generate → 直调"""
    user_prompt = GENERATOR_USER_PROMPT.format(
        seed_text=seed_text, event_scale=event_scale,
        event_controversy=event_controversy, event_type=event_type,
        event_summary=event_summary, error_feedback=error_feedback,
    )
    result = _call_llm(GENERATOR_SYSTEM_PROMPT, user_prompt, extra_params)
    try:
        entities_data = _coerce_top_level_object(_parse_llm_json_payload(result), "Test")
    except (json.JSONDecodeError, ValueError, SyntaxError, TypeError) as e:
        raise ValueError(f"JSON 解析失败: {e}\n原始: {result[:200]}")
    entities_data = _post_process_entities(entities_data, seed_text)
    return entities_data


# ── 运行方案 ──
def run_approach(name: str, extra_params: Optional[Dict] = None, n: int = 10):
    print(f"\n{'='*65}")
    print(f"  [{name}]")
    print(f"{'='*65}")
    results = []

    for i in range(n):
        error_feedback = ""
        ok = False
        for attempt in range(MAX_RETRIES):
            try:
                t0 = time.perf_counter()
                data = _raw_generator(
                    SEED_TEXT, EVENT_SCALE, EVENT_CONTROVERSY,
                    EVENT_TYPE, EVENT_SUMMARY,
                    error_feedback=error_feedback,
                    extra_params=extra_params,
                )
                elapsed = time.perf_counter() - t0
                ec = len(data.get("event_entities", []))
                sc = len(data.get("opinion_spreaders", []))
                retry_mark = f" (retry {attempt})" if attempt > 0 else ""
                print(f"  ✓ [{i+1}/{n}]{retry_mark} entities={ec} spreaders={sc} ({elapsed:.1f}s)")
                results.append({"ok": True, "retries": attempt, "entities": ec, "spreaders": sc})
                ok = True
                break
            except Exception as e:
                print(f"  ⚠ [{i+1}/{n}] attempt {attempt+1}: {str(e)[:100]}")
                error_feedback = f"上一轮输出未能解析为合法 JSON。请严格输出单个 JSON object。\n- {e}"
                continue

        if not ok:
            print(f"  ✗ [{i+1}/{n}] 全部 {MAX_RETRIES} 次失败")
            results.append({"ok": False})

    total = len(results)
    ok_count = sum(1 for r in results if r["ok"])
    retry_total = sum(r["retries"] for r in results if r.get("ok"))
    entity_total = sum(r["entities"] for r in results if r.get("ok"))
    spreader_total = sum(r["spreaders"] for r in results if r.get("ok"))
    print(f"\n  ── {name} 汇总 ──")
    print(f"  成功率: {ok_count}/{total}")
    print(f"  总重试: {retry_total}")
    print(f"  平均实体: {entity_total/max(ok_count,1):.1f}  平均传播者: {spreader_total/max(ok_count,1):.1f}")
    return {"ok": ok_count, "total": total, "retries": retry_total}


def main():
    print("=" * 65)
    print("  结构化输出路径实验")
    print(f"  Model: qwen36-35b  |  Seed: test8.txt  |  n=10  |  MAX_RETRIES={MAX_RETRIES}")
    print("=" * 65)

    s1 = run_approach("1-baseline (无额外参数)")
    s2 = run_approach("2-json_object", {"response_format": {"type": "json_object"}})
    s3 = run_approach("3-json_schema", {
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "entity_output",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "event_entities": {"type": "array", "items": {"type": "object"}},
                        "opinion_spreaders": {"type": "array", "items": {"type": "object"}},
                        "relations": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": ["event_entities", "opinion_spreaders", "relations"],
                },
            },
        },
    })
    s4 = run_approach("4-guided_json", {
        "guided_json": {
            "type": "object",
            "properties": {
                "event_entities": {"type": "array", "items": {"type": "object"}},
                "opinion_spreaders": {"type": "array", "items": {"type": "object"}},
                "relations": {"type": "array", "items": {"type": "object"}},
            },
        },
    })

    print(f"\n{'='*65}")
    print(f"  ★ 最终对比")
    print(f"{'='*65}")
    print(f"{'方案':<25} {'成功':>6} {'重试':>6}")
    print(f"{'─'*25} {'─'*6} {'─'*6}")
    for name, s in [("1-baseline", s1), ("2-json_object", s2),
                     ("3-json_schema", s3), ("4-guided_json", s4)]:
        print(f"{name:<25} {s['ok']:>3}/{s['total']:<2} {s['retries']:>6}")
    print()


if __name__ == "__main__":
    main()
