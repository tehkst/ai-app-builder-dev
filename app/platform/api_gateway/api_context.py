from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ApiRequestContext:
    tenant_id: str
    actor_id: str
    request_id: str
    trace_id: str
    idempotency_key: Optional[str] = None

    def valid(self) -> bool:
        return all([self.tenant_id, self.actor_id, self.request_id, self.trace_id])

    def headers(self) -> Dict[str, str]:
        values = {
            "x-tenant-id": self.tenant_id,
            "x-actor-id": self.actor_id,
            "x-request-id": self.request_id,
            "x-trace-id": self.trace_id,
        }
        if self.idempotency_key:
            values["idempotency-key"] = self.idempotency_key
        return values


def context_from_headers(headers: Dict[str, str]) -> ApiRequestContext:
    normalized = {key.lower(): value for key, value in headers.items()}
    return ApiRequestContext(
        tenant_id=normalized.get("x-tenant-id", ""),
        actor_id=normalized.get("x-actor-id", ""),
        request_id=normalized.get("x-request-id", ""),
        trace_id=normalized.get("x-trace-id", ""),
        idempotency_key=normalized.get("idempotency-key"),
    )
