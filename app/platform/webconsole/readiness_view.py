from __future__ import annotations

from app.platform.readiness.readiness_models import ReadinessContext
from app.platform.readiness.readiness_store import summarize_readiness
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_readiness_view(context: ReadinessContext) -> ConsoleView:
    summary = summarize_readiness(context.items, context.environments, context.dependencies, context.performance)
    return ConsoleView(
        view_id="admin_readiness",
        title="Production Readiness",
        cards=[
            ConsoleCard("items", "Checklist Items", str(summary.item_count), "healthy", {}),
            ConsoleCard("passed", "Required Passed", str(summary.passed_required_count), "healthy", {}),
            ConsoleCard("failed", "Required Failed", str(summary.failed_required_count), "healthy", {}),
            ConsoleCard("env", "Ready Environments", str(summary.environment_ready_count), "healthy", {}),
            ConsoleCard("deps", "Ready Dependencies", str(summary.dependency_ready_count), "healthy", {}),
            ConsoleCard("perf", "Performance Passed", str(summary.performance_pass_count), "healthy", {}),
        ],
    )
