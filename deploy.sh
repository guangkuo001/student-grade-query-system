#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PID_FILE="$ROOT_DIR/app.pid"
PORT_FILE="$ROOT_DIR/app.port"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/app.log"
DEFAULT_PORT="${APP_PORT:-5000}"

cd "$ROOT_DIR"

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" > /dev/null 2>&1; then
    echo "服务已在运行中，PID: $PID"
    echo "如需重启，请先执行: ./stop.sh"
    exit 0
  else
    rm -f "$PID_FILE"
  fi
fi

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

is_port_in_use() {
  local p="$1"
  python3 - "$p" <<'PY'
import socket
import sys

port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.2)
in_use = s.connect_ex(("127.0.0.1", port)) == 0
s.close()
sys.exit(0 if in_use else 1)
PY
}

PORT="$DEFAULT_PORT"
while is_port_in_use "$PORT"; do
  PORT=$((PORT + 1))
done

mkdir -p "$LOG_DIR"
nohup "$VENV_DIR/bin/gunicorn" -w 2 -b "0.0.0.0:$PORT" app:app > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "$PORT" > "$PORT_FILE"

sleep 1
if kill -0 "$(cat "$PID_FILE")" > /dev/null 2>&1; then
  echo "部署完成，服务已启动。"
  echo "访问地址: http://127.0.0.1:$PORT"
  echo "日志文件: $LOG_FILE"
else
  echo "启动失败，请查看日志: $LOG_FILE"
  exit 1
fi
