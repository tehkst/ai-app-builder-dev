import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformOperationalEvidence


def latest_operational_record(evidence_type: str, scope: Optional[str] = None) -> Optional[Dict[str, Any]]:
    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        query = db.query(PlatformOperationalEvidence).filter(PlatformOperationalEvidence.evidence_type == evidence_type)
        if scope:
            query = query.filter(PlatformOperationalEvidence.scope == scope)
        row = query.order_by(PlatformOperationalEvidence.observed_at.desc()).first()
        if row is None:
            return None
        try:
            payload = json.loads(row.payload_json or "{}")
        except (TypeError, ValueError):
            payload = {}
        return {"evidence_id": row.evidence_id, "status": row.status, "authority": row.authority, "scope": row.scope, "observed_at": _iso(row.observed_at), "payload": payload}
    finally:
        db.close()


def record_operational_evidence(evidence_type: str, authority: str, scope: str, status: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        row = PlatformOperationalEvidence(
            evidence_id="EVIDENCE-%s" % uuid4().hex.upper(), evidence_type=evidence_type,
            authority=authority, scope=scope, status=status,
            payload_json=json.dumps(payload, default=str), observed_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.commit()
        return {"evidence_id": row.evidence_id, "observed_at": _iso(row.observed_at)}
    finally:
        db.close()


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None
