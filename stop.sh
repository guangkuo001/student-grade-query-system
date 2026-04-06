#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT_DIR/app.pid"
PORT_FILE="$ROOT_DIR/app.port"

if [[ ! -f "$PID_FILE" ]]; then
  echo "未找到运行中的服务（app.pid 不存在）。"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" > /dev/null 2>&1; then
  kill "$PID"
  echo "服务已停止，PID: $PID"
else
  echo "进程不存在，清理 PID 文件。"
fi

rm -f "$PID_FILE"
rm -f "$PORT_FILE"
