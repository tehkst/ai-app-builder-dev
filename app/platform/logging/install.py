from __future__ import annotations

from fastapi import FastAPI

from app.platform.logging import configure_logging
from app.platform.logging.middleware import request_logging_middleware


def install_request_logging(app: FastAPI, level: str = "info") -> None:
    configure_logging(level)
    app.middleware("http")(request_logging_middleware)
