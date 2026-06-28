from __future__ import annotations

from typing import List

from app.platform.deployment.deployment_models import DeploymentResult
from app.platform.integration.shared_components import status_card
from app.platform.integration.ui_models import SharedStatusCard
from app.platform.operations.deployment_dashboard import deployment_panel
from app.platform.operations.health_dashboard import health_panel


def admin_health_cards(checks: List[dict]) -> List[SharedStatusCard]:
    panel = health_panel(checks)
    return [status_card(panel.panel_id, panel.title, panel.value, panel.status)]


def admin_deployment_cards(results: List[DeploymentResult]) -> List[SharedStatusCard]:
    panel = deployment_panel(results)
    return [status_card(panel.panel_id, panel.title, panel.value, panel.status)]
