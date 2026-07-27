from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.cognitive_memory.entities import DEFAULT_TENANT_SCOPE
from app.platform.persistence.models import PlatformEdge


def find_or_create_edge(
    db: Session,
    *,
    tenant_id: Optional[str],
    source_entity_id: str,
    target_entity_id: str,
    relationship: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> PlatformEdge:
    existing = (
        db.query(PlatformEdge)
        .filter(
            PlatformEdge.source_entity_id == source_entity_id,
            PlatformEdge.target_entity_id == target_entity_id,
            PlatformEdge.relationship == relationship.strip().lower(),
        )
        .first()
    )
    if existing:
        return existing
    edge = PlatformEdge(
        edge_id="edge_%s" % uuid.uuid4().hex,
        tenant_id=tenant_id or DEFAULT_TENANT_SCOPE,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        relationship=relationship.strip().lower(),
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


def edges_for_entity(db: Session, *, entity_id: str, relationship: Optional[str] = None) -> List[PlatformEdge]:
    query = db.query(PlatformEdge).filter(
        (PlatformEdge.source_entity_id == entity_id) | (PlatformEdge.target_entity_id == entity_id)
    )
    if relationship:
        query = query.filter(PlatformEdge.relationship == relationship.strip().lower())
    return query.order_by(PlatformEdge.created_at.desc()).all()


def serialize_edge(edge: PlatformEdge) -> Dict[str, Any]:
    try:
        metadata = json.loads(edge.metadata_json or "{}")
    except json.JSONDecodeError:
        metadata = {}
    return {
        "edge_id": edge.edge_id,
        "tenant_id": edge.tenant_id,
        "source_entity_id": edge.source_entity_id,
        "target_entity_id": edge.target_entity_id,
        "relationship": edge.relationship,
        "metadata": metadata,
        "created_at": edge.created_at.isoformat() if edge.created_at else None,
    }
