from __future__ import annotations

from typing import Iterable, List

from app.platform.launch.launch_models import DocumentationAsset, LaunchSignal, LaunchSummary, PublishingPackage


def ready_documentation(assets: Iterable[DocumentationAsset]) -> List[DocumentationAsset]:
    return [asset for asset in assets if asset.status == "ready"]


def published_packages(packages: Iterable[PublishingPackage]) -> List[PublishingPackage]:
    return [package for package in packages if package.status == "published"]


def required_signals(signals: Iterable[LaunchSignal]) -> List[LaunchSignal]:
    return [signal for signal in signals if signal.required]


def ready_required_signals(signals: Iterable[LaunchSignal]) -> List[LaunchSignal]:
    return [signal for signal in required_signals(signals) if signal.status == "ready"]


def launch_is_ready(signals: Iterable[LaunchSignal]) -> bool:
    required = required_signals(signals)
    return bool(required) and len(required) == len(ready_required_signals(required))


def summarize_launch(
    documentation: Iterable[DocumentationAsset],
    packages: Iterable[PublishingPackage],
    signals: Iterable[LaunchSignal],
) -> LaunchSummary:
    doc_list = list(documentation)
    package_list = list(packages)
    signal_list = list(signals)
    required = required_signals(signal_list)
    return LaunchSummary(
        documentation_count=len(doc_list),
        ready_documentation_count=len(ready_documentation(doc_list)),
        package_count=len(package_list),
        published_package_count=len(published_packages(package_list)),
        required_signal_count=len(required),
        ready_required_signal_count=len(ready_required_signals(required)),
    )
