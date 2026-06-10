from pathlib import Path


APPROVAL_DASHBOARD_TEMPLATE = Path(__file__).with_name("templates") / "approval_dashboard.html"
APPROVAL_DASHBOARD_HTML = APPROVAL_DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
