from __future__ import annotations

from app.platform.release.release_models import ReleaseContext
from app.platform.release.release_store import summarize_release
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_release_view(context: ReleaseContext) -> ConsoleView:
    summary = summarize_release(context.releases, context.versions, context.notes, context.changes)
    return ConsoleView(
        view_id="admin_release",
        title="Release Management",
        cards=[
            ConsoleCard("releases", "Releases", str(summary.release_count), "healthy", {}),
            ConsoleCard("versions", "Supported Versions", str(summary.active_version_count), "healthy", {}),
            ConsoleCard("notes", "Release Notes", str(summary.note_count), "healthy", {}),
            ConsoleCard("changes", "Changes", str(summary.change_count), "healthy", {}),
            ConsoleCard("production", "Production Releases", str(summary.production_ready_count), "healthy", {}),
        ],
    )
