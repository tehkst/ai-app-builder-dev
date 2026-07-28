from app.platform.persistence.model_definitions.base import Column, DateTime, Integer, PlatformBase, String, Text, utc_now


class PlatformImportedRepository(PlatformBase):
    """A founder-connected external GitHub repository Jarvis can read and reference.

    Read-only by design: no write-back path exists yet. credential_key_name points at
    the PlatformCredential this repository's requests are authenticated with.
    """

    __tablename__ = "platform_imported_repositories"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, unique=True, index=True, nullable=False)
    owner = Column(String, nullable=False)
    repo = Column(String, nullable=False)
    default_branch = Column(String, nullable=True)
    credential_key_name = Column(String, nullable=False)
    status = Column(String, default="connected", nullable=False)
    last_error = Column(Text, nullable=True)
    top_level_entries_json = Column(Text, default="[]", nullable=False)
    imported_by = Column(String, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
