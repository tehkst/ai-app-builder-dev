from __future__ import annotations

from app.platform.lifecycle.lifecycle_catalog import lifecycle_stage_ids, lifecycle_stages
from app.platform.lifecycle.lifecycle_manager import (
    advance_application,
    applications_for_tenant,
    create_lifecycle_application,
    record_lifecycle_event,
    summarize_lifecycle,
)
from app.platform.lifecycle.lifecycle_workflow import run_demo_lifecycle


def main() -> None:
    stages = lifecycle_stages()
    assert len(stages) == 9, stages
    assert lifecycle_stage_ids()[0] == "idea"
    assert lifecycle_stage_ids()[-1] == "continuous_improvement"
    assert stages[6].service_owner == "deployment_platform", stages[6]

    application = create_lifecycle_application(
        "app_lifecycle",
        "tenant_platform",
        "AI Lifecycle App",
        "user_platform_owner",
    )
    assert application.current_stage == "idea", application

    deployed = advance_application(application, "deployment")
    assert deployed.status == "deployed", deployed

    improved = advance_application(deployed, "continuous_improvement")
    assert improved.status == "improving", improved

    event = record_lifecycle_event(
        "event_review",
        improved,
        "user_platform_owner",
        "complete_review",
        metadata={"artifact": "review_record"},
    )
    assert event.stage_id == "continuous_improvement", event
    assert event.metadata["artifact"] == "review_record", event

    summary = summarize_lifecycle([application, improved], [event])
    assert summary.application_count == 2, summary
    assert summary.stage_count == 9, summary
    assert summary.completed_stage_count == 1, summary

    assert applications_for_tenant([application], "tenant_platform") == [application]
    assert applications_for_tenant([application], "other") == []

    plan = run_demo_lifecycle()
    assert plan.application.current_stage == "continuous_improvement", plan
    assert len(plan.events) == 9, plan.events
    assert plan.events[0].stage_id == "idea", plan.events[0]
    assert plan.events[-1].action == "complete_continuous_improvement", plan.events[-1]

    print("LIFECYCLE CHECK PASSED")


if __name__ == "__main__":
    main()
