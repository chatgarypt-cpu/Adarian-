#!/bin/bash
# Adarian — 双击启动 Web 控制台

cd "$(dirname "$0")"
echo "Adarian 平行世界舆情推演系统 — 启动中..."
export PYTHONPATH=src
exec .venv/bin/python -m adarian serve --open-browser
