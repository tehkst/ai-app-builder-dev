from __future__ import annotations

from pathlib import Path
from typing import Any

from app.platform.repository.markdown import (
    artifact_source,
    bullet_list,
    first_value,
    heading_id_and_title,
    markdown_files,
    read_markdown,
)


def _entry_from_file(path: Path) -> dict[str, Any]:
    content = read_markdown(path)
    entry_id, title = heading_id_and_title(content, path.stem)
    return {
        "entry_id": entry_id,
        "title": title,
        "category": first_value(content, "Category"),
        "status": first_value(content, "Status"),
        "owner": first_value(content, "Owner"),
        "summary": first_value(content, "Summary"),
        "tags": bullet_list(content, "Tags"),
        "source": artifact_source(path),
    }


def build_knowledge_vault_summary() -> dict[str, Any]:
    entries = [_entry_from_file(path) for path in markdown_files("company/knowledge")]
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
