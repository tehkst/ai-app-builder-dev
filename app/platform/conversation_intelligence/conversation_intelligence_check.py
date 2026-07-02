from __future__ import annotations

from app.platform.conversation_intelligence.service import analyze_conversation, build_conversation_intelligence_summary


def main() -> None:
    summary = build_conversation_intelligence_summary()
    assert summary["milestone"] == "CI-01"
    assert summary["status"] == "conversation-intelligence-ready"

    payload = {
        "message": "Review the current Mission Control architecture. Audit duplicate Board Room implementations. After my approval, execute through GitHub using small reviewable PRs. Do not modify login or authentication."
    }
    result = analyze_conversation(payload)
    ci = result["conversation_intelligence"]
    assert ci["mode"] in {"Engineering Mission", "Architecture", "Review", "Deployment"}
    assert ci["mission_required"] is True
    assert ci["decisions"]
    assert ci["actions"]
    assert ci["knowledge"]
    assert ci["mission_suggestion"]["suggested"] is True

    general = analyze_conversation({"message": "Explain how this works."})["conversation_intelligence"]
    assert general["mode"] == "Knowledge"
    assert general["mission_required"] is False

    print("CONVERSATION INTELLIGENCE CHECK PASSED")


if __name__ == "__main__":
    main()
