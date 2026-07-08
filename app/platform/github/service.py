from __future__ import annotations

from typing import Any

from app.platform.auth.service import require_founder
from app.platform.github.client import github_repository, github_token_mounted
from app.platform.github.health import build_github_health


def build_github_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Mission Control GitHub Platform",
        "milestone": "MC-GH-01",
        "status": "github-platform-ready",
        "repository": github_repository(),
        "token_mounted": github_token_mounted(),
        "token_visible": False,
        "capabilities": [
            "repository-health",
            "branch-read",
            "pull-request-read",
            "actions-read",
        ],
        "mutation_policy": "disabled-until-founder-approved",
        "next_step": "Add GitHub Control Center after health verification.",
    }


def github_health(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return {"status": "unauthorized", "authenticated": False}

    result = build_github_health()
    result["authenticated"] = True
    return result
