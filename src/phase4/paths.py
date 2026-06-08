"""Run directory path construction for Adarian pipeline.

委派给 src.output_paths.DefaultRunPaths（向后兼容入口）。
"""

from pathlib import Path


def build_run_paths(seed_file: Path) -> dict:
    """委派给 DefaultRunPaths（向后兼容入口）。"""
    from src.output_paths import DefaultRunPaths
    return DefaultRunPaths(seed_file).build()
