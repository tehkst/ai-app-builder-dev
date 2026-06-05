from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.security.rate_limit import PLATFORM_API_RATE_LIMIT, limiter
from app.platform.services.approval_service import (
    approval_to_dict,
    decide_approval,
    get_approval_or_404,
)
from app.platform.telegram.approval_messages import (
    build_approval_keyboard,
    build_approval_message,
)
from app.platform.telegram.client import TelegramClient, TelegramClientError
from app.platform.telegram.config import get_telegram_config

router = APIRouter(prefix="/platform/telegram", tags=["platform-telegram"])


class TelegramTestMessageRequest(BaseModel):
    text: str = "AI Software Factory Telegram gateway test message."


def get_config_or_503():
    config = get_telegram_config()
    if config is None:
        raise HTTPException(
            status_code=503,
            detail="Telegram is not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID.",
        )
    return config


def send_approval_message_to_telegram(db: Session, approval_id: str):
    config = get_config_or_503()
    approval = get_approval_or_404(db, approval_id)
    approval_data = approval_to_dict(approval)
    client = TelegramClient(config)

    try:
        telegram_response = client.send_message(
            text=build_approval_message(approval_data),
            reply_markup=build_approval_keyboard(approval_id),
        )
    except TelegramClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "sent": True,
        "approval": approval_data,
        "telegram": telegram_response.get("result", telegram_response),
    }


@router.post("/test-message")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def send_test_message(
    request: Request,
    payload: TelegramTestMessageRequest,
    platform_admin=Depends(require_platform_admin),
):
    config = get_config_or_503()
    client = TelegramClient(config)
    try:
        response = client.send_message(payload.text)
    except TelegramClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"sent": True, "telegram": response.get("result", response)}


@router.post("/send-approval/{approval_id}")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def send_approval_to_telegram(
    request: Request,
    approval_id: str,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    return send_approval_message_to_telegram(db, approval_id)


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_webhook_secret: str = Header(default=""),
    db: Session = Depends(get_platform_db),
):
    config = get_config_or_503()
    if x_telegram_webhook_secret != config.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")

    payload = await request.json()
    callback_query = payload.get("callback_query")
    if not callback_query:
        return {"ok": True, "ignored": True, "reason": "no_callback_query"}

    callback_query_id = callback_query.get("id")
    callback_data = callback_query.get("data", "")
    parts = callback_data.split(":")
    if len(parts) != 3 or parts[0] != "approval":
        return {"ok": True, "ignored": True, "reason": "unknown_callback_data"}

    action = parts[1]
    approval_id = parts[2]
    status_map = {
        "approve": "approved",
        "reject": "rejected",
        "request-changes": "changes_requested",
    }
    new_status = status_map.get(action)
    if not new_status:
        return {"ok": True, "ignored": True, "reason": "unknown_action"}

    try:
        approval_data = decide_approval(
            db=db,
            approval_id=approval_id,
            new_status=new_status,
            approver_id="telegram_admin",
            decision_note=f"Decision received from Telegram action: {action}",
        )
        ack_text = f"Approval {approval_id} marked as {new_status}."
    except HTTPException as exc:
        approval_data = {"approval_id": approval_id, "error": exc.detail}
        ack_text = str(exc.detail)

    if callback_query_id:
        try:
            TelegramClient(config).answer_callback_query(callback_query_id, ack_text)
        except TelegramClientError:
            pass

    return {"ok": True, "approval": approval_data}
