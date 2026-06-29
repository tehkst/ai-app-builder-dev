from __future__ import annotations

from pathlib import Path

CHECKLIST_PATH = Path("docs/data/d3-4-data-safety.md")
REQUIRED_SECTIONS = [
    "Snapshot cadence",
    "Retention policy",
    "Restore drill",
    "Ownership",
    "Verification",
    "Incident notes",
    "D3.4 completion criteria",
]


def main() -> None:
    assert CHECKLIST_PATH.exists(), f"Missing checklist: {CHECKLIST_PATH}"
    content = CHECKLIST_PATH.read_text(encoding="utf-8")
    missing = [section for section in REQUIRED_SECTIONS if f"## {section}" not in content]
    assert not missing, f"Missing checklist sections: {missing}"
    assert "No runtime behavior is changed." in content
    assert "No existing data-layer APIs are modified." in content
    print("D3.4 DATA SAFETY CHECK PASSED")


if __name__ == "__main__":
    main()
