from __future__ import annotations

from pathlib import Path


def assert_contains(path: str, text: str) -> None:
    content = Path(path).read_text()
    assert text in content, "{} missing {}".format(path, text)


def main() -> None:
    required = [
        "infra/gcp/cloud-run-service.yaml",
        "infra/gcp/env.cloudrun.example",
    ]
    for file_path in required:
        assert Path(file_path).exists(), file_path

    assert_contains("infra/gcp/cloud-run-service.yaml", "kind: Service")
    assert_contains("infra/gcp/cloud-run-service.yaml", "containerPort: 8000")
    assert_contains("infra/gcp/cloud-run-service.yaml", "/health")
    assert_contains("infra/gcp/cloud-run-service.yaml", "/ready")
    assert_contains("infra/gcp/env.cloudrun.example", "PROJECT_ID=")
    assert_contains("infra/gcp/env.cloudrun.example", "REGION=")
    assert_contains("infra/gcp/env.cloudrun.example", "SERVICE_NAME=")

    print("GCP RUNTIME CHECK PASSED")


if __name__ == "__main__":
    main()
