from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


GITHUB_API = "https://api.github.com"
DEFAULT_REPOSITORY = "tehkst/ai-app-builder-dev"


def _github_token() -> str | None:
    from app.platform.credential_vault.service import resolve_credential

    return resolve_credential("GITHUB_TOKEN")


def github_token_mounted() -> bool:
    return bool(_github_token())


def github_repository() -> str:
    return os.getenv("GITHUB_REPOSITORY", DEFAULT_REPOSITORY)


def github_get(path: str) -> dict[str, Any]:
    token = _github_token()
    if not token:
        return {"ok": False, "status_code": None, "error": "GITHUB_TOKEN is not mounted"}

    request = urllib.request.Request(
        f"{GITHUB_API}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-software-factory-mission-control",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body) if body else {}
            return {"ok": 200 <= response.status < 300, "status_code": response.status, "data": data}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status_code": exc.code, "error": exc.reason}
    except urllib.error.URLError as exc:
        return {"ok": False, "status_code": None, "error": str(exc.reason)}
