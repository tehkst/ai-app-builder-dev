from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping, Optional
from uuid import uuid4


DOMAIN_EVENT_TYPES = {
    "FounderRequestReceived", "MissionCreated", "MissionAccepted", "MissionAdvanced", "MissionCompleted",
    "WorkflowCreated", "WorkflowUpdated", "WorkflowCompleted", "PullRequestOpened", "PullRequestMerged",
    "DeploymentStarted", "DeploymentSucceeded", "DeploymentFailed", "VerificationPassed", "VerificationFailed",
}


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, (tuple, frozenset)):
        return [_thaw(item) for item in value]
    return value


def _frozen_mapping(value: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    return _freeze(value or {})


@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    event_type: str
    timestamp: str
    source: str
    aggregate_type: str
    aggregate_id: str
    correlation_id: str
    causation_id: Optional[str]
    actor: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id or not self.event_type or not self.aggregate_id:
            raise ValueError("event_id, event_type, and aggregate_id are required")
        object.__setattr__(self, "payload", _frozen_mapping(self.payload))
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id, "event_type": self.event_type, "timestamp": self.timestamp,
            "source": self.source, "aggregate_type": self.aggregate_type, "aggregate_id": self.aggregate_id,
            "correlation_id": self.correlation_id, "causation_id": self.causation_id, "actor": self.actor,
            "payload": _thaw(self.payload), "metadata": _thaw(self.metadata),
        }


def create_domain_event(
    event_type: str, *, source: str, aggregate_type: str, aggregate_id: str,
    correlation_id: Optional[str] = None, causation_id: Optional[str] = None,
    actor: str = "system", payload: Optional[Mapping[str, Any]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> DomainEvent:
    return DomainEvent(
        event_id="EVENT-{}".format(uuid4().hex.upper()), event_type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat(), source=source,
        aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        correlation_id=correlation_id or aggregate_id, causation_id=causation_id,
        actor=actor, payload=payload or {}, metadata=metadata or {},
    )
