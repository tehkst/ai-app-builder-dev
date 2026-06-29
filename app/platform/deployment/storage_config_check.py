from __future__ import annotations

from pathlib import Path


def assert_contains(path: str, text: str) -> None:
    content = Path(path).read_text()
    assert text in content, "{} missing {}".format(path, text)


def main() -> None:
    config_path = "infra/gcp/db.env.example"
    assert Path(config_path).exists(), config_path
    assert_contains(config_path, "DB_INSTANCE_NAME=")
    assert_contains(config_path, "DB_VERSION=")
    assert_contains(config_path, "DB_REGION=")
    assert_contains(config_path, "DB_NAME=")
    assert_contains(config_path, "DB_USER=")
    print("STORAGE CONFIG CHECK PASSED")


if __name__ == "__main__":
    main()
