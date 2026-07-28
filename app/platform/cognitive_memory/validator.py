from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.platform.cognitive_memory.entities import normalize_name
from app.platform.cognitive_memory.episodes import record_episode
from app.platform.cognitive_memory.retrieval import query_facts, search_episodes
from app.platform.runtime.ai_provider import AIProviderError
from app.platform.runtime.provider_router import invoke_provider

MAX_CORRECTION_ATTEMPTS = 2

ANSWER_SYSTEM_PROMPT = (
    "You are answering a question using ONLY the verified facts listed below, plus your own "
    "general reasoning. Never state something as a known fact about this platform or its "
    "entities unless it appears in the verified facts. If information relevant to the question "
    "is not in the verified facts, say plainly that it is not verified/known, rather than "
    "guessing or inventing it."
)

CLAIM_EXTRACTION_SYSTEM_PROMPT = (
    "Restate the factual claims made in the given analysis as a JSON object with a single key "
    '"claims", a list of {"subject": string, "predicate": string, "object": string} triples. '
    "Only include claims presented as established facts about specific named things - skip "
    "hedged/uncertain statements, opinions, and general reasoning. "
    "Respond with ONLY the JSON object, no prose. If there are no such claims, return "
    '{"claims": []}.'
)


def ask_with_validation(db, *, tenant_id: str, question: str) -> Dict[str, Any]:
    facts = _relevant_facts(db, tenant_id=tenant_id, question=question)
    supporting_episodes = search_episodes(db, tenant_id=tenant_id, query_text=question, limit=3)

    facts_text = _format_facts(facts) or "No verified facts are currently stored for this scope."
    prompt = "Verified facts:\n%s\n\nQuestion: %s" % (facts_text, question)

    try:
        analysis = invoke_provider(provider=None, prompt=prompt, system=ANSWER_SYSTEM_PROMPT, model=None)
    except AIProviderError as exc:
        return {"status": "provider_error", "error": str(exc), "facts_used": facts}
    if analysis.status != "completed":
        return {"status": "provider_error", "error": analysis.output_text or analysis.status, "facts_used": facts}

    answer_text = analysis.output_text
    correction_history: List[Dict[str, Any]] = []
    claims: List[Dict[str, str]] = []
    contradictions: List[Dict[str, Any]] = []

    for attempt in range(1, MAX_CORRECTION_ATTEMPTS + 1):
        claims = extract_claims(answer_text)
        contradictions = check_contradictions(claims, facts)
        if not contradictions:
            break
        correction_history.append({"attempt": attempt, "contradictions": contradictions})
        correction_prompt = (
            "Your previous analysis contained claims that contradict the verified facts.\n\n"
            "Contradictions found:\n%s\n\n"
            "Verified facts:\n%s\n\n"
            "Original analysis:\n%s\n\n"
            "Revise the analysis so it matches the verified facts exactly. Keep everything else "
            "that was correct."
        ) % (_format_contradictions(contradictions), facts_text, answer_text)
        try:
            revised = invoke_provider(provider=None, prompt=correction_prompt, system=ANSWER_SYSTEM_PROMPT, model=None)
        except AIProviderError as exc:
            correction_history[-1]["revision_error"] = str(exc)
            break
        if revised.status != "completed":
            correction_history[-1]["revision_error"] = revised.output_text or revised.status
            break
        answer_text = revised.output_text

    episode_result = record_episode(
        db,
        tenant_id=tenant_id,
        content="Q: %s\nA: %s" % (question, answer_text),
        entity_references=[fact["source"].get("entity_id") for fact in facts if fact["source"].get("entity_id")],
        source_type="validated_query",
        with_embedding=True,
    )

    return {
        "status": "answered",
        "answer": answer_text,
        "facts_used": facts,
        "supporting_episodes": supporting_episodes,
        "claims_checked": claims,
        "self_corrected": bool(correction_history and not contradictions),
        "correction_attempts": len(correction_history),
        "correction_history": correction_history,
        "unresolved_contradictions": contradictions,
        "episode": episode_result["episode"],
    }


def _relevant_facts(db, *, tenant_id: str, question: str) -> List[Dict[str, Any]]:
    all_facts = query_facts(db, tenant_id=tenant_id)
    lowered = question.lower()
    matched = [
        fact
        for fact in all_facts
        if fact["source"].get("name") and fact["source"]["name"].lower() in lowered
        or fact["target"].get("name") and fact["target"]["name"].lower() in lowered
    ]
    return matched if matched else all_facts[:50]


def _format_facts(facts: List[Dict[str, Any]]) -> str:
    lines = []
    for fact in facts:
        source_name = fact["source"].get("name") or fact["source"].get("entity_id")
        target_name = fact["target"].get("name") or fact["target"].get("entity_id")
        lines.append("%s -[%s]-> %s" % (source_name, fact["relationship"], target_name))
    return "\n".join(lines)


def _format_contradictions(contradictions: List[Dict[str, Any]]) -> str:
    lines = []
    for item in contradictions:
        lines.append(
            "Claimed: %s -[%s]-> %s | Verified fact: %s -[%s]-> %s"
            % (
                item["claim"]["subject"], item["claim"]["predicate"], item["claim"]["object"],
                item["claim"]["subject"], item["claim"]["predicate"], item["verified_object"],
            )
        )
    return "\n".join(lines)


def extract_claims(analysis_text: str) -> List[Dict[str, str]]:
    try:
        result = invoke_provider(provider=None, prompt=analysis_text, system=CLAIM_EXTRACTION_SYSTEM_PROMPT, model=None)
    except AIProviderError:
        return []
    if result.status != "completed":
        return []
    candidate = result.output_text.strip()
    match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if match:
        candidate = match.group(0)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return []
    claims = parsed.get("claims") if isinstance(parsed, dict) else None
    if not isinstance(claims, list):
        return []
    return [
        {
            "subject": str(item.get("subject") or "").strip(),
            "predicate": str(item.get("predicate") or "").strip(),
            "object": str(item.get("object") or "").strip(),
        }
        for item in claims
        if isinstance(item, dict) and item.get("subject") and item.get("predicate") and item.get("object")
    ]


def check_contradictions(claims: List[Dict[str, str]], facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    fact_index: Dict[str, str] = {}
    for fact in facts:
        source_name = fact["source"].get("name")
        target_name = fact["target"].get("name")
        if not source_name or not target_name:
            continue
        key = "%s|%s" % (normalize_name(source_name), normalize_name(fact["relationship"]))
        fact_index[key] = target_name

    contradictions = []
    for claim in claims:
        key = "%s|%s" % (normalize_name(claim["subject"]), normalize_name(claim["predicate"]))
        verified_object = fact_index.get(key)
        if verified_object and normalize_name(verified_object) != normalize_name(claim["object"]):
            contradictions.append({"claim": claim, "verified_object": verified_object})
    return contradictions
