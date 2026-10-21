"""Token usage, prices and model tiers. Never guesses a price: unpriced models report tokens only."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
PRICING_FILE = REPO_ROOT / "company" / "ai-pricing.yaml"


def _config(path: Optional[Path] = None) -> Dict[str, Any]:
    try:
        return yaml.safe_load((path or PRICING_FILE).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def cost_of(provider: str, model: str, tokens: Dict[str, int], config: Optional[Dict[str, Any]] = None) -> Optional[float]:
    """US dollars for these tokens, or None when the model has no price in the pricing file."""
    price = ((config if config is not None else _config()).get("prices") or {}).get(provider, {}).get(model)
    if not price:
        return None
    cached = min(tokens.get("cached", 0), tokens.get("input", 0))
    fresh = tokens.get("input", 0) - cached
    cached_rate = price.get("cached_input", price.get("input", 0))
    return round((fresh * price.get("input", 0) + cached * cached_rate + tokens.get("output", 0) * price.get("output", 0))
                 / 1_000_000, 6)


def summarize(entries: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Totals over usage entries ({"employee", "provider", "model", "calls", "input", "cached", "output"}).
    cost_usd is the priced part; unpriced lists the models whose tokens couldn't be priced."""
    config = _config()
    total = {"calls": 0, "input": 0, "cached": 0, "output": 0, "cost_usd": 0.0, "unpriced": [], "by_employee": {}}
    for entry in entries:
        tokens = {k: int(entry.get(k) or 0) for k in ("input", "cached", "output")}
        cost = cost_of(entry.get("provider", ""), entry.get("model", ""), tokens, config)
        total["calls"] += int(entry.get("calls") or 0)
        for key, value in tokens.items():
            total[key] += value
        if cost is None:
            label = f"{entry.get('provider')}/{entry.get('model')}"
            if tokens["input"] or tokens["output"]:
                total["unpriced"] = sorted(set(total["unpriced"]) | {label})
        else:
            total["cost_usd"] = round(total["cost_usd"] + cost, 6)
        who = entry.get("employee") or "other"
        mine = total["by_employee"].setdefault(who, {"calls": 0, "tokens": 0, "cost_usd": 0.0})
        mine["calls"] += int(entry.get("calls") or 0)
        mine["tokens"] += tokens["input"] + tokens["output"]
        mine["cost_usd"] = round(mine["cost_usd"] + (cost or 0.0), 6)
    total["tokens"] = total["input"] + total["output"]
    return total


def model_for_tier(provider: str, standard_model: str, tier: str) -> str:
    """The model for an employee's tier within the mission's provider (standard = the given model)."""
    if not tier or tier == "standard":
        return standard_model
    return ((_config().get("tiers") or {}).get(provider) or {}).get(tier) or standard_model
