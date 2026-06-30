from __future__ import annotations

from app.platform.company_objects.service import build_company_object_registry


def main() -> None:
    registry = build_company_object_registry()
    assert registry["company"] == "AI Software Factory"
    assert registry["product"] == "Company Objects"
    assert registry["storage"] == "repository-filesystem"
    assert registry["total_objects"] >= 3
    object_ids = {item["object_id"] for item in registry["objects"]}
    assert "ADR-0001" in object_ids
    assert "SPEC-0001" in object_ids
    assert "M-0001" in object_ids
    sources = {item["source"] for item in registry["objects"]}
    assert "company/objects/ADR-0001.md" in sources
    print("COMPANY OBJECT MODEL CHECK PASSED")


if __name__ == "__main__":
    main()
