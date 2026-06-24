#!/bin/bash
# Adarian — 双击启动 Web 控制台

cd "$(dirname "$0")"
echo "Adarian 平行世界舆情推演系统 — 启动中..."
.venv/bin/python -m src.adarian serve

echo ""
echo "服务已停止。按 Enter 关闭窗口"
read -r
