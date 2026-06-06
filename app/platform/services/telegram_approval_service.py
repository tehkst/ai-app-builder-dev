from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.services.approval_service import (
    approval_to_dict,
    get_approval_or_404,
)
from app.platform.telegram.approval_messages import (
    build_approval_keyboard,
    build_approval_message,
)
from app.platform.telegram.client import TelegramClient, TelegramClientError
from app.platform.telegram.config import get_telegram_config


class TelegramApprovalSendError(RuntimeError):
    pass


def send_approval_to_telegram(
    db: Session,
    approval_id: str,
) -> Dict[str, Any]:
    config = get_telegram_config()
    if config is None:
        raise TelegramApprovalSendError(
            "Telegram is not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID."
        )

    approval = get_approval_or_404(db, approval_id)
    approval_data = approval_to_dict(approval)

    client = TelegramClient(config)

    try:
        telegram_response = client.send_message(
            text=build_approval_message(approval_data),
            reply_markup=build_approval_keyboard(approval_id),
        )
    except TelegramClientError as exc:
        raise TelegramApprovalSendError(str(exc)) from exc

    return {
        "sent": True,
        "approval": approval_data,
        "telegram": telegram_response.get("result", telegram_response),
    }
