from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from app.platform.cognitive_memory.edges import find_or_create_edge, serialize_edge
from app.platform.cognitive_memory.entities import find_or_create_entity, serialize_entity
from app.platform.runtime.ai_provider import AIProviderError
from app.platform.runtime.provider_router import invoke_provider

EXTRACTION_SYSTEM_PROMPT = (
    "Extract factual entities and relationships from the given text. "
    "Respond with ONLY valid JSON, no prose, matching exactly this shape: "
    '{"entities": [{"name": string, "type": string}], '
    '"edges": [{"source": string, "target": string, "relationship": string}]}. '
    "Only extract facts that are explicitly stated in the text. "
    "Never infer, guess, or add information that is not directly present in the text. "
    "If the text contains no clear facts, return empty lists for both entities and edges."
)


def extract_entities_and_edges(text: str) -> Dict[str, List[Dict[str, Any]]]:
    result = invoke_provider(provider=None, prompt=text, system=EXTRACTION_SYSTEM_PROMPT, model=None)
    if result.status != "completed":
        raise AIProviderError(result.output_text or ("AI provider returned status: %s" % result.status))
    return _parse_extraction_output(result.output_text)


def _parse_extraction_output(output_text: str) -> Dict[str, List[Dict[str, Any]]]:
    candidate = output_text.strip()
    match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if match:
        candidate = match.group(0)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return {"entities": [], "edges": []}
    entities = parsed.get("entities") if isinstance(parsed, dict) else None
    edges = parsed.get("edges") if isinstance(parsed, dict) else None
    clean_entities = [
        {"name": str(item.get("name")).strip(), "type": str(item.get("type") or "fact").strip()}
        for item in (entities or [])
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]
    clean_edges = [
        {
            "source": str(item.get("source")).strip(),
            "target": str(item.get("target")).strip(),
            "relationship": str(item.get("relationship") or "related_to").strip(),
        }
        for item in (edges or [])
        if isinstance(item, dict) and str(item.get("source") or "").strip() and str(item.get("target") or "").strip()
    ]
    return {"entities": clean_entities, "edges": clean_edges}


def persist_extraction(db, *, tenant_id: str, extraction: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    entity_ids_by_name: Dict[str, str] = {}
    created_entities = []
    for item in extraction.get("entities", []):
        entity = find_or_create_entity(db, tenant_id=tenant_id, name=item["name"], type_=item["type"])
        entity_ids_by_name[item["name"]] = entity.entity_id
        created_entities.append(serialize_entity(entity))

    created_edges = []
    for item in extraction.get("edges", []):
        source_id = entity_ids_by_name.get(item["source"])
        if not source_id:
            source_entity = find_or_create_entity(db, tenant_id=tenant_id, name=item["source"], type_="fact")
            source_id = source_entity.entity_id
            entity_ids_by_name[item["source"]] = source_id
            created_entities.append(serialize_entity(source_entity))
        target_id = entity_ids_by_name.get(item["target"])
        if not target_id:
            target_entity = find_or_create_entity(db, tenant_id=tenant_id, name=item["target"], type_="fact")
            target_id = target_entity.entity_id
            entity_ids_by_name[item["target"]] = target_id
            created_entities.append(serialize_entity(target_entity))
        edge = find_or_create_edge(
            db, tenant_id=tenant_id, source_entity_id=source_id, target_entity_id=target_id,
            relationship=item["relationship"],
        )
        created_edges.append(serialize_edge(edge))

    return {
        "entities": created_entities,
        "edges": created_edges,
        "entity_ids": list(entity_ids_by_name.values()),
    }
