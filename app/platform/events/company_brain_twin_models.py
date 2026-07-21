from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainGraph,
    CompanyBrainRelationship,
)
from app.platform.events.company_brain_reasoning_models import ReasoningFinding


TWIN_ALIGNED = "aligned"
TWIN_MISSING = "missing"
TWIN_UNEXPECTED = "unexpected"


@dataclass(frozen=True)
class TwinComponent:
    entity: CompanyBrainEntity
    desired: bool = False
    observed: bool = False
    status: str = TWIN_ALIGNED

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "entity": self.entity.as_dict(),
            "desired": self.desired,
            "observed": self.observed,
            "status": self.status,
        }


@dataclass(frozen=True)
class DigitalTwinSnapshot:
    mission: CompanyBrainEntity
    desired_graph: CompanyBrainGraph
    observed_graph: CompanyBrainGraph | None = None
    components: Tuple[TwinComponent, ...] = field(default_factory=tuple)
    topology: Tuple[CompanyBrainRelationship, ...] = field(default_factory=tuple)
    drift: Tuple[ReasoningFinding, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    @property
    def reconciled(self) -> bool:
        return self.observed_graph is not None

    @property
    def aligned(self) -> bool:
        return self.reconciled and not self.drift

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "mission": self.mission.as_dict(),
            "desired_graph": self.desired_graph.as_dict(),
            "observed_graph": self.observed_graph.as_dict() if self.observed_graph else None,
            "components": [component.as_dict() for component in self.components],
            "topology": [relationship.as_dict() for relationship in self.topology],
            "drift": [finding.as_dict() for finding in self.drift],
            "warnings": list(self.warnings),
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
            "reconciled": self.reconciled,
            "aligned": self.aligned,
        }
