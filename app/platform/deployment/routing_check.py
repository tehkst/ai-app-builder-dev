from __future__ import annotations

from pathlib import Path


def assert_contains(path: str, text: str) -> None:
    content = Path(path).read_text()
    assert text in content, "{} missing {}".format(path, text)


def main() -> None:
    env_path = "infra/gcp/routing.env.example"
    checklist_path = "infra/gcp/routing-checklist.md"
    assert Path(env_path).exists(), env_path
    assert Path(checklist_path).exists(), checklist_path
    assert_contains(env_path, "APP_HOST=")
    assert_contains(env_path, "SERVICE_NAME=")
    assert_contains(env_path, "REGION=")
    assert_contains(env_path, "TLS_POLICY=")
    assert_contains(env_path, "DNS_RECORD_TYPE=")
    assert_contains(checklist_path, "health endpoint")
    assert_contains(checklist_path, "readiness endpoint")
    print("ROUTING CHECK PASSED")


if __name__ == "__main__":
    main()
