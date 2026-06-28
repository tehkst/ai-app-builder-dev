from __future__ import annotations

from app.platform.opscenter.opscenter_models import OpsCenterContext
from app.platform.opscenter.opscenter_store import summarize_opscenter
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_opscenter_view(context: OpsCenterContext) -> PortalView:
    summary = summarize_opscenter(context.health, context.jobs, context.logs, context.metrics, context.backups)
    return PortalView(
        view_id="portal_opscenter",
        title="Operations",
        cards=[
            PortalCard("healthy", "Healthy", str(summary.healthy_count), "healthy", {}),
            PortalCard("queued", "Queued Jobs", str(summary.queued_count), "healthy", {}),
            PortalCard("metrics", "Metrics", str(summary.metric_count), "healthy", {}),
            PortalCard("backups", "Backups", str(summary.successful_backup_count), "healthy", {}),
        ],
    )
