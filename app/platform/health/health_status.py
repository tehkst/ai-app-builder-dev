from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List

from app.platform.config import load_settings


_STARTED_AT = time.time()


@dataclass(frozen=True)
class ComponentStatus:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class ServiceStatus:
    status: str
    service: str
    version: str
    uptime_seconds: int
    components: List[ComponentStatus]

    def to_dict(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "service": self.service,
            "version": self.version,
            "uptime_seconds": self.uptime_seconds,
            "components": [component.__dict__ for component in self.components],
        }


def _uptime_seconds() -> int:
    return int(time.time() - _STARTED_AT)


def build_health_status() -> Dict[str, object]:
    settings = load_settings(validate=False)
    status = ServiceStatus(
        status="healthy",
        service=settings.app_name,
        version="1.0.0",
        uptime_seconds=_uptime_seconds(),
        components=[
            ComponentStatus("application", "healthy", "Application process is running."),
        ],
    )
    return status.to_dict()


def build_readiness_status() -> Dict[str, object]:
    settings = load_settings(validate=False)
    components = [
        ComponentStatus("configuration", "ready", "Configuration loaded."),
        ComponentStatus("database", "configured", settings.database_url.split("://", 1)[0]),
        ComponentStatus("redis", "configured", settings.redis_url.split("://", 1)[0]),
    ]
    status = ServiceStatus(
        status="ready",
        service=settings.app_name,
        version="1.0.0",
        uptime_seconds=_uptime_seconds(),
        components=components,
    )
    return status.to_dict()
