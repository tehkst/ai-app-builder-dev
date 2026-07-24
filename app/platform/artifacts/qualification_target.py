from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LEGACY_GENERATED_APP = ROOT / "generated_apps" / "crm-saas-multifile-001"
GENERATED_APP_PATH_ENV = "AFOS_GENERATED_APP_PATH"


def generated_app_path(value: str | None = None) -> Path:
    configured = str(value or os.getenv(GENERATED_APP_PATH_ENV) or "").strip()
    if not configured:
        return LEGACY_GENERATED_APP
    path = Path(configured).expanduser()
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()
