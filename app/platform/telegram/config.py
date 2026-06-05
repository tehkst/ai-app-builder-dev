import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    admin_chat_id: str
    webhook_secret: str


def get_telegram_config() -> Optional[TelegramConfig]:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip()
    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()

    if not bot_token or not admin_chat_id:
        return None

    return TelegramConfig(
        bot_token=bot_token,
        admin_chat_id=admin_chat_id,
        webhook_secret=webhook_secret or "local-telegram-secret",
    )
