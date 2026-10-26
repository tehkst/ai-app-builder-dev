"""Check for production item 2, saving keys on the founder's Mac: without Cloud KMS, keys saved in
Settings are envelope-encrypted with a local key file (mode 600, made on the first save, refused when
others can read it); the database never holds the plain value; saved keys win over environment
variables; older Cloud KMS envelopes still go to KMS; Cloud KMS wins when both are configured; and
the always-on service turns local mode on. Uses a temporary database and key file only."""
from __future__ import annotations

import json
import os
import stat
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

TMP = Path(tempfile.mkdtemp()).resolve()
os.environ["PLATFORM_DATABASE_URL"] = f"sqlite:///{TMP / 'platform.db'}"
for name in ("KMS_KEY_NAME", "ASF_VAULT_KEY_FILE", "DEEPSEEK_API_KEY"):
    os.environ.pop(name, None)

import app.core.secret_vault as secret_vault  # noqa: E402
from app.platform.auth.service import _sign_claims  # noqa: E402
from app.platform.credential_vault import service  # noqa: E402

VALUE = "sk-test-local-vault-0000-abcd"


def check_modes() -> None:
    assert secret_vault.vault_mode() == "none" and not secret_vault.vault_configured()
    try:
        secret_vault.encrypt_secret("x")
        raise AssertionError("never stores an unencrypted secret")
    except RuntimeError:
        pass
    os.environ["ASF_VAULT_KEY_FILE"] = str(TMP / "vault.key")
    assert secret_vault.vault_mode() == "local"
    os.environ["KMS_KEY_NAME"] = "projects/p/locations/l/keyRings/r/cryptoKeys/k"
    assert secret_vault.vault_mode() == "kms", "Cloud KMS wins when both are configured"
    os.environ.pop("KMS_KEY_NAME")


def check_local_round_trip() -> None:
    key = TMP / "vault.key"
    envelope = secret_vault.encrypt_secret(VALUE)
    assert key.is_file() and stat.S_IMODE(key.stat().st_mode) == 0o600, "made on first save, only you can read it"
    data = json.loads(envelope)
    assert data["kek"] == "local" and VALUE not in envelope
    assert secret_vault.decrypt_secret(envelope) == VALUE
    assert secret_vault.encrypt_secret(VALUE) != envelope, "fresh data key and nonce every time"
    first = key.read_bytes()
    secret_vault.encrypt_secret("again")
    assert key.read_bytes() == first, "the key file is made once, never replaced"

    os.chmod(key, 0o644)
    try:
        secret_vault.decrypt_secret(envelope)
        raise AssertionError("a key file others can read is refused")
    except RuntimeError as exc:
        assert "chmod 600" in str(exc)
    os.chmod(key, 0o600)

    other = TMP / "other.key"
    os.environ["ASF_VAULT_KEY_FILE"] = str(other)
    secret_vault.encrypt_secret("y")  # makes a different key
    try:
        secret_vault.decrypt_secret(envelope)
        raise AssertionError("the wrong key never decrypts")
    except Exception as exc:
        assert type(exc).__name__ == "InvalidTag", type(exc).__name__
    os.environ["ASF_VAULT_KEY_FILE"] = str(key)


def check_kms_envelopes_unchanged() -> None:
    seen = []
    original = secret_vault.unwrap_key
    secret_vault.unwrap_key = lambda wrapped: seen.append(wrapped) or b"\0" * 32
    try:
        legacy = json.dumps({"v": 1, "wrapped_dek": "AAAA", "nonce": "AAAAAAAAAAAAAAAA", "ciphertext": "AAAA"})
        try:
            secret_vault.decrypt_secret(legacy)
        except Exception:
            pass  # fake ciphertext; what matters is where the data key went
        assert seen, "envelopes without a kek field are Cloud KMS ones"
    finally:
        secret_vault.unwrap_key = original


def check_api() -> None:
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    token = _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})
    os.environ["DEEPSEEK_API_KEY"] = "env-value-from-ai-keys"
    listed = service.list_credentials({"token": token})
    assert listed["vault_configured"] and listed["vault_mode"] == "local"
    row = next(c for c in listed["credentials"] if c["key_name"] == "DEEPSEEK_API_KEY")
    assert row["source"] == "environment"
    saved = service.save_credential({"token": token, "key_name": "DEEPSEEK_API_KEY", "value": VALUE})
    assert saved["status"] == "saved" and saved["masked_value"].endswith("abcd"), saved
    assert service.resolve_credential("DEEPSEEK_API_KEY") == VALUE, "a key saved in Settings wins over the env file"
    row = next(c for c in service.list_credentials({"token": token})["credentials"] if c["key_name"] == "DEEPSEEK_API_KEY")
    assert row["source"] == "vault" and VALUE not in json.dumps(row)
    assert VALUE.encode() not in (TMP / "platform.db").read_bytes(), "the database never holds the plain value"
    assert service.reveal_credential({"token": token, "key_name": "DEEPSEEK_API_KEY"})["value"] == VALUE
    assert service.save_credential({"key_name": "DEEPSEEK_API_KEY", "value": "x"})["status"] == "unauthorised"

    # Key file lost (e.g. data restored on another Mac): fall back to the environment, never crash.
    (TMP / "vault.key").rename(TMP / "vault.key.moved")
    assert service.resolve_credential("DEEPSEEK_API_KEY") == "env-value-from-ai-keys"
    (TMP / "vault.key.moved").rename(TMP / "vault.key")


def check_service_env() -> None:
    from app.platform.ops import mac_service

    home = TMP / "asf-home"
    env = mac_service.service_environment(home)
    assert env["ASF_VAULT_KEY_FILE"] == str(home / "vault.key")
    (home).mkdir()
    (home / "ai-keys.env").write_text("ASF_VAULT_KEY_FILE=/somewhere/else.key\n")
    assert mac_service.serve_environment(home)["ASF_VAULT_KEY_FILE"] == str(home / "vault.key")


def main() -> None:
    import shutil

    try:
        check_modes()
        check_local_round_trip()
        check_kms_envelopes_unchanged()
        check_api()
        check_service_env()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    print("LOCAL VAULT CHECK PASSED")


if __name__ == "__main__":
    main()
