#!/bin/sh
set -e

cd /app/backend

if [ "$RUN_SEED" = "1" ]; then
  echo "Running seed script..."
  python seed.py || true
fi

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
