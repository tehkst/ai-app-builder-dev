# Split from the legacy module to keep each Python file under 200 lines.
from typing import Dict, List
from app.ai.llm import invoke_node_llm
from app.ai.state import ProjectState

def normalize_review_feedback(feedback: str) -> str:
    return (
        feedback
        .replace("*", "")
        .replace("`", "")
        .strip()
        .lower()
    )

def detect_security_features(files: List[Dict]) -> Dict:
    combined_text = "\n\n".join(
        file.get("content", "")
        for file in files
    )

    has_rate_limiting = (
        "slowapi" in combined_text
        and "limiter.limit" in combined_text
    )

    has_require_role = "def require_role" in combined_text

    has_blind_rbac = (
        has_require_role
        and "return True" in combined_text
        and "Membership.role.in_" not in combined_text
    )

    has_membership_rbac = (
        has_require_role
        and "Membership.role.in_" in combined_text
        and "HTTPException(status_code=403" in combined_text
    )

    return {
        "rate_limit_present": has_rate_limiting,
        "rbac_present": has_require_role,
        "blind_rbac_present": has_blind_rbac,
        "membership_rbac_present": has_membership_rbac,
    }
