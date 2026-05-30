from typing import TypedDict, List, Dict, Any, Optional


class AppBuilderState(TypedDict, total=False):
    # Core Project Info
    project_id: str
    user_id: str
    organization_id: str

    # User Prompt
    raw_prompt: str

    # Clarification Phase
    clarifying_questions: List[str]
    answers: Dict[str, Any]

    # Product Definition
    product_spec: Dict[str, Any]

    # Architecture
    architecture_plan: Dict[str, Any]

    # Generated Code
    generated_files: List[Dict[str, str]]

    # QA + Security
    qa_report: Dict[str, Any]
    security_report: Dict[str, Any]

    # Approval System
    approval_required: bool
    approval_type: Optional[str]
    approved: bool
    
    # Error Tracking
    errors: List[str]

    # Workflow Tracking
    current_step: str
