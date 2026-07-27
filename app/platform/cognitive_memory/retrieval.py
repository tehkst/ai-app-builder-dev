from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.cognitive_memory.edges import edges_for_entity, serialize_edge
from app.platform.cognitive_memory.embeddings import cosine_similarity, deserialize_embedding, generate_embedding
from app.platform.cognitive_memory.entities import (
    DEFAULT_TENANT_SCOPE,
    find_entity_by_name,
    list_entities,
    serialize_entity,
)
from app.platform.cognitive_memory.episodes import serialize_episode
from app.platform.persistence.models import PlatformEntity, PlatformEpisode, PlatformSemanticEmbedding
from app.platform.runtime.ai_provider import AIProviderError


def query_facts(
    db: Session,
    *,
    tenant_id: Optional[str],
    entity_name: Optional[str] = None,
    entity_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Exact-match fact lookup. This is the ONLY grounding source for verified claims -
    the validator never treats episode search results as verified facts, only as supporting
    context."""
    scope = tenant_id or DEFAULT_TENANT_SCOPE
    if entity_name:
        entities = []
        match = find_entity_by_name(db, tenant_id=scope, name=entity_name, type_=entity_type)
        if match:
            entities = [match]
    else:
        entities = list_entities(db, tenant_id=scope, type_=entity_type, limit=200)

    facts: List[Dict[str, Any]] = []
    seen_edge_ids = set()
    entity_by_id: Dict[str, PlatformEntity] = {}
    for entity in entities:
        for edge in edges_for_entity(db, entity_id=entity.entity_id):
            if edge.edge_id in seen_edge_ids:
                continue
            seen_edge_ids.add(edge.edge_id)
            for entity_id in (edge.source_entity_id, edge.target_entity_id):
                if entity_id not in entity_by_id:
                    row = db.query(PlatformEntity).filter(PlatformEntity.entity_id == entity_id).first()
                    if row:
                        entity_by_id[entity_id] = row
            source = entity_by_id.get(edge.source_entity_id)
            target = entity_by_id.get(edge.target_entity_id)
            facts.append(
                {
                    "source": serialize_entity(source) if source else {"entity_id": edge.source_entity_id},
                    "relationship": edge.relationship,
                    "target": serialize_entity(target) if target else {"entity_id": edge.target_entity_id},
                    "confidence": "grounded",
                }
            )
    return facts


def search_episodes(
    db: Session, *, tenant_id: Optional[str], query_text: str, limit: int = 5, candidate_pool: int = 300
) -> List[Dict[str, Any]]:
    """Best-effort semantic recall over episodes. Never treated as verified fact - supporting
    context only. Falls back to plain substring matching if embeddings aren't configured."""
    scope = tenant_id or DEFAULT_TENANT_SCOPE
    try:
        query_vector = generate_embedding(query_text)
    except AIProviderError:
        query_vector = None

    if not query_vector:
        rows = (
            db.query(PlatformEpisode)
            .filter(PlatformEpisode.tenant_id == scope)
            .order_by(PlatformEpisode.created_at.desc())
            .limit(candidate_pool)
            .all()
        )
        lowered = query_text.lower()
        matches = [row for row in rows if lowered in row.content.lower()]
        return [dict(serialize_episode(row), similarity=None) for row in matches[:limit]]

    embedding_rows = (
        db.query(PlatformSemanticEmbedding)
        .filter(PlatformSemanticEmbedding.tenant_id == scope, PlatformSemanticEmbedding.source_type == "episode")
        .order_by(PlatformSemanticEmbedding.created_at.desc())
        .limit(candidate_pool)
        .all()
    )
    scored = []
    for row in embedding_rows:
        vector = deserialize_embedding(row.embedding_vector)
        similarity = cosine_similarity(query_vector, vector)
        scored.append((similarity, row.source_id))
    scored.sort(key=lambda item: item[0], reverse=True)

    results: List[Dict[str, Any]] = []
    for similarity, episode_id in scored[:limit]:
        episode = db.query(PlatformEpisode).filter(PlatformEpisode.episode_id == episode_id).first()
        if episode:
            results.append(dict(serialize_episode(episode), similarity=round(similarity, 4)))
    return results
