from __future__ import annotations


TEMPLATE_PATH = 'backend/app/core/config.py'
TEMPLATE_CONTENT = 'from functools import lru_cache\nfrom pathlib import Path\n\nfrom pydantic_settings import BaseSettings\n\n\nBASE_DIR = Path(__file__).resolve().parents[2]\nENV_FILE = BASE_DIR / ".env"\n\n\nclass Settings(BaseSettings):\n    APP_NAME: str = "Generated Enterprise App"\n    DATABASE_URL: str\n    JWT_SECRET_KEY: str\n    JWT_ALGORITHM: str = "HS256"\n    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60\n    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]\n\n    class Config:\n        env_file = str(ENV_FILE)\n\n\n@lru_cache\ndef get_settings():\n    return Settings()\n\n\nsettings = get_settings()\n'
