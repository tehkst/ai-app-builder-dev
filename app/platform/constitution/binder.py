from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.platform.constitution.runtime import build_constitution_context, get_runtime_constitution


def bind_constitution(payload: dict[str, Any] | None = None, *, surface: str = "runtime") -> dict[str, Any]:
    data = deepcopy(payload or {})
    data["runtime_constitution"] = build_constitution_context()
    data["constitution_binding"] = {
        "surface": surface,
        "status": "constitution-bound",
        "version": data["runtime_constitution"]["version"],
        "source": data["runtime_constitution"]["source"],
        "hash": data["runtime_constitution"]["hash"],
    }
    return data


def constitution_governance_summary(surface: str) -> dict[str, Any]:
    constitution = get_runtime_constitution()
    return {
        "surface": surface,
        "status": "constitution-bound",
        "version": constitution.version,
        "source": constitution.source,
        "hash": constitution.content_hash,
        "loaded": constitution.loaded,
        "approval_policy": constitution.approval_rules,
        "security_policy": constitution.security_rules,
        "engineering_policy": constitution.engineering_rules,
    }
