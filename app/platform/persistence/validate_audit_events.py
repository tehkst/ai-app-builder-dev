import json

from app.platform.persistence.audit import (
    create_audit_event,
    list_audit_events,
)
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables


def validate_audit_events():
    create_platform_tables()
    db = PlatformSessionLocal()

    try:
        event = create_audit_event(
            db,
            event_type="platform_api_auth_success",
            status="success",
            actor_type="platform_admin",
            actor_id="validation-script",
            tenant_id="default-tenant",
            workspace_id="default-workspace",
            project_id="audit-validation-project",
            route="/platform/projects",
            auth_mode="internal_token",
            metadata={
                "source": "validate_audit_events",
            },
        )

        events = list_audit_events(db, limit=10)

        passed = (
            event.id is not None
            and event.event_type == "platform_api_auth_success"
            and event.status == "success"
            and len(events) >= 1
        )

        return {
            "passed": passed,
            "created_event_id": event.id,
            "created_event_type": event.event_type,
            "created_status": event.status,
            "audit_event_count_sample": len(events),
        }

    finally:
        db.close()


def main():
    report = validate_audit_events()
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
