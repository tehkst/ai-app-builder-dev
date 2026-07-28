from __future__ import annotations

from typing import Any, Dict, Optional

from app.platform.auth.service import require_founder
from app.platform.cognitive_memory import CONTRACT
from app.platform.cognitive_memory.entities import DEFAULT_TENANT_SCOPE, list_entities, serialize_entity
from app.platform.cognitive_memory.episodes import list_episodes, record_episode, serialize_episode
from app.platform.cognitive_memory.extraction import extract_entities_and_edges, persist_extraction
from app.platform.cognitive_memory.retrieval import query_facts, search_episodes
from app.platform.cognitive_memory.validator import ask_with_validation
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.runtime.ai_provider import AIProviderError


def build_cognitive_memory_summary() -> Dict[str, Any]:
    return {
        "contract": CONTRACT,
        "status": "available",
        "founder_authentication_required": True,
        "layers": {
            "memory": "platform_entities/platform_edges (exact-match facts) + platform_episodes (recall/context)",
            "compute": "runtime.provider_router (swappable OpenAI/DeepSeek)",
            "validation": "claim-extraction + contradiction-check + bounded self-correction loop",
        },
    }


def build_cognitive_memory_context_briefing() -> Dict[str, Any]:
    """Read-only context for the already-authenticated Board Room pipeline.

    Unlike the founder-facing API in this module, this builder takes no payload and
    performs no auth check - it is an internal read used by Jarvis's ContextRetriever,
    matching the signature of every other context builder it sits alongside.
    """
    tenant_id = DEFAULT_TENANT_SCOPE
    try:
        create_platform_tables()
        with PlatformSessionLocal() as db:
            facts = query_facts(db, tenant_id=tenant_id)
            entities = list_entities(db, tenant_id=tenant_id, limit=50)
    except Exception as exc:
        return {"status": "unavailable", "detail": type(exc).__name__}
    return {
        "status": "available",
        "contract": CONTRACT,
        "tenant_id": tenant_id,
        "fact_count": len(facts),
        "facts": facts[:50],
        "entity_count": len(entities),
    }


def query_memory_overview(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    tenant_id = _tenant_scope(payload)
    create_platform_tables()
    with PlatformSessionLocal() as db:
        entities = list_entities(db, tenant_id=tenant_id, limit=100)
        episodes = list_episodes(db, tenant_id=tenant_id, limit=25)
        facts = query_facts(db, tenant_id=tenant_id)
        return {
            "contract": CONTRACT,
            "status": "ready",
            "tenant_id": tenant_id,
            "metrics": {
                "entity_count": len(entities),
                "fact_count": len(facts),
                "episode_count": len(episodes),
            },
            "entities": [serialize_entity(item) for item in entities],
            "recent_episodes": [serialize_episode(item) for item in episodes],
        }


def query_memory_facts(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    tenant_id = _tenant_scope(payload)
    entity_name = str(payload.get("entity_name") or "").strip() or None
    entity_type = str(payload.get("entity_type") or "").strip() or None
    create_platform_tables()
    with PlatformSessionLocal() as db:
        facts = query_facts(db, tenant_id=tenant_id, entity_name=entity_name, entity_type=entity_type)
    return {"contract": CONTRACT, "status": "ready", "tenant_id": tenant_id, "facts": facts}


def search_memory_episodes(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    tenant_id = _tenant_scope(payload)
    query_text = str(payload.get("query_text") or "").strip()
    if not query_text:
        return {"contract": CONTRACT, "status": "invalid", "error": "query_text is required."}
    create_platform_tables()
    with PlatformSessionLocal() as db:
        episodes = search_episodes(db, tenant_id=tenant_id, query_text=query_text, limit=int(payload.get("limit") or 5))
    return {"contract": CONTRACT, "status": "ready", "tenant_id": tenant_id, "episodes": episodes}


def save_fact(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    text = str(payload.get("text") or "").strip()
    if len(text) < 5:
        return {"contract": CONTRACT, "status": "invalid", "error": "text must be at least 5 characters."}
    tenant_id = _tenant_scope(payload)
    try:
        extraction = extract_entities_and_edges(text)
    except AIProviderError as exc:
        return {"contract": CONTRACT, "status": "provider_error", "error": str(exc)}
    if not extraction["entities"] and not extraction["edges"]:
        return {
            "contract": CONTRACT,
            "status": "no_facts_found",
            "message": "No explicit facts were found in the given text.",
        }
    create_platform_tables()
    with PlatformSessionLocal() as db:
        persisted = persist_extraction(db, tenant_id=tenant_id, extraction=extraction)
        episode_result = record_episode(
            db,
            tenant_id=tenant_id,
            content=text,
            entity_references=persisted["entity_ids"],
            source_type="founder_fact",
        )
    return {
        "contract": CONTRACT,
        "status": "saved",
        "tenant_id": tenant_id,
        "entities": persisted["entities"],
        "edges": persisted["edges"],
        "episode": episode_result["episode"],
        "embedding_status": episode_result["embedding_status"],
    }


def ask(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    question = str(payload.get("question") or "").strip()
    if len(question) < 3:
        return {"contract": CONTRACT, "status": "invalid", "error": "question is required."}
    tenant_id = _tenant_scope(payload)
    create_platform_tables()
    with PlatformSessionLocal() as db:
        result = ask_with_validation(db, tenant_id=tenant_id, question=question)
    return dict(result, contract=CONTRACT, tenant_id=tenant_id)


def _tenant_scope(payload: Dict[str, Any]) -> str:
    return str(payload.get("tenant_id") or "").strip() or DEFAULT_TENANT_SCOPE


def _authorise(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    founder = require_founder(payload)
    if founder.get("authorized"):
        return None
    return {
        "contract": CONTRACT,
        "status": "unauthorised",
        "authenticated": False,
        "error": "Founder authentication is required for cognitive memory data.",
    }
