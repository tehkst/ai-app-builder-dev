from __future__ import annotations

from typing import Iterable, List, Optional

from app.platform.adminops.adminops_models import ApiKey, AdminOpsSummary, FeatureFlag, Integration, TenantSetting, WebhookEndpoint


def settings_for_tenant(settings: Iterable[TenantSetting], tenant_id: str) -> List[TenantSetting]:
    return [setting for setting in settings if setting.tenant_id == tenant_id]


def find_setting(settings: Iterable[TenantSetting], tenant_id: str, key: str) -> Optional[TenantSetting]:
    for setting in settings:
        if setting.tenant_id == tenant_id and setting.key == key:
            return setting
    return None


def active_api_keys(api_keys: Iterable[ApiKey], tenant_id: str) -> List[ApiKey]:
    return [key for key in api_keys if key.tenant_id == tenant_id and key.status == "active"]


def integrations_for_tenant(integrations: Iterable[Integration], tenant_id: str) -> List[Integration]:
    return [integration for integration in integrations if integration.tenant_id == tenant_id]


def active_webhooks(webhooks: Iterable[WebhookEndpoint], tenant_id: str) -> List[WebhookEndpoint]:
    return [webhook for webhook in webhooks if webhook.tenant_id == tenant_id and webhook.status == "active"]


def enabled_flags(flags: Iterable[FeatureFlag], tenant_id: str) -> List[FeatureFlag]:
    return [flag for flag in flags if flag.tenant_id == tenant_id and flag.enabled]


def toggle_flag(flag: FeatureFlag, enabled: bool) -> FeatureFlag:
    return FeatureFlag(flag.flag_id, flag.tenant_id, flag.name, enabled, flag.rollout)


def summarize_adminops(
    settings: Iterable[TenantSetting],
    api_keys: Iterable[ApiKey],
    integrations: Iterable[Integration],
    webhooks: Iterable[WebhookEndpoint],
    flags: Iterable[FeatureFlag],
    tenant_id: str,
) -> AdminOpsSummary:
    return AdminOpsSummary(
        setting_count=len(settings_for_tenant(settings, tenant_id)),
        active_key_count=len(active_api_keys(api_keys, tenant_id)),
        integration_count=len(integrations_for_tenant(integrations, tenant_id)),
        active_webhook_count=len(active_webhooks(webhooks, tenant_id)),
        enabled_flag_count=len(enabled_flags(flags, tenant_id)),
    )
