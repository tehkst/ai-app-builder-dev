from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from app.platform.runtime.ai_provider import AIProviderError, invoke_openai, provider_configured


OPENAI_SECRET_NAME = "OPENAI_API_KEY"


def build_persistent_runtime_summary() -> dict[str, Any]:
    provider = build_ai_provider_status()
    return {
        "company": "AI Software Factory",
        "product": "Persistent Company Runtime",
        "milestone": "GCP-07",
        "status": "ai-provider-runtime-ready",
        "purpose": "Run AI provider calls and autonomous mission-worker previews inside the GCP runtime.",
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
            "invoke": "POST /mission-control/runtime/ai/invoke",
            "worker_preview": "POST /mission-control/runtime/worker/next-step",
            "secret_manager": "GET /mission-control/runtime/secrets",
        },
        "next_step": "GCP-08 Autonomous Pull Request Generation",
    }


def build_runtime_memory_status() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Persistent Company Runtime",
        "milestone": "GCP-07",
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
                "purpose": "Persistent mission and work-package state before async worker leases.",
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
    api_key_configured = provider_configured()
    model = os.getenv("OPENAI_MODEL", "gpt-5.5")
    return {
        "provider": "openai",
        "status": "configured" if api_key_configured else "missing-secret",
        "secret_name": OPENAI_SECRET_NAME,
        "model": model,
        "api_key_present": api_key_configured,
        "api_key_visible": False,
        "routing_mode": "single-provider-runtime",
        "capabilities": ["text-generation", "planning", "mission-worker-preview"],
        "note": "The raw API key must live in Google Secret Manager and be mounted into Cloud Run as OPENAI_API_KEY.",
    }


def build_secret_manager_status() -> dict[str, Any]:
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "unknown"
    return {
        "company": "AI Software Factory",
        "product": "Persistent Company Runtime",
        "milestone": "GCP-07",
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


def invoke_ai(payload: dict[str, Any]) -> dict[str, Any]:
    invoked_at = _now()
    prompt = str(payload.get("prompt") or "").strip()
    system = str(payload.get("system") or "You are an AI Software Factory runtime agent.").strip()
    model = str(payload.get("model") or os.getenv("OPENAI_MODEL", "gpt-5.5")).strip()
    invocation_id = _id("AICALL", invoked_at, {"prompt": prompt, "model": model})

    if not prompt:
        return {
            "company": "AI Software Factory",
            "product": "AI Provider Runtime",
            "milestone": "GCP-07",
            "status": "invalid-request",
            "error": "prompt is required",
        }

    try:
        result = invoke_openai(prompt=prompt, system=system, model=model)
    except AIProviderError as exc:
        return {
            "company": "AI Software Factory",
            "product": "AI Provider Runtime",
            "milestone": "GCP-07",
            "status": "provider-error",
            "invocation_id": invocation_id,
            "provider": "openai",
            "model": model,
            "error": str(exc),
            "api_key_visible": False,
        }

    return {
        "company": "AI Software Factory",
        "product": "AI Provider Runtime",
        "milestone": "GCP-07",
        "status": result.status,
        "invocation_id": invocation_id,
        "provider": result.provider,
        "model": result.model,
        "output_text": result.output_text,
        "api_key_visible": False,
        "audit": {
            "timestamp": invoked_at,
            "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        },
    }


def build_worker_next_step(payload: dict[str, Any]) -> dict[str, Any]:
    mission_id = str(payload.get("mission_id") or "MISSION-UNSPECIFIED").strip()
    plan_id = str(payload.get("plan_id") or "PLAN-UNSPECIFIED").strip()
    work_package = payload.get("work_package") or payload.get("workPackage") or {}
    worker_role = str(work_package.get("agent_role") or payload.get("agent_role") or "architect").strip()
    worker_prompt = _worker_prompt(mission_id=mission_id, plan_id=plan_id, worker_role=worker_role, work_package=work_package)
    result = invoke_ai(
        {
            "system": "You are an autonomous AI Software Factory worker. Produce concise, structured next actions only.",
            "prompt": worker_prompt,
            "model": payload.get("model") or os.getenv("OPENAI_MODEL", "gpt-5.5"),
        }
    )
    status = "worker-step-ready" if result.get("status") == "completed" else f"worker-{result.get('status', 'unknown')}"
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Mission Worker",
        "milestone": "GCP-07",
        "status": status,
        "mission_id": mission_id,
        "plan_id": plan_id,
        "worker_role": worker_role,
        "provider_result": result,
        "next_step": "Persist worker output and convert it into an execution task record.",
    }


def build_runtime_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_time = _now()
    event_type = str(payload.get("event_type") or payload.get("type") or "runtime.event").strip()
    actor = str(payload.get("actor") or "system").strip()
    subject = str(payload.get("subject") or "persistent-runtime").strip()
    return {
        "company": "AI Software Factory",
        "product": "Persistent Company Runtime",
        "milestone": "GCP-07",
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


def _worker_prompt(*, mission_id: str, plan_id: str, worker_role: str, work_package: dict[str, Any]) -> str:
    return (
        f"Mission: {mission_id}\n"
        f"Plan: {plan_id}\n"
        f"Worker role: {worker_role}\n"
        f"Work package: {json.dumps(work_package, sort_keys=True)}\n\n"
        "Return JSON-like text with: objective, next_actions, risks, validation, handoff. "
        "Do not claim work has been completed; only propose the next executable step."
    )


def _id(prefix: str, timestamp: str, data: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
