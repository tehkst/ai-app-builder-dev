from app.langgraph_app.state import AppBuilderState


async def intake_node(state: AppBuilderState) -> AppBuilderState:

    raw_prompt = state.get("raw_prompt", "")

    questions = [
        "Who are the users of this app?",
        "What is the main goal of the app?",
        "Does the app require login and authentication?",
        "Does the app require payments?",
        "Does the app require admin dashboards?",
    ]

    state["clarifying_questions"] = questions
    state["current_step"] = "intake_completed"

    return state
