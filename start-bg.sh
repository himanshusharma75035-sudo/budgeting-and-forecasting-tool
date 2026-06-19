#!/usr/bin/env bash
# Start/stop the backend + frontend in the background (logs under ./logs).
#   ./start-bg.sh [start]   start both (default)
#   ./start-bg.sh stop      stop both
#   ./start-bg.sh restart   stop then start
#   ./start-bg.sh status    show what's running
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
LOG_DIR="$ROOT/logs"
BE_PID="$LOG_DIR/backend.pid"
FE_PID="$LOG_DIR/frontend.pid"

venv_python() {
  if   [ -x "$BACKEND/.venv/bin/python" ];        then printf '%s' "$BACKEND/.venv/bin/python"
  elif [ -x "$BACKEND/.venv/Scripts/python.exe" ]; then printf '%s' "$BACKEND/.venv/Scripts/python.exe"
  else printf '%s' ""
  fi
}

is_running() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }

start() {
  local vpy; vpy="$(venv_python)"
  if [ -z "$vpy" ]; then
    echo "Backend is not set up. Run ./setup.sh first." >&2; exit 1
  fi
  if [ ! -d "$FRONTEND/node_modules" ]; then
    echo "Frontend is not set up. Run ./setup.sh first." >&2; exit 1
  fi
  mkdir -p "$LOG_DIR"

  if is_running "$BE_PID"; then
    echo "Backend already running (pid $(cat "$BE_PID"))."
  else
    ( cd "$BACKEND" && nohup "$vpy" -m uvicorn app.main:app --reload --reload-dir app \
        >"$LOG_DIR/backend.log" 2>&1 & echo $! >"$BE_PID" )
    echo "Backend  started (pid $(cat "$BE_PID"))  ->  http://127.0.0.1:8000  (docs at /docs)"
  fi

  if is_running "$FE_PID"; then
    echo "Frontend already running (pid $(cat "$FE_PID"))."
  else
    ( cd "$FRONTEND" && nohup npm run dev \
        >"$LOG_DIR/frontend.log" 2>&1 & echo $! >"$FE_PID" )
    echo "Frontend started (pid $(cat "$FE_PID"))  ->  http://127.0.0.1:5173"
  fi

  echo
  echo "Logs:  logs/backend.log   logs/frontend.log"
  echo "Stop:  ./start-bg.sh stop"
}

stop() {
  local stopped=0
  for pf in "$BE_PID" "$FE_PID"; do
    if [ -f "$pf" ]; then
      pid="$(cat "$pf")"
      if kill -0 "$pid" 2>/dev/null; then kill "$pid" 2>/dev/null || true; stopped=1; fi
      rm -f "$pf"
    fi
  done
  [ "$stopped" -eq 1 ] && echo "Stopped backend + frontend." || echo "Nothing was running."
}

status() {
  is_running "$BE_PID"  && echo "Backend:  running (pid $(cat "$BE_PID"))"  || echo "Backend:  stopped"
  is_running "$FE_PID"  && echo "Frontend: running (pid $(cat "$FE_PID"))"  || echo "Frontend: stopped"
}

case "${1:-start}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; sleep 1; start ;;
  status)  status ;;
  *) echo "usage: $(basename "$0") [start|stop|restart|status]" >&2; exit 1 ;;
esac
