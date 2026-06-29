from __future__ import annotations

from app.platform.knowledge_vault.service import build_knowledge_vault_summary


def main() -> None:
    summary = build_knowledge_vault_summary()
    assert summary["company"] == "AI Software Factory"
    assert summary["product"] == "Knowledge Vault"
    assert summary["total_entries"] >= 5
    categories = set(summary["categories"])
    assert "company-dna" in categories
    assert "runbook" in categories
    assert "architecture" in categories
    assert "lesson" in categories
    assert "operating-policy" in categories
    print("KNOWLEDGE VAULT CHECK PASSED")


if __name__ == "__main__":
    main()
