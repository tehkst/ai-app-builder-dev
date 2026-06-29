from __future__ import annotations

from pathlib import Path


def assert_contains(path: str, text: str) -> None:
    content = Path(path).read_text()
    assert text in content, "{} missing {}".format(path, text)


def main() -> None:
    required = [
        "docker-compose.yml",
        ".env.example",
        "infra/postgres/init/001_extensions.sql",
    ]
    for file_path in required:
        assert Path(file_path).exists(), file_path

    assert_contains("docker-compose.yml", "postgres:")
    assert_contains("docker-compose.yml", "redis:")
    assert_contains("docker-compose.yml", "pgvector/pgvector:pg16")
    assert_contains("docker-compose.yml", "redis:7-alpine")
    assert_contains("docker-compose.yml", "postgres_data:")
    assert_contains("docker-compose.yml", "redis_data:")
    assert_contains("docker-compose.yml", "service_healthy")
    assert_contains(".env.example", "DATABASE_URL=")
    assert_contains(".env.example", "REDIS_URL=")
    assert_contains("infra/postgres/init/001_extensions.sql", "CREATE EXTENSION IF NOT EXISTS vector")

    print("POSTGRES REDIS CHECK PASSED")


if __name__ == "__main__":
    main()
