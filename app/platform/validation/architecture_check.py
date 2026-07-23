from __future__ import annotations

from app.platform.validate_all import validation_catalogue


def main() -> None:
    catalogue = validation_catalogue()
    assert catalogue
    names = {item["name"] for item in catalogue}
    assert len(names) == len(catalogue)

    for item in catalogue:
        assert item["profiles"]
        assert item["test_type"]
        assert isinstance(item["requires_cloud"], bool)
        assert isinstance(item["requires_secrets"], list)
        assert isinstance(item["mandatory_release_gate"], bool)
        if "local" in item["profiles"]:
            assert item["requires_cloud"] is False
            assert item["requires_secrets"] == []
        if "ci" in item["profiles"]:
            assert item["requires_cloud"] is False
            assert item["requires_secrets"] == []

    by_name = {item["name"]: item for item in catalogue}
    assert by_name["generation_graph"]["profiles"] == ["ai-integration"]
    assert by_name["generation_graph"]["requires_secrets"] == ["OPENAI_API_KEY"]
    for name in ("frontend_contract", "frontend_build", "security_report", "artifact_registry"):
        assert by_name[name]["profiles"] == ["artifact"]

    print("VALIDATION ARCHITECTURE CHECK PASSED")


if __name__ == "__main__":
    main()
