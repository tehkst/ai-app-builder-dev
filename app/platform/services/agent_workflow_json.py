from __future__ import annotations

import json
from typing import Any, Dict


def json_size_bytes(value: Any) -> int:
    return len(json.dumps(value, sort_keys=True, default=str).encode("utf-8"))


def summarize_oversized_value(value: Any, *, max_bytes: int) -> Dict[str, Any]:
    return {
        "truncated": True,
        "reason": "max_json_bytes_exceeded",
        "original_json_bytes": json_size_bytes(value),
        "max_json_bytes": max_bytes,
        "summary_type": type(value).__name__,
    }
