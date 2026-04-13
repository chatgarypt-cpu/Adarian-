"""Subprocess entrypoint for a single chain benchmark execution unit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

if __package__ in (None, ""):
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

from profiling.chain_benchmark import run_chain_case


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a single chain benchmark unit in a subprocess.")
    parser.add_argument("--input", required=True, help="Path to worker input JSON")
    parser.add_argument("--output", required=True, help="Path to worker output JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    payload = _load_json(Path(args.input))
    if not isinstance(payload, dict):
        raise ValueError("worker input payload must be a JSON object")

    try:
        result = run_chain_case(
            generator_model=str(payload["generator_model"]),
            validator_model=str(payload["validator_model"]),
            case=payload["case"],
            max_retry_count=int(payload["max_retry_count"]),
            provider=str(payload["provider"]),
            api_key=str(payload["api_key"]),
            base_url=str(payload["base_url"]),
            generator_temperature=float(payload["generator_temperature"]),
            validator_temperature=float(payload["validator_temperature"]),
            max_tokens=int(payload["max_tokens"]),
            request_timeout=float(payload["request_timeout"]),
        )
        _write_json(Path(args.output), {"ok": True, "result": result})
        return 0
    except Exception as exc:
        _write_json(
            Path(args.output),
            {
                "ok": False,
                "error": {
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "error_types": [f"generator_error:{type(exc).__name__}"],
                    "timeout": False,
                },
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
