from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeEntry:
    entry_id: str
    title: str
    category: str
    status: str
    owner: str
    summary: str
    tags: list[str]


@dataclass(frozen=True)
class KnowledgeVaultSummary:
    company: str
    product: str
    purpose: str
    total_entries: int
    categories: list[str]
    entries: list[KnowledgeEntry]
