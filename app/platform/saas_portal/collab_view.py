from __future__ import annotations

from app.platform.collab.collab_models import CollabContext
from app.platform.collab.collab_store import summarize_collab
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_collab_view(context: CollabContext, tenant_id: str) -> PortalView:
    summary = summarize_collab(
        context.comments,
        context.mentions,
        context.presences,
        context.timeline,
        context.audit_records,
        tenant_id,
    )
    return PortalView(
        view_id="portal_collab",
        title="Collaboration",
        cards=[
            PortalCard("comments", "Comments", str(summary.comment_count), "healthy", {}),
            PortalCard("mentions", "Mentions", str(summary.mention_count), "healthy", {}),
            PortalCard("online", "Online", str(summary.online_count), "healthy", {}),
            PortalCard("timeline", "Timeline", str(summary.timeline_count), "healthy", {}),
        ],
    )
