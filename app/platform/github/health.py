from __future__ import annotations

from typing import Any

from app.platform.github.client import github_get, github_repository, github_token_mounted


def build_github_health() -> dict[str, Any]:
    repo = github_repository()
    if not github_token_mounted():
        return {
            "status": "github-missing-token",
            "connected": False,
            "repository": repo,
            "token_mounted": False,
            "token_visible": False,
        }

    checks = {
        "repository": github_get(f"/repos/{repo}"),
        "branches": github_get(f"/repos/{repo}/branches?per_page=1"),
        "pull_requests": github_get(f"/repos/{repo}/pulls?per_page=1"),
        "actions": github_get(f"/repos/{repo}/actions/runs?per_page=1"),
    }

    connected = all(check.get("ok") for check in checks.values())
    return {
        "status": "github-connected" if connected else "github-partial",
        "connected": connected,
        "repository": repo,
        "token_mounted": True,
        "token_visible": False,
        "checks": _safe_checks(checks),
    }


def _safe_checks(checks: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "ok": bool(result.get("ok")),
            "status_code": result.get("status_code"),
            "error": result.get("error"),
        }
        for name, result in checks.items()
    }
