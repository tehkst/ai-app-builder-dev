from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class CompanyBrainEntity:
    authority: str
    entity_id: str

    @property
    def key(self) -> str:
        return "%s:%s" % (self.authority, self.entity_id)

    def as_dict(self) -> Mapping[str, str]:
        return {"authority": self.authority, "entity_id": self.entity_id, "key": self.key}


@dataclass(frozen=True)
class CompanyBrainRelationship:
    source_key: str
    target_key: str
    relationship: str
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "source_key": self.source_key,
            "target_key": self.target_key,
            "relationship": self.relationship,
            "supporting_event_ids": list(self.supporting_event_ids),
        }


@dataclass(frozen=True)
class CompanyBrainGraph:
    entities: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    relationships: Tuple[CompanyBrainRelationship, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "entities": [entity.as_dict() for entity in self.entities],
            "relationships": [relationship.as_dict() for relationship in self.relationships],
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class CompanyBrainExplanation:
    subject: CompanyBrainEntity
    related_entities: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    relationships: Tuple[CompanyBrainRelationship, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "subject": self.subject.as_dict(),
            "related_entities": [entity.as_dict() for entity in self.related_entities],
            "relationships": [relationship.as_dict() for relationship in self.relationships],
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }
