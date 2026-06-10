from __future__ import annotations


TEMPLATE_PATH = 'backend/docker-compose.yml'
TEMPLATE_CONTENT = 'services:\n  db:\n    image: postgres:16-alpine\n    environment:\n      POSTGRES_DB: generated_app\n      POSTGRES_USER: postgres\n      POSTGRES_PASSWORD: postgres\n    ports:\n      - "5433:5432"\n    volumes:\n      - generated_postgres_data:/var/lib/postgresql/data\n    healthcheck:\n      test: ["CMD-SHELL", "pg_isready -U postgres -d generated_app"]\n      interval: 5s\n      timeout: 5s\n      retries: 10\n\n  backend:\n    build: .\n    env_file:\n      - .env\n    ports:\n      - "8001:8000"\n    depends_on:\n      db:\n        condition: service_healthy\n\nvolumes:\n  generated_postgres_data:\n'
