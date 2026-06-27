from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RegistryResource:
    resource_id: str
    resource_type: str
    name: str
    source: str
    metadata: Dict[str, object]
    active: bool = True
