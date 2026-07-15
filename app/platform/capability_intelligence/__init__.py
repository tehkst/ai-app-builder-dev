"""Read-only platform capability intelligence."""

from app.platform.capability_intelligence.service import (
    discover_relevant_capabilities,
    get_capability_context,
    get_capability_intelligence_status,
)

__all__ = [
    "discover_relevant_capabilities",
    "get_capability_context",
    "get_capability_intelligence_status",
]
