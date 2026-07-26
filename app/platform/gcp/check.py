from __future__ import annotations

from pathlib import Path

REQUIRED_PATHS = [
    "Dockerfile",
    "infra/README.md",
    ".github/workflows/platform-deploy.yml",
    "infra/scripts/gate.sh",
    "infra/scripts/validate.sh",
]


def main() -> None:
    missing = [path for path in REQUIRED_PATHS if not Path(path).exists()]
    assert not missing, f"Missing GCP foundation paths: {missing}"
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "PORT=8080" in dockerfile
    assert "EXPOSE 8080" in dockerfile
    workflow = Path(".github/workflows/platform-deploy.yml").read_text(encoding="utf-8")
    assert "gcloud run deploy" in workflow
    assert "--port=8080" in workflow
    assert "--min-instances" in workflow
    assert "--max-instances" in workflow
    assert "google-github-actions/auth" in workflow
    print("P1.7 NETWORKING FOUNDATION CHECK PASSED")


if __name__ == "__main__":
    main()
