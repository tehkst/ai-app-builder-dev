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


def _relationships(content: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in _section(content, "Relationships").splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return []
    headers = [item.strip().lower().replace(" ", "_") for item in lines[0].strip("|").split("|")]
    records: list[dict[str, str]] = []
    for line in lines[2:]:
        values = [item.strip() for item in line.strip("|").split("|")]
        records.append(dict(zip(headers, values)))
    return records


def _object_from_file(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    heading = content.splitlines()[0].removeprefix("# ").strip()
    object_id, title = heading.split(": ", 1) if ": " in heading else (path.stem, heading)
    return {
        "object_id": object_id,
        "object_type": _first_value(content, "Object Type"),
        "title": title,
        "status": _first_value(content, "Status"),
        "owner": _first_value(content, "Owner"),
        "version": _first_value(content, "Version"),
        "summary": _first_value(content, "Summary"),
        "tags": _tags(content),
        "relationships": _relationships(content),
        "source": str(path),
    }


def build_company_object_registry() -> dict[str, Any]:
    root = Path("company/objects")
    objects = [_object_from_file(path) for path in sorted(root.glob("*.md"))]
    return {
        "company": "AI Software Factory",
        "product": "Company Objects",
        "storage": "repository-filesystem",
        "total_objects": len(objects),
        "objects": objects,
    }
