from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.exc import IntegrityError

from app.platform.events.event_models import OrganizationalEvent
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformOrganizationalEvent


_AUTHORITY_REFERENCES_KEY = "authority_references"


class DurableOrganizationalEventStore:
    """Append-only store for non-authoritative organizational event references."""

    def __init__(
        self,
        session_factory: Callable[[], Any] = PlatformSessionLocal,
        ensure_schema: Callable[[], None] = create_platform_tables,
    ) -> None:
        self._session_factory = session_factory
        self._ensure_schema = ensure_schema

    def append(self, event: OrganizationalEvent) -> Dict[str, Any]:
        self._ensure_schema()
        db = self._session_factory()
        try:
            existing = (
                db.query(PlatformOrganizationalEvent)
                .filter(PlatformOrganizationalEvent.idempotency_key == event.idempotency_key)
                .first()
            )
            if existing is not None:
                return self._serialize(existing, replayed=True)

            metadata = dict(event.metadata)
            metadata[_AUTHORITY_REFERENCES_KEY] = [
                reference.as_dict() for reference in event.authority_references
            ]
            row = PlatformOrganizationalEvent(
                event_id=event.event_id,
                idempotency_key=event.idempotency_key,
                event_type=event.event_type,
                source=event.source,
                source_authority=event.source_authority,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                schema_version=event.schema_version,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
                actor=event.actor,
                evidence_references_json=json.dumps(list(event.evidence_references)),
                payload_json=json.dumps(dict(event.payload), default=str, sort_keys=True),
                metadata_json=json.dumps(metadata, default=str, sort_keys=True),
                occurred_at=event.occurred_at,
            )
            db.add(row)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                existing = (
                    db.query(PlatformOrganizationalEvent)
                    .filter(PlatformOrganizationalEvent.idempotency_key == event.idempotency_key)
                    .first()
                )
                if existing is None:
                    raise
                return self._serialize(existing, replayed=True)
            db.refresh(row)
            return self._serialize(row, replayed=False)
        finally:
            db.close()

    def list_for_aggregate(
        self,
        aggregate_type: str,
        aggregate_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        self._ensure_schema()
        bounded_limit = max(1, min(int(limit), 500))
        db = self._session_factory()
        try:
            rows = (
                db.query(PlatformOrganizationalEvent)
                .filter(PlatformOrganizationalEvent.aggregate_type == aggregate_type)
                .filter(PlatformOrganizationalEvent.aggregate_id == aggregate_id)
                .order_by(PlatformOrganizationalEvent.occurred_at.asc(), PlatformOrganizationalEvent.id.asc())
                .limit(bounded_limit)
                .all()
            )
            return [self._serialize(row, replayed=False) for row in rows]
        finally:
            db.close()

    def list_for_correlation_id(
        self,
        correlation_id: str,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Return a stable cross-aggregate event stream for one correlation boundary."""

        normalized_id = str(correlation_id or "").strip()
        if not normalized_id:
            raise ValueError("correlation_id is required")
        self._ensure_schema()
        bounded_limit = max(1, min(int(limit), 1000))
        db = self._session_factory()
        try:
            rows = (
                db.query(PlatformOrganizationalEvent)
                .filter(PlatformOrganizationalEvent.correlation_id == normalized_id)
                .order_by(PlatformOrganizationalEvent.occurred_at.asc(), PlatformOrganizationalEvent.id.asc())
                .limit(bounded_limit)
                .all()
            )
            return [self._serialize(row, replayed=False) for row in rows]
        finally:
            db.close()

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        self._ensure_schema()
        db = self._session_factory()
        try:
            row = (
                db.query(PlatformOrganizationalEvent)
                .filter(PlatformOrganizationalEvent.idempotency_key == idempotency_key)
                .first()
            )
            return self._serialize(row, replayed=False) if row is not None else None
        finally:
            db.close()

    @staticmethod
    def _serialize(row: PlatformOrganizationalEvent, replayed: bool) -> Dict[str, Any]:
        metadata = json.loads(row.metadata_json or "{}")
        authority_references = metadata.pop(_AUTHORITY_REFERENCES_KEY, [])
        return {
            "event_id": row.event_id,
            "idempotency_key": row.idempotency_key,
            "event_type": row.event_type,
            "source": row.source,
            "source_authority": row.source_authority,
            "aggregate_type": row.aggregate_type,
            "aggregate_id": row.aggregate_id,
            "schema_version": row.schema_version,
            "correlation_id": row.correlation_id,
            "causation_id": row.causation_id,
            "actor": row.actor,
            "evidence_references": json.loads(row.evidence_references_json or "[]"),
            "authority_references": authority_references,
            "payload": json.loads(row.payload_json or "{}"),
            "metadata": metadata,
            "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "replayed": replayed,
            "authoritative": False,
        }


class DurableEventSink:
    """EventSink adapter backed by existing platform persistence."""

    def __init__(self, store: Optional[DurableOrganizationalEventStore] = None) -> None:
        self._store = store or DurableOrganizationalEventStore()

    def emit(self, event: OrganizationalEvent) -> None:
        self._store.append(event)
