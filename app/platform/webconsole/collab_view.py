from __future__ import annotations

from app.platform.collab.collab_models import CollabContext
from app.platform.collab.collab_store import summarize_collab
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_collab_view(context: CollabContext, tenant_id: str) -> ConsoleView:
    summary = summarize_collab(
        context.comments,
        context.mentions,
        context.presences,
        context.timeline,
        context.audit_records,
        tenant_id,
    )
    return ConsoleView(
        view_id="admin_collab",
        title="Collaboration",
        cards=[
            ConsoleCard("comments", "Comments", str(summary.comment_count), "healthy", {}),
            ConsoleCard("mentions", "Mentions", str(summary.mention_count), "healthy", {}),
            ConsoleCard("online", "Online", str(summary.online_count), "healthy", {}),
            ConsoleCard("timeline", "Timeline", str(summary.timeline_count), "healthy", {}),
            ConsoleCard("audit", "Audit", str(summary.audit_count), "healthy", {}),
            ConsoleCard("high", "High Audit", str(summary.high_audit_count), "healthy", {}),
        ],
    )
