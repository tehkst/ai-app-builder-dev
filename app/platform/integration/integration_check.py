from __future__ import annotations

from app.platform.deployment.deployment_engine import execute_deployment
from app.platform.deployment.deployment_planner import build_deployment_plan
from app.platform.integration.admin_integration import admin_deployment_cards, admin_health_cards
from app.platform.integration.api_integration import customer_api_overview
from app.platform.integration.e2e_flow import login_deploy_observe_flow
from app.platform.integration.lifecycle_flow import lifecycle_console_portal_flow
from app.platform.integration.plan_flow import plan_console_portal_flow
from app.platform.integration.registry_navigation import admin_registry_navigation, portal_registry_navigation
from app.platform.integration.shared_components import health_status, status_card
from app.platform.registry.registry import base_registry


def main() -> None:
    card = status_card("health", "Health", "ok", "healthy")
    assert card.status == "healthy", card
    assert health_status(0) == "healthy"
    assert health_status(1) == "degraded"

    registry = base_registry()
    admin_nav = admin_registry_navigation(registry)
    portal_nav = portal_registry_navigation(registry)
    assert len(admin_nav) == len(registry), admin_nav
    assert len(portal_nav) == len(registry), portal_nav
    assert admin_nav[0].audience == "admin"
    assert portal_nav[0].audience == "portal"

    health_cards = admin_health_cards([{"name": "runtime", "passed": True}])
    assert health_cards[0].status == "healthy", health_cards

    plan = build_deployment_plan("app", "local", "safe_release")
    result = execute_deployment(plan)
    deployment_cards = admin_deployment_cards([result])
    assert deployment_cards[0].status == "healthy", deployment_cards

    overview = customer_api_overview()
    assert overview["deployment_plan_count"] >= 1, overview
    assert overview["registry_resource_count"] >= 1, overview

    flow = login_deploy_observe_flow()
    assert flow["authenticated"] is True, flow
    assert flow["deployment_status"] == "completed", flow
    assert flow["operations_status"] == "healthy", flow

    lifecycle_flow = lifecycle_console_portal_flow()
    assert lifecycle_flow["final_stage"] == "continuous_improvement", lifecycle_flow
    assert lifecycle_flow["admin_stage_count"] == 9, lifecycle_flow
    assert lifecycle_flow["portal_stage_count"] == 9, lifecycle_flow
    assert lifecycle_flow["completed_events"] == 9, lifecycle_flow

    plan_flow = plan_console_portal_flow()
    assert plan_flow["plan_count"] == 3, plan_flow
    assert plan_flow["subscription_count"] == 1, plan_flow
    assert plan_flow["admin_card_count"] == 4, plan_flow
    assert plan_flow["portal_card_count"] == 3, plan_flow

    print("INTEGRATION CHECK PASSED")


if __name__ == "__main__":
    main()
