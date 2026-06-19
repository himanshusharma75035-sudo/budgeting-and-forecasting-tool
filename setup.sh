#!/usr/bin/env bash
# One-time (idempotent) setup for the backend + frontend, then start both.
#   ./setup.sh              setup, then launch both in the background
#   ./setup.sh --no-start   setup only
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

START=1
[ "${1:-}" = "--no-start" ] && START=0

# Bootstrap interpreter for creating the venv.
PYBIN="${PYTHON:-}"
if [ -z "$PYBIN" ]; then
  if command -v python3 >/dev/null 2>&1; then PYBIN=python3; else PYBIN=python; fi
fi

# Resolve the venv's python across Linux/macOS (bin/) and Git-Bash on Windows (Scripts/).
venv_python() {
  if   [ -x "$BACKEND/.venv/bin/python" ];        then printf '%s' "$BACKEND/.venv/bin/python"
  elif [ -x "$BACKEND/.venv/Scripts/python.exe" ]; then printf '%s' "$BACKEND/.venv/Scripts/python.exe"
  else printf '%s' ""
  fi
}

echo "==> Backend setup"
cd "$BACKEND"
if [ -z "$(venv_python)" ]; then
  echo "    creating virtual environment"
  "$PYBIN" -m venv .venv
fi
VPY="$(venv_python)"
"$VPY" -m pip install --upgrade pip
"$VPY" -m pip install -e ".[dev]"
if [ ! -f "$BACKEND/data/openfpa.db" ]; then
  echo "    seeding demo database"
  "$VPY" scripts/seed.py
fi

echo "==> Frontend setup"
cd "$FRONTEND"
if [ ! -d node_modules ]; then
  npm install
fi

echo
echo "Setup complete."
if [ "$START" -eq 1 ]; then
  exec "$ROOT/start-bg.sh" start
else
  echo "Start the app any time with:  ./start-bg.sh"
fi
