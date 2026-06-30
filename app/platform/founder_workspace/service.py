from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_founder_workspace_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Founder Workspace",
        "purpose": "Founder-facing workspace for ideas, requests, proposals, approvals, and missions.",
        "status": "request-intake-foundation",
        "intake": {
            "endpoint": "/mission-control/requests",
            "method": "POST",
            "storage_target": "company/requests",
            "current_mode": "preview-only",
            "next_step": "GitHub-backed write adapter",
        },
    }


def build_request_intake(payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title") or "Untitled founder request").strip()
    description = str(payload.get("description") or payload.get("request") or "").strip()
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    request_id = "REQ-PREVIEW-0001"
    artifact_path = f"company/requests/{request_id}.md"
    return {
        "company": "AI Software Factory",
        "product": "Founder Workspace",
        "status": "captured-preview",
        "request_id": request_id,
        "artifact_path": artifact_path,
        "title": title,
        "description": description,
        "created_at": created_at,
        "next_step": "GCP-02 GitHub-backed request write adapter",
    }
