#!/usr/bin/env python3
"""
config_ui.py — HTTP 后端，为平行世界调度器提供配置 UI + 运行监控。
零外部依赖（stdlib only）。

Endpoints:
  GET  /api/models          — 可用模型列表
  POST /api/hello-test      — 对单个模型发 hello
  POST /api/hello-test-all  — 批量 hello
  POST /api/launch          — 启动调度器（记录 session）
  GET  /api/session?dir=... — 查询 session 下各 world 状态
  GET  /api/session/log?dir=...&world=...&lines=30 — world 的 run.log 尾部
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ── 项目路径 ──────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── 加载 .env（同 hello_test.py） ─────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── 内网 endpoint 绕过代理（同 LLMClient 行为） ──────────────────
_BASE_URL = os.environ.get("LLM_BASE_URL", "http://100.89.3.59:8090/v1")
if "100.89.3.59" in _BASE_URL:
    existing = os.environ.get("NO_PROXY", "")
    if "100.89.3.59" not in existing:
        combined = f"100.89.3.59,localhost,127.0.0.1,{existing}".strip(",")
        os.environ["NO_PROXY"] = combined
        os.environ["no_proxy"] = combined

_API_KEY = os.environ.get("LLM_API_KEY", "")

# ── 引用项目模块 ──────────────────────────────────────────────────
from src.model_router import CATALOG
from tools.probe_scheduler.probe_config import ProbeConfig, WorldConfig
from tools.probe_scheduler.scheduler import run_probe

_OUTPUTS_DIR = _PROJECT_ROOT / "outputs" / "runs"


# ── Session store ─────────────────────────────────────────────────
_sessions: dict[str, dict] = {}
"""batch_dir -> {worlds: [{name, model, label}], launched_at, batch_tag}"""


# ── Helpers ───────────────────────────────────────────────────────

def _available_models() -> dict[str, str]:
    """从 CATALOG 过滤掉不可用和不必要的模型。"""
    exclude = {
        "bge-m3",           # embedding
        "bge-m3-tke",       # embedding
        "deepseek-v4-flash",  # 外网 fallback
    }
    return {
        k: v for k, v in CATALOG.items()
        if "❌" not in v and k not in exclude
    }


def _hello_one(model: str, timeout: float = 25.0) -> dict:
    """对单个模型发 hi，返回耗时和状态。"""
    import httpx
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10,
    }
    headers = {"Authorization": f"Bearer {_API_KEY}"}
    t0 = time.perf_counter()
    try:
        resp = httpx.post(
            f"{_BASE_URL}/chat/completions",
            json=payload, headers=headers, timeout=timeout,
        )
        elapsed = round(time.perf_counter() - t0, 2)
        if resp.status_code == 200:
            data = resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning_content") or ""
            return {"status": "ok", "elapsed": elapsed, "response": content[:60]}
        else:
            err_body = resp.text[:100] if resp.text else ""
            return {"status": "fail", "elapsed": elapsed, "error": f"HTTP {resp.status_code}: {err_body}"}
    except httpx.TimeoutException:
        elapsed = round(time.perf_counter() - t0, 2)
        return {"status": "fail", "elapsed": elapsed, "error": "timeout"}
    except httpx.ConnectError as e:
        elapsed = round(time.perf_counter() - t0, 2)
        return {"status": "fail", "elapsed": elapsed, "error": f"connect: {str(e)[:50]}"}
    except Exception as e:
        elapsed = round(time.perf_counter() - t0, 2)
        return {"status": "fail", "elapsed": elapsed, "error": str(e)[:60]}


# ── 监控：读 world 状态 ───────────────────────────────────────────

def _read_world_status(world_dir: Path) -> dict:
    """从 world 目录读取状态（model, 耗时, 日志尾部, 错误）。"""
    result = {"status": "running", "elapsed": None, "model": "", "error": None, "run_log": ""}

    # 读 run_meta.json → model + status
    meta = world_dir / "run_meta.json"
    if meta.exists():
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
            result["model"] = m.get("model", "")
            if m.get("status") == "success":
                result["status"] = "completed"
            elif m.get("status") == "failed":
                result["status"] = "failed"
        except (json.JSONDecodeError, OSError):
            pass

    # 读 run.log → 错误信息 + 耗时
    log = world_dir / "run.log"
    if log.exists():
        try:
            text = log.read_text(encoding="utf-8")
            result["run_log"] = text

            # 提取错误行
            for line in text.splitlines():
                if "ERROR" in line or "failed" in line or "error=" in line:
                    result["error"] = line.strip()

            # 提取耗时
            m = re.search(r"总耗时:\s*([\d.]+)s", text)
            if m:
                result["elapsed"] = float(m.group(1))
            m = re.search(r"elapsed=([\d.]+)s", text)
            if m:
                result["elapsed"] = float(m.group(1))
        except OSError:
            pass

    return result


def _find_run_dir_for_world(world_index: int, launched_at: float) -> Path | None:
    """按创建顺序分配：第 N 个在 launch 后新建的 run 目录 = world_N。"""
    today_str = datetime.fromtimestamp(launched_at).strftime("%Y-%m-%d")
    today_dir = _OUTPUTS_DIR / today_str
    if not today_dir.exists():
        return None

    dirs = []
    for batch in today_dir.iterdir():
        if not batch.is_dir():
            continue
        for run in batch.iterdir():
            if not run.is_dir():
                continue
            created = run.stat().st_mtime
            if created > launched_at - 60:
                dirs.append((created, run))

    dirs.sort(key=lambda x: x[0])  # 时间升序
    if world_index < len(dirs):
        return dirs[world_index][1]
    return None


def _resolve_world_status(batch_dir_str: str, world_info: dict, launched_at: float, world_index: int) -> dict:
    """找到 world 的输出目录并读取状态。"""
    batch_dir = Path(batch_dir_str)
    wname = world_info["name"]

    # 优先：batch_dir/world_N/
    world_dir = batch_dir / wname
    if world_dir.exists():
        status = _read_world_status(world_dir)
        status["dir"] = str(world_dir)
        return status

    # 兜底：按创建顺序分配
    orphan = _find_run_dir_for_world(world_index, launched_at)
    if orphan:
        status = _read_world_status(orphan)
        status["dir"] = str(orphan)
        return status

    return {"status": "pending", "elapsed": None, "model": world_info["model"], "error": None, "run_log": "", "dir": ""}


# ── Session 管理 ──────────────────────────────────────────────────

def _register_session(batch_dir: str, worlds: list[dict], batch_tag: str):
    _sessions[batch_dir] = {
        "batch_dir": batch_dir,
        "batch_tag": batch_tag,
        "worlds": worlds,
        "launched_at": time.time(),
    }


def _get_session_status(batch_dir: str) -> dict | None:
    sess = _sessions.get(batch_dir)
    if not sess:
        return None

    worlds_status = []
    for i, w in enumerate(sess["worlds"]):
        ws = _resolve_world_status(batch_dir, w, sess["launched_at"], i)
        ws["name"] = w["name"]
        ws["model"] = w["model"]
        ws["label"] = w.get("label", w["model"])
        worlds_status.append(ws)

    n = len(worlds_status)
    completed = sum(1 for w in worlds_status if w["status"] == "completed")
    failed = sum(1 for w in worlds_status if w["status"] == "failed")
    running = sum(1 for w in worlds_status if w["status"] == "running")
    pending = sum(1 for w in worlds_status if w["status"] == "pending")

    return {
        "batch_dir": batch_dir,
        "batch_tag": sess["batch_tag"],
        "launched_at": sess["launched_at"],
        "worlds": worlds_status,
        "summary": {
            "total": n,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
        },
    }


# ── HTTP Handler ──────────────────────────────────────────────────

class ConfigUIHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = self.path

        # /api/models
        if path == "/api/models":
            self._send_json(200, _available_models())
            return

        # /api/session?dir=...
        if path.startswith("/api/session"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(path).query)
            dir_val = qs.get("dir", [None])[0]
            if not dir_val:
                self._send_json(400, {"error": "?dir= 参数必填"})
                return
            status = _get_session_status(dir_val)
            if status is None:
                self._send_json(404, {"error": "session not found"})
                return
            self._send_json(200, status)
            return

        # /api/session/log?dir=...&world=...&lines=30
        if path.startswith("/api/session/log"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(path).query)
            dir_val = qs.get("dir", [None])[0]
            world = qs.get("world", [None])[0]
            lines = int(qs.get("lines", ["30"])[0])
            if not dir_val or not world:
                self._send_json(400, {"error": "?dir= + &world= 必填"})
                return
            log_path = Path(dir_val) / world / "run.log"
            if not log_path.exists():
                # 兜底：查 session 的 world model 匹配
                sess = _sessions.get(dir_val)
                if sess:
                    for i, w in enumerate(sess["worlds"]):
                        if w["name"] == world:
                            orphan = _find_run_dir_for_world(i, sess["launched_at"])
                            if orphan:
                                log_path = orphan / "run.log"
                            break
            if not log_path.exists():
                self._send_json(404, {"error": "run.log not found"})
                return
            try:
                text = log_path.read_text(encoding="utf-8")
                tail = "\n".join(text.splitlines()[-lines:])
                self._send_json(200, {"log": tail, "total_lines": len(text.splitlines())})
            except OSError as e:
                self._send_json(500, {"error": str(e)})
            return

        # 默认：静态 HTML
        self._serve_html()

    def _serve_html(self):
        html_path = Path(__file__).parent / "config_ui.html"
        if not html_path.exists():
            self._send_text(404, "config_ui.html not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(html_path.read_bytes())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        body = json.loads(raw) if raw else {}

        if self.path == "/api/hello-test":
            self._handle_hello(body)
        elif self.path == "/api/hello-test-all":
            self._handle_hello_all(body)
        elif self.path == "/api/launch":
            self._handle_launch(body)
        else:
            self._send_json(404, {"error": "not found"})

    def _handle_hello(self, body):
        model = body.get("model", "")
        if not model:
            self._send_json(400, {"error": "model required"})
            return
        print(f"[hello] {model} ...", flush=True)
        result = _hello_one(model)
        icon = "✓" if result["status"] == "ok" else "✗"
        print(f"[hello] {model} {icon} {result.get('elapsed','?')}s  {result.get('error','')}", flush=True)
        self._send_json(200, result)

    def _handle_hello_all(self, body):
        models = body.get("models", [])
        if not models:
            self._send_json(400, {"error": "models list required"})
            return
        results = {}
        for m in models:
            results[m] = _hello_one(m)
        self._send_json(200, results)

    def _handle_launch(self, body):
        models = body.get("models", [])
        if len(models) < 2:
            self._send_json(400, {"error": "至少选择 2 个模型"})
            return

        seed_path = body.get("seed", "seeds/test8.txt")
        batch_tag = body.get("tag", "parallel")

        worlds = []
        for i, m in enumerate(models):
            desc = CATALOG.get(m, m)
            worlds.append(WorldConfig(
                name=f"world_{i}",
                label=m,
                model=m,
                base_url=_BASE_URL,
                api_key_from_env="LLM_API_KEY",
                max_tokens=16384,
            ))

        cfg = ProbeConfig(
            worlds=worlds,
            seed_path=seed_path,
            batch_tag=batch_tag,
        )

        # 先算出 batch_dir，注册 session 再跑线程
        now = datetime.now()
        date_dir = now.strftime("%Y-%m-%d")
        batch_id = f"{cfg.batch_tag}_{now.strftime('%H%M%S')}"
        batch_dir = _OUTPUTS_DIR / date_dir / batch_id

        world_infos = [{"name": f"world_{i}", "model": m, "label": desc} for i, m in enumerate(models)]
        _register_session(str(batch_dir), world_infos, batch_tag)

        t = threading.Thread(target=run_probe, args=(cfg,), daemon=True)
        t.start()

        self._send_json(200, {
            "status": "launched",
            "worlds": len(worlds),
            "batch_tag": batch_tag,
            "batch_dir": str(batch_dir),
        })

    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_text(self, code, text):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))


def run(host="127.0.0.1", port=9788):
    server = HTTPServer((host, port), ConfigUIHandler)
    url = f"http://{host}:{port}"
    print(f"Config UI: {url}")
    import subprocess
    subprocess.Popen(["open", url])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n再见。")
        server.server_close()


if __name__ == "__main__":
    run()
