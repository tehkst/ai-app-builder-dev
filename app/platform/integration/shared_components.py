from __future__ import annotations

from app.platform.integration.ui_models import SharedStatusCard


def status_card(card_id: str, title: str, value: str, status: str = "active") -> SharedStatusCard:
    return SharedStatusCard(
        card_id=card_id,
        title=title,
        value=value,
        status=status,
        metadata={},
    )


def health_status(failed_count: int) -> str:
    return "healthy" if failed_count == 0 else "degraded"
