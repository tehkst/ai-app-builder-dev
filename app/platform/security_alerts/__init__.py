"""Security alert sweep: match published alerts (company/security-alerts.yaml) against client code."""
from app.platform.security_alerts.service import ALERTS_FILE, load_alerts, match_alert, match_inventory, sweep

__all__ = ["ALERTS_FILE", "load_alerts", "match_alert", "match_inventory", "sweep"]
