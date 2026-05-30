from app.ai.state import ProjectState


def approval_node(state: ProjectState) -> ProjectState:
    return {
        **state,
        "approval_required": True,
        "approved": False,
        "approval_type": "generated_app",
        "current_step": "waiting_for_human_approval",
    }
