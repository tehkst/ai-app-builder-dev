#!/usr/bin/env sh
set -e

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

chmod +x scripts/start.sh scripts/wait-for-db.sh scripts/check-local.sh

docker compose up --build
