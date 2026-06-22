#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTTP backend for Adarian Parallel World Console R0."""

from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .run import (
    DEFAULT_BASE_URL,
    BatchSession,
    available_models,
    execute_session,
    inspect_batch,
    start_batch,
)


_SESSIONS: dict[str, BatchSession] = {}
_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def _json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _hello_one(model: str, timeout: float = 20.0) -> dict:
    """Small OpenAI-compatible health check for one model."""

    try:
        import httpx
    except Exception as exc:
        return {"status": "fail", "elapsed": 0, "error": f"httpx unavailable: {exc}"}

    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.environ.get("LLM_API_KEY", "")
    if "100.89.3.59" in base_url:
        no_proxy = os.environ.get("NO_PROXY", "")
        merged = ",".join(["100.89.3.59", "localhost", "127.0.0.1", no_proxy]).strip(",")
        os.environ["NO_PROXY"] = merged
        os.environ["no_proxy"] = merged

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    t0 = time.perf_counter()
    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        elapsed = round(time.perf_counter() - t0, 2)
        if resp.status_code == 200:
            data = resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning_content") or ""
            return {"status": "ok", "elapsed": elapsed, "response": content[:80]}
        return {
            "status": "fail",
            "elapsed": elapsed,
            "error": f"HTTP {resp.status_code}: {resp.text[:140]}",
        }
    except httpx.TimeoutException:
        return {"status": "fail", "elapsed": round(time.perf_counter() - t0, 2), "error": "timeout"}
    except httpx.ConnectError as exc:
        return {
            "status": "fail",
            "elapsed": round(time.perf_counter() - t0, 2),
            "error": f"connect: {str(exc)[:120]}",
        }
    except Exception as exc:
        return {"status": "fail", "elapsed": round(time.perf_counter() - t0, 2), "error": str(exc)[:160]}


class ConfigUIHandler(BaseHTTPRequestHandler):
    """Minimal stdlib HTTP handler for the console."""

    def log_message(self, fmt, *args):
        return

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/models":
            self._send_json(200, available_models())
            return

        if parsed.path == "/api/session":
            params = parse_qs(parsed.query)
            batch_dir = params.get("dir", [""])[0]
            if not batch_dir:
                self._send_json(400, {"error": "dir required"})
                return
            session = _SESSIONS.get(batch_dir)
            if session:
                self._send_json(200, session.as_dict())
                return
            self._send_json(200, inspect_batch(batch_dir))
            return

        if parsed.path == "/api/log":
            params = parse_qs(parsed.query)
            batch_dir = params.get("dir", [""])[0]
            world = params.get("world", [""])[0]
            if not batch_dir or not world:
                self._send_json(400, {"error": "dir and world required"})
                return
            log_path = Path(batch_dir) / world / "run.log"
            if not log_path.exists():
                self._send_json(404, {"error": "run.log not found"})
                return
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            self._send_json(200, {"log": "\n".join(lines[-80:])})
            return

        self._serve_html()

    def do_POST(self):
        try:
            body = _json_body(self)
        except json.JSONDecodeError as exc:
            self._send_json(400, {"error": f"invalid json: {exc}"})
            return

        if self.path == "/api/hello-test":
            model = body.get("model", "")
            if not model:
                self._send_json(400, {"error": "model required"})
                return
            self._send_json(200, _hello_one(model))
            return

        if self.path == "/api/launch":
            self._handle_launch(body)
            return

        self._send_json(404, {"error": "not found"})

    def _handle_launch(self, body: dict) -> None:
        models = [str(item).strip() for item in body.get("models", []) if str(item).strip()]
        if not models:
            self._send_json(400, {"error": "至少选择 1 个模型"})
            return
        try:
            session = start_batch(
                models=models,
                seed_text=str(body.get("seed_text", "")),
                seed_path=str(body.get("seed_path", "")),
                tag=str(body.get("tag", "batch")),
                base_url=str(body.get("base_url", DEFAULT_BASE_URL) or DEFAULT_BASE_URL),
            )
        except Exception as exc:
            self._send_json(400, {"error": str(exc)})
            return

        _SESSIONS[str(session.batch_dir)] = session
        _POOL.submit(execute_session, session)
        self._send_json(
            200,
            {
                "status": "launched",
                "batch_id": session.batch_id,
                "batch_dir": str(session.batch_dir),
                "worlds": [world.as_dict() for world in session.worlds],
                "report_agent_consumer": session.as_dict()["report_agent_consumer"],
            },
        )

    def _serve_html(self):
        path = Path(__file__).with_name("config_ui.html")
        if not path.exists():
            self._send_text(404, "config_ui.html not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def _send_json(self, code: int, data: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_text(self, code: int, text: str):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def run(host: str = "127.0.0.1", port: int = 9788, open_browser: bool = False) -> None:
    server = HTTPServer((host, port), ConfigUIHandler)
    url = f"http://{host}:{port}"
    print(f"Adarian Parallel World Console: {url}", flush=True)
    if open_browser:
        try:
            subprocess.Popen(["open", url])
        except OSError:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nserver stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
