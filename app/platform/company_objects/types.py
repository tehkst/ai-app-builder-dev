from __future__ import annotations

from typing import Literal

CompanyObjectType = Literal[
    "board_meeting",
    "decision",
    "resolution",
    "mission",
    "adr",
    "policy",
    "executive",
    "roadmap_item",
    "product",
    "customer",
    "deployment",
    "incident",
    "lesson",
]

CompanyObjectStatus = Literal[
    "draft",
    "proposed",
    "approved",
    "active",
    "completed",
    "archived",
    "rejected",
]

RelationshipType = Literal[
    "created_from",
    "approves",
    "implements",
    "documents",
    "depends_on",
    "blocks",
    "supersedes",
    "references",
    "produced_by",
    "owned_by",
]
