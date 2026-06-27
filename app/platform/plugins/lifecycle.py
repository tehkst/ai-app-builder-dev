from __future__ import annotations

from dataclasses import replace

from app.platform.plugins.plugin import PlatformPlugin


def activate_plugin(plugin: PlatformPlugin) -> PlatformPlugin:
    return replace(plugin, status="active")


def pause_plugin(plugin: PlatformPlugin) -> PlatformPlugin:
    return replace(plugin, status="paused")


def retire_plugin(plugin: PlatformPlugin) -> PlatformPlugin:
    return replace(plugin, status="retired")
