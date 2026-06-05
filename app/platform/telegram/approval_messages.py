import html
import json
from typing import Any, Dict, List


def _safe(value: Any) -> str:
    if value is None:
        return "-"
    return html.escape(str(value))


def _load_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        loaded = json.loads(value)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        return {}
    return {}


def _format_list(title: str, items: List[Any]) -> str:
    if not items:
        return ""

    lines = [f"<b>{_safe(title)}:</b>"]
    for item in items[:6]:
        if isinstance(item, dict):
            reason = item.get("reason") or item
            lines.append(f"- {_safe(reason)}")
        else:
            lines.append(f"- {_safe(item)}")
    return "\n".join(lines)


def _build_requirement_explanation(approval: Dict[str, Any]) -> str:
    payload = _load_json(
        approval.get("action_payload")
        or approval.get("action_payload_json")
    )
    input_payload = _load_json(payload.get("input_payload"))
    requirement_analysis = input_payload.get("requirement_analysis") or {}

    if not isinstance(requirement_analysis, dict):
        return ""

    architecture_fit = requirement_analysis.get("architecture_fit")
    core = requirement_analysis.get("core_requirements") or []
    optional = requirement_analysis.get("optional_requirements") or []
    unclear = requirement_analysis.get("unclear_requirements") or []
    conflicts = requirement_analysis.get("conflicts") or []
    noise = requirement_analysis.get("noise") or []
    risks = requirement_analysis.get("risk_flags") or []
    approval_recommended = requirement_analysis.get("approval_recommended")

    parts: List[str] = []

    parts.append("<b>Why approval is needed:</b>")

    if approval_recommended:
        parts.append("- Requirement analysis recommends human approval")

    if architecture_fit:
        parts.append(f"- Architecture fit: {_safe(architecture_fit)}")

    if risks:
        parts.append(_format_list("Risk flags", risks))

    if conflicts:
        parts.append(_format_list("Conflicts / clarification needed", conflicts))

    if unclear:
        parts.append(_format_list("Unclear requirements", unclear))

    if core:
        parts.append(_format_list("Clean core requirements", core))

    if optional:
        parts.append(_format_list("Optional requirements", optional))

    if noise:
        parts.append(_format_list("Possible noise ignored", noise))

    return "\n".join(part for part in parts if part)


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

    requirement_explanation = _build_requirement_explanation(approval)

    message = (
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

    if requirement_explanation:
        message += f"\n\n{requirement_explanation}"

    return message


def build_approval_keyboard(approval_id: str) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "Approve", "callback_data": f"a:ok:{approval_id}"},
                {"text": "Reject", "callback_data": f"a:no:{approval_id}"},
            ],
            [
                {
                    "text": "Request Changes",
                    "callback_data": f"a:chg:{approval_id}",
                }
            ],
        ]
    }
