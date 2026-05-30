from app.ai.state import ProjectState


def human_review_node(state: ProjectState) -> ProjectState:
    return {
        **state,
        "approval_required": True,
        "approval_type": "human_review_required",
        "approved": False,
        "current_step": "human_review_required",
    }
