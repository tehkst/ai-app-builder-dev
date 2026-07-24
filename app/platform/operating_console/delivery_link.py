from __future__ import annotations

from typing import Any


def link_authority_result(
    payload: dict[str, Any],
    response: dict[str, Any],
    *,
    authority: str,
    event_key: Any,
) -> dict[str, Any]:
    workflow_run_id = str(payload.get("workflow_run_id") or "").strip()
    execution_metadata = (
        payload.get("execution_metadata")
        if isinstance(payload.get("execution_metadata"), dict)
        else {}
    )
    mission_id = str(
        payload.get("mission_id")
        or response.get("mission_id")
        or execution_metadata.get("mission_id")
        or ""
    ).strip()
    if not workflow_run_id or not mission_id or not event_key:
        return response
    from app.platform.operating_console.mission_run_service import (
        record_delivery_authority_result,
    )

    lifecycle = record_delivery_authority_result(
        workflow_run_id=workflow_run_id,
        mission_id=mission_id,
        authority=authority,
        evidence=response,
        event_key=str(event_key),
    )
    return {**response, "mission_lifecycle": lifecycle}
