from app.platform.persistence.model_definitions.base import Column, DateTime, PlatformBase, String, Text, utc_now


class PlatformCredential(PlatformBase):
    """Founder-scoped, KMS-envelope-encrypted credential (GitHub token, provider API key, etc.).

    The plaintext value is never stored - only the envelope produced by
    app.core.secret_vault.encrypt_secret. last_four is stored separately, in the
    clear, purely so the UI can show a masked preview without decrypting anything.
    """

    __tablename__ = "platform_credentials"

    key_name = Column(String, primary_key=True)
    display_name = Column(String, nullable=False)
    envelope_json = Column(Text, nullable=False)
    last_four = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
