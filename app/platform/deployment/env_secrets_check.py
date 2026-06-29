from __future__ import annotations

import os
from pathlib import Path

from app.platform.config.settings import REQUIRED_PRODUCTION_KEYS, load_settings, placeholder_keys, validate_production_env


def assert_contains(path: str, text: str) -> None:
    content = Path(path).read_text()
    assert text in content, "{} missing {}".format(path, text)


def main() -> None:
    assert Path("app/platform/config/settings.py").exists()
    assert Path(".env.example").exists()

    for key in REQUIRED_PRODUCTION_KEYS:
        assert_contains(".env.example", key + "=")

    example = Path(".env.example").read_text()
    assert "DATABASE_URL=" in example
    assert "REDIS_URL=" in example
    assert "SECRET_KEY=change-me" in example

    values = {
        "APP_ENV": "production",
        "APP_NAME": "AI Software Factory",
        "PORT": "8000",
        "LOG_LEVEL": "info",
        "DATABASE_URL": "postgresql+asyncpg://app:strong-password@postgres:5432/ai_software_factory",
        "REDIS_URL": "redis://redis:6379/0",
        "SECRET_KEY": "production-grade-secret-key",
    }
    validate_production_env(values)
    assert placeholder_keys(values) == []

    old_values = {key: os.environ.get(key) for key in values}
    try:
        os.environ.update(values)
        settings = load_settings(validate=True)
        assert settings.app_env == "production", settings
        assert settings.port == 8000, settings
        assert settings.database_url.startswith("postgresql+asyncpg://"), settings
        assert settings.redis_url.startswith("redis://"), settings
    finally:
        for key, old_value in old_values.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value

    print("ENV SECRETS CHECK PASSED")


if __name__ == "__main__":
    main()
