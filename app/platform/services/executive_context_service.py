from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformContextStore

DEFAULT_SCOPE = "mission_control"
MAX_BODY_CHARS = 1800


def _trim(value: str, limit: int) -> str:
    text = (value or "").strip()
    return text[:limit]


def list_context_items(db: Session, scope: str = DEFAULT_SCOPE, limit: int = 12) -> List[Dict[str, Any]]:
    records = (
        db.query(PlatformContextStore)
        .filter(PlatformContextStore.scope == scope)
        .order_by(PlatformContextStore.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": record.id,
            "scope": record.scope,
            "type": record.kind,
            "title": record.title,
            "body": record.body,
            "source": record.source,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }
        for record in records
    ]


def format_context_block(db: Session, scope: str = DEFAULT_SCOPE, limit: int = 8) -> str:
    items = list_context_items(db=db, scope=scope, limit=limit)
    if not items:
        return "No persistent executive context has been captured yet."
    lines = ["Persistent executive context:"]
    for item in items:
        lines.append(f"- [{item['type']}] {item['title']}: {_trim(item['body'], 360)}")
    return "\n".join(lines)


def capture_context(
    db: Session,
    *,
    title: str,
    body: str,
    kind: str = "conversation_learning",
    source: str = "board_room",
    scope: str = DEFAULT_SCOPE,
) -> Dict[str, Any]:
    clean_title = _trim(title, 220) or "Board Room context"
    clean_body = _trim(body, MAX_BODY_CHARS)
    if not clean_body:
        return {"captured": False, "reason": "empty_body"}

    record = PlatformContextStore(
        scope=scope,
        kind=_trim(kind, 80) or "conversation_learning",
        title=clean_title,
        body=clean_body,
        source=_trim(source, 120) or "board_room",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"captured": True, "id": record.id, "title": record.title, "type": record.kind}


def summarize_exchange_for_context(message: str, response: str) -> str:
    message = _trim(message, 700)
    response = _trim(response, 900)
    return f"Founder asked: {message}\nBoard Room responded: {response}"
