from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping, Optional, Tuple
from uuid import uuid4


SCHEMA_VERSION = "organizational-event-v1"


@dataclass(frozen=True)
class OrganizationalEvent:
    """Immutable, non-authoritative reference to a canonical platform fact."""

    event_id: str
    event_type: str
    source: str
    source_authority: str
    aggregate_type: str
    aggregate_id: str
    occurred_at: datetime
    schema_version: str = SCHEMA_VERSION
    idempotency_key: str = ""
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    actor: str = "system"
    evidence_references: Tuple[str, ...] = field(default_factory=tuple)
    payload: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "source_authority": self.source_authority,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "schema_version": self.schema_version,
            "idempotency_key": self.idempotency_key,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise ValueError("organizational event missing required fields: %s" % ", ".join(sorted(missing)))
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "source_authority": self.source_authority,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "occurred_at": self.occurred_at.astimezone(timezone.utc).isoformat(),
            "schema_version": self.schema_version,
            "idempotency_key": self.idempotency_key,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "actor": self.actor,
            "evidence_references": list(self.evidence_references),
            "payload": dict(self.payload),
            "metadata": dict(self.metadata),
        }


def build_organizational_event(
    event_type: str,
    *,
    source: str,
    source_authority: str,
    aggregate_type: str,
    aggregate_id: str,
    idempotency_key: Optional[str] = None,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    actor: str = "system",
    evidence_references: Tuple[str, ...] = (),
    payload: Optional[Mapping[str, Any]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    occurred_at: Optional[datetime] = None,
) -> OrganizationalEvent:
    normalized_payload = dict(payload or {})
    normalized_evidence = tuple(str(item) for item in evidence_references if str(item).strip())
    event_time = occurred_at or datetime.now(timezone.utc)
    derived_key = idempotency_key or _derive_idempotency_key(
        event_type=event_type,
        source=source,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        evidence_references=normalized_evidence,
        payload=normalized_payload,
    )
    return OrganizationalEvent(
        event_id="ORG-EVT-%s" % uuid4().hex,
        event_type=event_type,
        source=source,
        source_authority=source_authority,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        occurred_at=event_time,
        idempotency_key=derived_key,
        correlation_id=correlation_id,
        causation_id=causation_id,
        actor=actor,
        evidence_references=normalized_evidence,
        payload=normalized_payload,
        metadata=dict(metadata or {}),
    )


def _derive_idempotency_key(
    *,
    event_type: str,
    source: str,
    aggregate_type: str,
    aggregate_id: str,
    evidence_references: Tuple[str, ...],
    payload: Mapping[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "event_type": event_type,
            "source": source,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "evidence_references": list(evidence_references),
            "payload": payload,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return "ORG-IDEMP-%s" % sha256(canonical.encode("utf-8")).hexdigest()
