from __future__ import annotations

from app.platform.company_brain.service import build_company_brain_repository_summary, get_company_brain_artifact


def main() -> None:
    summary = build_company_brain_repository_summary()
    assert summary["company"] == "AI Software Factory"
    assert summary["product"] == "Company Brain Repository"
    assert summary["storage"] == "repository-filesystem"
    assert summary["total_artifacts"] >= 10
    artifact_types = {item["artifact_type"] for item in summary["artifacts"]}
    assert "adr" in artifact_types
    assert "strategy" in artifact_types
    assert "board" in artifact_types
    adr = get_company_brain_artifact("architecture/adr/ADR-0001-the-company-owns-its-knowledge.md")
    assert adr["title"] == "ADR-0001: The Company Owns Its Knowledge"
    print("COMPANY BRAIN REPOSITORY CHECK PASSED")


if __name__ == "__main__":
    main()
