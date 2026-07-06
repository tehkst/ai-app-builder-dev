from __future__ import annotations

NAV_ITEMS = [
    {"key": "home", "label": "Home", "status": "operational"},
    {"key": "board", "label": "Board Room", "status": "operational"},
    {"key": "projects", "label": "Projects", "status": "operational"},
    {"key": "workflows", "label": "Workflows", "status": "operational"},
    {"key": "proposals", "label": "Proposals", "status": "operational"},
    {"key": "executions", "label": "Executions", "status": "operational"},
    {"key": "deployments", "label": "Deployments", "status": "operational"},
    {"key": "integrations", "label": "Integrations", "status": "operational"},
    {"key": "agents", "label": "Agents", "status": "operational"},
    {"key": "customers", "label": "Customers", "status": "operational"},
    {"key": "analytics", "label": "Analytics", "status": "operational"},
    {"key": "reports", "label": "Reports", "status": "operational"},
    {"key": "knowledge", "label": "Knowledge", "status": "operational"},
    {"key": "settings", "label": "Settings", "status": "operational"},
]


def build_nav_status():
    return NAV_ITEMS
