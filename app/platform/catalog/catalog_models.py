from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class CatalogItem:
    item_id: str
    item_type: str
    name: str
    publisher: str
    version: str
    status: str
    categories: List[str]
    capabilities: List[str]


@dataclass(frozen=True)
class CatalogRelease:
    release_id: str
    item_id: str
    version: str
    status: str
    notes: str


@dataclass(frozen=True)
class CatalogActivation:
    activation_id: str
    tenant_id: str
    item_id: str
    version: str
    status: str


@dataclass(frozen=True)
class CatalogRule:
    rule_id: str
    item_id: str
    rule: str
    severity: str


@dataclass(frozen=True)
class CatalogSummary:
    item_count: int
    published_count: int
    activation_count: int
    rule_count: int
    template_count: int
    extension_count: int
    connector_count: int


@dataclass(frozen=True)
class CatalogContext:
    items: List[CatalogItem]
    releases: List[CatalogRelease]
    activations: List[CatalogActivation]
    rules: List[CatalogRule]
    metadata: Dict[str, object]
