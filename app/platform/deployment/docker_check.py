from __future__ import annotations

from pathlib import Path


REQUIRED_FILES = [
    "Dockerfile",
    ".dockerignore",
    "docker-compose.yml",
    ".env.example",
    "scripts/start.sh",
    "scripts/wait-for-db.sh",
    "app/platform/server.py",
]


def assert_contains(path: str, text: str) -> None:
    content = Path(path).read_text()
    assert text in content, "{} missing {}".format(path, text)


def main() -> None:
    for file_path in REQUIRED_FILES:
        assert Path(file_path).exists(), file_path

    assert_contains("Dockerfile", "FROM python:3.9-slim")
    assert_contains("Dockerfile", "CMD [\"/app/scripts/start.sh\"]")
    assert_contains("docker-compose.yml", "services:")
    assert_contains("docker-compose.yml", "app:")
    assert_contains(".env.example", "APP_ENV=production")
    assert_contains("scripts/start.sh", "uvicorn app.platform.server:app")
    assert_contains("app/platform/server.py", "@app.get(\"/health\")")
    assert_contains("app/platform/server.py", "@app.get(\"/ready\")")

    print("DOCKER FOUNDATION CHECK PASSED")


if __name__ == "__main__":
    main()
