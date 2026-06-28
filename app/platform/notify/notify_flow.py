from __future__ import annotations

from app.platform.notify.notify_models import NoticeContext
from app.platform.notify.notify_store import make_notice, make_preference


def run_demo_notices() -> NoticeContext:
    notices = [
        make_notice("notice1", "tenant_platform", "user_platform_owner", "in_app", "Lifecycle completed", "AI CRM App reached improvement stage.", "medium"),
        make_notice("notice2", "tenant_platform", "user_platform_owner", "email", "Task needs review", "Prepare CRM app is waiting for review.", "high"),
        make_notice("notice3", "tenant_platform", "user_platform_owner", "in_app", "Catalog item active", "AI CRM Starter is ready.", "low", "sent"),
        make_notice("notice4", "other_tenant", "other_user", "in_app", "Other update", "Other tenant update.", "low"),
    ]
    preferences = [
        make_preference("user_platform_owner", "in_app", True),
        make_preference("user_platform_owner", "email", True),
        make_preference("user_platform_owner", "sms", False),
    ]
    return NoticeContext(notices=notices, preferences=preferences, metadata={"flow": "notices"})
