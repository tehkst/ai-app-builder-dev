from __future__ import annotations

from app.platform.executive_office.service import build_executive_briefing


def main() -> None:
    briefing = build_executive_briefing()
    assert briefing["company"] == "AI Software Factory"
    assert briefing["source"] == "executive_intelligence"
    assert briefing["platform_health"]["source"] == "platform_health"
    assert briefing["next_focus"]["source"] in {"executive_state", "mission_pipeline", "github_api"}
    assert "Mission Control" in briefing["headline"]
    print("EXECUTIVE OFFICE CHECK PASSED")


if __name__ == "__main__":
    main()
