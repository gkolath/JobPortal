#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -d "$ROOT/.venv" ]; then
  python3 -m venv "$ROOT/.venv"
fi
source "$ROOT/.venv/bin/activate"
pip install -q -r "$ROOT/requirements.txt"

if [ ! -d "$ROOT/frontend/dist" ] && command -v npm >/dev/null 2>&1; then
  echo "Building frontend..."
  cd "$ROOT/frontend" && npm install && npm run build
fi

cd "$ROOT/backend"
python seed.py 2>/dev/null || true
echo "Starting API at http://127.0.0.1:8000"
uvicorn main:app --reload --host 127.0.0.1 --port 8000
