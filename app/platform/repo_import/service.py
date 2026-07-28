from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.platform.auth.service import require_founder
from app.platform.credential_vault.service import resolve_credential
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformImportedRepository
from app.platform.repo_import import CONTRACT

GITHUB_API = "https://api.github.com"
DEFAULT_CREDENTIAL_KEY = "GITHUB_IMPORT_TOKEN"
FALLBACK_CREDENTIAL_KEY = "GITHUB_TOKEN"
MAX_FILE_BYTES = 200_000

_OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def import_repository(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()

    owner = str(payload.get("owner") or "").strip()
    repo = str(payload.get("repo") or "").strip()
    credential_key_name = str(payload.get("credential_key_name") or "").strip() or _default_credential_key()
    if not _OWNER_PATTERN.match(owner) or not _REPO_PATTERN.match(repo):
        return {"contract": CONTRACT, "status": "invalid", "error": "owner and repo must be valid GitHub name segments."}

    token = resolve_credential(credential_key_name)
    if not token:
        return {
            "contract": CONTRACT,
            "status": "missing-credential",
            "error": "%s is not configured. Add it under Settings > Credentials first." % credential_key_name,
        }

    repo_result = _github_get("/repos/%s/%s" % (owner, repo), token)
    if not repo_result["ok"]:
        return {
            "contract": CONTRACT,
            "status": "connect_failed",
            "error": repo_result.get("error") or "Could not reach the repository with this credential.",
            "status_code": repo_result.get("status_code"),
        }
    repo_data = repo_result["data"]
    default_branch = str(repo_data.get("default_branch") or "main")

    contents_result = _github_get("/repos/%s/%s/contents/" % (owner, repo), token)
    top_level = []
    if contents_result["ok"] and isinstance(contents_result["data"], list):
        top_level = [
            {"name": item.get("name"), "type": item.get("type"), "path": item.get("path")}
            for item in contents_result["data"][:100]
        ]

    full_name = "%s/%s" % (owner, repo)
    create_platform_tables()
    with PlatformSessionLocal() as db:
        row = db.query(PlatformImportedRepository).filter(PlatformImportedRepository.full_name == full_name).first()
        if row is None:
            row = PlatformImportedRepository(full_name=full_name, owner=owner, repo=repo)
            db.add(row)
        row.default_branch = default_branch
        row.credential_key_name = credential_key_name
        row.status = "connected"
        row.last_error = None
        row.top_level_entries_json = json.dumps(top_level)
        row.imported_by = founder.get("email") or "founder"
        row.last_synced_at = datetime.now(timezone.utc)
        db.commit()

    return {
        "contract": CONTRACT,
        "status": "connected",
        "full_name": full_name,
        "default_branch": default_branch,
        "top_level_entries": top_level,
    }


def list_imported_repositories(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()
    create_platform_tables()
    with PlatformSessionLocal() as db:
        rows = db.query(PlatformImportedRepository).order_by(PlatformImportedRepository.created_at.desc()).all()
        repositories = [_serialize(row) for row in rows]
    return {"contract": CONTRACT, "status": "ready", "repositories": repositories}


def inspect_imported_repository(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()
    full_name = str(payload.get("full_name") or "").strip()
    path = str(payload.get("path") or "").strip().lstrip("/")
    create_platform_tables()
    with PlatformSessionLocal() as db:
        row = db.query(PlatformImportedRepository).filter(PlatformImportedRepository.full_name == full_name).first()
        if row is None:
            return {"contract": CONTRACT, "status": "not_found", "full_name": full_name}
        credential_key_name = row.credential_key_name
        owner, repo = row.owner, row.repo

    token = resolve_credential(credential_key_name)
    if not token:
        return {"contract": CONTRACT, "status": "missing-credential", "error": "%s is not configured." % credential_key_name}

    encoded_path = urllib.parse.quote(path) if path else ""
    result = _github_get("/repos/%s/%s/contents/%s" % (owner, repo, encoded_path), token)
    if not result["ok"]:
        return {"contract": CONTRACT, "status": "fetch_failed", "error": result.get("error"), "status_code": result.get("status_code")}

    data = result["data"]
    if isinstance(data, list):
        return {
            "contract": CONTRACT,
            "status": "directory",
            "full_name": full_name,
            "path": path,
            "entries": [{"name": item.get("name"), "type": item.get("type"), "path": item.get("path")} for item in data[:200]],
        }

    size = int(data.get("size") or 0)
    if size > MAX_FILE_BYTES:
        return {
            "contract": CONTRACT,
            "status": "file_too_large",
            "full_name": full_name,
            "path": path,
            "size": size,
            "limit": MAX_FILE_BYTES,
        }
    content = ""
    if data.get("encoding") == "base64" and data.get("content"):
        try:
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        except Exception:
            content = ""
    return {"contract": CONTRACT, "status": "file", "full_name": full_name, "path": path, "size": size, "content": content}


def remove_imported_repository(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()
    full_name = str(payload.get("full_name") or "").strip()
    create_platform_tables()
    with PlatformSessionLocal() as db:
        row = db.query(PlatformImportedRepository).filter(PlatformImportedRepository.full_name == full_name).first()
        if row is None:
            return {"contract": CONTRACT, "status": "not_found", "full_name": full_name}
        db.delete(row)
        db.commit()
    return {"contract": CONTRACT, "status": "removed", "full_name": full_name}


def build_imported_repositories_context() -> Dict[str, Any]:
    """Internal, unauthenticated builder for Jarvis's ContextRetriever - matches the
    pattern of organization_console.build_internal_organisation_context()."""
    try:
        create_platform_tables()
        with PlatformSessionLocal() as db:
            rows = db.query(PlatformImportedRepository).order_by(PlatformImportedRepository.created_at.desc()).limit(20).all()
            repositories = [_serialize(row) for row in rows]
    except Exception as exc:
        return {"status": "unavailable", "detail": type(exc).__name__}
    return {"status": "ready", "repository_count": len(repositories), "repositories": repositories}


def _serialize(row: PlatformImportedRepository) -> Dict[str, Any]:
    try:
        top_level = json.loads(row.top_level_entries_json or "[]")
    except json.JSONDecodeError:
        top_level = []
    return {
        "full_name": row.full_name,
        "owner": row.owner,
        "repo": row.repo,
        "default_branch": row.default_branch,
        "status": row.status,
        "last_error": row.last_error,
        "top_level_entries": top_level,
        "imported_by": row.imported_by,
        "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None,
    }


def _default_credential_key() -> str:
    if resolve_credential(DEFAULT_CREDENTIAL_KEY):
        return DEFAULT_CREDENTIAL_KEY
    return FALLBACK_CREDENTIAL_KEY


def _github_get(path: str, token: str) -> Dict[str, Any]:
    request = urllib.request.Request(
        "%s%s" % (GITHUB_API, path),
        headers={
            "Authorization": "Bearer %s" % token,
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-software-factory-repo-import",
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
    except Exception as exc:
        return {"ok": False, "status_code": None, "error": type(exc).__name__}


def _unauthorised() -> Dict[str, Any]:
    return {
        "contract": CONTRACT,
        "status": "unauthorised",
        "authenticated": False,
        "error": "Founder authentication is required for repository import.",
    }
