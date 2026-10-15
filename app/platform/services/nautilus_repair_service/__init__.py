"""Nautilus-powered repairs for the generated-app self-healing loop.

Fills the step between "repair plan approved" and "execute approved repair": Nautilus proposes
concrete file changes on a scratch copy, and the existing executor applies them after approval.
See docs/architecture/nautilus.md.
"""
from app.platform.services.nautilus_repair_service.apply import apply_nautilus_repair_proposal
from app.platform.services.nautilus_repair_service.proposal import (
    NAUTILUS_REPAIR_SAFETY_MODE,
    get_nautilus_repair_proposals,
    latest_nautilus_proposal,
    propose_nautilus_repair,
    reset_nautilus_repair_proposals_for_check,
)

__all__ = [
    "NAUTILUS_REPAIR_SAFETY_MODE", "apply_nautilus_repair_proposal", "get_nautilus_repair_proposals",
    "latest_nautilus_proposal", "propose_nautilus_repair", "reset_nautilus_repair_proposals_for_check",
]
