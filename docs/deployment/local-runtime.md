# D1 Local Runtime

This document describes the local container runtime for AI Software Factory.

## Start

```bash
cp .env.example .env
chmod +x scripts/bootstrap-local.sh scripts/check-local.sh scripts/start.sh scripts/wait-for-db.sh
./scripts/bootstrap-local.sh
```

## Check

In another terminal:

```bash
./scripts/check-local.sh
```

Expected endpoints:

- `GET /health`
- `GET /ready`

## Services

The local runtime includes:

- FastAPI application
- PostgreSQL with pgvector
- Redis
- shared Docker network
- persistent Docker volumes

## Notes

The `.env.example` file is safe to commit. The `.env` file should stay local.
