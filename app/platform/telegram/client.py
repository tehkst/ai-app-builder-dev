import json
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from app.platform.telegram.config import TelegramConfig


class TelegramClientError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.base_url = f"https://api.telegram.org/bot{config.bot_token}"

    def _post(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/{method}"
        data = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read().decode("utf-8")
        except Exception as exc:
            error_body = ""
            if hasattr(exc, "read"):
                try:
                    error_body = exc.read().decode("utf-8")
                except Exception:
                    error_body = ""
            raise TelegramClientError(
                f"Telegram request failed: {exc}. Body: {error_body}"
            ) from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise TelegramClientError("Telegram returned invalid JSON") from exc

        if not parsed.get("ok"):
            raise TelegramClientError(f"Telegram API error: {parsed}")

        return parsed

    def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "chat_id": chat_id or self.config.admin_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        return self._post("sendMessage", payload)


    def edit_message_text(
        self,
        chat_id: str,
        message_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
        if reply_markup is not None:
            payload["reply_markup"] = (
                "" if reply_markup == {} else json.dumps(reply_markup)
            )
        return self._post("editMessageText", payload)


    def edit_message_reply_markup(
        self,
        chat_id: str,
        message_id: int,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        if reply_markup is not None:
            payload["reply_markup"] = json.dumps(reply_markup)
        return self._post("editMessageReplyMarkup", payload)

    def answer_callback_query(self, callback_query_id: str, text: str) -> Dict[str, Any]:
        return self._post(
            "answerCallbackQuery",
            {
                "callback_query_id": callback_query_id,
                "text": text,
                "show_alert": "false",
            },
        )
