from typing import TypedDict, Optional, Dict, Any


MAX_FIX_ATTEMPTS = 0
MAX_RUNTIME_FIX_ATTEMPTS = 1


class ProjectState(TypedDict, total=False):

    project_id: str

    raw_prompt: str

    architecture_plan: Dict[str, Any]

    dependency_report: Dict[str, Any]
    generated_backend_code: str
    generated_frontend_code: str

    interface_contract: Dict[str, Any]
    file_plan: Dict[str, Any]
    file_manifest: Dict[str, Any]
    generated_files: Dict[str, str]

    workspace_isolation_report: Dict[str, Any]

    review_feedback: str
    review_status: str

    runtime_report: Dict[str, Any]
    runtime_error_analysis: Dict[str, Any]
    runtime_fix_attempts: int

    fix_attempts: int

    approval_required: bool
    approved: bool
    approval_type: str

    current_step: str

    errors: Optional[str]

    contract_report: Dict[str, Any]
