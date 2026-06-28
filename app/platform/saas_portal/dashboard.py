from __future__ import annotations

from typing import List

from app.platform.saas_portal.portal_models import PortalCard, PortalView


def dashboard_card(card_id: str, title: str, value: str, status: str = "active") -> PortalCard:
    return PortalCard(
        card_id=card_id,
        title=title,
        value=value,
        status=status,
        metadata={},
    )


def customer_dashboard(cards: List[PortalCard]) -> PortalView:
    return PortalView(
        view_id="customer_dashboard",
        title="Dashboard",
        cards=cards,
    )
