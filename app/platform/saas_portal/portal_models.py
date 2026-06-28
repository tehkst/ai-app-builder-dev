from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PortalPage:
    page_id: str
    title: str
    route: str
    section: str
    tenant_scoped: bool = True


@dataclass(frozen=True)
class PortalCard:
    card_id: str
    title: str
    value: str
    status: str
    metadata: Dict[str, object]


@dataclass(frozen=True)
class PortalView:
    view_id: str
    title: str
    cards: List[PortalCard]


@dataclass(frozen=True)
class CustomerProject:
    project_id: str
    tenant_id: str
    name: str
    status: str


@dataclass(frozen=True)
class CustomerApplication:
    application_id: str
    project_id: str
    tenant_id: str
    name: str
    status: str
