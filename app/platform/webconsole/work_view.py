from __future__ import annotations

from app.platform.webconsole.console_models import ConsoleCard, ConsoleView
from app.platform.work.work_models import WorkContext
from app.platform.work.work_store import summarize_work


def admin_work_view(context: WorkContext) -> ConsoleView:
    summary = summarize_work(context.items, context.steps, context.notes)
    return ConsoleView(
        view_id="admin_work",
        title="Work",
        cards=[
            ConsoleCard("items", "Items", str(summary.item_count), "healthy", {}),
            ConsoleCard("open", "Open", str(summary.open_count), "healthy", {}),
            ConsoleCard("done", "Done", str(summary.done_count), "healthy", {}),
            ConsoleCard("steps", "Steps", str(summary.step_count), "healthy", {}),
            ConsoleCard("notes", "Notes", str(summary.note_count), "healthy", {}),
        ],
    )
