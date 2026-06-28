from __future__ import annotations

from app.platform.onboarding.onboarding_models import OnboardingContext
from app.platform.onboarding.onboarding_store import summarize_onboarding
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_onboarding_view(context: OnboardingContext, tenant_id: str) -> ConsoleView:
    summary = summarize_onboarding(context.guides, context.steps, tenant_id)
    return ConsoleView(
        view_id="admin_onboarding",
        title="Onboarding",
        cards=[
            ConsoleCard("guides", "Guides", str(summary.guide_count), "healthy", {}),
            ConsoleCard("steps", "Steps", str(summary.step_count), "healthy", {}),
            ConsoleCard("done", "Done", str(summary.done_count), "healthy", {}),
            ConsoleCard("open", "Open", str(summary.open_count), "healthy", {}),
            ConsoleCard("progress", "Progress", str(summary.progress_percent), "healthy", {}),
        ],
    )
