from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    actor_user_id: str
    action: str
    resource: str
    tenant_id: str
    metadata: Dict[str, object]


def record_audit_event(events: List[AuditEvent], event: AuditEvent) -> List[AuditEvent]:
    return events + [event]


def audit_events_for_tenant(events: List[AuditEvent], tenant_id: str) -> List[AuditEvent]:
    return [event for event in events if event.tenant_id == tenant_id]
