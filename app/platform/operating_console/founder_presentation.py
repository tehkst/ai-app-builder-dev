from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_INTERNAL_KEYS = {"executive_reasoning", "technical_details", "reasoning", "context_snapshot"}


def _without_internal_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _without_internal_fields(item)
            for key, item in value.items()
            if str(key) not in _INTERNAL_KEYS
        }
    if isinstance(value, list):
        return [_without_internal_fields(item) for item in value]
    return value


@dataclass(frozen=True)
class FounderChatPresentation:
    """Founder-safe Board Room contract with no internal reasoning passthrough."""

    status: str
    authenticated: bool
    meeting_id: str
    board_room_response: str
    conversation_intelligence: dict[str, Any]
    action_metadata: dict[str, Any]
    governance: dict[str, Any]
    next_step: str

    def to_dict(self) -> dict[str, Any]:
        presentation = {
            "presentation_contract": "founder-chat-v1",
            "status": self.status,
            "authenticated": self.authenticated,
            "meeting_id": self.meeting_id,
            "board_room_response": self.board_room_response,
            "conversation_intelligence": self.conversation_intelligence,
            "action_metadata": self.action_metadata,
            "governance": self.governance,
            "next_step": self.next_step,
        }
        return _without_internal_fields(presentation)


def present_founder_chat(
    *,
    status: str,
    meeting_id: str,
    board_room_response: str,
    conversation_intelligence: dict[str, Any],
    action_metadata: dict[str, Any],
    governance: dict[str, Any],
    next_step: str,
) -> dict[str, Any]:
    return FounderChatPresentation(
        status=status,
        authenticated=True,
        meeting_id=meeting_id,
        board_room_response=board_room_response,
        conversation_intelligence=conversation_intelligence,
        action_metadata=action_metadata,
        governance=governance,
        next_step=next_step,
    ).to_dict()
