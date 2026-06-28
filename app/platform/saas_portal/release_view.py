from __future__ import annotations

from app.platform.release.release_models import ReleaseContext
from app.platform.release.release_store import summarize_release
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_release_view(context: ReleaseContext) -> PortalView:
    summary = summarize_release(context.releases, context.versions, context.notes, context.changes)
    return PortalView(
        view_id="portal_release",
        title="Release Notes",
        cards=[
            PortalCard("versions", "Supported Versions", str(summary.active_version_count), "healthy", {}),
            PortalCard("notes", "Release Notes", str(summary.note_count), "healthy", {}),
            PortalCard("changes", "Changes", str(summary.change_count), "healthy", {}),
        ],
    )
