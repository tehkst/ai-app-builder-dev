from __future__ import annotations

from pathlib import Path
from typing import Any


def read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def title(content: str) -> str:
    for line in content.splitlines():
        value = line.strip()
        if value.startswith("# "):
            return value.removeprefix("# ").strip()
    return ""


def section(content: str, heading: str) -> str:
    marker = f"## {heading}"
    start = content.find(marker)
    if start == -1:
        return ""
    rest = content[start + len(marker):]
    next_heading = rest.find("\n## ")
    if next_heading >= 0:
        rest = rest[:next_heading]
    return rest.strip()


def first_value(content: str, heading: str) -> str:
    for line in section(content, heading).splitlines():
        value = line.strip()
        if value:
            return value
    return ""


def bullet_list(content: str, heading: str) -> list[str]:
    return [
        line.strip().removeprefix("- ").strip()
        for line in section(content, heading).splitlines()
        if line.strip().startswith("- ")
    ]


def markdown_table(content: str, heading: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in section(content, heading).splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return []
    headers = [item.strip().lower().replace(" ", "_") for item in lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        values = [item.strip() for item in line.strip("|").split("|")]
        rows.append(dict(zip(headers, values)))
    return rows


def heading_id_and_title(content: str, fallback: str) -> tuple[str, str]:
    heading = title(content)
    if not heading:
        return fallback, fallback
    return heading.split(": ", 1) if ": " in heading else (fallback, heading)


def markdown_files(root: str) -> list[Path]:
    return sorted(Path(root).glob("*.md"))


def artifact_source(path: Path) -> str:
    return str(path)
