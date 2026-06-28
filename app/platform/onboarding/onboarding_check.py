from __future__ import annotations

from app.platform.onboarding.onboarding_flow import run_demo_onboarding
from app.platform.onboarding.onboarding_store import complete_step, guides_for_tenant, steps_for_tenant, summarize_onboarding


def main() -> None:
    data = run_demo_onboarding()
    assert len(data.guides) == 3, data
    assert len(data.steps) == 5, data

    tenant_guides = guides_for_tenant(data.guides, "tenant_platform")
    assert len(tenant_guides) == 2, tenant_guides

    tenant_steps = steps_for_tenant(data.steps, "tenant_platform")
    assert len(tenant_steps) == 4, tenant_steps
    assert [step.order for step in tenant_steps] == [1, 2, 3, 4], tenant_steps

    completed = complete_step(tenant_steps[2])
    assert completed.status == "done", completed

    summary = summarize_onboarding(data.guides, data.steps, "tenant_platform")
    assert summary.guide_count == 2, summary
    assert summary.step_count == 4, summary
    assert summary.done_count == 2, summary
    assert summary.open_count == 2, summary
    assert summary.progress_percent == 50, summary

    print("ONBOARDING CHECK PASSED")


if __name__ == "__main__":
    main()
