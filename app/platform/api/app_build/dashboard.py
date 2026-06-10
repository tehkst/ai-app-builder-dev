from __future__ import annotations

from importlib.resources import files

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response


router = APIRouter()


def _load_dashboard_html() -> str:
    template = files("app.platform.api.templates").joinpath("app_build_dashboard.html")
    return template.read_text(encoding="utf-8")


def _load_dashboard_css() -> str:
    template = files("app.platform.api.templates").joinpath("app_build_dashboard.css")
    return template.read_text(encoding="utf-8")


@router.get("/dashboard", response_class=HTMLResponse)
def app_build_dashboard():
    """Serve the browser dashboard shell.

    Sensitive dashboard actions remain protected by API endpoints using
    require_platform_admin. The HTML shell must be loadable after browser
    login because normal page navigation cannot attach Authorization headers.
    """
    return HTMLResponse(_load_dashboard_html())


@router.get("/dashboard.css")
def app_build_dashboard_css():
    return Response(_load_dashboard_css(), media_type="text/css")
