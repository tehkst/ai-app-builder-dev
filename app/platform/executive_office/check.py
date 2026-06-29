from __future__ import annotations

from app.platform.executive_office.service import build_executive_briefing


def main() -> None:
    briefing = build_executive_briefing()
    assert briefing["company"] == "AI Software Factory"
    assert briefing["environment"] in {"dev", "staging", "production"}
    assert briefing["platform_health"] == "healthy"
    assert len(briefing["metrics"]) >= 4
    assert len(briefing["decisions"]) >= 3
    assert "Mission Control" in briefing["headline"]
    print("EXECUTIVE OFFICE CHECK PASSED")


if __name__ == "__main__":
    main()
