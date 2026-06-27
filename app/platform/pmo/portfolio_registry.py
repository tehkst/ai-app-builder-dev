from __future__ import annotations

from typing import Dict, Optional

from app.platform.pmo.models import PortfolioItem
from app.platform.pmo.program_registry import all_programs


PORTFOLIOS: Dict[str, PortfolioItem] = {
    "ai_software_factory": PortfolioItem(
        portfolio_id="ai_software_factory",
        name="AI Software Factory",
        owner="ceo_agent",
        program_ids=list(all_programs().keys()),
        status="active",
    ),
}


def all_portfolios() -> Dict[str, PortfolioItem]:
    return dict(PORTFOLIOS)


def get_portfolio(portfolio_id: str) -> Optional[PortfolioItem]:
    return PORTFOLIOS.get(portfolio_id)
