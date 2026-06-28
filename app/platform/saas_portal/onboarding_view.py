from __future__ import annotations

from app.platform.onboarding.onboarding_models import OnboardingContext
from app.platform.onboarding.onboarding_store import summarize_onboarding
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_onboarding_view(context: OnboardingContext, tenant_id: str) -> PortalView:
    summary = summarize_onboarding(context.guides, context.steps, tenant_id)
    return PortalView(
        view_id="portal_onboarding",
        title="Getting Started",
        cards=[
            PortalCard("steps", "Steps", str(summary.step_count), "healthy", {}),
            PortalCard("done", "Done", str(summary.done_count), "healthy", {}),
            PortalCard("progress", "Progress", str(summary.progress_percent), "healthy", {}),
        ],
    )
