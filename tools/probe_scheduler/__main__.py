#!/usr/bin/env python3
"""
探针调度器 CLI 入口。

用法：
  python -m tools.probe_scheduler --help
  python -m tools.probe_scheduler run                    # 默认配置
  python -m tools.probe_scheduler run --config my.yaml   # 自定义配置
  python -m tools.probe_scheduler analyze 批次目录        # 分析已有探针
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="平行世界探针调度器 — 并发多模型模拟 + 算力池拓扑推断",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    run_p = sub.add_parser("run", help="执行一次探针运行")
    run_p.add_argument(
        "-c", "--config",
        default=str(Path(__file__).parent / "default_worlds.yaml"),
        help="YAML 配置路径 (默认: default_worlds.yaml)",
    )
    run_p.add_argument(
        "--tag", default=None,
        help="批次标签 (覆盖 YAML 中的 batch_tag)",
    )
    run_p.add_argument(
        "--worlds", default=None,
        help="只跑指定世界，逗号分隔 (如 world_0,world_2)",
    )

    # ui
    ui_p = sub.add_parser("ui", help="启动配置 UI（浏览器界面）")
    ui_p.add_argument(
        "--port", type=int, default=9788,
        help="HTTP 端口 (默认: 9788)",
    )
    ui_p.add_argument(
        "--host", default="127.0.0.1",
        help="监听地址 (默认: 127.0.0.1)",
    )

    # analyze
    ana_p = sub.add_parser("analyze", help="分析已有探针运行结果")
    ana_p.add_argument("batch_dir", help="探针批次目录路径")

    args = parser.parse_args()

    if args.command == "run":
        _do_run(args)
    elif args.command == "ui":
        _do_ui(args)
    elif args.command == "analyze":
        _do_analyze(args)


def _do_run(args):
    from .probe_config import ProbeConfig
    from .scheduler import run_probe

    cfg = ProbeConfig.from_yaml(args.config)

    # 覆盖
    if args.tag:
        cfg.batch_tag = args.tag
    if args.worlds:
        selected = set(args.worlds.split(","))
        cfg.worlds = [w for w in cfg.worlds if w.name in selected]

    if not cfg.worlds:
        print("没有要跑的世界。")
        sys.exit(1)

    print(f"探针配置: {args.config}")
    print(f"世界数: {len(cfg.worlds)}")

    run_probe(cfg)


def _do_ui(args):
    """启动配置 UI（浏览器界面）。"""
    from .config_ui import run
    run(host=args.host, port=args.port)


def _do_analyze(args):
    _do_analyze_inner(Path(args.batch_dir))


def _do_analyze_inner(batch_dir: Path):
    from .analyzer import analyze
    report = analyze(str(batch_dir))
    print()
    print(report)

    # 写报告文件
    report_path = batch_dir / "probe_latency_report.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n报告已写入: {report_path}")


if __name__ == "__main__":
    main()
