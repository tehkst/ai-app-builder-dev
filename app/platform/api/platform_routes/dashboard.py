from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter()
REPAIR_DASHBOARD_TEMPLATE = Path(__file__).with_name("repair_dashboard.html")


@router.get("/dashboard/repair", response_class=HTMLResponse)
def repair_dashboard():
    html = REPAIR_DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
    return HTMLResponse(html)
