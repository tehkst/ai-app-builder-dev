from app.platform.persistence.model_definitions.base import Column, DateTime, PlatformBase, String, utc_now


class PlatformRuntimeSetting(PlatformBase):
    __tablename__ = "platform_runtime_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
