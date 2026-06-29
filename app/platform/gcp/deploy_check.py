from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(".github/workflows/platform-deploy.yml")


def main() -> None:
    assert WORKFLOW.exists(), "Missing platform deploy workflow"
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch" in content
    assert "Run platform gates" in content
    assert "terraform validate" in content
    assert "docker/build-push-action" in content
    assert "Deployment summary" in content
    print("P1.10.1 DEPLOY WORKFLOW CHECK PASSED")


if __name__ == "__main__":
    main()
