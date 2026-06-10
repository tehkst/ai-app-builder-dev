from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class SaaSModuleBlueprintRequest:
    """Input contract for a blueprint-only SaaS module plan."""

    product_name: str
    module_request: str
    target_users: str = ""
    core_features: str = ""
    data_entities: str = ""
    needs_admin: bool = True
    needs_payments: bool = False
    notes: str = ""


