from __future__ import annotations

from app.platform.launch.launch_models import DocumentationAsset, LaunchContext, LaunchSignal, PublishingPackage


def run_demo_launch() -> LaunchContext:
    documentation = [
        DocumentationAsset("doc_arch", "Architecture Guide", "architecture", "ready"),
        DocumentationAsset("doc_api", "API Guide", "api", "ready"),
        DocumentationAsset("doc_user", "User Guide", "user", "ready"),
    ]
    packages = [
        PublishingPackage("pkg_marketplace", "Marketplace Starter Pack", "marketplace", "published"),
        PublishingPackage("pkg_platform", "Platform Core", "production", "published"),
    ]
    signals = [
        LaunchSignal("signal_release", "Release Management", "ready", True),
        LaunchSignal("signal_readiness", "Production Readiness", "ready", True),
        LaunchSignal("signal_marketplace", "Marketplace Publishing", "ready", True),
        LaunchSignal("signal_docs", "Documentation", "ready", True),
        LaunchSignal("signal_banner", "Version 1.0 Banner", "ready", False),
    ]
    return LaunchContext(
        documentation=documentation,
        packages=packages,
        signals=signals,
        metadata={"flow": "launch_pack", "version": "1.0.0"},
    )
