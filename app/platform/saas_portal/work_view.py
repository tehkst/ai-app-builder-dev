from __future__ import annotations

from app.platform.saas_portal.portal_models import PortalCard, PortalView
from app.platform.work.work_models import WorkContext
from app.platform.work.work_store import items_for_tenant, summarize_work


def portal_work_view(context: WorkContext, tenant_id: str) -> PortalView:
    rows = items_for_tenant(context.items, tenant_id)
    row_ids = {row.item_id for row in rows}
    row_steps = [step for step in context.steps if step.item_id in row_ids]
    row_notes = [note for note in context.notes if note.item_id in row_ids]
    summary = summarize_work(rows, row_steps, row_notes)
    return PortalView(
        view_id="portal_work",
        title="Work",
        cards=[
            PortalCard("items", "Items", str(summary.item_count), "healthy", {}),
            PortalCard("open", "Open", str(summary.open_count), "healthy", {}),
            PortalCard("steps", "Steps", str(summary.step_count), "healthy", {}),
        ],
    )
