#!/usr/bin/env sh
set -e

HOST="${1:-postgres}"
PORT="${2:-5432}"

python - <<PY
import socket
import sys
import time

host = "${HOST}"
port = int("${PORT}")
deadline = time.time() + 30

while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            print("Database is reachable:", host, port)
            sys.exit(0)
    except OSError:
        time.sleep(1)

print("Database is not reachable:", host, port)
sys.exit(1)
PY
