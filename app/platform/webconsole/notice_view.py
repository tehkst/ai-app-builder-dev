from __future__ import annotations

from app.platform.notify.notify_models import NoticeContext
from app.platform.notify.notify_store import summarize_notices
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_notice_view(context: NoticeContext) -> ConsoleView:
    summary = summarize_notices(context.notices, context.preferences)
    return ConsoleView(
        view_id="admin_notices",
        title="Notices",
        cards=[
            ConsoleCard("notices", "Notices", str(summary.notice_count), "healthy", {}),
            ConsoleCard("unread", "Unread", str(summary.unread_count), "healthy", {}),
            ConsoleCard("sent", "Sent", str(summary.sent_count), "healthy", {}),
            ConsoleCard("high", "High", str(summary.high_count), "healthy", {}),
            ConsoleCard("channels", "Channels", str(summary.channel_count), "healthy", {}),
        ],
    )
