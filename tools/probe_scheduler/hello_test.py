#!/usr/bin/env python3
"""Quick hello test — 5 个候选模型各发一条 hi，确认存活。"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 跟 config.py 一致的方式加载 .env
from dotenv import load_dotenv
load_dotenv()

# 内网 endpoint 绕过代理（同 LLMClient 行为）
if "100.89.3.59" in (os.environ.get("LLM_BASE_URL", "http://100.89.3.59:8090/v1")):
    existing = os.environ.get("NO_PROXY", "")
    if "100.89.3.59" not in existing:
        os.environ["NO_PROXY"] = f"100.89.3.59,localhost,127.0.0.1,{existing}"
        os.environ["no_proxy"] = os.environ["NO_PROXY"]

BASE_URL = os.environ.get("LLM_BASE_URL", "http://100.89.3.59:8090/v1")
API_KEY = os.environ.get("LLM_API_KEY", "")

CANDIDATES = [
    ("qwen36-35b",        "当前主力"),
    ("qwen3-80b-tke",     "Qwen 80B 对照"),
    ("deepseek-v4f",      "DeepSeek v4 Flash"),
    ("ds",                "DeepSeek 基础版"),
    ("minimax",           "MiniMax"),
]

def hello(model: str) -> dict:
    """发一条最简单请求，返回耗时和状态。"""
    import httpx
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10,
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}
    t0 = time.perf_counter()
    try:
        resp = httpx.post(
            f"{BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=30,
        )
        elapsed = time.perf_counter() - t0
        if resp.status_code == 200:
            data = resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            # 兼容推理模型：content 可能为空，内容在 reasoning_content 或 reasoning
            content = msg.get("content") or msg.get("reasoning_content") or msg.get("reasoning", "")
            text = content[:60] if content else "(空响应)"
            return {"status": "✓", "elapsed": elapsed, "response": text}
        else:
            return {"status": "✗", "elapsed": elapsed, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return {"status": "✗", "elapsed": elapsed, "error": str(e)[:60]}

def main():
    print(f"内网端点: {BASE_URL}")
    print(f"测试时间: {datetime.now().strftime('%H:%M:%S')}")
    print()
    print(f"{'模型':25s} {'状态':4s} {'耗时':8s} {'响应/错误'}")
    print(f"{'─'*25} {'─'*4} {'─'*8} {'─'*40}")

    all_ok = True
    for model, note in CANDIDATES:
        label = f"{model} ({note})"
        r = hello(model)
        elapsed_str = f"{r['elapsed']:.2f}s" if r['elapsed'] < 60 else f"{r['elapsed']:.0f}s"
        detail = r.get("response") or r.get("error", "?")
        icon = {"✓": "✅", "✗": "❌"}.get(r["status"], "?")
        print(f"  {icon} {label:35s} {r['status']:4s} {elapsed_str:8s} {detail}")
        if r["status"] != "✓":
            all_ok = False

    print()
    if all_ok:
        print("✅ 全部存活，可以跑探针。")
    else:
        print("⚠  有模型不可用，建议先换掉再跑探针。")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
