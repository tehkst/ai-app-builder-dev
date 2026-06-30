from __future__ import annotations

from dataclasses import dataclass, field

from app.platform.company_objects.types import CompanyObjectStatus, CompanyObjectType, RelationshipType


@dataclass(frozen=True)
class CompanyObjectRelationship:
    relationship_type: RelationshipType
    target_object_id: str
    description: str


@dataclass(frozen=True)
class CompanyObject:
    object_id: str
    object_type: CompanyObjectType
    title: str
    status: CompanyObjectStatus
    owner: str
    version: str = "1.0"
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    relationships: list[CompanyObjectRelationship] = field(default_factory=list)
