from __future__ import annotations

import base64
import json
import os

KMS_KEY_NAME_ENV = "KMS_KEY_NAME"


def vault_configured() -> bool:
    return bool(os.getenv(KMS_KEY_NAME_ENV))


def _kms_client():
    from google.cloud import kms

    return kms.KeyManagementServiceClient()


def _wrap_key(plaintext_key: bytes) -> bytes:
    key_name = os.getenv(KMS_KEY_NAME_ENV)
    if not key_name:
        raise RuntimeError("Email credential vault is not configured (KMS_KEY_NAME missing).")
    try:
        response = _kms_client().encrypt(request={"name": key_name, "plaintext": plaintext_key})
        return response.ciphertext
    except Exception as exc:
        raise RuntimeError(f"KMS encrypt failed: {exc}") from exc


def _unwrap_key(wrapped_key: bytes) -> bytes:
    key_name = os.getenv(KMS_KEY_NAME_ENV)
    if not key_name:
        raise RuntimeError("Email credential vault is not configured (KMS_KEY_NAME missing).")
    try:
        response = _kms_client().decrypt(request={"name": key_name, "ciphertext": wrapped_key})
        return response.plaintext
    except Exception as exc:
        raise RuntimeError(f"KMS decrypt failed: {exc}") from exc


def encrypt_secret(plaintext: str) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    data_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    ciphertext = AESGCM(data_key).encrypt(nonce, plaintext.encode("utf-8"), None)
    wrapped_key = _wrap_key(data_key)
    envelope = {
        "v": 1,
        "wrapped_dek": base64.b64encode(wrapped_key).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(envelope)


def decrypt_secret(envelope_json: str) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    envelope = json.loads(envelope_json)
    data_key = _unwrap_key(base64.b64decode(envelope["wrapped_dek"]))
    nonce = base64.b64decode(envelope["nonce"])
    ciphertext = base64.b64decode(envelope["ciphertext"])
    return AESGCM(data_key).decrypt(nonce, ciphertext, None).decode("utf-8")
