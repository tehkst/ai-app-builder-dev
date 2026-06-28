from __future__ import annotations

from app.platform.adminops.adminops_models import ApiKey, AdminOpsContext, FeatureFlag, Integration, TenantSetting, WebhookEndpoint


def run_demo_adminops() -> AdminOpsContext:
    settings = [
        TenantSetting("setting1", "tenant_platform", "default_region", "asia-southeast1", "tenant"),
        TenantSetting("setting2", "tenant_platform", "approval_mode", "manual", "tenant"),
        TenantSetting("setting3", "other_tenant", "default_region", "us-central1", "tenant"),
    ]
    api_keys = [
        ApiKey("key1", "tenant_platform", "Portal Key", "active", ["read", "write"]),
        ApiKey("key2", "tenant_platform", "Old Key", "revoked", ["read"]),
        ApiKey("key3", "other_tenant", "Other Key", "active", ["read"]),
    ]
    integrations = [
        Integration("integration1", "tenant_platform", "github", "connected", ["repo_sync"]),
        Integration("integration2", "tenant_platform", "slack", "pending", ["notify"]),
        Integration("integration3", "other_tenant", "github", "connected", ["repo_sync"]),
    ]
    webhooks = [
        WebhookEndpoint("webhook1", "tenant_platform", "Deploy Hook", "https://example.com/deploy", "active", ["deployment.completed"]),
        WebhookEndpoint("webhook2", "tenant_platform", "Billing Hook", "https://example.com/billing", "paused", ["invoice.created"]),
    ]
    flags = [
        FeatureFlag("flag1", "tenant_platform", "new_workspace", True, 100),
        FeatureFlag("flag2", "tenant_platform", "beta_portal", False, 20),
        FeatureFlag("flag3", "other_tenant", "new_workspace", True, 100),
    ]
    return AdminOpsContext(
        settings=settings,
        api_keys=api_keys,
        integrations=integrations,
        webhooks=webhooks,
        flags=flags,
        metadata={"flow": "adminops_pack"},
    )
