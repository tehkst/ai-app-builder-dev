from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class DocumentationAsset:
    asset_id: str
    title: str
    category: str
    status: str


@dataclass(frozen=True)
class PublishingPackage:
    package_id: str
    name: str
    channel: str
    status: str


@dataclass(frozen=True)
class LaunchSignal:
    signal_id: str
    name: str
    status: str
    required: bool


@dataclass(frozen=True)
class LaunchSummary:
    documentation_count: int
    ready_documentation_count: int
    package_count: int
    published_package_count: int
    required_signal_count: int
    ready_required_signal_count: int


@dataclass(frozen=True)
class LaunchContext:
    documentation: List[DocumentationAsset]
    packages: List[PublishingPackage]
    signals: List[LaunchSignal]
    metadata: Dict[str, object]
