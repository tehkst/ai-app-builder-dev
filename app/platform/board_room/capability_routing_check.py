from __future__ import annotations

from unittest.mock import patch

from app.platform.board_room.capability_router import CapabilityRouter
from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.operating_console.service import board_room_chat


PROMPTS = {
    "How should we improve the UI?": ("executive_intelligence", {"executive_intelligence", "capability_intelligence", "repository_intelligence", "architecture_intelligence"}),
    "Determine whether the Coding Agent exists.": ("capability_intelligence", {"capability_intelligence", "repository_intelligence", "architecture_intelligence"}),
    "Review repository health.": ("repository_intelligence", {"repository_intelligence", "health"}),
    "What should we build next?": ("executive_intelligence", {"executive_intelligence", "mission_history"}),
    "Review deployment.": ("deployment", {"deployment", "production_verification"}),
}


def main() -> None:
    router = CapabilityRouter()
    for prompt, (primary, expected) in PROMPTS.items():
        decomposition = RequestDecomposer().decompose(prompt)
        route = router.route(prompt, decomposition)
        assert route["llm_stage"] == "last"
        assert route["platform_match"] is True
        assert route["primary_capability"] == primary, (prompt, route["primary_capability"])
        assert expected.issubset(set(route["selected_sources"])), (prompt, route["selected_sources"])
        assert route["capability_context"]["read_only"] is True

    with patch("app.platform.operating_console.service.require_founder", return_value={"authorized": True}), patch(
        "app.platform.operating_console.service.invoke_ai",
        return_value={"status": "completed", "output_text": "Evidence-derived executive response."},
    ):
        responses = {prompt: board_room_chat({"message": prompt}) for prompt in PROMPTS}

    generic = {
        "What outcome would you like to improve, and what would success look like?",
        "I’m with you. What would you like to work through?",
    }
    for prompt, response in responses.items():
        assert response["board_room_response"] not in generic, prompt
        assert response["capability_route"]["platform_match"] is True
        assert response["capability_route"]["llm_stage"] == "last"
        assert response["governance"]["execution_allowed"] is False

    coding = responses["Determine whether the Coding Agent exists."]["board_room_response"]
    assert "first-party platform evidence" in coding
    assert "distributed across several components" in coding
    assert "Architecture Intelligence" in coding
    repository = responses["Review repository health."]["board_room_response"]
    assert "Repository Intelligence" in repository and "Health" in repository
    deployment = responses["Review deployment."]["board_room_response"]
    assert "Deployment" in deployment and "Production Verification" in deployment
    print("Board Room capability routing checks passed")


if __name__ == "__main__":
    main()
