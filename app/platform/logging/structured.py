from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_request_id() -> str:
    return str(uuid.uuid4())


def build_log_record(level: str, message: str, request_id: Optional[str] = None, **fields: object) -> Dict[str, object]:
    record = {
        "timestamp": utc_timestamp(),
        "level": level.lower(),
        "message": message,
    }
    if request_id:
        record["request_id"] = request_id
    record.update(fields)
    return record


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = build_log_record(
            record.levelname,
            record.getMessage(),
            getattr(record, "request_id", None),
            logger=record.name,
        )
        return json.dumps(payload, sort_keys=True)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers = []
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
