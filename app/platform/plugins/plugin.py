from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PlatformPlugin:
    plugin_id: str
    provider: str
    capabilities: List[str]
    status: str
    version: str
