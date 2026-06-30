from __future__ import annotations

from pathlib import Path

REQUIRED_PATHS = [
    "company/README.md",
    "company/constitution/README.md",
    "company/board/README.md",
    "company/strategy/README.md",
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
    assert "Company Brain" in root
    assert "Code is replaceable. Company knowledge is not." in root
    print("COMPANY BRAIN FOUNDATION CHECK PASSED")


if __name__ == "__main__":
    main()
