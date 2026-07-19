from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.platform.persistence.database import PlatformSessionLocal
from app.platform.persistence.execution_migrations import run_execution_layer_migrations
from app.platform.persistence.models import PlatformExecutionEvidence


def record_execution_evidence(payload: Dict[str, Any], decision: Dict[str, Any], outcome: Dict[str, Any]) -> Dict[str, Any]:
    run_execution_layer_migrations()
    record = PlatformExecutionEvidence(
        evidence_id="EXEC-EVIDENCE-%s" % uuid.uuid4().hex[:16].upper(),
        mission_id=str(payload.get("mission_id") or "unknown"),
        actor=str(decision.get("actor") or payload.get("actor") or "mission_control"),
        capability=str(decision.get("capability") or payload.get("capability") or "unknown"),
        requested_action=str(decision.get("requested_action") or "unknown"),
        authorization_json=json.dumps(decision, sort_keys=True, default=str),
        outcome=str(outcome.get("status") or "unknown"),
        artifact_json=json.dumps(_artifacts(outcome), sort_keys=True, default=str),
    )
    with PlatformSessionLocal() as db:
        db.add(record)
        db.commit()
        return {"evidence_id": record.evidence_id, "recorded_at": record.created_at.isoformat()}


def latest_execution_evidence(capability: str) -> Optional[Dict[str, Any]]:
    run_execution_layer_migrations()
    with PlatformSessionLocal() as db:
        record = db.query(PlatformExecutionEvidence).filter_by(capability=capability).order_by(PlatformExecutionEvidence.id.desc()).first()
        if not record:
            return None
        return {"evidence_id": record.evidence_id, "outcome": record.outcome, "observed_at": record.created_at.isoformat()}


def _artifacts(outcome: Dict[str, Any]) -> Dict[str, Any]:
    keys = ("commit", "commit_sha", "merge_commit_sha", "pr_number", "pull_request_number", "pull_request_url", "revision_name", "target_revision", "overall_result", "release_url", "tag_name")
    return {key: outcome.get(key) for key in keys if outcome.get(key) is not None}
