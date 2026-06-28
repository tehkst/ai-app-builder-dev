from __future__ import annotations

from app.platform.notify.notify_models import NoticeContext
from app.platform.notify.notify_store import notices_for_tenant, summarize_notices
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_notice_view(context: NoticeContext, tenant_id: str) -> PortalView:
    tenant_notices = notices_for_tenant(context.notices, tenant_id)
    summary = summarize_notices(tenant_notices, context.preferences)
    return PortalView(
        view_id="portal_notices",
        title="Notices",
        cards=[
            PortalCard("notices", "Notices", str(summary.notice_count), "healthy", {}),
            PortalCard("unread", "Unread", str(summary.unread_count), "healthy", {}),
            PortalCard("high", "High", str(summary.high_count), "healthy", {}),
        ],
    )
