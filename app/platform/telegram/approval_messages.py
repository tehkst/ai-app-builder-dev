import html
from typing import Any, Dict


def _safe(value: Any) -> str:
    if value is None:
        return "-"
    return html.escape(str(value))


def build_approval_message(approval: Dict[str, Any]) -> str:
    title = _safe(approval.get("title"))
    approval_id = _safe(approval.get("approval_id"))
    status = _safe(approval.get("status"))
    risk_level = _safe(approval.get("risk_level"))
    requested_by = _safe(approval.get("requested_by"))
    action_type = _safe(approval.get("action_type"))
    source_type = _safe(approval.get("source_type"))
    source_id = _safe(approval.get("source_id"))
    description = _safe(approval.get("description"))

    return (
        "<b>AI Software Factory Approval Request</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"<b>ID:</b> {approval_id}\n"
        f"<b>Status:</b> {status}\n"
        f"<b>Risk:</b> {risk_level}\n"
        f"<b>Requested by:</b> {requested_by}\n"
        f"<b>Action:</b> {action_type}\n"
        f"<b>Source:</b> {source_type} / {source_id}\n\n"
        f"<b>Description:</b>\n{description}"
    )


def build_approval_keyboard(approval_id: str) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "Approve", "callback_data": f"approval:approve:{approval_id}"},
                {"text": "Reject", "callback_data": f"approval:reject:{approval_id}"},
            ],
            [
                {
                    "text": "Request Changes",
                    "callback_data": f"approval:request-changes:{approval_id}",
                }
            ],
        ]
    }
