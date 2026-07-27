from __future__ import annotations

from typing import Optional

AI_PROVIDER_KEY = "ai_provider"
AI_MODEL_KEY = "ai_model"
FOUNDER_PASSWORD_HASH_KEY = "founder_password_hash"
SMTP_PROVIDER_KEY = "smtp_provider"


def get_setting(key: str) -> Optional[str]:
    from app.platform.persistence.database import PlatformSessionLocal
    from app.platform.persistence.models import PlatformRuntimeSetting

    db = PlatformSessionLocal()
    try:
        row = db.get(PlatformRuntimeSetting, key)
        return row.value if row else None
    finally:
        db.close()


def set_setting(key: str, value: str) -> None:
    from app.platform.persistence.database import PlatformSessionLocal
    from app.platform.persistence.models import PlatformRuntimeSetting

    db = PlatformSessionLocal()
    try:
        row = db.get(PlatformRuntimeSetting, key)
        if row:
            row.value = value
        else:
            db.add(PlatformRuntimeSetting(key=key, value=value))
        db.commit()
    finally:
        db.close()
