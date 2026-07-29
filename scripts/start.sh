#!/usr/bin/env sh
set -e

if [ -n "${DATABASE_HOST:-}" ]; then
  /app/scripts/wait-for-db.sh "${DATABASE_HOST}" "${DATABASE_PORT:-5432}"
fi

exec uvicorn app.platform.server:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
