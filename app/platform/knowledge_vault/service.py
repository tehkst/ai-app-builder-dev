from __future__ import annotations

from pathlib import Path
from typing import Any


def _section(content: str, heading: str) -> str:
    marker = f"## {heading}"
    start = content.find(marker)
    if start == -1:
        return ""
    rest = content[start + len(marker):]
    next_heading = rest.find("\n## ")
    if next_heading >= 0:
        rest = rest[:next_heading]
    return rest.strip()


def _first_value(content: str, heading: str) -> str:
    for line in _section(content, heading).splitlines():
        value = line.strip()
        if value:
            return value
    return ""


def _tags(content: str) -> list[str]:
    return [line.removeprefix("- ").strip() for line in _section(content, "Tags").splitlines() if line.strip().startswith("- ")]


def _entry_from_file(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    heading = content.splitlines()[0].removeprefix("# ").strip()
    entry_id, title = heading.split(": ", 1) if ": " in heading else (path.stem, heading)
    return {
        "entry_id": entry_id,
        "title": title,
        "category": _first_value(content, "Category"),
        "status": _first_value(content, "Status"),
        "owner": _first_value(content, "Owner"),
        "summary": _first_value(content, "Summary"),
        "tags": _tags(content),
        "source": str(path),
    }


def build_knowledge_vault_summary() -> dict[str, Any]:
    root = Path("company/knowledge")
    entries = [_entry_from_file(path) for path in sorted(root.glob("*.md"))]
    categories = sorted({entry["category"] for entry in entries})
    return {
        "company": "AI Software Factory",
        "product": "Knowledge Vault",
        "purpose": "Institutional memory for decisions, runbooks, lessons, and operating policy.",
        "storage": "repository-filesystem",
        "total_entries": len(entries),
        "categories": categories,
        "entries": entries,
    }
