from __future__ import annotations

from app.platform.billing.billing_workflow import run_demo_billing
from app.platform.deployment.deployment_engine import execute_deployment, fail_deployment
from app.platform.deployment.deployment_planner import build_deployment_plan
from app.platform.lifecycle.lifecycle_workflow import run_demo_lifecycle
from app.platform.operations.health_dashboard import health_panel
from app.platform.plugins.plugin_registry import plugin_registry
from app.platform.registry.registry import base_registry
from app.platform.webconsole.agent_view import agent_detail, agent_view
from app.platform.webconsole.dashboard import executive_dashboard, summary_card
from app.platform.webconsole.deployment_view import deployment_view
from app.platform.webconsole.lifecycle_view import admin_lifecycle_plan_view, admin_lifecycle_view
from app.platform.webconsole.navigation import admin_navigation, navigation_routes
from app.platform.webconsole.operations_view import operations_view
from app.platform.webconsole.plan_view import admin_plan_view
from app.platform.webconsole.plugin_view import plugin_view
from app.platform.webconsole.pmo_view import pmo_view
from app.platform.webconsole.registry_view import registry_view
from app.platform.webconsole.runtime_view import runtime_view


def main() -> None:
    nav = admin_navigation()
    assert len(nav) >= 10, nav
    assert "/admin/operations" in navigation_routes()
    assert "/admin/lifecycle" in navigation_routes()
    assert "/admin/plans" in navigation_routes()
    assert "/admin/agents" in navigation_routes()
    assert next(page for page in nav if page.page_id == "agents").title == "Agent Center"
    assert all(page.admin_only for page in nav)

    dashboard = executive_dashboard([
        summary_card("health", "Health", "healthy"),
        summary_card("incidents", "Open Incidents", "0"),
    ])
    assert dashboard.view_id == "executive_dashboard", dashboard
    assert len(dashboard.cards) == 2, dashboard

    health = health_panel([{"name": "platform", "passed": True}])
    ops = operations_view([health])
    assert ops.title == "Operations", ops
    assert ops.cards[0].status == "healthy", ops

    runtime = runtime_view([], [])
    assert runtime.cards[0].value == "0", runtime

    plan = build_deployment_plan("app", "local", "safe_release")
    done = execute_deployment(plan)
    failed = fail_deployment(plan, "timeout")
    deployments = deployment_view([done, failed])
    assert deployments.cards[1].status == "degraded", deployments

    pmo = pmo_view(1, 2, 3)
    assert pmo.cards[2].value == "3", pmo

    registry = registry_view(base_registry())
    assert registry.cards[0].value == "3", registry

    agents = agent_view(
        runtime_status={
            "cto": {"status": "running", "health": "healthy", "source": "runtime"},
        },
        current_assignments={
            "cto": {"mission_id": "AFOS-001", "task": "Architecture review", "source": "agent_task"},
        },
    )
    assert agents.title == "Agent Center", agents
    assert int(agents.cards[0].value) >= 9, agents
    cto_card = next(card for card in agents.cards if card.card_id == "agent_cto")
    assert cto_card.metadata["current_mission"] == "AFOS-001", cto_card
    assert cto_card.metadata["owns_state"] is False, cto_card

    cto = agent_detail(
        "cto",
        runtime_status={"cto": {"status": "running", "health": "healthy"}},
        current_assignments={"cto": {"mission_id": "AFOS-001", "task": "Architecture review"}},
    )
    assert cto.view_id == "agent_detail", cto
    assert any(card.card_id == "runtime" and card.value == "running" for card in cto.cards)
    assert any(card.card_id == "assignment" and card.value == "AFOS-001" for card in cto.cards)

    plugins = plugin_view(plugin_registry())
    assert plugins.cards[0].value == "1", plugins

    lifecycle_plan = run_demo_lifecycle()
    lifecycle = admin_lifecycle_view([lifecycle_plan.application], lifecycle_plan.events)
    assert lifecycle.view_id == "admin_lifecycle", lifecycle
    assert lifecycle.cards[2].value == "9", lifecycle

    lifecycle_plan_view = admin_lifecycle_plan_view(lifecycle_plan)
    assert lifecycle_plan_view.cards[0].title == "Idea", lifecycle_plan_view
    assert lifecycle_plan_view.cards[-1].status == "healthy", lifecycle_plan_view

    plan_context = run_demo_billing()
    plan_view = admin_plan_view(plan_context)
    assert plan_view.view_id == "admin_plan", plan_view
    assert plan_view.cards[0].value == "3", plan_view
    assert plan_view.cards[2].value == "12", plan_view

    print("ADMIN CONSOLE CHECK PASSED")


if __name__ == "__main__":
    main()
