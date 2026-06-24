#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI entry for `python -m adarian`.

Subcommands:
  run      — 单次 pipeline 执行
  serve    — 启动 Web 控制台
  batch    — 多模型并行推演
  inspect  — 检查已有 batch 产物
  dev      — 一键启动 Web + 跑 pipeline
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main():
    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    parser = argparse.ArgumentParser(
        description="Adarian — 平行世界舆情推演系统",
    )
    sub = parser.add_subparsers(dest="command")

    # run
    run_p = sub.add_parser("run", help="单次 pipeline 执行")
    run_p.add_argument("seed", nargs="?", default="seeds/test8.txt",
                       help="种子文件路径（默认: seeds/test8.txt）")

    # serve
    serve_p = sub.add_parser("serve", help="启动 Web 控制台")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=9788)
    serve_p.add_argument("--open-browser", action="store_true",
                         help="启动后用浏览器打开 URL")

    # batch
    batch_p = sub.add_parser("batch", help="多模型并行推演")
    batch_p.add_argument("--models", required=True,
                         help="逗号分隔模型名，如 qwen36-35b,ds")
    batch_p.add_argument("--seed-text", default="", help="直接传入舆情事件文本")
    batch_p.add_argument("--seed-path", default="", help="种子文件路径")
    batch_p.add_argument("--tag", default="batch", help="batch 标签")
    batch_p.add_argument("--max-concurrent", type=int, default=None)

    # inspect
    inspect_p = sub.add_parser("inspect", help="检查已有 batch 产物")
    inspect_p.add_argument("batch_dir", help="batch 目录路径")

    # dev
    dev_p = sub.add_parser("dev", help="一键启动 Web 控制台 + 跑 pipeline")
    dev_p.add_argument("seed", nargs="?", default="seeds/test8.txt",
                       help="种子文件路径（默认: seeds/test8.txt）")
    dev_p.add_argument("--host", default="127.0.0.1")
    dev_p.add_argument("--port", type=int, default=9788)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    if args.command == "run":
        _run(args)
    elif args.command == "serve":
        _serve(args)
    elif args.command == "batch":
        _batch(args)
    elif args.command == "inspect":
        _inspect(args)
    elif args.command == "dev":
        _dev(args)


def _run(args):
    from adarian.run import run_pipeline
    run_pipeline(args.seed)


def _serve(args):
    from adarian.serve import run
    run(host=args.host, port=args.port, open_browser=args.open_browser)


def _batch(args):
    from adarian.batch import run_batch
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    session = run_batch(
        models=models,
        seed_text=args.seed_text,
        seed_path=args.seed_path,
        tag=args.tag,
        max_concurrent=args.max_concurrent,
    )
    print(json.dumps(session.as_dict(), ensure_ascii=False, indent=2))


def _inspect(args):
    from adarian.inspect import inspect_batch
    print(json.dumps(inspect_batch(args.batch_dir), ensure_ascii=False, indent=2))


def _dev(args):
    """Start Web UI in background + run a pipeline."""
    from adarian.serve import run as serve_run
    from adarian.run import run_pipeline

    url = f"http://{args.host}:{args.port}"
    print(f"╔══════════════════════════════════════════╗")
    print(f"║  Adarian Dev Mode                        ║")
    print(f"║  Web UI: {url:<33s}║")
    print(f"║  Pipeline: {args.seed:<30s}║")
    print(f"╚══════════════════════════════════════════╝")
    print()

    # Start serve in background thread
    server_thread = threading.Thread(
        target=serve_run,
        args=(args.host, args.port),
        daemon=True,
    )
    server_thread.start()
    time.sleep(0.5)  # brief pause for server to start

    # Run pipeline
    run_pipeline(args.seed)


if __name__ == "__main__":
    main()
