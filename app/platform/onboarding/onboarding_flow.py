from __future__ import annotations

from app.platform.onboarding.onboarding_models import OnboardingContext
from app.platform.onboarding.onboarding_store import make_guide, make_step


def run_demo_onboarding() -> OnboardingContext:
    guides = [
        make_guide("guide_admin", "tenant_platform", "Admin Setup", "admin"),
        make_guide("guide_user", "tenant_platform", "Portal Setup", "portal"),
        make_guide("guide_other", "other_tenant", "Other Setup", "portal"),
    ]
    steps = [
        make_step("step_profile", "tenant_platform", "Complete profile", "account", 1, "done"),
        make_step("step_project", "tenant_platform", "Create first project", "workspace", 2, "done"),
        make_step("step_catalog", "tenant_platform", "Activate catalog item", "catalog", 3),
        make_step("step_notice", "tenant_platform", "Review notices", "notices", 4),
        make_step("step_other", "other_tenant", "Other step", "workspace", 1),
    ]
    return OnboardingContext(guides=guides, steps=steps, metadata={"flow": "onboarding"})
