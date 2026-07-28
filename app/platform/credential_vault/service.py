from __future__ import annotations

import os
from typing import Any, Dict, Optional

from app.core.secret_vault import decrypt_secret, encrypt_secret, vault_configured
from app.platform.auth.service import require_founder
from app.platform.credential_vault import CONTRACT
from app.platform.persistence.audit import create_audit_event
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformCredential

# Every entry here needs a real consumer wired to resolve_credential() before it's
# added - this list is deliberately not open-ended, so nothing in the vault UI is
# decorative.
KNOWN_CREDENTIALS = {
    "GITHUB_TOKEN": "GitHub Token (platform repository)",
    "GITHUB_IMPORT_TOKEN": "GitHub Token (imported repositories)",
    "OPENAI_API_KEY": "OpenAI API Key",
    "DEEPSEEK_API_KEY": "DeepSeek API Key",
}


def list_credentials(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()
    create_platform_tables()
    with PlatformSessionLocal() as db:
        rows = {row.key_name: row for row in db.query(PlatformCredential).all()}
    credentials = []
    for key_name, display_name in KNOWN_CREDENTIALS.items():
        row = rows.get(key_name)
        env_configured = bool(os.getenv(key_name))
        source = "vault" if row else ("environment" if env_configured else "none")
        credentials.append({
            "key_name": key_name,
            "display_name": display_name,
            "configured": bool(row) or env_configured,
            "source": source,
            "masked_value": _mask(row.last_four if row else None, source=source),
            "updated_at": row.updated_at.isoformat() if row else None,
        })
    return {
        "contract": CONTRACT,
        "status": "ready",
        "vault_configured": vault_configured(),
        "credentials": credentials,
    }


def save_credential(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()
    key_name = str(payload.get("key_name") or "").strip()
    value = str(payload.get("value") or "")
    if key_name not in KNOWN_CREDENTIALS:
        return {"contract": CONTRACT, "status": "invalid", "error": "Unknown credential key."}
    if not value.strip():
        return {"contract": CONTRACT, "status": "invalid", "error": "value is required."}
    if not vault_configured():
        return {
            "contract": CONTRACT,
            "status": "encryption_not_configured",
            "error": "KMS_KEY_NAME is not configured, so credentials cannot be safely encrypted at rest yet.",
        }
    try:
        envelope = encrypt_secret(value)
    except Exception as exc:
        return {
            "contract": CONTRACT,
            "status": "encryption_failed",
            "error": "Could not reach Cloud KMS to encrypt this value (%s). No credential was saved." % type(exc).__name__,
        }
    create_platform_tables()
    with PlatformSessionLocal() as db:
        row = db.query(PlatformCredential).filter(PlatformCredential.key_name == key_name).first()
        if row is None:
            row = PlatformCredential(key_name=key_name, display_name=KNOWN_CREDENTIALS[key_name])
            db.add(row)
        row.envelope_json = envelope
        row.last_four = value.strip()[-4:]
        row.display_name = KNOWN_CREDENTIALS[key_name]
        row.updated_by = founder.get("email") or "founder"
        db.commit()
        last_four = row.last_four
        create_audit_event(
            db,
            event_type="credential_saved",
            status="success",
            actor_type="founder",
            actor_id=founder.get("email"),
            route="/mission-control/credentials/save",
            metadata={"key_name": key_name},
        )
    return {"contract": CONTRACT, "status": "saved", "key_name": key_name, "masked_value": _mask(last_four)}


def reveal_credential(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()
    key_name = str(payload.get("key_name") or "").strip()
    if key_name not in KNOWN_CREDENTIALS:
        return {"contract": CONTRACT, "status": "invalid", "error": "Unknown credential key."}
    create_platform_tables()
    with PlatformSessionLocal() as db:
        row = db.query(PlatformCredential).filter(PlatformCredential.key_name == key_name).first()
        if row is None:
            env_value = os.getenv(key_name)
            if not env_value:
                return {"contract": CONTRACT, "status": "not_configured", "key_name": key_name}
            _audit_reveal(db, founder, key_name, source="environment")
            return {"contract": CONTRACT, "status": "revealed", "key_name": key_name, "value": env_value, "source": "environment"}
        try:
            value = decrypt_secret(row.envelope_json)
        except Exception as exc:
            return {"contract": CONTRACT, "status": "decrypt_error", "error": type(exc).__name__}
        _audit_reveal(db, founder, key_name, source="vault")
        return {"contract": CONTRACT, "status": "revealed", "key_name": key_name, "value": value, "source": "vault"}


def delete_credential(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()
    key_name = str(payload.get("key_name") or "").strip()
    create_platform_tables()
    with PlatformSessionLocal() as db:
        row = db.query(PlatformCredential).filter(PlatformCredential.key_name == key_name).first()
        if row is None:
            return {"contract": CONTRACT, "status": "not_found", "key_name": key_name}
        db.delete(row)
        db.commit()
        create_audit_event(
            db,
            event_type="credential_deleted",
            status="success",
            actor_type="founder",
            actor_id=founder.get("email"),
            route="/mission-control/credentials/delete",
            metadata={"key_name": key_name},
        )
    return {"contract": CONTRACT, "status": "deleted", "key_name": key_name}


def resolve_credential(key_name: str) -> Optional[str]:
    """Internal-use resolver: vault first, environment variable fallback.

    No payload/auth - matches the pattern of other internal context builders (e.g.
    organization_console.build_internal_organisation_context). Consumers that read
    GITHUB_TOKEN/OPENAI_API_KEY/etc. should call this instead of os.getenv directly,
    so a credential saved in Settings actually takes effect.
    """
    try:
        create_platform_tables()
        with PlatformSessionLocal() as db:
            row = db.query(PlatformCredential).filter(PlatformCredential.key_name == key_name).first()
            if row is not None:
                return decrypt_secret(row.envelope_json)
    except Exception:
        pass
    return os.getenv(key_name)


def _audit_reveal(db, founder: Dict[str, Any], key_name: str, *, source: str) -> None:
    create_audit_event(
        db,
        event_type="credential_revealed",
        status="success",
        actor_type="founder",
        actor_id=founder.get("email"),
        route="/mission-control/credentials/reveal",
        metadata={"key_name": key_name, "source": source},
    )


def _mask(last_four: Optional[str], *, source: str = "none") -> str:
    if last_four:
        return "••••••••" + last_four
    if source == "environment":
        return "Configured (environment variable)"
    return "Not configured"


def _unauthorised() -> Dict[str, Any]:
    return {
        "contract": CONTRACT,
        "status": "unauthorised",
        "authenticated": False,
        "error": "Founder authentication is required for credential management.",
    }
