from app.langgraph_app.state import AppBuilderState


async def approval_node(state: AppBuilderState) -> AppBuilderState:

    state["approval_required"] = True

    state["current_step"] = (
        f"waiting_for_{state.get('approval_type')}_approval"
    )

    return state
