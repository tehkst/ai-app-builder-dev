from __future__ import annotations

from app.platform.launch.launch_models import LaunchContext
from app.platform.launch.launch_store import launch_is_ready, summarize_launch
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_launch_view(context: LaunchContext) -> ConsoleView:
    summary = summarize_launch(context.documentation, context.packages, context.signals)
    ready = "ready" if launch_is_ready(context.signals) else "blocked"
    return ConsoleView(
        view_id="admin_launch",
        title="Version 1.0 Launch",
        cards=[
            ConsoleCard("docs", "Documentation", str(summary.ready_documentation_count), "healthy", {}),
            ConsoleCard("packages", "Published Packages", str(summary.published_package_count), "healthy", {}),
            ConsoleCard("signals", "Required Signals", str(summary.ready_required_signal_count), "healthy", {}),
            ConsoleCard("launch", "Launch Status", ready, "healthy", {}),
        ],
    )
