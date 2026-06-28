from __future__ import annotations

from app.platform.auth.api_key_provider import issue_api_key
from app.platform.auth.authentication import authenticate_identity
from app.platform.auth.identity_provider import find_identity
from app.platform.billing.billing_workflow import run_demo_billing
from app.platform.deployment.deployment_engine import execute_deployment, fail_deployment
from app.platform.deployment.deployment_planner import build_deployment_plan
from app.platform.lifecycle.lifecycle_workflow import run_demo_lifecycle
from app.platform.saas_portal.api_key_view import api_key_view, api_keys_for_tenant
from app.platform.saas_portal.application_view import application_view, applications_for_tenant
from app.platform.saas_portal.dashboard import customer_dashboard, dashboard_card
from app.platform.saas_portal.deployment_view import portal_deployment_view
from app.platform.saas_portal.lifecycle_view import portal_lifecycle_plan_view, portal_lifecycle_view
from app.platform.saas_portal.navigation import portal_navigation, portal_routes
from app.platform.saas_portal.plan_view import portal_plan_view
from app.platform.saas_portal.portal_models import CustomerApplication, CustomerProject
from app.platform.saas_portal.project_view import project_view, projects_for_tenant
from app.platform.saas_portal.runtime_view import portal_runtime_view
from app.platform.saas_portal.settings_view import settings_view


def main() -> None:
    nav = portal_navigation()
    assert len(nav) >= 9, nav
    assert "/portal/projects" in portal_routes()
    assert "/portal/lifecycle" in portal_routes()
    assert "/portal/account-plan" in portal_routes()
    assert all(page.tenant_scoped for page in nav)

    dashboard = customer_dashboard([
        dashboard_card("apps", "Running Apps", "1"),
        dashboard_card("deployments", "Deployments", "2"),
    ])
    assert dashboard.view_id == "customer_dashboard", dashboard
    assert len(dashboard.cards) == 2, dashboard

    projects = [CustomerProject("project1", "tenant_platform", "AI CRM", "active")]
    scoped_projects = projects_for_tenant(projects, "tenant_platform")
    assert scoped_projects == projects
    projects_view = project_view(scoped_projects)
    assert projects_view.cards[0].value == "1", projects_view

    applications = [CustomerApplication("app1", "project1", "tenant_platform", "AI CRM App", "deployed")]
    scoped_apps = applications_for_tenant(applications, "tenant_platform")
    assert scoped_apps == applications
    apps_view = application_view(scoped_apps)
    assert apps_view.cards[1].value == "1", apps_view

    plan = build_deployment_plan("app", "local", "safe_release")
    done = execute_deployment(plan)
    failed = fail_deployment(plan, "timeout")
    deployments = portal_deployment_view([done, failed])
    assert deployments.cards[1].status == "degraded", deployments

    runtime = portal_runtime_view([], [])
    assert runtime.cards[0].value == "0", runtime

    api_key = issue_api_key("key1", "user_platform_owner", "org_platform", "tenant_platform")
    assert api_keys_for_tenant([api_key], "tenant_platform") == [api_key]
    keys_view = api_key_view([api_key])
    assert keys_view.cards[1].value == "1", keys_view

    identity = find_identity("user_platform_owner")
    auth = authenticate_identity(identity, "org_platform", "tenant_platform")
    settings = settings_view(auth.principal)
    assert settings.cards[2].value == "tenant_platform", settings

    lifecycle_plan = run_demo_lifecycle()
    lifecycle = portal_lifecycle_view(
        [lifecycle_plan.application],
        lifecycle_plan.events,
        "tenant_platform",
    )
    assert lifecycle.view_id == "portal_lifecycle", lifecycle
    assert lifecycle.cards[0].value == "1", lifecycle
    assert lifecycle.cards[2].value == "9", lifecycle

    lifecycle_plan_view = portal_lifecycle_plan_view(lifecycle_plan, "tenant_platform")
    assert len(lifecycle_plan_view.cards) == 9, lifecycle_plan_view
    assert lifecycle_plan_view.cards[-1].status == "healthy", lifecycle_plan_view

    hidden = portal_lifecycle_plan_view(lifecycle_plan, "other_tenant")
    assert hidden.cards == [], hidden

    plan_context = run_demo_billing()
    account_plan = portal_plan_view(plan_context, "tenant_platform")
    assert account_plan.view_id == "portal_plan", account_plan
    assert account_plan.cards[0].value == "1", account_plan
    assert account_plan.cards[1].value == "12", account_plan

    print("SAAS PORTAL CHECK PASSED")


if __name__ == "__main__":
    main()
