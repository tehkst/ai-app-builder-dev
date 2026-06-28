from __future__ import annotations

from app.platform.deployment.deployment_engine import execute_deployment, fail_deployment
from app.platform.deployment.deployment_planner import build_deployment_plan
from app.platform.operations.health_dashboard import health_panel
from app.platform.plugins.plugin_registry import plugin_registry
from app.platform.registry.registry import base_registry
from app.platform.webconsole.agent_view import agent_view
from app.platform.webconsole.dashboard import executive_dashboard, summary_card
from app.platform.webconsole.deployment_view import deployment_view
from app.platform.webconsole.navigation import admin_navigation, navigation_routes
from app.platform.webconsole.operations_view import operations_view
from app.platform.webconsole.plugin_view import plugin_view
from app.platform.webconsole.pmo_view import pmo_view
from app.platform.webconsole.registry_view import registry_view
from app.platform.webconsole.runtime_view import runtime_view


def main() -> None:
    nav = admin_navigation()
    assert len(nav) >= 8, nav
    assert "/admin/operations" in navigation_routes()
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

    agents = agent_view(2, 5)
    assert agents.cards[1].value == "5", agents

    plugins = plugin_view(plugin_registry())
    assert plugins.cards[0].value == "1", plugins

    print("ADMIN CONSOLE CHECK PASSED")


if __name__ == "__main__":
    main()
