from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional


def collect_evidence(name: str, collector: Callable[[], Any], checked_at: str) -> Dict[str, Any]:
    try:
        value = collector()
    except Exception as exc:
        return evidence_entry(name, None, checked_at, "unavailable", "%s failed: %s" % (name, type(exc).__name__))
    if isinstance(value, dict) and value.get("status") == "unknown":
        return evidence_entry(name, value, checked_at, "unavailable", str(value.get("unknown_reason") or "No authoritative evidence exists."))
    return evidence_entry(name, value, checked_at, "available", None)


def evidence_entry(name: str, value: Any, checked_at: str, status: str, error_reason: Optional[str]) -> Dict[str, Any]:
    return {
        "status": "observed" if status == "available" else "unknown",
        "registry_status": status,
        "value": value,
        "source": name,
        "evidence_type": "live_read" if status == "available" else "unavailable_evidence",
        "checked_at": checked_at,
        "last_checked": checked_at,
        "freshness": "checked-on-request",
        "fresh": status == "available",
        "confidence": "high" if status == "available" else "none",
        "error_reason": error_reason,
        "unknown_reason": error_reason,
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
