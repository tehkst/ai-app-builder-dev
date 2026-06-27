from __future__ import annotations

from app.platform.plugins.capability_adapter import has_capability, matching_plugins
from app.platform.plugins.lifecycle import pause_plugin
from app.platform.plugins.plugin_loader import load_plugin, plugin_loaded
from app.platform.plugins.plugin_metrics import plugin_metrics
from app.platform.plugins.plugin_registry import plugin_registry
from app.platform.plugins.provider_registry import capabilities_for_provider


def main() -> None:
    assert "runtime" in capabilities_for_provider("platform_core")

    plugins = plugin_registry()
    assert "platform_core_plugin" in plugins, plugins

    plugin = load_plugin("platform_core_plugin")
    assert plugin is not None
    assert plugin_loaded("platform_core_plugin") is True

    assert has_capability("runtime") is True
    assert matching_plugins("runtime") == ["platform_core_plugin"]

    paused = pause_plugin(plugin)
    assert paused.status == "paused", paused

    metrics = plugin_metrics([plugin, paused])
    assert metrics["plugin_count"] == 2, metrics
    assert metrics["active_plugin_count"] == 1, metrics
    assert metrics["paused_plugin_count"] == 1, metrics

    print("PLUGIN CHECK PASSED")


if __name__ == "__main__":
    main()
