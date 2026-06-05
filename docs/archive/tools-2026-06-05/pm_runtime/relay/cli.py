"""CLI for the PM Runtime Communication Substrate MVP."""

from __future__ import annotations

import argparse
import sys
import traceback

from . import recovery
from .relay_runner import init_task, run_task, write_pm_runtime_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.pm_runtime.relay.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize a relay task")
    init_parser.add_argument("--config", required=True)

    run_parser = subparsers.add_parser("run", help="run the configured executor")
    run_parser.add_argument("--task-dir", required=True)

    recover_parser = subparsers.add_parser("recover", help="recover partial evidence")
    recover_parser.add_argument("--task-dir", required=True)

    summary_parser = subparsers.add_parser("summary", help="write PM Runtime summary")
    summary_parser.add_argument("--task-dir", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            return init_task(args.config)
        if args.command == "run":
            result = run_task(args.task_dir)
            return result.exit_code
        if args.command == "recover":
            exit_code, _ = recovery.recover_task(args.task_dir)
            return exit_code
        if args.command == "summary":
            write_pm_runtime_summary(args.task_dir)
            return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except PermissionError as exc:
        print(f"permission_blocked: {exc}", file=sys.stderr)
        return 6
    except FileNotFoundError as exc:
        print(f"artifact_path_missing: {exc}", file=sys.stderr)
        return 3
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
