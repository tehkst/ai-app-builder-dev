from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformEntity

DEFAULT_TENANT_SCOPE = "platform"


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip().lower())


def canonical_key(tenant_id: Optional[str], type_: str, name: str) -> str:
    return "%s|%s|%s" % (tenant_id or DEFAULT_TENANT_SCOPE, type_.strip().lower(), normalize_name(name))


def find_or_create_entity(
    db: Session,
    *,
    tenant_id: Optional[str],
    name: str,
    type_: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> PlatformEntity:
    scope = tenant_id or DEFAULT_TENANT_SCOPE
    key = canonical_key(scope, type_, name)
    existing = db.query(PlatformEntity).filter(PlatformEntity.canonical_key == key).first()
    if existing:
        if metadata:
            merged = json.loads(existing.metadata_json or "{}")
            merged.update(metadata)
            existing.metadata_json = json.dumps(merged, sort_keys=True)
            db.commit()
            db.refresh(existing)
        return existing
    entity = PlatformEntity(
        entity_id="entity_%s" % uuid.uuid4().hex,
        tenant_id=scope,
        name=str(name).strip(),
        type=type_.strip().lower(),
        canonical_key=key,
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def find_entity_by_name(
    db: Session, *, tenant_id: Optional[str], name: str, type_: Optional[str] = None
) -> Optional[PlatformEntity]:
    scope = tenant_id or DEFAULT_TENANT_SCOPE
    if type_:
        key = canonical_key(scope, type_, name)
        return db.query(PlatformEntity).filter(PlatformEntity.canonical_key == key).first()
    target = normalize_name(name)
    for entity in db.query(PlatformEntity).filter(PlatformEntity.tenant_id == scope).all():
        if normalize_name(entity.name) == target:
            return entity
    return None


def list_entities(
    db: Session, *, tenant_id: Optional[str], type_: Optional[str] = None, limit: int = 200
) -> List[PlatformEntity]:
    scope = tenant_id or DEFAULT_TENANT_SCOPE
    query = db.query(PlatformEntity).filter(PlatformEntity.tenant_id == scope)
    if type_:
        query = query.filter(PlatformEntity.type == type_.strip().lower())
    return query.order_by(PlatformEntity.updated_at.desc()).limit(max(1, min(limit, 500))).all()


def serialize_entity(entity: PlatformEntity) -> Dict[str, Any]:
    try:
        metadata = json.loads(entity.metadata_json or "{}")
    except json.JSONDecodeError:
        metadata = {}
    return {
        "entity_id": entity.entity_id,
        "tenant_id": entity.tenant_id,
        "name": entity.name,
        "type": entity.type,
        "metadata": metadata,
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
    }
