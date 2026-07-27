from __future__ import annotations

import base64
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.kms import kms_configured, unwrap_key, wrap_key

ENVELOPE_VERSION = 1


def vault_configured() -> bool:
    return kms_configured()


def encrypt_secret(plaintext: str) -> str:
    """Envelope-encrypt a secret: a fresh AES-256-GCM data key encrypts the value locally,
    then that data key is wrapped by the Cloud KMS key-encryption key before storage.
    Only the wrapped key and ciphertext are ever persisted — the plaintext key never is.
    """
    if not vault_configured():
        raise RuntimeError(
            "Secret encryption is not configured (KMS_KEY_NAME missing). "
            "Refusing to store an unencrypted secret."
        )

    data_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    ciphertext = AESGCM(data_key).encrypt(nonce, plaintext.encode("utf-8"), None)
    wrapped_key = wrap_key(data_key)

    envelope = {
        "v": ENVELOPE_VERSION,
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

    data_key = unwrap_key(wrapped_key)
    plaintext = AESGCM(data_key).decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
