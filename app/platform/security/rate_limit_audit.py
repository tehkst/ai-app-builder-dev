from slowapi import _rate_limit_exceeded_handler

from app.platform.persistence.audit import create_audit_event
from app.platform.persistence.database import PlatformSessionLocal


RATE_LIMIT_EVENT_TYPE = "platform_rate_limit_exceeded"


def get_safe_client_host(request):
    if request.client is None:
        return None

    return request.client.host


def record_rate_limit_audit(request):
    db = PlatformSessionLocal()

    try:
        create_audit_event(
            db,
            event_type=RATE_LIMIT_EVENT_TYPE,
            status="blocked",
            actor_type="unknown",
            route=request.url.path,
            auth_mode="rate_limit",
            metadata={
                "method": request.method,
                "client_host": get_safe_client_host(request),
            },
        )
    finally:
        db.close()


async def audited_rate_limit_exceeded_handler(request, exc):
    record_rate_limit_audit(request)
    return _rate_limit_exceeded_handler(request, exc)
