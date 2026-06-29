#!/usr/bin/env python3
"""
Adarian Structured Output Pathfinder — 试验场

测试 Qwen 集群不同 endpoint 能力，找到可靠 JSON 输出的最佳路径。
"""

import requests
import json
import sys
import os
import time
from typing import Optional

# ── 加载配置 ──
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["NO_PROXY"] = "localhost"
os.environ["no_proxy"] = "localhost"

from adarian.config import LLM_API_KEY, LLM_BASE_URL

HEADERS = {
    "Authorization": f"Bearer {LLM_API_KEY}",
    "Content-Type": "application/json",
}
NO_PROXY = {"http": None, "https": None}

# ── 简单测试 Schema ──
SIMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "score": {"type": "integer", "minimum": 1, "maximum": 10},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5}
    },
    "required": ["name", "score", "tags"],
    "additionalProperties": False
}

# ── Adarian Entity Schema（简化版，模拟实际 Generator 输出）──
ENTITY_SCHEMA = {
    "type": "object",
    "properties": {
        "entities_and_relations": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "entity_type": {"type": "string"},
                            "attributes": {"type": "object"},
                        },
                        "required": ["name", "entity_type"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["entities"],
            "additionalProperties": False
        }
    },
    "required": ["entities_and_relations"],
    "additionalProperties": False
}


def call_llm(model: str, messages: list, extra: dict = None) -> dict:
    """发送请求到 Qwen endpoint"""
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": 512,
        **(extra or {}),
    }
    start = time.time()
    r = requests.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers=HEADERS,
        json=body,
        timeout=60,
        proxies=NO_PROXY,
    )
    elapsed = time.time() - start
    resp = r.json()
    return {"response": resp, "elapsed": elapsed, "status": r.status_code}


def extract_content(resp: dict) -> tuple:
    """从响应中提取 content 和 reasoning，返回 (content, reasoning, success)"""
    r = resp["response"]
    if resp["status"] != 200:
        return (None, None, False, f"HTTP {resp['status']}: {r.get('error', {}).get('message', '')}")
    choices = r.get("choices", [])
    if not choices:
        return (None, None, False, "No choices in response")
    msg = choices[0].get("message", {})
    content = msg.get("content", "")
    reasoning = msg.get("reasoning_content") or msg.get("reasoning", "")
    return (content, reasoning, True, "")


def test_json_mode(model: str) -> dict:
    """Test 1: response_format=json_object"""
    prompt = "Return a JSON object with fields: name (string), score (integer 1-10), tags (array of strings, 2-3 items). No other text."
    resp = call_llm(model, [
        {"role": "system", "content": "You are a JSON-only assistant. Always output valid JSON."},
        {"role": "user", "content": prompt},
    ], extra={"response_format": {"type": "json_object"}})
    return {"approach": "json_object", **resp}


def test_json_schema(model: str) -> dict:
    """Test 2: response_format with json_schema (vLLM structured output style)"""
    prompt = "Return data matching the schema."
    resp = call_llm(model, [
        {"role": "system", "content": "You are a JSON-only assistant."},
        {"role": "user", "content": prompt},
    ], extra={
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "test_output",
                "schema": SIMPLE_SCHEMA,
                "strict": True,
            }
        }
    })
    return {"approach": "json_schema", **resp}


def test_guided_json(model: str) -> dict:
    """Test 3: guided_json (vLLM native parameter)"""
    prompt = "Return data matching the schema."
    resp = call_llm(model, [
        {"role": "system", "content": "You are a JSON-only assistant."},
        {"role": "user", "content": prompt},
    ], extra={"guided_json": SIMPLE_SCHEMA})
    return {"approach": "guided_json", **resp}


def test_tool_call(model: str) -> dict:
    """Test 4: Function calling / tools (OpenAI-compatible)"""
    prompt = "Return an object with name, score, and tags."
    resp = call_llm(model, [
        {"role": "user", "content": prompt},
    ], extra={
        "tools": [{
            "type": "function",
            "function": {
                "name": "output_data",
                "description": "Output structured data",
                "parameters": SIMPLE_SCHEMA,
            }
        }],
        "tool_choice": {"type": "function", "function": {"name": "output_data"}},
    })
    return {"approach": "tool_call", **resp}


def test_prompt_only(model: str) -> dict:
    """Test 5: Baseline — just prompt engineering, nothing else"""
    prompt = """You must output ONLY valid JSON. No explanations, no markdown, no other text.
Follow this exact structure:
{
  "name": "<string>",
  "score": <integer between 1-10>,
  "tags": ["<string>", "<string>"]
}
Return a JSON object with a name (like 'test_result'), score (like 8), and tags (like ['fast', 'reliable'])."""
    resp = call_llm(model, [
        {"role": "system", "content": "You are a JSON-only assistant. Output ONLY valid JSON objects, nothing else."},
        {"role": "user", "content": prompt},
    ])
    return {"approach": "prompt_only", **resp}


def try_extract_json(raw: str) -> Optional[dict]:
    """Try multiple strategies to extract JSON from text"""
    if not raw:
        return None
    # Strategy 1: Direct parse
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    # Strategy 2: Find JSON block
    import re
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    # Strategy 3: Find code block
    m = re.search(r'```(?:json)?\n(.*?)\n```', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return None


def validate_simple_schema(data: dict) -> tuple:
    """Validate against SIMPLE_SCHEMA"""
    if not isinstance(data, dict):
        return (False, "Not a dict")
    errors = []
    for field in ["name", "score", "tags"]:
        if field not in data:
            errors.append(f"Missing '{field}'")
    if "name" in data and not isinstance(data["name"], str):
        errors.append("name not string")
    if "score" in data and not isinstance(data["score"], int):
        errors.append("score not integer")
    if "tags" in data:
        if not isinstance(data["tags"], list):
            errors.append("tags not array")
        elif any(not isinstance(t, str) for t in data["tags"]):
            errors.append("tags items not strings")
    return (len(errors) == 0, "; ".join(errors) if errors else "OK")


def run_suite(model: str, name: str):
    """Run all tests for a given model and approach"""
    tests = [
        test_json_mode,
        test_json_schema,
        test_guided_json,
        test_tool_call,
        test_prompt_only,
    ]

    print(f"\n{'='*60}")
    print(f"  Model: {model}  ({name})")
    print(f"{'='*60}")

    viable = []

    for test_fn in tests:
        approach = test_fn.__name__.replace("test_", "")
        result = test_fn(model)
        content, reasoning, ok, err = extract_content(result)

        # Show approach
        approach_name = result["approach"]
        status_icon = "✓" if ok else "✗"
        print(f"\n  [{status_icon}] {approach_name} ({result['elapsed']:.1f}s)")

        if not ok:
            print(f"       Error: {err}")
            continue

        # Try to extract JSON
        parsed = try_extract_json(content) if content else None
        if parsed:
            valid, msg = validate_simple_schema(parsed)
            print(f"       Content: {json.dumps(parsed, ensure_ascii=False)[:100]}")
            print(f"       Valid: {valid} — {msg}")
            if valid:
                viable.append(approach_name)
        else:
            # Show raw content (first 150 chars)
            raw = (content or "(empty)")[:150]
            print(f"       Raw: {raw}")
            if reasoning:
                print(f"       Reasoning: {str(reasoning)[:100]}...")

    return viable


def discover_models():
    """Discover available models and their capabilities"""
    r = requests.get(f"{LLM_BASE_URL}/models", headers=HEADERS, timeout=10, proxies=NO_PROXY)
    models = [m["id"] for m in r.json()["data"]]
    return models


def main():
    models = discover_models()
    print(f"Found {len(models)} models:")
    for m in models:
        print(f"  - {m}")

    # Test key models
    test_models = []
    for target in ["qwen36-35b", "qwen3-32b-tke", "qwen3-30b-tke"]:
        if target in models:
            test_models.append(target)

    if not test_models:
        print("\n⚠️  None of target models found! Testing first 3 available.")
        test_models = models[:3]

    all_viable = {}
    for m in test_models:
        viable = run_suite(m, "Adarian Qwen cluster")
        all_viable[m] = viable

    print(f"\n{'='*60}")
    print("  Summary: Viable Approaches")
    print(f"{'='*60}")
    for model, approaches in all_viable.items():
        if approaches:
            print(f"  ✓ {model}: {', '.join(approaches)}")
        else:
            print(f"  ✗ {model}: No viable approach found")


if __name__ == "__main__":
    main()
