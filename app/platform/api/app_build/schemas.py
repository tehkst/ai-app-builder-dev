from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AppBuildRunRequest(BaseModel):
    app_request: str = Field(..., min_length=1)
    workflow_name: Optional[str] = None
    real_bridge: bool = False


class RestoreApprovalDecisionRequest(BaseModel):
    approver_id: str = "platform_admin"
    decision_note: Optional[str] = None


class GeneratedFileContentUpdateRequest(BaseModel):
    content_preview: str = ""
    editor_id: str = "platform_admin"
