from __future__ import annotations

from pathlib import Path


def assert_contains(path: str, text: str) -> None:
    content = Path(path).read_text()
    assert text in content, "{} missing {}".format(path, text)


def main() -> None:
    required = [
        "scripts/bootstrap-local.sh",
        "scripts/check-local.sh",
        "docs/deployment/local-runtime.md",
        "docker-compose.yml",
        ".env.example",
    ]
    for file_path in required:
        assert Path(file_path).exists(), file_path

    assert_contains("scripts/bootstrap-local.sh", "docker compose")
    assert_contains("scripts/check-local.sh", "BASE_URL")
    assert_contains("docs/deployment/local-runtime.md", "FastAPI")
    assert_contains("docs/deployment/local-runtime.md", "PostgreSQL")
    assert_contains("docs/deployment/local-runtime.md", "Redis")
    assert_contains("docker-compose.yml", "depends_on")
    assert_contains("docker-compose.yml", "service_healthy")

    print("BOOTSTRAP CHECK PASSED")


if __name__ == "__main__":
    main()
