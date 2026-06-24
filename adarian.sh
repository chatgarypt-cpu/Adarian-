#!/bin/bash
# Adarian — 平行世界舆情推演系统 统一入口
#
# 用法:
#   ./adarian.sh up                        启动 Web + 返回 CLI
#   ./adarian.sh run [seed]                单次 pipeline
#   ./adarian.sh serve                     启动 Web 控制台（前台）
#   ./adarian.sh batch --models ...        多模型并行
#   ./adarian.sh inspect <dir>             检查 batch 产物
#

set -e
cd "$(dirname "$0")"

if [ $# -eq 0 ]; then
    .venv/bin/python -m src.adarian --help
    exit 0
fi

CMD=$1
shift

if [ "$CMD" = "up" ]; then
    echo "Adarian — Web 后台启动中..."
    .venv/bin/python -m src.adarian serve &
    sleep 2
    echo "Web 控制台: http://127.0.0.1:9788"
    echo "CLI 可用: ./adarian.sh run seeds/test8.txt"
    echo "停止: kill %1 或 pkill -f 'adarian serve'"
    wait %1 2>/dev/null || true
    exit 0
fi

exec .venv/bin/python -m src.adarian "$CMD" "$@"
