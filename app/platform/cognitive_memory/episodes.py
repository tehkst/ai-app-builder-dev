from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.cognitive_memory.embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    embeddings_configured,
    generate_embedding,
    serialize_embedding,
)
from app.platform.cognitive_memory.entities import DEFAULT_TENANT_SCOPE
from app.platform.persistence.models import PlatformEpisode, PlatformSemanticEmbedding
from app.platform.runtime.ai_provider import AIProviderError


def record_episode(
    db: Session,
    *,
    tenant_id: Optional[str],
    content: str,
    entity_references: Optional[List[str]] = None,
    source_type: str,
    source_id: Optional[str] = None,
    with_embedding: bool = True,
) -> Dict[str, Any]:
    episode = PlatformEpisode(
        episode_id="episode_%s" % uuid.uuid4().hex,
        tenant_id=tenant_id or DEFAULT_TENANT_SCOPE,
        content=str(content or ""),
        entity_references_json=json.dumps(list(entity_references or []), sort_keys=True),
        source_type=source_type,
        source_id=source_id,
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)

    embedding_status = "not_configured"
    if with_embedding and embeddings_configured():
        try:
            vector = generate_embedding(episode.content)
        except AIProviderError as exc:
            embedding_status = "failed: %s" % exc
            vector = None
        if vector:
            record = PlatformSemanticEmbedding(
                embedding_id="embedding_%s" % uuid.uuid4().hex,
                tenant_id=episode.tenant_id,
                source_type="episode",
                source_id=episode.episode_id,
                embedding_model=DEFAULT_EMBEDDING_MODEL,
                embedding_dimensions=len(vector),
                embedding_vector=serialize_embedding(vector),
                metadata_payload={},
            )
            db.add(record)
            db.commit()
            embedding_status = "stored"
        elif embedding_status == "not_configured":
            embedding_status = "unavailable"

    return {"episode": serialize_episode(episode), "embedding_status": embedding_status}


def list_episodes(
    db: Session, *, tenant_id: Optional[str], source_type: Optional[str] = None, limit: int = 100
) -> List[PlatformEpisode]:
    scope = tenant_id or DEFAULT_TENANT_SCOPE
    query = db.query(PlatformEpisode).filter(PlatformEpisode.tenant_id == scope)
    if source_type:
        query = query.filter(PlatformEpisode.source_type == source_type)
    return query.order_by(PlatformEpisode.created_at.desc()).limit(max(1, min(limit, 500))).all()


def serialize_episode(episode: PlatformEpisode) -> Dict[str, Any]:
    try:
        entity_references = json.loads(episode.entity_references_json or "[]")
    except json.JSONDecodeError:
        entity_references = []
    return {
        "episode_id": episode.episode_id,
        "tenant_id": episode.tenant_id,
        "content": episode.content,
        "entity_references": entity_references,
        "source_type": episode.source_type,
        "source_id": episode.source_id,
        "created_at": episode.created_at.isoformat() if episode.created_at else None,
    }
