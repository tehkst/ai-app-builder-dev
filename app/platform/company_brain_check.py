from __future__ import annotations

from pathlib import Path

REQUIRED_PATHS = [
    "company/README.md",
    "company/constitution/README.md",
    "company/board/README.md",
    "company/strategy/README.md",
    "company/strategy/company-brain-spec-v1.md",
    "company/architecture/adr/README.md",
    "company/product/README.md",
    "company/missions/README.md",
    "company/executives/README.md",
    "company/knowledge/README.md",
]


def main() -> None:
    for path in REQUIRED_PATHS:
        assert Path(path).exists(), f"Missing company brain path: {path}"
    root = Path("company/README.md").read_text(encoding="utf-8")
    spec = Path("company/strategy/company-brain-spec-v1.md").read_text(encoding="utf-8")
    assert "Company Brain" in root
    assert "Code is replaceable. Company knowledge is not." in root
    assert "The company owns its knowledge. AI models do not." in spec
    assert "Idea" in spec
    assert "Discovery" in spec
    assert "Mission" in spec
    assert "Corporate Secretary" in spec
    assert "Board Room" in spec
    print("COMPANY BRAIN SPEC CHECK PASSED")


if __name__ == "__main__":
    main()
