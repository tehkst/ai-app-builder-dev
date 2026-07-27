from app.platform.persistence.model_definitions.base import Column, DateTime, Integer, PlatformBase, String, utc_now


class PlatformRuntimeSetting(PlatformBase):
    __tablename__ = "platform_runtime_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class PlatformFounderResetToken(PlatformBase):
    __tablename__ = "platform_founder_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
