from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.api.dependencies import get_current_user
from app.models.user import User
from app.platform.saas_builder.service import build_status, create_build, delete_build, get_build
from app.platform.saas_builder.ui import render_builder


router = APIRouter()


@router.get("/saas-builder", response_class=HTMLResponse)
def builder_page():
    return render_builder()


@router.get("/api/saas-builder")
def capability():
    return build_status()


@router.post("/api/saas-builder/builds")
def start_build(payload: dict, user: User = Depends(get_current_user)):
    return create_build(payload, user)


@router.get("/api/saas-builder/builds/{workflow_run_id}")
def inspect_build(workflow_run_id: str, user: User = Depends(get_current_user)):
    return get_build(workflow_run_id, user)


@router.delete("/api/saas-builder/builds/{workflow_run_id}")
def teardown_build(workflow_run_id: str, user: User = Depends(get_current_user)):
    return delete_build(workflow_run_id, user)
