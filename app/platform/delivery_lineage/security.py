from __future__ import annotations

import re
from typing import Any, Dict, List


_SECRET_PATTERNS = (
    re.compile(r"(?i)(github_pat_[A-Za-z0-9_]+)"),
    re.compile(r"(?i)(sk-[A-Za-z0-9_-]{12,})"),
    re.compile(r"(?i)((?:token|password|secret|authorization|cookie)\s*[=:]\s*)[^\s,;]+"),
)


def safe_text(value: Any, limit: int = 600) -> str:
    text = str(value or "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(_replacement, text)
    return text[:limit]


def safe_references(values: Any) -> List[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    return [safe_text(value, 240) for value in values if value]


def sanitize_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for item in entries:
        item["summary"] = safe_text(item.get("summary"))
        item["error_code"] = safe_text(item.get("error_code"), 160) or None
        for key in (
            "artifact_refs", "repository_refs", "validation_refs",
            "approval_refs", "deployment_refs", "evidence_refs", "input_artifact_refs",
        ):
            item[key] = safe_references(item.get(key))
    return entries


def _replacement(match: re.Match) -> str:
    prefix = match.group(1) if match.lastindex else ""
    if prefix and any(marker in prefix.lower() for marker in ("token", "password", "secret", "authorization", "cookie")):
        return "%s[REDACTED]" % prefix
    return "[REDACTED]"
