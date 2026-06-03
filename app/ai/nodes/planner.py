from app.ai.llm import invoke_llm
from app.ai.state import ProjectState


def planner_node(state: ProjectState) -> ProjectState:

    prompt = f"""
    You are an expert software architect.

    Analyze this software request:

    {state['raw_prompt']}

    Produce:
    - app type
    - frontend stack
    - backend stack
    - database
    - key features
    - api modules
    - pages required
    """

    response = invoke_llm(
        prompt,
        node_name="planner",
        project_id=state.get("project_id"),
        metadata={
            "current_step": state.get("current_step"),
        },
    )

    return {
        **state,
        "architecture_plan": {
            "plan": response.content
        },
        "current_step": "planning_completed"
    }
