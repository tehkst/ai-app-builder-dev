from __future__ import annotations

from app.platform.repository_intelligence.service import inspect_repository_evidence


def main() -> None:
    path = "app/platform/execution/service.py"
    result = inspect_repository_evidence(
        [path, "../outside.py"],
        requested_by="architecture_review",
        relevance_by_path={path: "Execution mission state is an integration dependency."},
        max_items=2,
    )
    assert result["bounded"] is True
    assert result["inspected_count"] == 1
    assert result["missing"][0]["path"] == "../outside.py"
    manifest = result["manifest"][0]
    assert manifest["path"] == path
    assert manifest["inspected"] is True
    assert manifest["requested_by"] == "architecture_review"
    assert manifest["relevance"] == "Execution mission state is an integration dependency."
    assert len(manifest["fingerprint"]) == 64
    assert "content" not in manifest
    assert result["context"][0]["content"]
    print("repository inspected-evidence manifest ok")


if __name__ == "__main__":
    main()
