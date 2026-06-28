from __future__ import annotations

from app.platform.adminops.adminops_flow import run_demo_adminops
from app.platform.adminops.adminops_store import (
    active_api_keys,
    active_webhooks,
    enabled_flags,
    find_setting,
    integrations_for_tenant,
    settings_for_tenant,
    summarize_adminops,
    toggle_flag,
)


def main() -> None:
    data = run_demo_adminops()
    assert len(data.settings) == 3, data
    assert len(data.api_keys) == 3, data
    assert len(data.integrations) == 3, data
    assert len(data.webhooks) == 2, data
    assert len(data.flags) == 3, data

    assert len(settings_for_tenant(data.settings, "tenant_platform")) == 2
    assert find_setting(data.settings, "tenant_platform", "default_region").value == "asia-southeast1"
    assert len(active_api_keys(data.api_keys, "tenant_platform")) == 1
    assert len(integrations_for_tenant(data.integrations, "tenant_platform")) == 2
    assert len(active_webhooks(data.webhooks, "tenant_platform")) == 1
    assert len(enabled_flags(data.flags, "tenant_platform")) == 1

    toggled = toggle_flag(data.flags[1], True)
    assert toggled.enabled is True, toggled

    summary = summarize_adminops(data.settings, data.api_keys, data.integrations, data.webhooks, data.flags, "tenant_platform")
    assert summary.setting_count == 2, summary
    assert summary.active_key_count == 1, summary
    assert summary.integration_count == 2, summary
    assert summary.active_webhook_count == 1, summary
    assert summary.enabled_flag_count == 1, summary

    print("ADMINOPS PACK CHECK PASSED")


if __name__ == "__main__":
    main()
