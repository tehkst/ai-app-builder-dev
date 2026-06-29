#!/usr/bin/env sh
set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

curl -fsS "$BASE_URL/health" >/dev/null
curl -fsS "$BASE_URL/ready" >/dev/null

echo "Local stack check passed"
