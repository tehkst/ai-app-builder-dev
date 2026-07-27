from __future__ import annotations

import os

KMS_KEY_NAME_ENV = "KMS_KEY_NAME"


def kms_configured() -> bool:
    return bool(os.getenv(KMS_KEY_NAME_ENV))


def _client():
    from google.cloud import kms

    return kms.KeyManagementServiceClient()


def wrap_key(plaintext_key: bytes) -> bytes:
    """Wrap (encrypt) a locally-generated data encryption key with the Cloud KMS key-encryption key.

    The key-encryption key itself never leaves Cloud KMS/HSM in plaintext.
    """
    key_name = os.getenv(KMS_KEY_NAME_ENV)
    if not key_name:
        raise RuntimeError(
            "KMS_KEY_NAME is not configured. Set it to a Cloud KMS CryptoKey resource name "
            "(projects/*/locations/*/keyRings/*/cryptoKeys/*) before storing secrets."
        )
    try:
        client = _client()
        response = client.encrypt(request={"name": key_name, "plaintext": plaintext_key})
        return response.ciphertext
    except Exception as exc:
        raise RuntimeError(f"Cloud KMS encrypt call failed: {type(exc).__name__}") from exc


def unwrap_key(wrapped_key: bytes) -> bytes:
    key_name = os.getenv(KMS_KEY_NAME_ENV)
    if not key_name:
        raise RuntimeError("KMS_KEY_NAME is not configured.")
    try:
        client = _client()
        response = client.decrypt(request={"name": key_name, "ciphertext": wrapped_key})
        return response.plaintext
    except Exception as exc:
        raise RuntimeError(f"Cloud KMS decrypt call failed: {type(exc).__name__}") from exc
