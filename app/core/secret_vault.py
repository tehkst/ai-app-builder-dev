from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.kms import kms_configured, unwrap_key, wrap_key

ENVELOPE_VERSION = 1
# Local mode (the founder's Mac, no Cloud KMS): the data key is wrapped with a 256-bit key kept in a
# file only the founder can read. Set only by the always-on service (app/platform/ops); on Cloud Run
# the variable is absent and Cloud KMS is required as before.
LOCAL_KEY_FILE_ENV = "ASF_VAULT_KEY_FILE"


def _local_key_path() -> Path | None:
    value = os.getenv(LOCAL_KEY_FILE_ENV)
    return Path(value).expanduser() if value else None


def vault_mode() -> str:
    """"kms", "local" or "none". Cloud KMS wins when both are configured."""
    if kms_configured():
        return "kms"
    return "local" if _local_key_path() else "none"


def vault_configured() -> bool:
    return vault_mode() != "none"


def _local_key(create: bool) -> bytes:
    path = _local_key_path()
    if path is None:
        raise RuntimeError(f"{LOCAL_KEY_FILE_ENV} is not configured.")
    if not path.exists():
        if not create:
            raise RuntimeError("The local vault key file is missing; saved credentials can't be decrypted.")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass  # created by a concurrent save: use that one
        else:
            with os.fdopen(fd, "wb") as handle:
                handle.write(base64.b64encode(AESGCM.generate_key(bit_length=256)) + b"\n")
    if path.stat().st_mode & 0o077:
        raise RuntimeError(f"{path} must be readable only by you (chmod 600).")
    key = base64.b64decode(path.read_bytes().strip())
    if len(key) != 32:
        raise RuntimeError("The local vault key file is damaged.")
    return key


def _wrap_local(data_key: bytes) -> bytes:
    nonce = os.urandom(12)
    return nonce + AESGCM(_local_key(create=True)).encrypt(nonce, data_key, b"asf-local-kek")


def _unwrap_local(wrapped: bytes) -> bytes:
    return AESGCM(_local_key(create=False)).decrypt(wrapped[:12], wrapped[12:], b"asf-local-kek")


def encrypt_secret(plaintext: str) -> str:
    """Envelope-encrypt a secret: a fresh AES-256-GCM data key encrypts the value locally,
    then that data key is wrapped by the Cloud KMS key-encryption key (or, in local mode, the
    founder's local key file) before storage.
    Only the wrapped key and ciphertext are ever persisted — the plaintext key never is.
    """
    if not vault_configured():
        raise RuntimeError(
            "Secret encryption is not configured (KMS_KEY_NAME or ASF_VAULT_KEY_FILE missing). "
            "Refusing to store an unencrypted secret."
        )

    data_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    ciphertext = AESGCM(data_key).encrypt(nonce, plaintext.encode("utf-8"), None)
    mode = vault_mode()
    wrapped_key = wrap_key(data_key) if mode == "kms" else _wrap_local(data_key)

    envelope = {
        "v": ENVELOPE_VERSION,
        "kek": mode,
        "wrapped_dek": base64.b64encode(wrapped_key).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(envelope)


def decrypt_secret(envelope_json: str) -> str:
    envelope = json.loads(envelope_json)
    wrapped_key = base64.b64decode(envelope["wrapped_dek"])
    nonce = base64.b64decode(envelope["nonce"])
    ciphertext = base64.b64decode(envelope["ciphertext"])

    # Envelopes written before local mode have no "kek" field: they were all Cloud KMS.
    data_key = _unwrap_local(wrapped_key) if envelope.get("kek") == "local" else unwrap_key(wrapped_key)
    plaintext = AESGCM(data_key).decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
