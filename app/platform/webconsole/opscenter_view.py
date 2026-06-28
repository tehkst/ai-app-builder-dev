from __future__ import annotations

from app.platform.opscenter.opscenter_models import OpsCenterContext
from app.platform.opscenter.opscenter_store import summarize_opscenter
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_opscenter_view(context: OpsCenterContext) -> ConsoleView:
    summary = summarize_opscenter(context.health, context.jobs, context.logs, context.metrics, context.backups)
    return ConsoleView(
        view_id="admin_opscenter",
        title="Operations Center",
        cards=[
            ConsoleCard("healthy", "Healthy", str(summary.healthy_count), "healthy", {}),
            ConsoleCard("degraded", "Degraded", str(summary.degraded_count), "degraded", {}),
            ConsoleCard("queued", "Queued Jobs", str(summary.queued_count), "healthy", {}),
            ConsoleCard("errors", "Error Logs", str(summary.error_log_count), "degraded", {}),
            ConsoleCard("metrics", "Metrics", str(summary.metric_count), "healthy", {}),
            ConsoleCard("backups", "Backups", str(summary.successful_backup_count), "healthy", {}),
        ],
    )
