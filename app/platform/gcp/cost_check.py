from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(".github/workflows/platform-deploy.yml")
COST_DOC = Path("infra/docs/cost-controls.md")


def main() -> None:
    assert WORKFLOW.exists(), "Missing deployment workflow"
    assert COST_DOC.exists(), "Missing cost controls documentation"
    workflow = WORKFLOW.read_text(encoding="utf-8")
    doc = COST_DOC.read_text(encoding="utf-8")
    assert "cost_review" in workflow
    assert "MAX_MONTHLY_COST_USD" in workflow
    assert "infracost" in workflow.lower()
    assert "Budget" in doc
    assert "Infracost" in doc
    print("COST GATE CHECK PASSED")


if __name__ == "__main__":
    main()
