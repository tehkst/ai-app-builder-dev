from __future__ import annotations

from typing import Iterable, List

from app.platform.onboarding.onboarding_models import OnboardingGuide, OnboardingStep, OnboardingSummary


def make_guide(guide_id: str, tenant_id: str, title: str, audience: str, status: str = "active") -> OnboardingGuide:
    return OnboardingGuide(guide_id, tenant_id, title, audience, status)


def make_step(step_id: str, tenant_id: str, title: str, category: str, order: int, status: str = "open") -> OnboardingStep:
    return OnboardingStep(step_id, tenant_id, title, category, status, order)


def guides_for_tenant(guides: Iterable[OnboardingGuide], tenant_id: str) -> List[OnboardingGuide]:
    return [guide for guide in guides if guide.tenant_id == tenant_id]


def steps_for_tenant(steps: Iterable[OnboardingStep], tenant_id: str) -> List[OnboardingStep]:
    return sorted([step for step in steps if step.tenant_id == tenant_id], key=lambda step: step.order)


def complete_step(step: OnboardingStep) -> OnboardingStep:
    return OnboardingStep(step.step_id, step.tenant_id, step.title, step.category, "done", step.order)


def summarize_onboarding(guides: Iterable[OnboardingGuide], steps: Iterable[OnboardingStep], tenant_id: str) -> OnboardingSummary:
    tenant_guides = guides_for_tenant(guides, tenant_id)
    tenant_steps = steps_for_tenant(steps, tenant_id)
    done_count = len([step for step in tenant_steps if step.status == "done"])
    open_count = len([step for step in tenant_steps if step.status != "done"])
    progress = int((done_count / len(tenant_steps)) * 100) if tenant_steps else 0
    return OnboardingSummary(
        guide_count=len(tenant_guides),
        step_count=len(tenant_steps),
        done_count=done_count,
        open_count=open_count,
        progress_percent=progress,
    )
