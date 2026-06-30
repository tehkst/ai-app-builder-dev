from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


OPENAI_SECRET_NAME = "OPENAI_API_KEY"


def build_persistent_runtime_summary() -> dict[str, Any]:
    provider = build_ai_provider_status()
    return {
        "company": "AI Software Factory",
        "product": "Persistent Company Runtime",
        "milestone": "GCP-06",
        "status": "persistent-runtime-ready",
        "purpose": "Move company memory, AI provider configuration, and mission workflow execution into GCP runtime foundations.",
        "runtime": {
            "environment": os.getenv("AI_FACTORY_ENV", os.getenv("ENVIRONMENT", "production")),
            "memory_mode": os.getenv("AI_FACTORY_MEMORY_MODE", "repository-backed"),
            "queue_mode": os.getenv("AI_FACTORY_QUEUE_MODE", "repository-backed"),
            "audit_mode": os.getenv("AI_FACTORY_AUDIT_MODE", "repository-backed"),
        },
        "ai_provider": provider,
        "secret_manager": build_secret_manager_status(),
        "endpoints": {
            "runtime": "GET /mission-control/runtime",
            "memory": "GET /mission-control/runtime/memory",
            "ai_provider": "GET /mission-control/runtime/ai-provider",
            "secret_manager": "GET /mission-control/runtime/secrets",
        },
        "next_step": "GCP-07 AI Provider Runtime + Autonomous Mission Worker",
    }


def build_runtime_memory_status() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Persistent Company Runtime",
        "milestone": "GCP-06",
        "status": "memory-foundation-ready",
        "memory_layers": [
            {
                "name": "Company Brain",
                "mode": "repository-backed",
                "purpose": "Durable company knowledge, architecture, decisions, proposals, approvals, missions, and execution artifacts.",
            },
            {
                "name": "Mission Queue",
                "mode": os.getenv("AI_FACTORY_QUEUE_MODE", "repository-backed"),
                "purpose": "Persistent mission and work-package state before introducing async workers.",
            },
            {
                "name": "Audit Trail",
                "mode": os.getenv("AI_FACTORY_AUDIT_MODE", "repository-backed"),
                "purpose": "Immutable trace of founder approvals, agent actions, and runtime decisions.",
            },
        ],
        "future_backends": ["Cloud SQL", "Firestore", "Cloud Tasks", "Pub/Sub", "Vector store"],
        "next_step": "Introduce persistent task records and AI worker leases.",
    }


def build_ai_provider_status() -> dict[str, Any]:
    api_key_configured = bool(os.getenv(OPENAI_SECRET_NAME))
    model = os.getenv("OPENAI_MODEL", "gpt-5.5")
    return {
        "provider": "openai",
        "status": "configured" if api_key_configured else "missing-secret",
        "secret_name": OPENAI_SECRET_NAME,
        "model": model,
        "api_key_present": api_key_configured,
        "api_key_visible": False,
        "routing_mode": "single-provider-foundation",
        "note": "The raw API key must live in Google Secret Manager and be mounted into Cloud Run as OPENAI_API_KEY.",
    }


def build_secret_manager_status() -> dict[str, Any]:
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "unknown"
    return {
        "company": "AI Software Factory",
        "product": "Persistent Company Runtime",
        "milestone": "GCP-06",
        "status": "secret-manager-contract-ready",
        "project_id": project_id,
        "required_secrets": [
            {
                "name": OPENAI_SECRET_NAME,
                "purpose": "Activate OpenAI-powered AI runtime inside GCP.",
                "expected_cloud_run_env": OPENAI_SECRET_NAME,
                "configured": bool(os.getenv(OPENAI_SECRET_NAME)),
            }
        ],
        "setup_hint": "Create secret OPENAI_API_KEY in Google Secret Manager and grant the Cloud Run runtime service account Secret Manager Secret Accessor.",
    }


def build_runtime_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_time = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    event_type = str(payload.get("event_type") or payload.get("type") or "runtime.event").strip()
    actor = str(payload.get("actor") or "system").strip()
    subject = str(payload.get("subject") or "persistent-runtime").strip()
    return {
        "company": "AI Software Factory",
        "product": "Persistent Company Runtime",
        "milestone": "GCP-06",
        "status": "event-recorded-preview",
        "event": {
            "event_type": event_type,
            "actor": actor,
            "subject": subject,
            "timestamp": event_time,
            "metadata": payload.get("metadata") or {},
        },
        "next_step": "Persist runtime events as repository-backed or database-backed audit records.",
    }
