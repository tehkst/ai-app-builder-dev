from __future__ import annotations

from typing import List

from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def executive_dashboard(cards: List[ConsoleCard]) -> ConsoleView:
    return ConsoleView(
        view_id="executive_dashboard",
        title="Executive Dashboard",
        cards=cards,
    )


def summary_card(card_id: str, title: str, value: str, status: str = "healthy") -> ConsoleCard:
    return ConsoleCard(
        card_id=card_id,
        title=title,
        value=value,
        status=status,
        metadata={},
    )
