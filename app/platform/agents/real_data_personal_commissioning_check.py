"""Real-data personal commissioning readiness smoke check.

This check is intentionally safe: it uses realistic internal business prompts but does
not execute generated code, start servers, run migrations, deploy externally, or mutate
production source files. It validates whether the private Railway operator workflow is
ready for Toni to use as a self-building/self-healing system.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


SAFE_INTERNAL_SCENARIOS: list[dict[str, Any]] = [
    {
