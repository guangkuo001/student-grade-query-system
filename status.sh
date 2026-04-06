#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT_DIR/app.pid"
PORT_FILE="$ROOT_DIR/app.port"

if [[ ! -f "$PID_FILE" ]]; then
  echo "服务未运行。"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" > /dev/null 2>&1; then
  PORT="5000"
  if [[ -f "$PORT_FILE" ]]; then
    PORT="$(cat "$PORT_FILE")"
  fi
  echo "服务运行中，PID: $PID"
  echo "访问地址: http://127.0.0.1:$PORT"
else
  echo "PID 文件存在但进程未运行。"
fi
