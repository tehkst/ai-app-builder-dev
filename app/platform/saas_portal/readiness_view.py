from __future__ import annotations

from app.platform.readiness.readiness_models import ReadinessContext
from app.platform.readiness.readiness_store import summarize_readiness
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_readiness_view(context: ReadinessContext) -> PortalView:
    summary = summarize_readiness(context.items, context.environments, context.dependencies, context.performance)
    return PortalView(
        view_id="portal_readiness",
        title="Readiness",
        cards=[
            PortalCard("passed", "Required Passed", str(summary.passed_required_count), "healthy", {}),
            PortalCard("failed", "Required Failed", str(summary.failed_required_count), "healthy", {}),
            PortalCard("perf", "Performance Passed", str(summary.performance_pass_count), "healthy", {}),
        ],
    )
